"""One normalized, temporally correct TradeScor decision contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from analysis.asset_rules import asset_rules
from analysis.amd_engine import analyze_amd, normalized_amd
from analysis.auto_strategy_router import route_auto
from analysis.candle_bundle import build_candle_bundle, bundle_contract
from analysis.market_features import calculate_market_features
from analysis.ict_consistency_validator import validate_ict_consistency
from analysis.m5_execution_engine import build_m5_execution_plan
from analysis.regime_classifier import classify_regime
from analysis.top_down_engine import analyze_top_down_market
from analysis.trade_chart import build_trade_chart
from analysis.execution_state import normalize_execution_state
from analysis.liquidity_target_engine import build_liquidity_targets
from analysis.setup_recovery import apply_setup_recovery
from analysis.market_presentation import build_market_presentation
from analysis.directional_structure import analyze_directional_structure
from evidence.performance_registry import PerformanceRegistry
from strategies.ict_2022_v2 import analyze_ict_2022_v2
from analysis.derived_family_classifier import classify_derived_family
from analysis.synthetic_volatility import synthetic_volatility_profile
from analysis.synthetic_spike_detector import detect_synthetic_spike


STAGE_BY_STATE = {
    "waiting_for_zone": "waiting_for_m15_area", "in_zone": "in_m15_area", "waiting_for_trigger": "m5_setup_forming",
    "trigger_forming": "waiting_for_m5_close", "trigger_confirmed": "m5_confirmed", "entry_valid": "entry_available",
    "entry_extended": "entry_extended", "too_late": "too_late", "invalidated": "invalidated", "unavailable": "waiting_for_m15_area",
}
EXECUTION_STATE = {
    "waiting_for_zone": "waiting_for_m15_area", "in_zone": "in_m15_area", "waiting_for_trigger": "m5_setup_forming",
    "trigger_forming": "waiting_for_m5_close", "trigger_confirmed": "m5_confirmed", "entry_valid": "entry_available",
    "entry_extended": "entry_extended", "too_late": "too_late", "invalidated": "invalidated", "unavailable": "waiting_for_m15_area",
}


def build_decision(
    *, symbol: str, asset_class: str, display_timeframe: str,
    candles_by_timeframe: dict[str, pd.DataFrame], analysis_timestamp: object,
    requested_strategy: str = "auto", session: dict[str, object] | None = None,
    filters: dict[str, object] | None = None, spread: object = 0,
    minimum_rr: float = 1.5, execution_mode: str = "conservative",
    time_metadata: dict[str, object] | None = None,
    evidence_registry: PerformanceRegistry | None = None,
    asset_metadata: dict[str,object] | None = None,
) -> dict[str, object]:
    """Build the sole authoritative decision used by API, UI, and backtests."""
    now = _utc(analysis_timestamp)
    rules = asset_rules(symbol, asset_class)
    bundle = build_candle_bundle(symbol=symbol, asset_class=asset_class, analysis_time=now, candles_by_timeframe=candles_by_timeframe, metadata=time_metadata or {})
    synchronized = {timeframe: row["candles"] for timeframe, row in bundle["timeframes"].items()}
    # Preserve the live M5 candle for forming-state detection; confirmed events
    # still use completed candles inside the execution engine.
    synchronized["M5"] = bundle["timeframes"]["M5"]["available_candles"]
    features = calculate_market_features(bundle)
    regime = classify_regime(features)
    top_down = analyze_top_down_market(symbol=symbol, candles_by_timeframe=synchronized, analysis_timestamp=now)
    market_filters = filters or {}
    amd_context = analyze_amd(symbol=symbol, asset_class=asset_class, analysis_time=now, m5_candles=synchronized.get("M5", pd.DataFrame()), top_down=top_down, filters=market_filters, session=session or {})
    strict_ict = analyze_ict_2022_v2(symbol=symbol, asset_class=asset_class, bundle=bundle, top_down=top_down, analysis_time=now, spread=spread, filters=market_filters, session=session or {}, minimum_rr=minimum_rr, execution_mode=execution_mode, amd=amd_context)
    derived_family=classify_derived_family(asset_metadata or {"provider_symbol":symbol}) if asset_class=="derived_index" else None
    synthetic_volatility=synthetic_volatility_profile(synchronized.get("M15",pd.DataFrame()),tick_size=float(rules.get("tick_size",.01)),family=derived_family["family"]) if derived_family else None
    spike_state=detect_synthetic_spike(synchronized.get("M5",pd.DataFrame()),family=derived_family["family"],atr=synthetic_volatility.get("atr")) if derived_family else None
    research_router = route_auto(symbol=symbol, asset_class=asset_class, regime=regime, features=features, top_down=top_down, session=session or {}, execution_mode=execution_mode, registry=evidence_registry, amd=amd_context, ict_model=strict_ict, spread=spread, derived_family=derived_family, spike_state=spike_state)
    selected_candidate = research_router.get("selected_candidate")
    requested_key = str(requested_strategy or "auto").lower()
    if requested_key != "auto":
        manual=[row for row in research_router["candidates"] if row["strategy_id"]==requested_key and row["eligible"]]; selected_candidate=max(manual,key=lambda row:(row.get("candidate_score",0),row.get("present_quality_score",0)),default=None)
    routing = {"selected_strategy": selected_candidate["strategy_id"] if selected_candidate else "", "market_condition": regime["regime"], "reason": research_router["selection_reason"] if requested_key == "auto" else f"Manual {requested_key} candidate remains subject to eligibility and M5 risk gates.", "eligible_strategies": research_router["eligible_strategies"], "evidence_status": research_router["evidence_status"]}
    if selected_candidate:
        top_down = _top_down_for_candidate(top_down, selected_candidate)
    m5 = synchronized.get("M5", pd.DataFrame())
    current = _last_available_close(m5, now)
    execution_minimum_rr=max(float(minimum_rr),float((selected_candidate or {}).get("minimum_rr",minimum_rr)))
    execution = build_m5_execution_plan(
        top_down_analysis=top_down, m5_candles=m5, analysis_timestamp=now, current_price=current,
        spread=spread, asset_type=asset_class, news_filters=market_filters,
        session_context=session or {}, minimum_rr=execution_minimum_rr, mode=execution_mode,
    )
    amd_context = analyze_amd(symbol=symbol, asset_class=asset_class, analysis_time=now, m5_candles=m5, top_down=top_down, execution=execution, filters=market_filters, session=session or {})
    setup_source = top_down.get("m15_setup") or {}
    zone_source = setup_source.get("zone") if setup_source.get("enabled") else None
    direction = str((top_down.get("alignment") or {}).get("primary_direction", "neutral"))
    if not routing["selected_strategy"]:
        direction = "neutral"
        execution = _unavailable_execution(execution)
    setup_strategy_identity = f"{routing['selected_strategy']}:{(selected_candidate or {}).get('strategy_version', '')}"
    setup_id = _setup_id(symbol, direction, setup_strategy_identity, zone_source, setup_source.get("setup_type")) if zone_source else None
    raw_state = str(execution.get("state", "unavailable"))
    stage = STAGE_BY_STATE.get(raw_state, "none") if setup_id else "none"
    trade_valid = raw_state == "entry_valid" and _valid_plan(execution, minimum_rr)
    data_quality, data_rejections = _data_quality(synchronized, time_metadata or {}, top_down)
    if bundle["data_quality"] == "invalid":
        data_quality = "invalid"
    elif bundle["warnings"] and data_quality == "valid":
        data_quality = "partial"
    filter_rejections = _filter_rejections(asset_class, session or {}, market_filters)
    rejection_reasons = data_rejections + filter_rejections
    if data_quality == "invalid" or filter_rejections:
        trade_valid = False
    score, components = _quality_score(top_down, setup_source, execution, data_quality, trade_valid)
    confidence = _confidence(top_down, stage, trade_valid, data_quality)
    status = _status(direction, trade_valid, bool(setup_id), rejection_reasons, raw_state)
    if status == "NO VALID SETUP" and raw_state not in {"too_late", "invalidated"} and rejection_reasons:
        direction = "neutral"
    setup = _setup_contract(setup_id, direction, routing, setup_source, execution, stage, now)
    execution_contract = _execution_contract(direction, execution, trade_valid)
    user_output = _user_output(status, direction, execution_contract, setup, rejection_reasons, routing, research_router)
    overlays = _overlays(setup, execution_contract, trade_valid)
    cutoffs = {tf: (top_down.get("timeframes") or {}).get(tf, {}).get("last_closed_candle_time") for tf in ("D1", "H4", "H1", "M15", "M5")}
    decision_seed = {"symbol": symbol, "time": now.isoformat(), "setup": setup_id, "state": execution_contract["state"]}
    result = {
        "decision_id": _stable_id("decision", decision_seed), "symbol": symbol, "asset_class": asset_class,
        "analysis_time": now.isoformat(), "display_timeframe": display_timeframe, "setup_timeframe": "M15", "execution_timeframe": "M5",
        "regime": regime,
        "market_regime": {"value": regime["regime"].lower(), "confidence": regime["confidence"], "reason": " ".join(regime["evidence"])},
        "top_down": _top_down_contract(top_down, execution), "alignment": top_down.get("alignment") or {"state": "mixed", "primary_direction": "neutral", "message": ""},
        "router": research_router, "directional_candidates":research_router["directional_candidates"], "directional_audit":_directional_audit(top_down,research_router,selected_candidate), "strategy_routing": routing, "primary_strategy": routing["selected_strategy"] or None, "supporting_strategies": research_router.get("supporting_strategies", []), "primary_candidate": selected_candidate, "setup": setup, "execution": execution_contract,
        "quality": {"score": score, "components": components, "confidence": confidence, "data_quality": data_quality, "trade_plan_valid": trade_valid, "rejection_reasons": rejection_reasons},
        "filters": {"session": session or {}, "news": market_filters.get("news_risk", {}), "dxy": market_filters.get("dxy_confirmation", {})},
        "asset_rules": rules, "candle_bundle": bundle_contract(bundle), "market_features": features, "candle_cutoffs": cutoffs, "time_metadata": time_metadata or {},
        "amd": normalized_amd(amd_context), "amd_result": _amd_result(amd_context), "breakout_retest_result": _breakout_result(selected_candidate, execution, current), "research_shadow": {"ict_2022_v2": strict_ict}, "configuration_hash": strict_ict["configuration_hash"], "user_output": user_output, "overlays": overlays,
    }
    if selected_candidate and selected_candidate.get("strategy_id")=="breakout_retest" and not trade_valid:
        side="BUY" if direction=="buy" else "SELL"
        result["user_output"].update({"status":f"POTENTIAL {side} RETEST","direction":"Long" if direction=="buy" else "Short","execution_stage":result["breakout_retest_result"]["state"],"next_action":result["breakout_retest_result"].get("message")})
        if selected_candidate.get("relationship")=="countertrend_breakout": result["quality"]["confidence"]="low"
    if requested_key == "ict_2022":
        ict = strict_ict
        validation = validate_ict_consistency(ict)
        ict["validation"] = validation
        if not validation["valid"]:
            ict["user_output"]["status"] = validation["downgrade_status"]
            ict["user_output"]["why"] = [*ict["user_output"]["why"], *validation["failures"]]
            ict["quality"].update({"trade_plan_valid": False, "confidence": "low"})
            ict["execution"].update({"entry": None, "stop": None, "targets": [], "remaining_rr": None})
        _apply_manual_ict_v2(result, ict)
    if "liquidity_targets" not in result:
        _apply_liquidity_targets(result,symbol,asset_class,synchronized,now,spread,minimum_rr)
    normalize_execution_state(result,current_price=current,minimum_rr=minimum_rr,tolerance=float(rules["tick_size"])/2)
    if selected_candidate and selected_candidate.get("strategy_id")=="breakout_retest" and result["execution"]["state"]!="entry_available":
        side="BUY" if direction=="buy" else "SELL"; br=result["breakout_retest_result"]
        result["user_output"].update({"status":f"POTENTIAL {side} RETEST","direction":"Long" if direction=="buy" else "Short","execution_stage":br["state"],"next_action":br.get("message")})
        if selected_candidate.get("relationship")=="countertrend_breakout": result["quality"]["confidence"]="low"
    m5_atr=((((features.get("timeframes") or {}).get("M5") or {}).get("atr") or {}).get("value"))
    apply_setup_recovery(result,current_price=current,analysis_time=now,asset_rules=rules,m5_atr=m5_atr)
    result["directional_structure"]=analyze_directional_structure(m5_candles=m5,analysis_time=now,features=features,top_down=top_down,asset_rules=rules,current_price=current)
    top_down["directional_structure"]=result["directional_structure"]
    build_market_presentation(result,top_down=top_down,features=features,current_price=current)
    if requested_key=="ict_2022" and synchronized.get("M5",pd.DataFrame()).empty:
        action=str((result.get("user_output") or {}).get("next_action") or "Wait for completed M5 confirmation.")
        if "Load valid M5 data" not in action:result["user_output"]["next_action"]=f"Load valid M5 data, then {action[0].lower()+action[1:]}"
    result["m15_setup_zone"]={key:(result.get("setup") or {}).get("zone",{}).get(key) for key in ("low","high","type")}
    result["m5_execution_zone"]=(result.get("execution") or {}).get("m5_execution_zone") or {"low":None,"high":None,"type":""}
    result["confirmed_entry"]=(result.get("execution") or {}).get("confirmed_entry") or {"price":None,"confirmed_at":None,"trigger_price":None,"trigger_close":None}
    result["trade_chart"] = build_trade_chart(result, current_price=current, asset_rules=rules)
    if derived_family:
        result["market"]={"provider":"deriv","asset_class":"derived_index","market_schedule":"24_7","market_open":True,"family":derived_family["family"],"paper_analysis_only":True}
        result["derived_index"]={"rules":rules,"family":derived_family,"volatility":synthetic_volatility,"spike":spike_state,"execution_timeframe":"M5"}
    return result


def _apply_liquidity_targets(decision,symbol,asset_class,frames,now,spread,minimum_rr):
    setup=decision.get("setup") or {}; execution=decision.get("execution") or {}; zone=setup.get("zone") or {}; direction=setup.get("direction"); low,high=_number(zone.get("low")),_number(zone.get("high")); entry=_number(execution.get("entry")); reference=entry if entry is not None else (low+high)/2 if low is not None and high is not None else None; stop=_number(execution.get("stop")) or _number((setup.get("invalidation") or {}).get("price"))
    engine=build_liquidity_targets(symbol=symbol,asset_class=asset_class,direction=direction,entry_price=reference,stop_price=stop,candles_by_timeframe=frames,decision_timestamp=now,higher_timeframe_draw=direction,strategy=setup.get("strategy") or decision.get("primary_strategy") or "auto",spread=spread,preferred_rr=minimum_rr)
    selected=[row for row in (engine["selected_targets"].get(key) for key in ("tp1","tp2","tp3")) if row]; decision["liquidity_targets"]=engine; execution["projected_targets"]=selected
    if entry is not None and _number(execution.get("stop")) is not None:
        execution["targets"]=selected if engine["quality_gate"]["passed"] else []; execution["risk_reward"]=(selected[0].get("risk_reward") if selected and engine["quality_gate"]["passed"] else None); decision["quality"]["trade_plan_valid"]=bool(selected and engine["quality_gate"]["passed"])
    decision["execution"]=execution

def _amd_result(amd):
    accepted=amd.get("boundary_event")=="accepted_breakout"
    return {"eligible":bool((amd.get("validation") or {}).get("valid_cycle")),"state":"failed" if accepted else str((amd.get("phase") or {}).get("current","searching")),"failure_reason":"accepted_breakout" if accepted else None,"boundary_event":amd.get("boundary_event")}

def _breakout_result(candidate,execution,current):
    if not candidate or candidate.get("strategy_id")!="breakout_retest": return {"eligible":False,"state":"not_selected"}
    zone=candidate.get("zone") or {}; low=_number(zone.get("low")); high=_number(zone.get("high")); direction=candidate.get("direction"); price=_number(current)
    inside=price is not None and low is not None and high is not None and low<=price<=high
    confirmed=bool(execution.get("confirmed_signal")); state="CONFIRMED" if confirmed else "RETEST_IN_PROGRESS" if inside else "WAITING_FOR_RETEST"
    boundary=_number((candidate.get("breakout") or {}).get("boundary"))
    return {"eligible":bool(candidate.get("eligible")),"state":state,"locked_range":candidate.get("locked_range"),"breakout":candidate.get("breakout"),"retest_zone":zone,"retest":{"touched":inside or execution.get("state") not in {"waiting_for_zone","unavailable"},"held":confirmed,"failed":execution.get("state")=="invalidated"},"confirmation":{"price":execution.get("trigger") if confirmed else None,"time":((execution.get("confirmed_signal") or {}).get("candle_time") if confirmed else None)},"higher_timeframe_direction":candidate.get("higher_timeframe_direction"),"local_setup_direction":direction,"relationship":candidate.get("relationship"),"primary_actionable_direction":direction if execution.get("state")=="entry_valid" else "neutral","minimum_rr":candidate.get("minimum_rr"),"message":f"Price is above the retest area. Wait for a pullback toward {boundary:.5f}. Do not buy at the current price." if direction=="buy" and state=="WAITING_FOR_RETEST" and boundary is not None else f"Price is below the retest area. Wait for a pullback toward {boundary:.5f}. Do not sell at the current price." if direction=="sell" and state=="WAITING_FOR_RETEST" and boundary is not None else execution.get("message")}


def _directional_audit(top_down,router,selected):
    frames=top_down.get("timeframes") or {}; setup=top_down.get("m15_setup") or {}; candidates=router.get("directional_candidates") or {}
    evidence={timeframe:{"direction":(frames.get(timeframe) or {}).get("bias","neutral"),"structure":(frames.get(timeframe) or {}).get("structure"),"last_closed_candle":(frames.get(timeframe) or {}).get("last_closed_candle_time")} for timeframe in ("D1","H4","H1")}
    evidence["M15"]={"direction":setup.get("direction","neutral"),"structure":setup.get("setup_type"),"zone":setup.get("zone")}; evidence["M5"]={"direction":selected.get("direction") if selected else "neutral","structure":"execution pending" if selected else "no selected execution"}
    return {"timeframes":evidence,"buy_candidates_found":((candidates.get("buy") or {}).get("diagnostics") or {}).get("candidates_found",0),"sell_candidates_found":((candidates.get("sell") or {}).get("diagnostics") or {}).get("candidates_found",0),"buy_candidates_rejected":((candidates.get("buy") or {}).get("diagnostics") or {}).get("rejected_count",0),"sell_candidates_rejected":((candidates.get("sell") or {}).get("diagnostics") or {}).get("rejected_count",0),"best_buy":candidates.get("buy"),"best_sell":candidates.get("sell"),"final_selection":{"direction":selected.get("direction") if selected else "neutral","strategy":selected.get("strategy_id") if selected else None,"reason":router.get("selection_reason"),"conflict":router.get("conflict",False)}}


def _top_down_for_candidate(top_down: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    """Map a locked normalized M15 candidate into the shared M5 executor."""
    copied = {**top_down, "m15_setup": dict(top_down.get("m15_setup") or {})}
    zone = candidate.get("zone") or {}
    if zone.get("low") is None or zone.get("high") is None:
        copied["m15_setup"]["enabled"] = False
        return copied
    copied["m15_setup"].update({"enabled": True, "direction": candidate["direction"], "setup_type": candidate["setup_type"], "zone_low": zone["low"], "zone_high": zone["high"], "zone": {"low": zone["low"], "high": zone["high"], "failure_boundary": zone.get("failure_boundary"), "type": zone.get("type", ""), "label": "Retest Area" if candidate["strategy_id"] == "breakout_retest" else candidate["strategy_id"].replace("_", " ").title(), "start_time": zone.get("origin_time"), "valid_after": zone.get("valid_after")}, "status": "in_zone" if candidate["stage"] == "in_area" else "watching", "confirmation_hint": "Require a retest before completed M5 confirmation." if candidate["strategy_id"] == "breakout_retest" else "Require the selected strategy's completed M5 confirmation sequence.", "invalidation_context": "Invalid beyond locked M5 execution structure.", "countertrend": False})
    copied["alignment"] = {**(copied.get("alignment") or {}), "primary_direction": candidate["direction"]}
    return copied


def _apply_manual_ict(decision: dict[str, object], ict: dict[str, object]) -> None:
    """Make manual ICT context authoritative without pretending it is eligible."""
    context = ict["ict_context"]; direction = context["direction"]
    decision.update({"requested_strategy": "ict_2022", "ict_context": context, "ict_eligibility": ict["ict_eligibility"], "sequence": ict["sequence"], "sequence_events": ict["sequence_events"], "ict_checklist": ict["checklist"], "ict_validation": ict["validation"], "primary_strategy": "ict_2022", "primary_candidate": decision.get("primary_candidate") if ict["ict_eligibility"]["eligible"] else None})
    decision["quality"].update({"score": ict["score"], "confidence": ict["confidence"], "trade_plan_valid": ict["status"] in {"READY TO BUY", "READY TO SELL"}})
    decision["execution"] = {"state": ict["execution"]["state"], "direction": direction, "timeframe": "M5", "available": ict["execution"]["available"], "execution_available": ict["execution"]["available"], "blocker": ict["execution"]["blocker"], "execution_blocker": ict["execution"]["execution_blocker"], "entry": ict["execution"]["entry"], "entry_zone": None, "stop": ict["execution"]["stop"], "targets": ict["execution"]["targets"], "risk_reward": ict["execution"]["remaining_rr"], "entry_distance": None, "message": ict["next_action"], "forming_state": None, "confirmed_state": (decision.get("execution") or {}).get("confirmed_state") if ict["sequence"]["m5_confirmation"] == "pass" else None}
    zone = context.get("zone") or {}
    decision["setup"] = {**decision["setup"], "setup_id": decision["setup"].get("setup_id") if ict["ict_eligibility"]["eligible"] else None, "context_id": context.get("context_id"), "direction": direction, "strategy": "ict_2022", "type": "ict_precision", "stage": ict["ict_eligibility"]["state"], "zone": {"low": zone.get("low"), "high": zone.get("high"), "type": zone.get("type", ""), "origin_time": _iso(zone.get("start_time"))}, "confirmation": {"price": None, "type": "m5_ict_sequence", "confirmed": ict["sequence"]["m5_confirmation"] == "pass", "confirmed_time": ict["sequence_events"]["m5_confirmation"]["timestamp"]}, "invalidation": {"price": ict["execution"]["stop"], "type": "m5_execution_structure" if ict["execution"]["stop"] is not None else ""}, "confirmation_hint": ict["next_action"], "invalidation_context": ""}
    decision["overlays"] = ict["overlays"]
    decision["user_output"] = {"status": ict["status"], "direction": ict["direction_label"], "requested_strategy": "ICT Precision", "strategy_used": "ICT Precision", "strategy_label": ict["strategy_label"], "eligibility": "Eligible" if ict["ict_eligibility"]["eligible"] else "Not yet eligible" if ict["ict_eligibility"]["state"] != "unavailable" else "Unavailable", "reason_strategy_selected": context["reason"], "evidence": "Manual evaluation", "execution_stage": ict["execution"]["state"], "entry_timing": ict["entry_timing"], "next_action": ict["next_action"], "summary": context["summary"], "why": ict["why"]}


def _apply_manual_ict_v2(decision: dict[str, object], ict: dict[str, object]) -> None:
    """Project the frozen v2 research object into the shared decision contract."""
    setup, execution, quality, output = ict["setup"], ict["execution"], ict["quality"], ict["user_output"]
    direction = setup["direction"]; ready = bool(quality["trade_plan_valid"]); legacy_zone=(decision.get("setup") or {}).get("zone") or {}
    m5_available=bool((((decision.get("candle_bundle") or {}).get("timeframes") or {}).get("M5") or {}).get("valid"))
    sequence={**ict["sequence"], "mss_choch": ict["sequence"].get("mss", "waiting")}
    eligibility_state=setup["state"] if setup["setup_id"] else "context_only" if direction in {"buy","sell"} else "unavailable"
    context={**ict["narrative"], "available": direction in {"buy","sell"}, "zone": legacy_zone}
    interaction=setup.get("entry_array_state") or {}; checklist=[{"key":"entry_array_touched","label":"Entry array previously touched","state":"pass" if interaction.get("entry_array_touched") else "waiting"},{"key":"price_in_entry_array","label":"Price returns to entry array","state":"pass" if interaction.get("currently_inside_entry_array") else "waiting"},{"key":"m5_confirmation","label":"M5 confirmation","state":ict["sequence"].get("m5_confirmation","waiting")},{"key":"risk_validation","label":"Stop and RR validation","state":"pass" if ready else "waiting"}]
    decision.update({"requested_strategy": "ict_2022", "ict_model": ict, "ict_context": context, "ict_eligibility": {"eligible": setup["setup_id"] is not None, "state": eligibility_state, "missing_requirements": [key for key, state in ict["sequence"].items() if state != "pass"]}, "sequence": sequence, "sequence_events": ict["sequence_events"], "ict_checklist": checklist, "ict_validation": ict["validation"], "primary_strategy": "ict_2022", "strategy_version": ict["strategy_version"], "configuration_hash": ict["configuration_hash"]})
    decision["quality"].update({"score": quality["sequence_score"], "setup_score":quality["setup_score"], "confidence": quality["confidence"], "trade_plan_valid": ready, "data_quality": quality["data_quality"], "rejection_reasons": execution["rejection_reasons"]})
    blocker=None if m5_available else "missing_m5_data"; confirmed_execution=setup.get("confirmed_execution") or {}; signal=confirmed_execution.get("signal") or {}
    decision["execution"] = {"state": str(confirmed_execution.get("state") or execution["state"]).lower(), "direction": direction, "timeframe": "M5", "available": m5_available, "execution_available": m5_available, "blocker": blocker or (execution["rejection_reasons"][0] if execution["rejection_reasons"] else None), "execution_blocker": blocker or (execution["rejection_reasons"][0] if execution["rejection_reasons"] else None), "entry": confirmed_execution.get("entry"), "m5_execution_zone":confirmed_execution.get("entry_zone"),"entry_zone": confirmed_execution.get("entry_zone"),"confirmed_entry":{"price":confirmed_execution.get("entry"),"confirmed_at":signal.get("candle_time"),"trigger_price":execution.get("trigger"),"trigger_close":signal.get("candle_close")}, "stop": confirmed_execution.get("stop"), "targets": confirmed_execution.get("targets",[]), "risk_reward": confirmed_execution.get("risk_reward"), "entry_distance": confirmed_execution.get("entry_distance"), "message": output["next_action"], "forming_state": None, "confirmed_state": signal if signal.get("completed") else None}
    array = setup.get("entry_array") or {}
    decision["setup"] = {**decision["setup"], "setup_id": setup["setup_id"], "direction": direction, "strategy": "ict_2022", "type": "ict_2022_v2", "stage": setup["state"].lower(), "zone": {"low": array.get("low"), "high": array.get("high"), "type": array.get("type", ""), "origin_time": array.get("formed_at"), "freshness":setup.get("freshness"), "touch_count":interaction.get("touch_count",0)}, "entry_array_state":interaction, "confirmation": {"price": execution["trigger"], "type": "completed_m5_close", "confirmed": execution["confirmed_at"] is not None, "confirmed_time": execution["confirmed_at"]}, "invalidation": {"price": setup.get("invalidation"), "type": "sweep_extreme" if setup.get("invalidation") is not None else ""}, "created_time": setup.get("created_at"), "updated_time": setup.get("updated_at"), "expires_time": setup.get("expires_at"), "confirmation_hint": output["next_action"], "invalidation_context": setup.get("expiration_reason") or ""}
    decision["liquidity_targets"]=setup.get("liquidity_targets") or {"direction":direction,"entry_price":None,"stop_price":None,"candidates":[],"selected_targets":{"tp1":None,"tp2":None,"tp3":None}}
    decision["execution"]["projected_targets"]=[row for row in (decision["liquidity_targets"]["selected_targets"].get(key) for key in ("tp1","tp2","tp3")) if row]
    decision["overlays"] = {"confirmation": None, "invalidation": None, "entry": None, "stop": None, "targets": [], "conditional_arrow": None, **ict["overlays"]}
    if not ready: decision["overlays"].update({"entry":None,"stop":None,"targets":[],"conditional_arrow":None})
    if not m5_available: output["next_action"] = f"Load valid M5 data, then {output['next_action'][0].lower() + output['next_action'][1:]}"
    decision["user_output"] = {**output, "requested_strategy": "ICT Precision", "strategy_used": "ICT Precision", "strategy_label": "ICT Precision v2 — Research", "eligibility": output.get("strategy_eligibility","Eligible" if setup["setup_id"] else "Not yet eligible"), "trade_readiness":output.get("trade_readiness","Ready" if ready else "Not confirmed"), "reason_strategy_selected": "Manual strict ICT 2022 v2 evaluation; core sequence requirements cannot be bypassed.", "evidence": "Research shadow mode", "entry_timing": "Ready" if ready else "Not confirmed"}


def _top_down_contract(top_down: dict[str, object], execution: dict[str, object]) -> dict[str, object]:
    result = {}
    for tf in ("D1", "H4", "H1", "M15", "M5"):
        source = (top_down.get("timeframes") or {}).get(tf) or {}
        result[tf] = {"bias": source.get("bias", "neutral"), "structure": source.get("structure", ""), "last_closed_candle": source.get("last_closed_candle_time")}
    result["M15"]["setup_type"] = (top_down.get("m15_setup") or {}).get("setup_type", "")
    result["M5"]["trigger_state"] = execution.get("state", "unavailable")
    result["M5"]["forming_state"] = execution.get("forming_signal")
    result["M5"]["confirmed_state"] = execution.get("confirmed_signal")
    return result


def _setup_contract(setup_id: str | None, direction: str, routing: dict[str, object], source: dict[str, object], execution: dict[str, object], stage: str, now: pd.Timestamp) -> dict[str, object]:
    zone = source.get("zone") if setup_id else None
    origin = _iso((zone or {}).get("start_time"))
    trigger = execution.get("trigger")
    confirmed = execution.get("confirmed_signal") or {}
    stop = execution.get("stop")
    return {
        "setup_id": setup_id, "direction": direction if setup_id else "neutral", "strategy": routing.get("selected_strategy", ""), "type": source.get("setup_type", "") if setup_id else "", "stage": stage,
        "zone": {"low": _number((zone or {}).get("low")), "high": _number((zone or {}).get("high")), "type": (zone or {}).get("type", ""), "origin_time": origin} if zone else {"low": None, "high": None, "type": "", "origin_time": None},
        "confirmation": {"price": _number(trigger), "type": "m5_closed_structure", "confirmed": bool(confirmed), "confirmed_time": confirmed.get("candle_time")},
        "invalidation": {"price": _number(stop), "type": "m5_execution_structure" if stop is not None else ""},
        "created_time": origin, "updated_time": now.isoformat() if setup_id else None, "expires_time": None,
        "zone_reached_time": _first_touch_time(source, execution), "reaction_time": (execution.get("forming_signal") or {}).get("candle_time"), "entry_time": confirmed.get("candle_time") if execution.get("entry") is not None else None, "invalidation_time": now.isoformat() if stage == "invalidated" else None,
        "confirmation_hint": source.get("confirmation_hint", ""), "invalidation_context": source.get("invalidation_context", ""), "target_context": source.get("target_context", {}),
    }


def _execution_contract(direction: str, source: dict[str, object], valid: bool) -> dict[str, object]:
    signal=source.get("confirmed_signal") or {}; confirmed=bool(signal.get("completed") and signal.get("candle_time") and _number(source.get("entry")) is not None); targets = [{"name": item.get("name"), "price": _number(item.get("price")), "timeframe": item.get("timeframe"), "reason": item.get("reason", ""), "valid": bool(item.get("valid")), "swept": bool(item.get("swept", False)), "risk_reward": item.get("risk_reward")} for item in source.get("targets", []) if _number(item.get("price")) is not None]
    zone=source.get("entry_zone") if confirmed else None; entry=_number(source.get("entry")) if confirmed else None; stop=_number(source.get("stop")) if confirmed else None; rr=_number(source.get("risk_reward")) if confirmed else None
    return {"state": EXECUTION_STATE.get(str(source.get("state")), "waiting_for_m15_area"), "direction": direction, "entry":entry,"m5_execution_zone":zone,"entry_zone":zone,"confirmed_entry":{"price":entry,"confirmed_at":signal.get("candle_time") if confirmed else None,"trigger_price":_number(source.get("trigger")) if confirmed else None,"trigger_close":_number(signal.get("candle_close")) if confirmed else None}, "stop":stop,"targets":targets if confirmed else [],"risk_reward":rr,"entry_distance": _number(source.get("entry_distance")), "message": str(source.get("message", "")), "forming_state": source.get("forming_signal"), "confirmed_state": signal if confirmed else None}


def _quality_score(top_down: dict[str, object], setup: dict[str, object], execution: dict[str, object], data_quality: str, valid: bool) -> tuple[int, dict[str, int]]:
    regime = str((top_down.get("regime") or {}).get("value", "")); alignment = str((top_down.get("alignment") or {}).get("state", "")); state = str(execution.get("state", ""))
    components = {"htf_alignment": 25 if regime in {"bullish", "bearish"} and alignment == "aligned" else 18 if regime in {"bullish", "bearish"} else 0, "m15_location": 20 if setup.get("enabled") and setup.get("zone") else 0, "price_interaction": 15 if state not in {"waiting_for_zone", "unavailable"} else 0, "m5_confirmation": 20 if execution.get("confirmed_signal") else 0, "target_and_rr": 15 if valid else 0, "data_and_filters": 5 if data_quality == "valid" else 2 if data_quality == "partial" else 0}
    score = sum(components.values())
    cap = 100 if valid else 90 if execution.get("confirmed_signal") else 80 if state in {"waiting_for_trigger", "trigger_forming"} else 70 if state == "in_zone" else 60 if setup.get("zone") else 40
    return min(score, cap), components


def _confidence(top_down: dict[str, object], stage: str, valid: bool, data_quality: str) -> str:
    if valid and data_quality == "valid": return "high"
    if data_quality == "invalid" or str((top_down.get("alignment") or {}).get("state")) in {"mixed", "countertrend"}: return "low"
    return "medium" if stage in {"waiting_for_area", "in_area", "reaction_forming", "waiting_for_m5_close", "confirmed"} else "low"


def _status(direction: str, valid: bool, has_setup: bool, rejections: list[str], state: str) -> str:
    if valid: return "READY TO BUY" if direction == "buy" else "READY TO SELL"
    if not has_setup or direction not in {"buy", "sell"} or state in {"too_late", "invalidated", "unavailable"} or rejections: return "NO VALID SETUP"
    return "BUY SETUP FORMING" if direction == "buy" else "SELL SETUP FORMING"


def _user_output(status: str, direction: str, execution: dict[str, object], setup: dict[str, object], rejections: list[str], routing: dict[str, object], router: dict[str, object]) -> dict[str, object]:
    display = "Long" if direction == "buy" else "Short" if direction == "sell" else "Neutral"
    if status.startswith("READY"): next_action = "Review the confirmed M5 trade plan and risk before entry."
    elif status.endswith("SETUP FORMING"): next_action = execution["message"] or "Wait for M5 confirmation."
    else: next_action = rejections[0] if rejections else execution["message"] or "Wait for a complete aligned setup."
    strategy = str(routing.get("selected_strategy") or "")
    evidence = str(router.get("evidence_status", "INSUFFICIENT_EVIDENCE")).replace("_", " ").title()
    return {"status": status, "direction": display, "strategy_used": strategy.replace("_", " ").title() if strategy else "", "reason_strategy_selected": routing.get("reason", ""), "evidence": evidence, "execution_stage": execution["state"], "next_action": next_action, "summary": f"{status.title()} · execution is M5.", "why": [item for item in [routing.get("reason"), setup.get("confirmation_hint"), setup.get("invalidation_context"), *rejections] if item][:3]}


def _overlays(setup: dict[str, object], execution: dict[str, object], valid: bool) -> dict[str, object]:
    zone = setup.get("zone") or {}; has_zone = zone.get("low") is not None and zone.get("high") is not None
    return {"setup_zone": {**zone, "setup_id": setup.get("setup_id")} if has_zone else None, "confirmation": {"price": setup["confirmation"]["price"], "confirmed": setup["confirmation"]["confirmed"]} if setup["confirmation"]["price"] is not None else None, "invalidation": {"price": setup["invalidation"]["price"]} if setup["invalidation"]["price"] is not None else None, "entry": {"price": execution["entry"]} if valid else None, "stop": {"price": execution["stop"]} if valid else None, "targets": execution["targets"] if valid else [], "conditional_arrow": "price_to_setup" if has_zone and not setup["confirmation"]["confirmed"] else "setup_to_confirmation" if has_zone and not valid else None}


def _valid_plan(execution: dict[str, object], minimum_rr: float) -> bool:
    return execution.get("entry") is not None and execution.get("stop") is not None and bool(execution.get("targets")) and (_number(execution.get("risk_reward")) or 0) >= max(1.0, minimum_rr)


def _data_quality(frames: dict[str, pd.DataFrame], metadata: dict[str, object], top_down: dict[str, object]) -> tuple[str, list[str]]:
    missing = [tf for tf in ("D1", "H4", "H1", "M15", "M5") if frames.get(tf) is None or frames.get(tf).empty]
    if missing: return "invalid", [f"Missing required candle data: {', '.join(missing)}."]
    insufficient = [tf for tf in ("D1", "H4", "H1", "M15", "M5") if ((top_down.get("timeframes") or {}).get(tf) or {}).get("structure") == "insufficient_data"]
    if insufficient: return "invalid", [f"Insufficient completed candle history: {', '.join(insufficient)}."]
    if metadata.get("timezone_warning"): return "partial", []
    return "valid", []


def _filter_rejections(asset_class: str, session: dict[str, object], filters: dict[str, object]) -> list[str]:
    result = []
    news = filters.get("news_risk") or {}
    if news.get("restriction_active"): result.append("High-impact news risk currently blocks entry.")
    if asset_class not in {"crypto","derived_index"} and session and not session.get("entry_allowed", True): result.append("The instrument session currently blocks entry timing.")
    return result


def _setup_id(symbol: str, direction: str, strategy: str, zone: dict[str, object], event: object) -> str:
    return _stable_id("setup", {"symbol": symbol, "direction": direction, "strategy": strategy, "origin": zone.get("start_time"), "low": _number(zone.get("low")), "high": _number(zone.get("high")), "event": event})


def _stable_id(prefix: str, value: object) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _unavailable_execution(source: dict[str, object]) -> dict[str, object]:
    return {**source, "state": "unavailable", "direction": "neutral", "entry": None, "entry_zone": None, "stop": None, "targets": [], "risk_reward": None, "message": "No strategy is eligible for the current market condition."}


def _last_available_close(candles: pd.DataFrame, boundary: pd.Timestamp) -> float | None:
    if candles is None or candles.empty: return None
    times = pd.to_datetime(candles["time"], utc=True, errors="coerce")
    rows = candles.loc[times <= boundary]
    return float(rows.iloc[-1]["close"]) if not rows.empty else None


def _first_touch_time(setup: dict[str, object], execution: dict[str, object]) -> str | None:
    signal = execution.get("confirmed_signal") or execution.get("forming_signal") or {}
    return signal.get("candle_time") if setup.get("status") == "in_zone" or execution.get("state") != "waiting_for_zone" else None


def _iso(value: object) -> str | None:
    if value is None: return None
    if isinstance(value, (int, float)): return datetime.fromtimestamp(value, timezone.utc).isoformat()
    try: return _utc(value).isoformat()
    except Exception: return None


def _utc(value: object) -> pd.Timestamp:
    stamp = pd.Timestamp(value if value is not None else datetime.now(timezone.utc))
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


def _number(value: object) -> float | None:
    try: number = float(value)
    except (TypeError, ValueError): return None
    return number if pd.notna(number) else None
