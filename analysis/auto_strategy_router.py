"""Eligibility-first, evidence-aware router for competing strategy experts."""

from __future__ import annotations

import hashlib
import json

from evidence.performance_registry import PerformanceRegistry
from analysis.asset_rules import asset_rules
from strategies.base import empty_candidate


def route_auto(*, symbol: str, asset_class: str, regime: dict[str, object], features: dict[str, object], top_down: dict[str, object], session: dict[str, object], execution_mode: str, registry: PerformanceRegistry | None = None, amd: dict[str, object] | None = None, ict_model: dict[str, object] | None = None, spread: object = 0, derived_family: dict[str,object]|None=None, spike_state:dict[str,object]|None=None) -> dict[str, object]:
    market_regime = str(regime.get("regime", "UNCLEAR")); registry = registry or PerformanceRegistry()
    candidates=[]
    for direction in ("buy","sell"):
        candidates.extend([_supply_candidate(market_regime,features,top_down,direction),_breakout_candidate(symbol,asset_class,market_regime,features,top_down,amd or {},direction,spread),_ict_candidate(asset_class,market_regime,features,top_down,session,amd or {},ict_model,direction)])
    for candidate in candidates:
        if asset_class=="derived_index":
            family=(derived_family or {}).get("family","OTHER_DERIVED"); preferred=(derived_family or {}).get("preferred_strategies",[]); blocked=(derived_family or {}).get("blocked_strategies",[])
            if candidate["strategy_id"] in blocked or (family=="RANGE_BREAK" and candidate["strategy_id"]!="breakout_retest"):
                candidate["eligible"]=False;candidate["rejection_reasons"]=[f"{candidate['strategy_id']} is not eligible for the {family} family."]
            if family in {"BOOM","CRASH"} and (spike_state or {}).get("cooldown_active"):
                candidate["eligible"]=False;candidate["rejection_reasons"]=["Fresh synthetic spike requires recalibration and a new pullback; do not chase."]
            candidate["family_preferred"]=candidate["strategy_id"] in preferred
        candidate["candidate_id"] = "candidate-" + hashlib.sha256(json.dumps({"symbol": symbol, "strategy": candidate["strategy_version"], "direction": candidate["direction"], "zone": candidate["zone"]}, sort_keys=True, default=str).encode()).hexdigest()[:20]
        evidence = registry.lookup({"symbol": symbol, "asset_class": asset_class, "strategy_version": candidate["strategy_version"], "direction": candidate["direction"], "market_regime": market_regime, "volatility_regime": _volatility(features), "setup_type": candidate["setup_type"], "session": session.get("liquidity_window") or session.get("name"), "execution_mode": execution_mode, "execution_timeframe": "M5"})
        candidate["evidence"] = evidence; candidate["evidence_multiplier"] = evidence["multiplier"]
        candidate["candidate_score"] = round(float(candidate["present_quality_score"]) * float(evidence["multiplier"]), 2) if candidate["eligible"] else 0
    eligible = [row for row in candidates if row["eligible"]]
    eligible.sort(key=lambda row: (row["candidate_score"], row["present_quality_score"]), reverse=True)
    selected, disagreement, reason = _resolve(eligible, market_regime)
    grades = {row["evidence"]["evidence_grade"] for row in eligible}
    evidence_status = "INSUFFICIENT_EVIDENCE" if not eligible or grades <= {"NO_EVIDENCE", "INSUFFICIENT"} else "MULTIPLE_PLAUSIBLE_STRATEGIES" if len(eligible) > 1 and abs(eligible[0]["candidate_score"] - eligible[1]["candidate_score"]) < 5 else eligible[0]["evidence"]["evidence_grade"]
    supporting = [row["strategy_id"] for row in eligible if selected and row["strategy_id"] != selected["strategy_id"] and row["direction"] == selected["direction"]]
    directional={side:_directional_contract(side,candidates) for side in ("buy","sell")}
    return {"market_regime": market_regime, "eligible_strategies": list(dict.fromkeys(row["strategy_id"] for row in eligible)), "ineligible_strategies": list(dict.fromkeys(row["strategy_id"] for row in candidates if not row["eligible"])), "candidates": candidates,"directional_candidates":directional,"buy_best_score":directional["buy"]["score"],"sell_best_score":directional["sell"]["score"],"selected_direction":selected["direction"] if selected else "neutral","conflict":disagreement, "selected_strategy": selected["strategy_id"] if selected else None, "selected_candidate": selected, "supporting_strategies": supporting, "selection_confidence": "low" if evidence_status == "INSUFFICIENT_EVIDENCE" else "medium" if evidence_status == "MULTIPLE_PLAUSIBLE_STRATEGIES" else "high", "selection_reason": reason, "evidence_status": evidence_status, "disagreement": disagreement}


def _supply_candidate(regime: str, features: dict[str, object], top_down: dict[str, object], direction=None) -> dict[str, object]:
    row = empty_candidate("supply_demand"); setup = top_down.get("m15_setup") or {}; detected=setup.get("direction","neutral"); direction=direction or detected
    eligible_regimes = {"TRENDING_BULLISH", "TRENDING_BEARISH", "PULLBACK_BULLISH_REGIME", "PULLBACK_BEARISH_REGIME"}
    eligible = regime in eligible_regimes and setup.get("enabled") and direction in {"buy", "sell"} and detected==direction
    quality = 75 if eligible and setup.get("status") == "in_zone" else 62 if eligible else 0
    row.update({"eligible": bool(eligible), "eligibility_score": 85 if eligible else 0, "eligibility_reasons": ["Directional pullback with an active M15 structural zone."] if eligible else [], "rejection_reasons": [] if eligible else ["Supply & Demand requires a clean trend/pullback regime and active zone."], "direction": direction if eligible else "neutral", "setup_type": setup.get("setup_type", ""), "stage": "in_area" if setup.get("status") == "in_zone" else "watching" if eligible else "not_eligible", "zone": _zone(setup), "confirmation_requirements": ["M5 rejection", "M5 displacement", "completed M5 structure close"], "structural_quality": 18 if eligible else 0, "location_quality": 14 if eligible else 0, "confirmation_quality": 0, "target_quality": 10 if setup.get("target_context") else 0, "present_quality_score": quality, "confidence": "medium" if eligible else "low", "status": "watching" if eligible else "not_eligible"})
    row["direction"]=direction; row["diagnostics"]={"detected_direction":detected,"requested_direction":direction,"regime":regime,"zone_type":((setup.get("zone") or {}).get("type")),"failed_requirement":None if eligible else f"No active {'demand' if direction=='buy' else 'supply'} zone aligned with this pipeline."}
    if not eligible:row["rejection_reasons"]=[row["diagnostics"]["failed_requirement"]]
    return row


def _breakout_candidate(symbol: str, asset_class=None, regime=None, features=None, top_down=None, amd=None, requested_direction=None, spread: object = 0) -> dict[str, object]:
    if isinstance(asset_class,dict):
        requested_direction=top_down; amd=features or {}; top_down=regime or {}; features=asset_class; regime=symbol; symbol="TEST"; asset_class="forex"
    row = empty_candidate("breakout_retest"); m15=features["timeframes"].get("M15",{}); range_data=_value(m15,"range") or {}; displacement=_value(m15,"displacement") or {}; compression=(_value(m15,"compression") or {}).get("active")
    event=amd.get("manipulation") or {}; accepted=amd.get("boundary_event")=="accepted_breakout"
    detected="buy" if accepted and event.get("side")=="high" else "sell" if accepted and event.get("side")=="low" else "buy" if displacement.get("active") and displacement.get("direction")=="bullish" else "sell" if displacement.get("active") and displacement.get("direction")=="bearish" else "neutral"
    direction=requested_direction or detected
    eligible=direction in {"buy","sell"} and detected==direction and (accepted or (regime in {"COMPRESSION","RANGING","BREAKOUT_EXPANSION"} and (compression or displacement.get("active")) and range_data.get("boundary_tests",0)>=2))
    locked=amd.get("accumulation") or {}; low=locked.get("range_low",range_data.get("low")); high=locked.get("range_high",range_data.get("high")); boundary=high if direction=="buy" else low if direction=="sell" else None
    rules=asset_rules(symbol,asset_class); atr=float(locked.get("atr") or 0); band=max(atr*.12,float(rules["tick_size"])*3,max(0.0,_number(spread) or 0.0)*2) if boundary is not None else 0
    event_time=event.get("breakout_time") or event.get("sweep_time")
    zone={"low":float(boundary)-band,"high":float(boundary)+band,"failure_boundary":float(boundary),"origin_time":event_time,"valid_after":event_time,"type":"breakout_retest","freshness":"fresh","touch_count":0} if boundary is not None else {"low":None,"high":None,"origin_time":None,"type":"breakout_retest","freshness":"","touch_count":0}
    htf=str((top_down.get("alignment") or {}).get("primary_direction","neutral")); relationship="aligned_breakout" if htf==direction else "countertrend_breakout" if htf in {"buy","sell"} and direction in {"buy","sell"} else "local_breakout"
    breakout={"direction":"bullish" if direction=="buy" else "bearish" if direction=="sell" else "neutral","boundary":boundary,"close":event.get("breakout_close"),"time":event_time,"accepted":bool(accepted)}
    confidence="low" if relationship=="countertrend_breakout" else "medium" if eligible else "low"
    reason="The locked range boundary has a completed accepted close; evaluate its retest independently from the failed AMD cycle." if accepted else "A tested range/compression breakout is present."
    row.update({"eligible":bool(eligible),"eligibility_score":95 if accepted and eligible else 90 if eligible else 0,"eligibility_reasons":[reason] if eligible else [],"rejection_reasons":[] if eligible else [f"No completed {direction} breakout from the locked range."],"direction":direction,"setup_type":"accepted_range_breakout_retest" if accepted and eligible else "range_breakout_retest" if eligible else "","stage":"waiting_for_retest" if eligible else "not_eligible","zone":zone,"locked_range":{"low":low,"high":high},"breakout":breakout,"higher_timeframe_direction":htf,"local_setup_direction":direction if eligible else "neutral","relationship":relationship,"primary_actionable_direction":"neutral","minimum_rr":2.0 if relationship=="countertrend_breakout" else 1.5,"confirmation_requirements":["completed close beyond locked boundary","retest of broken boundary","retest holds","completed M5 confirmation"],"structural_quality":19 if accepted else 16 if eligible else 0,"location_quality":10 if relationship=="countertrend_breakout" else 14 if eligible else 0,"present_quality_score":72 if accepted and relationship=="countertrend_breakout" else 80 if accepted else 66 if eligible else 0,"confidence":confidence,"status":"watching_for_retest" if eligible else "not_eligible"})
    row["diagnostics"]={"detected_direction":detected,"requested_direction":direction,"range_low":low,"range_high":high,"breakout":breakout,"relationship":relationship,"failed_requirement":row["rejection_reasons"][0] if row["rejection_reasons"] else None}
    return row


def _ict_candidate(asset_class: str, regime: str, features: dict[str, object], top_down: dict[str, object], session: dict[str, object], amd: dict[str, object], ict_model: dict[str, object] | None = None, requested_direction=None) -> dict[str, object]:
    row = empty_candidate("ict_2022"); m15 = features["timeframes"].get("M15", {}); liquidity = _value(m15, "liquidity") or {}; displacement = _value(m15, "displacement") or {}; fvgs = _value(m15, "fvg") or []; setup = top_down.get("m15_setup") or {}; direction = requested_direction or setup.get("direction", "neutral")
    if ict_model is not None:
        sequence=ict_model.get("sequence") or {}; narrative=ict_model.get("narrative") or {}; strict_setup=ict_model.get("setup") or {}; candidate=ict_model.get("bullish_candidate" if requested_direction=="buy" else "bearish_candidate") or {}; array=candidate.get("entry") or {}; direction=requested_direction or narrative.get("direction","neutral")
        core=("htf_narrative","directional_draw","opposing_liquidity","liquidity_sweep","displacement","mss","fvg")
        session_ok=asset_class in {"crypto","derived_index"} or bool(session.get("entry_allowed",True)); evidence={"opposing_liquidity":bool((candidate.get("liquidity") or {}).get("opposing_pool")),"liquidity_sweep":bool(candidate.get("sweep")),"displacement":bool(candidate.get("displacement")),"mss":bool(candidate.get("mss")),"fvg":bool(candidate.get("fvg"))}; eligible=direction in {"buy","sell"} and all(evidence.values()) and candidate.get("state") not in {"invalid","invalidated"} and session_ok
        missing=[key for key,value in evidence.items() if not value]
        row.update({"eligible":eligible,"eligibility_score":96 if eligible else 0,"eligibility_reasons":["Strict ICT 2022 v2 sweep → displacement → MSS → FVG sequence is complete."] if eligible else [],"rejection_reasons":[] if eligible else [f"Strict ICT v2 is waiting for {key.replace('_',' ')}." for key in missing[:3]],"direction":direction if eligible else "neutral","setup_type":"ict_2022_v2_core" if eligible else "","stage":str(strict_setup.get("state","not_eligible")).lower(),"zone":{"low":array.get("low"),"high":array.get("high"),"origin_time":array.get("formed_at"),"type":array.get("type","fvg"),"freshness":"locked","touch_count":1 if sequence.get("price_in_entry_array")=="pass" else 0},"confirmation_requirements":["completed M5 confirmation","structural stop","unswept target","minimum remaining RR"],"structural_quality":20 if eligible else 0,"location_quality":15 if eligible else 0,"present_quality_score":int((ict_model.get("quality") or {}).get("setup_score",0)) if eligible else 0,"confidence":"medium" if eligible else "low","status":"waiting_for_m5" if eligible else "not_eligible"})
        row["direction"]=direction; row["stage"]=candidate.get("state") or row["stage"]; row["diagnostics"]={"requested_direction":direction,"candidate_id":candidate.get("candidate_id"),"relationship":candidate.get("relationship"),"evidence":evidence,"failed_requirement":row["rejection_reasons"][0] if row["rejection_reasons"] else None}
        return row
    amd_direction = "buy" if amd.get("direction") == "bullish" else "sell" if amd.get("direction") == "bearish" else "neutral"; amd_manipulation = bool((amd.get("manipulation") or {}).get("detected") and (amd.get("manipulation") or {}).get("reclaimed_range") and not amd.get("countertrend")); amd_distribution = amd.get("distribution") or {}
    sweep_present = bool(liquidity.get("equal_lows") if direction == "buy" else liquidity.get("equal_highs")) or (amd_manipulation and amd_direction == direction); active_fvg = next((fvg for fvg in reversed(fvgs) if fvg["direction"] == ("bullish" if direction == "buy" else "bearish")), None) or (amd_distribution.get("fvg") if amd_direction == direction else None)
    session_ok = asset_class in {"crypto","derived_index"} or bool(session.get("entry_allowed", True)); aligned = regime in {"TRENDING_BULLISH", "TRENDING_BEARISH", "PULLBACK_BULLISH_REGIME", "PULLBACK_BEARISH_REGIME"}
    displacement_present = bool(displacement.get("active")) or (bool(amd_distribution.get("forming")) and amd_direction == direction)
    eligible = aligned and direction in {"buy", "sell"} and sweep_present and displacement_present and active_fvg is not None and session_ok
    row.update({"eligible": eligible, "eligibility_score": 96 if eligible and amd_manipulation else 92 if eligible else 0, "eligibility_reasons": ["A locked AMD range, reclaimed liquidity sweep, aligned distribution, and active entry array support ICT."] if eligible and amd_manipulation else ["Aligned liquidity, displacement, and active FVG context."] if eligible else [], "rejection_reasons": [] if eligible else [reason for condition, reason in ((aligned, "No aligned top-down ICT narrative."), (sweep_present, "No relevant liquidity sweep context."), (displacement_present, "No volatility-adjusted displacement."), (active_fvg is not None, "No active directionally aligned FVG."), (session_ok, "Asset-aware timing context is not eligible.")) if not condition], "direction": direction if eligible else "neutral", "setup_type": "amd_liquidity_sweep_fvg" if eligible and amd_manipulation else "liquidity_sweep_fvg" if eligible else "", "stage": "waiting_for_m5" if eligible else "not_eligible", "zone": {"low": active_fvg.get("low"), "high": active_fvg.get("high"), "origin_time": active_fvg.get("formation_time"), "type": "fvg", "freshness": "fresh", "touch_count": 0} if active_fvg else row["zone"], "confirmation_requirements": ["AMD accumulation", "liquidity swept and range reclaimed", "distribution displacement", "MSS/CHoCH", "entry array interaction", "completed M5 close"], "structural_quality": 20 if eligible and amd_manipulation else 19 if eligible else 0, "location_quality": 15 if eligible and amd_manipulation else 14 if eligible else 0, "present_quality_score": 82 if eligible and amd_distribution.get("detected") else 76 if eligible and amd_manipulation else 72 if eligible else 0, "confidence": "medium" if eligible else "low", "status": "waiting_for_m5" if eligible else "not_eligible"})
    row["direction"]=direction; row["diagnostics"]={"requested_direction":direction,"sweep_present":sweep_present,"displacement_present":displacement_present,"fvg_present":active_fvg is not None,"session_ok":session_ok,"failed_requirement":row["rejection_reasons"][0] if row["rejection_reasons"] else None}
    return row


def _resolve(eligible: list[dict[str, object]], regime: str) -> tuple[dict[str, object] | None, bool, str]:
    if not eligible: return None, False, "No strategy satisfies the current regime and setup requirements."
    best={side:next((row for row in eligible if row["direction"]==side),None) for side in ("buy","sell")}
    if all(best.values()) and abs(float(best["buy"]["candidate_score"])-float(best["sell"]["candidate_score"]))<5:return None,True,"Eligible buy and sell experts are too close; Auto returns a directional conflict."
    winner = eligible[0]
    return winner, False, f"{winner['strategy_id']} {winner['direction']} candidate fits {regime.lower()} and has the strongest present eligible score."


def _directional_contract(direction,candidates):
    rows=[row for row in candidates if row.get("direction")==direction]; eligible=[row for row in rows if row.get("eligible")]; ranked=sorted(eligible or rows,key=lambda row:(float(row.get("candidate_score",0)),float(row.get("present_quality_score",0))),reverse=True); best=ranked[0] if ranked else None
    return {"eligible":bool(eligible),"strategy":best.get("strategy_id") if best and best.get("eligible") else None,"score":float(best.get("candidate_score",0)) if best else 0,"stage":best.get("stage","") if best else "","rejection_reasons":[{"strategy":row.get("strategy_id"),"stage":row.get("stage"),"reason":reason,"diagnostics":row.get("diagnostics",{})} for row in rows if not row.get("eligible") for reason in row.get("rejection_reasons",[])],"diagnostics":{"candidates_found":len(rows),"eligible_count":len(eligible),"rejected_count":len(rows)-len(eligible),"best_candidate_id":best.get("candidate_id") if best else None}}


def _zone(setup: dict[str, object]) -> dict[str, object]:
    zone = setup.get("zone") or {}
    return {"low": zone.get("low"), "high": zone.get("high"), "origin_time": zone.get("start_time"), "type": zone.get("type", ""), "freshness": "fresh", "touch_count": 1 if setup.get("status") == "in_zone" else 0}
def _value(frame: dict[str, object], name: str): return (frame.get(name) or {}).get("value")
def _volatility(features: dict[str, object]) -> str: return str(_value(features["timeframes"].get("H1", {}), "volatility_regime") or "unknown")
def _number(value):
    try: return float(value) if value is not None else None
    except (TypeError, ValueError): return None
