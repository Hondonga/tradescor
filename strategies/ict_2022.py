"""Strict ICT 2022 strategy built on TradeScor's shared market analysis."""

from __future__ import annotations

import pandas as pd

from analysis.candles import to_unix_seconds
from analysis.objectives import analyze_objectives
from analysis.setup_state import build_setup_state, event_record
from analysis.timeframe_alignment import describe_timeframe_alignment
from scanner.amd_phase import analyze_amd_phase
from scanner.choch import detect_choch
from scanner.fvg import detect_fvgs, select_ict_fvg
from scanner.ict_checklist import build_ict_checklist, classify_ict_state, next_ict_action
from scanner.ict_order_block_quality import evaluate_order_block
from scanner.ifvg import detect_ifvg
from scanner.liquidity_sweep import analyze_liquidity_sweep
from scanner.objective_engine import levels_from_objective_plan
from scanner.ote import analyze_ote
from scanner.strategy import analyze_current_setup
from strategies.base import EMPTY_LEVELS, legacy_bias_to_strategy, make_strategy_result, research_candidate, research_eligible, research_explain


STRATEGY_NAME = "ICT 2022 Model"
STRATEGY_VERSION = "ict_2022_v1"
LEGACY_STRATEGY_VERSION = STRATEGY_VERSION

def is_eligible(context): return research_eligible(context, "ict_2022")
def detect_setup(context): return research_candidate(context, "ict_2022")
def build_candidate(context, setup): return setup
def explain(candidate): return research_explain(candidate)


def analyze(
    candles: pd.DataFrame,
    shared_analysis: dict[str, object],
    *,
    symbol: str,
    timeframe: str,
    top_down_analysis: dict[str, object] | None = None,
    context_candles: dict[str, pd.DataFrame] | None = None,
    macro_context: dict[str, object] | None = None,
    top_down_context: dict[str, object] | None = None,
    analysis_timestamp: object | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Run only ICT-specific logic and return the standardized strategy shape."""
    macro = macro_context or {}
    top_down_analysis = top_down_analysis or {}
    top_down_context = top_down_context or macro.get("top_down_context") or {}
    context_candles = context_candles or {}

    legacy = analyze_current_setup(
        candles,
        symbol=symbol,
        timeframe=timeframe,
        top_down_analysis=top_down_analysis,
        context_candles=context_candles,
        macro_context=macro,
    )
    timeframe_view = describe_timeframe_alignment(
        top_down_context,
        timeframe,
        (shared_analysis.get("trend") or {}).get("direction", "Neutral"),
    )
    bias = _ict_bias(timeframe_view, top_down_analysis, legacy)
    direction = bias.lower() if bias in {"Bullish", "Bearish"} else None
    swings = shared_analysis.get("swings") or {"highs": [], "lows": []}
    liquidity = shared_analysis.get("liquidity") or {}
    equal_levels = {
        "equal_highs": liquidity.get("equal_highs", []),
        "equal_lows": liquidity.get("equal_lows", []),
    }
    sweep = analyze_liquidity_sweep(candles, swings, equal_levels, direction)
    choch = detect_choch(candles, swings, sweep.get("sweep") or None)
    fvgs = detect_fvgs(candles)
    sequence_index = _sequence_index(choch, sweep)
    active_fvg = select_ict_fvg(candles, fvgs, direction, after_index=sequence_index)
    ifvg = detect_ifvg(candles, fvgs, direction, sequence_index, lookback=80)
    ote = analyze_ote(candles, direction)
    order_blocks = legacy.get("order_blocks") or (shared_analysis.get("zones") or {}).get("order_blocks") or {}
    current_price = float(candles.iloc[-1]["close"])
    ob_quality = evaluate_order_block(order_blocks, direction, current_price)
    session = macro.get("session") or legacy.get("session") or {}
    dxy = macro.get("dxy_correlation") or {}
    news = macro.get("economic_news") or {}
    amd = analyze_amd_phase(candles, session, sweep, choch)
    htf_confirmed = _htf_bias_confirmed(bias, timeframe_view)
    entry_zone = _entry_zone(ote, active_fvg, ifvg, ob_quality)
    entry_proximity = _price_in_zone(current_price, entry_zone)
    invalidation = _invalidation_level(candles, direction, sweep, entry_zone, shared_analysis)
    objective_plan = _objective_plan(
        direction,
        entry_zone,
        invalidation,
        shared_analysis,
        context_candles,
        legacy.get("liquidity_map") or {},
        candles,
    )
    objective = objective_plan.get("primary_objective") or objective_plan.get("best_rejected_objective") or {}
    rr = objective.get("rr")
    checklist = build_ict_checklist(
        htf_bias_confirmed=htf_confirmed,
        kill_zone_active=bool(session.get("entry_allowed")),
        liquidity_pool_identified=bool(sweep.get("pool_identified")),
        liquidity_swept=bool(sweep.get("swept")),
        choch_confirmed=bool(choch.get("confirmed")),
        fvg_present=active_fvg is not None or ifvg is not None,
        order_block_present=bool(ob_quality.get("present")),
        order_block_valid=bool(ob_quality.get("valid")),
        ote_available=bool(ote.get("available")),
        ote_aligned=bool(ote.get("in_zone")),
        dxy_status=str(dxy.get("correlation_status", "Waiting")),
        news_enabled=bool(news.get("enabled")),
        news_restricted=bool(news.get("restriction_active")),
        risk_reward=float(rr) if isinstance(rr, (int, float)) else None,
    )
    checklist["execution_alignment"] = (
        "pass" if timeframe_view["timeframe_alignment"] == "Aligned"
        else "fail" if timeframe_view["timeframe_alignment"] == "Counter-trend"
        else "waiting"
    )
    invalidated = str(legacy.get("setup_status", "")).upper() == "INVALIDATED"
    legacy_state = str((legacy.get("ict_state") or {}).get("key", ""))
    state = classify_ict_state(
        checklist,
        invalidated=invalidated,
        trade_active=legacy_state == "TRADE_ACTIVE",
    )
    if timeframe_view["timeframe_alignment"] == "Counter-trend" and state not in {"TRADE_ACTIVE", "INVALIDATED"}:
        state = "NO_TRADE"
    if state == "ENTRY_READY" and not entry_proximity:
        state = "CONFIRMED_WAITING_FOR_ENTRY"
    next_action = next_ict_action(state, checklist, choch.get("level"))
    if timeframe_view["timeframe_alignment"] == "Counter-trend":
        next_action = (
            f"Wait for {timeframe} to realign with the "
            f"{bias.lower()} higher-timeframe bias before considering an ICT entry."
        )
    levels_mode = "final" if state in {"ENTRY_READY", "TRADE_ACTIVE"} and objective_plan.get("trade_accepted") else "hidden"
    levels = _levels(entry_zone, invalidation, objective_plan, levels_mode)
    overlays = _overlays(
        candles,
        sweep,
        choch,
        active_fvg,
        ifvg,
        ote,
        ob_quality,
        levels,
        levels_mode,
        invalidation,
    )
    details = _ict_details(
        bias,
        session,
        sweep,
        choch,
        active_fvg,
        ifvg,
        ote,
        ob_quality,
        amd,
        dxy,
        news,
        objective_plan,
    )
    details["timeframe_alignment"] = timeframe_view
    trader_answers = _ict_trader_answers(
        symbol,
        bias,
        state,
        checklist,
        details,
        next_action,
        top_down_context,
        timeframe_view,
    )
    setup_quality = _checklist_quality(checklist)
    trade_quality = int(objective_plan.get("trade_quality", 0) or 0)
    trade_decision = "ACCEPT" if levels_mode == "final" else "REJECT" if state == "NO_TRADE" and objective_plan.get("decision") == "REJECT" else "PENDING"
    progress = _progress(state)
    why = [{"key": f"ict_{index}", "status": "info", "text": text} for index, text in enumerate(trader_answers["why"])]

    result = make_strategy_result(
        strategy_name=STRATEGY_NAME,
        bias=bias,
        state=state,
        score=setup_quality,
        market_story=trader_answers["market_story"],
        next_trigger=next_action,
        levels_mode=levels_mode,
        levels=levels,
        overlays=overlays,
        progress=progress,
        why=why,
    )
    result.update(
        {
            "setup_quality": setup_quality,
            "trade_quality": trade_quality,
            "trade_decision": trade_decision,
            "objective_plan": objective_plan,
            "ict_checklist": checklist,
            "ict_details": details,
            "trader_answers": trader_answers,
            "timeline": _ict_analysis_timeline(details, state, bias),
            "confirmation_achieved": bool(choch.get("confirmed")),
            "entry_zone_available": bool(entry_zone),
            "entry_proximity": entry_proximity,
        }
    )
    completed_events = []
    sweep_event = sweep.get("sweep") or {}
    if sweep_event:
        completed_events.append(event_record("liquidity_sweep", sweep_event.get("time", candles.iloc[0]["time"]), level=sweep_event.get("swept_level")))
    choch_event = choch.get("event") or {}
    if choch_event:
        completed_events.append(event_record("choch_confirmed", choch_event.get("time", candles.iloc[-1]["time"]), level=choch.get("level")))
    if active_fvg:
        completed_events.append(event_record("fvg_identified", active_fvg.get("start_time", candles.iloc[-1]["time"])))
    if ifvg:
        completed_events.append(event_record("ifvg_identified", ifvg.get("start_time", candles.iloc[-1]["time"])))
    result["setup_state"] = build_setup_state(
        strategy="ict_2022",
        direction=bias,
        created_at=sweep_event.get("time", analysis_timestamp or candles.iloc[0]["time"]),
        current_state=state,
        completed_events=completed_events,
        active_zone=entry_zone,
        trigger_level={"price": choch.get("level"), "time": choch_event.get("time"), "index": choch_event.get("index")},
        confirmation_event={"time": choch_event.get("time"), "index": choch_event.get("index"), "level": choch.get("level")} if choch_event else {},
        entry_zone=entry_zone,
        invalidation=invalidation,
        targets=objective_plan.get("targets", []),
        invalidated=state == "INVALIDATED",
        invalidation_reason="The ICT sequence was invalidated." if state == "INVALIDATED" else None,
    )

    legacy.update(
        {
            "bias": "LONG" if bias == "Bullish" else "SHORT" if bias == "Bearish" else "NEUTRAL",
            "setup_status": state.replace("_", " "),
            "status": state.replace("_", " "),
            "ict_state": {"key": state, "label": state.replace("_", " ").title()},
            "levels_mode": levels_mode,
            "levels": result["levels"],
            "chart_overlays": overlays,
            "overlays": overlays,
            "score": setup_quality,
            "setup_quality": setup_quality,
            "trade_quality": trade_quality,
            "trade_decision": trade_decision,
            "objective_plan": objective_plan,
            "ict_checklist": checklist,
            "ict_details": details,
            "trader_answers": trader_answers,
            "next_required_confirmation": next_action,
            "missing_confirmation": next_action,
            "suggested_action": next_action,
            "summary": trader_answers["market_story"],
        }
    )
    return result, legacy


def _ict_bias(
    timeframe_view: dict[str, str],
    top_down_analysis: dict[str, object],
    legacy: dict[str, object],
) -> str:
    higher_bias = str(timeframe_view.get("higher_timeframe_bias", "Neutral"))
    if higher_bias in {"Bullish", "Bearish"}:
        return higher_bias
    alignment = str(top_down_analysis.get("overall_alignment") or "Neutral")
    if "Bullish" in alignment:
        return "Bullish"
    if "Bearish" in alignment:
        return "Bearish"
    return legacy_bias_to_strategy(str(legacy.get("bias", "NEUTRAL")))


def _htf_bias_confirmed(
    bias: str,
    timeframe_view: dict[str, str],
) -> bool:
    return bias in {"Bullish", "Bearish"} and bias == timeframe_view.get("higher_timeframe_bias")


def _sequence_index(choch: dict[str, object], sweep: dict[str, object]) -> int | None:
    event = choch.get("event") or {}
    if event.get("index") is not None:
        return int(event["index"])
    sweep_event = sweep.get("sweep") or {}
    return int(sweep_event["index"]) if sweep_event.get("index") is not None else None


def _entry_zone(
    ote: dict[str, object],
    fvg: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    ob_quality: dict[str, object],
) -> dict[str, object]:
    zones = [zone for zone in (ote.get("zone") or {}, ifvg or {}, fvg or {}, (ob_quality.get("block") or {}) if ob_quality.get("valid") else {}) if zone]
    if not zones:
        return {}

    top = min(float(zone.get("top_price", zone.get("top"))) for zone in zones)
    bottom = max(float(zone.get("bottom_price", zone.get("bottom"))) for zone in zones)
    source = ote.get("zone") or ifvg or fvg or ob_quality.get("block") or {}
    if bottom > top:
        top = float(source.get("top_price", source.get("top")))
        bottom = float(source.get("bottom_price", source.get("bottom")))
    return {
        "top": round(max(top, bottom), 6),
        "bottom": round(min(top, bottom), 6),
        "start_time": source.get("start_time"),
        "end_time": source.get("end_time"),
    }


def _price_in_zone(price: float, zone: dict[str, object]) -> bool:
    if not zone:
        return False
    return float(zone["bottom"]) <= price <= float(zone["top"])


def _invalidation_level(
    candles: pd.DataFrame,
    direction: str | None,
    sweep: dict[str, object],
    entry_zone: dict[str, object],
    shared: dict[str, object],
) -> float | None:
    if not entry_zone or direction not in {"bullish", "bearish"}:
        return None
    atr = float((shared.get("volatility") or {}).get("atr") or (candles["high"] - candles["low"]).tail(20).mean())
    buffer = max(atr * 0.25, abs(float(candles.iloc[-1]["close"])) * 0.00005)
    event = sweep.get("sweep") or {}
    if direction == "bullish":
        base = min(float(entry_zone["bottom"]), float(event.get("swept_price", candles["low"].tail(20).min())))
        return round(base - buffer, 6)
    base = max(float(entry_zone["top"]), float(event.get("swept_price", candles["high"].tail(20).max())))
    return round(base + buffer, 6)


def _objective_plan(
    direction: str | None,
    entry_zone: dict[str, object],
    invalidation: float | None,
    shared: dict[str, object],
    context_candles: dict[str, pd.DataFrame],
    liquidity_map: dict[str, object],
    analysis_candles: pd.DataFrame,
) -> dict[str, object]:
    entry = None
    if entry_zone:
        entry = (float(entry_zone["top"]) + float(entry_zone["bottom"])) / 2
    return analyze_objectives(
        direction=direction,
        entry_price=entry,
        stop_loss=invalidation,
        shared_analysis=shared,
        context_candles=context_candles,
        liquidity_map=liquidity_map,
        analysis_candles=analysis_candles,
    )


def _levels(
    entry_zone: dict[str, object],
    invalidation: float | None,
    objective_plan: dict[str, object],
    levels_mode: str,
) -> dict[str, object]:
    if levels_mode != "final":
        return EMPTY_LEVELS.copy()
    levels = levels_from_objective_plan(
        entry_zone={"top": entry_zone["top"], "bottom": entry_zone["bottom"]},
        stop_loss=invalidation,
        objective_plan=objective_plan,
    )
    levels["primary_objective"] = objective_plan.get("primary_objective")
    levels["secondary_objective"] = objective_plan.get("secondary_objective")
    levels["display_note"] = objective_plan.get("summary")
    return levels


def _overlays(
    candles: pd.DataFrame,
    sweep: dict[str, object],
    choch: dict[str, object],
    fvg: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    ote: dict[str, object],
    ob_quality: dict[str, object],
    levels: dict[str, object],
    levels_mode: str,
    invalidation: float | None,
) -> dict[str, object]:
    current_time = candles.iloc[-1]["time"]
    fvg_overlay = _zone_overlay(fvg, current_time, "FVG")
    ifvg_overlay = _zone_overlay(ifvg, current_time, "IFVG")
    ote_overlay = _zone_overlay(ote.get("zone") or {}, current_time, "OTE")
    ob_overlay = _zone_overlay(ob_quality.get("block") or {}, current_time, "OB") if ob_quality.get("valid") else None
    entry_overlay = None
    if levels_mode == "final" and levels.get("entry_zone"):
        entry_overlay = {
            "type": "entry_zone",
            "label": "Entry Zone",
            "tag": "ENTRY",
            "start_time": to_unix_seconds(current_time),
            "end_time": to_unix_seconds(current_time),
            "top": levels["entry_zone"]["top"],
            "bottom": levels["entry_zone"]["bottom"],
        }

    return {
        "current_price": {"price": round(float(candles.iloc[-1]["close"]), 6), "time": to_unix_seconds(current_time)},
        "liquidity_pool": sweep.get("pool") or {},
        "liquidity_sweep": sweep.get("sweep") or {},
        "sweep_marker": sweep.get("sweep") or {},
        "choch_level": {"price": choch.get("level"), "label": "CHoCH"} if choch.get("level") is not None else {},
        "confirmation_level": {"price": choch.get("level"), "label": "CHoCH"} if choch.get("level") is not None else {},
        "fvg_zone": fvg_overlay,
        "active_fvg": fvg_overlay,
        "ifvg_zone": ifvg_overlay,
        "ote_zone": ote_overlay,
        "pullback_zone": ote_overlay,
        "valid_order_block": ob_overlay,
        "order_block": ob_overlay,
        "invalidation_level": invalidation,
        "entry_zone": entry_overlay,
        "stop_loss": levels.get("stop_loss") if levels_mode == "final" else None,
        "tp1": levels.get("tp1") if levels_mode == "final" else None,
        "tp2": levels.get("tp2") if levels_mode == "final" else None,
        "levels_mode": levels_mode,
        "trade_levels": {**levels, "mode": levels_mode} if levels_mode == "final" else None,
    }


def _zone_overlay(zone: dict[str, object] | None, current_time, tag: str) -> dict[str, object] | None:
    if not zone:
        return None
    top = zone.get("top_price", zone.get("top"))
    bottom = zone.get("bottom_price", zone.get("bottom"))
    if top is None or bottom is None:
        return None
    start = zone.get("start_time") or current_time
    end = zone.get("end_time") or zone.get("rectangle_end_time") or current_time
    return {
        "type": zone.get("type", tag.lower()),
        "label": zone.get("label", tag),
        "tag": tag,
        "tooltip": zone.get("tooltip", zone.get("label", tag)),
        "start_time": to_unix_seconds(start),
        "end_time": to_unix_seconds(end),
        "top": round(float(top), 6),
        "bottom": round(float(bottom), 6),
    }


def _ict_details(
    bias: str,
    session: dict[str, object],
    sweep: dict[str, object],
    choch: dict[str, object],
    fvg: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    ote: dict[str, object],
    ob_quality: dict[str, object],
    amd: dict[str, object],
    dxy: dict[str, object],
    news: dict[str, object],
    objective_plan: dict[str, object],
) -> dict[str, object]:
    return {
        "htf_bias": bias,
        "kill_zone": {
            "name": session.get("name", "Outside Trading Hours"),
            "active": bool(session.get("entry_allowed")),
            "status": "Active" if session.get("entry_allowed") else "Inactive",
        },
        "liquidity_sweep": sweep,
        "choch": choch,
        "fvg": {"present": fvg is not None, "status": "Present" if fvg else "Missing", "zone": fvg or {}},
        "ifvg": {"present": ifvg is not None, "status": "Present" if ifvg else "Missing", "zone": ifvg or {}},
        "ote": ote,
        "order_block_quality": ob_quality,
        "amd_phase": amd,
        "dxy": dxy,
        "news": news,
        "objective_plan": objective_plan,
    }


def _ict_trader_answers(
    symbol: str,
    bias: str,
    state: str,
    checklist: dict[str, str],
    details: dict[str, object],
    next_action: str,
    top_down_context: dict[str, object],
    timeframe_view: dict[str, str],
) -> dict[str, object]:
    ote = details.get("ote") or {}
    fvg = details.get("fvg") or {}
    ifvg = details.get("ifvg") or {}
    sweep = details.get("liquidity_sweep") or {}
    if ote.get("in_zone"):
        price_location = f"Inside OTE / {ote.get('location', 'dealing')} zone"
    elif ifvg.get("present"):
        price_location = "Inside active IFVG context"
    elif fvg.get("present"):
        price_location = "Inside active FVG context"
    elif sweep.get("pool_identified"):
        price_location = "At directional liquidity"
    else:
        price_location = "No clear ICT level"

    intents = {
        "NO_TRADE": "Waiting for clearer ICT context",
        "WAITING_FOR_KILL_ZONE": "Waiting for an active entry window",
        "WAITING_FOR_LIQUIDITY_SWEEP": f"Waiting for {sweep.get('expected_side', 'directional')} liquidity sweep",
        "WAITING_FOR_CHOCH": "Waiting for structure to shift after the sweep",
        "WAITING_FOR_FVG_OR_OB": "Waiting for imbalance or order-block confirmation",
        "WAITING_FOR_OTE": "Waiting for optimal retracement",
        "CONFIRMED_WAITING_FOR_ENTRY": "Waiting for price to return to the confirmed ICT entry zone",
        "ENTRY_READY": "Confirmations aligned for entry",
        "TRADE_ACTIVE": "Managing confirmed ICT delivery",
        "INVALIDATED": "Waiting for a fresh ICT sequence",
    }
    statuses = {
        "NO_TRADE": "No Trade",
        "WAITING_FOR_KILL_ZONE": "Wait",
        "WAITING_FOR_LIQUIDITY_SWEEP": "Wait",
        "WAITING_FOR_CHOCH": "Almost Ready",
        "WAITING_FOR_FVG_OR_OB": "Almost Ready",
        "WAITING_FOR_OTE": "Almost Ready",
        "CONFIRMED_WAITING_FOR_ENTRY": "Wait",
        "ENTRY_READY": "Entry Ready",
        "TRADE_ACTIVE": "Trade Active",
        "INVALIDATED": "Invalidated",
    }
    why = _ict_why(bias, checklist, details, timeframe_view)
    trade_status = statuses.get(state, "No Trade")
    intent = intents.get(state, "Waiting for clearer ICT context")
    if timeframe_view["timeframe_alignment"] == "Counter-trend":
        intent = (
            f"{timeframe_view['execution_timeframe_trend']} pullback against "
            f"{bias.lower()} higher-timeframe bias"
        )
    story = _ict_story(symbol, bias, price_location, intent, trade_status, next_action, timeframe_view)
    clarity = "High" if sum(value == "pass" for value in checklist.values()) >= 7 else "Medium" if bias in {"Bullish", "Bearish"} else "Low"
    readiness = "Ready" if trade_status in {"Entry Ready", "Trade Active"} else "Building" if trade_status in {"Wait", "Almost Ready"} else "Not Ready"
    return {
        "trend": timeframe_view["execution_timeframe_trend"] if timeframe_view["execution_timeframe_trend"] in {"Bullish", "Bearish"} else "Unclear",
        **timeframe_view,
        "price_location": price_location,
        "market_intent": intent,
        "trade_status": trade_status,
        "why": why,
        "top_down_summary": str(top_down_context.get("summary") or f"Higher-timeframe ICT bias is {bias.lower()}."),
        "market_story": story,
        "next_action": next_action,
        "market_clarity": clarity,
        "trade_readiness": readiness,
        "market_timeline": _ict_timeline(details, state),
    }


def _ict_why(
    bias: str,
    checklist: dict[str, str],
    details: dict[str, object],
    timeframe_view: dict[str, str],
) -> list[str]:
    direction = bias.lower() if bias in {"Bullish", "Bearish"} else "unclear"
    reasons = [f"Higher-timeframe bias is {direction}." if checklist.get("htf_bias") == "pass" else "Higher-timeframe direction is not confirmed."]
    if timeframe_view["timeframe_alignment"] == "Counter-trend":
        reasons.append(
            f"{timeframe_view['execution_timeframe']} execution is "
            f"{timeframe_view['execution_timeframe_trend'].lower()} and not aligned with the "
            f"{direction} higher-timeframe bias."
        )
    elif timeframe_view["timeframe_alignment"] == "Aligned":
        reasons.append(
            f"{timeframe_view['execution_timeframe']} execution confirms the {direction} higher-timeframe bias."
        )
    reasons.append("The active Kill Zone permits entries." if checklist.get("kill_zone") == "pass" else "The London or New York Kill Zone is not active.")
    if checklist.get("liquidity_swept") == "pass" and checklist.get("choch") != "pass":
        reasons.append("Liquidity sweep is present, but confirmation is still missing.")
    elif checklist.get("liquidity_swept") == "pass":
        reasons.append("Liquidity sweep and structure confirmation are present.")
    else:
        reasons.append("The liquidity sweep is still missing.")
    reasons.append("CHoCH confirms the intended direction." if checklist.get("choch") == "pass" else "CHoCH has not confirmed after the sweep.")
    if checklist.get("ote") == "pass":
        reasons.append("Price is inside the OTE retracement zone.")
    elif checklist.get("fvg") == "pass" or checklist.get("ob_valid") == "pass":
        reasons.append("An active FVG or valid order block supports the setup, but OTE alignment is missing.")
    else:
        reasons.append("No aligned FVG, order block, and OTE confluence is complete yet.")
    return reasons[:5]


def _ict_story(
    symbol: str,
    bias: str,
    location: str,
    intent: str,
    trade_status: str,
    next_action: str,
    timeframe_view: dict[str, str],
) -> str:
    direction = bias.lower() if bias in {"Bullish", "Bearish"} else "unclear"
    execution_timeframe = timeframe_view.get("execution_timeframe", "Execution timeframe")
    execution_trend = timeframe_view.get("execution_timeframe_trend", "Neutral").lower()
    if timeframe_view.get("timeframe_alignment") == "Counter-trend":
        return (
            f"{symbol} has a {direction} higher-timeframe ICT bias, while {execution_timeframe} "
            f"execution is {execution_trend}. The execution timeframe is not aligned, so trade "
            f"status is {trade_status}. {next_action}"
        )
    return (
        f"{symbol} has a {direction} higher-timeframe ICT bias. {execution_timeframe} execution "
        f"is {execution_trend}. Price is {location.lower()} and is {intent.lower()}. "
        f"Trade status is {trade_status}. {next_action}"
    )


def _ict_timeline(details: dict[str, object], state: str) -> list[str]:
    sweep = details.get("liquidity_sweep") or {}
    choch = details.get("choch") or {}
    rows = [f"AMD phase: {(details.get('amd_phase') or {}).get('phase', 'Waiting')}."]
    rows.append("Liquidity sweep confirmed." if sweep.get("swept") else "Waiting for liquidity sweep.")
    rows.append("CHoCH confirmed." if choch.get("confirmed") else "Waiting for CHoCH.")
    rows.append(f"Current ICT state: {state.replace('_', ' ').title()}.")
    return rows


def _ict_analysis_timeline(
    details: dict[str, object],
    state: str,
    bias: str,
) -> list[dict[str, object]]:
    """Return strategy events in the shared timeline contract."""
    sweep = details.get("liquidity_sweep") or {}
    choch = details.get("choch") or {}
    fvg = details.get("fvg") or {}
    events = []

    if sweep.get("swept"):
        event = sweep.get("sweep") or {}
        events.append(
            {
                "time": event.get("time", "Current"),
                "event_type": "Liquidity Sweep",
                "direction": bias,
                "explanation": "Directional liquidity was taken and price closed back inside the range.",
            }
        )
    if choch.get("confirmed"):
        event = choch.get("event") or {}
        events.append(
            {
                "time": event.get("time", "Current"),
                "event_type": "CHoCH Confirmed",
                "direction": bias,
                "explanation": "Price closed beyond the post-sweep structure level.",
            }
        )
    if fvg.get("present"):
        zone = fvg.get("zone") or {}
        events.append(
            {
                "time": zone.get("end_time", "Current"),
                "event_type": "FVG Detected",
                "direction": bias,
                "explanation": "A directional imbalance remains active for the current ICT sequence.",
            }
        )

    events.append(
        {
            "time": "Current",
            "event_type": state.replace("_", " ").title(),
            "direction": bias,
            "explanation": next_ict_action(state, {}, choch.get("level")),
        }
    )
    return events


def _checklist_quality(checklist: dict[str, str]) -> int:
    scored = [key for key in checklist if key not in {"dxy", "news"}]
    passed = sum(checklist.get(key) == "pass" for key in scored)
    return round((passed / len(scored)) * 100) if scored else 0


def _progress(state: str) -> list[dict[str, object]]:
    stages = [
        ("kill_zone", "Kill Zone", "WAITING_FOR_KILL_ZONE"),
        ("liquidity", "Liquidity Sweep", "WAITING_FOR_LIQUIDITY_SWEEP"),
        ("choch", "CHoCH", "WAITING_FOR_CHOCH"),
        ("fvg_ob", "FVG / OB", "WAITING_FOR_FVG_OR_OB"),
        ("ote", "OTE", "WAITING_FOR_OTE"),
        ("entry_location", "Waiting Entry Location", "CONFIRMED_WAITING_FOR_ENTRY"),
        ("entry", "Entry Ready", "ENTRY_READY"),
    ]
    order = {stage_state: index for index, (_key, _label, stage_state) in enumerate(stages)}
    current = order.get(state, -1)
    rows = []
    for index, (key, label, _stage_state) in enumerate(stages):
        status = "completed" if current > index or state in {"ENTRY_READY", "TRADE_ACTIVE"} else "current" if current == index else "inactive"
        rows.append({"key": key, "label": label, "status": status, "is_current": status == "current"})
    return rows
