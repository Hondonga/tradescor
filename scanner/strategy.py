"""Current-chart ICT 2022 setup analyzer."""

from __future__ import annotations

import pandas as pd

from scanner.fvg import detect_fvgs, nearest_active_fvg
from scanner.ifvg import detect_ifvg
from scanner.liquidity import (
    detect_equal_levels,
    detect_liquidity_sweeps,
    detect_swings,
    most_recent_sweep,
)
from scanner.liquidity_map import build_liquidity_map
from scanner.market_structure import detect_mss
from scanner.objective_engine import build_objective_plan, levels_from_objective_plan
from scanner.order_blocks import detect_order_blocks
from scanner.risk import build_levels
from scanner.scoring import score_setup_quality
from scanner.session_engine import get_session_context
from scanner.state_machine import classify_ict_state, classify_setup
from scanner.timeline import build_analysis_timeline


def analyze_current_setup(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    top_down_analysis: dict[str, object] | None = None,
    context_candles: dict[str, pd.DataFrame] | None = None,
    macro_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Analyze the selected chart and return one current setup object."""
    if len(candles) < 20:
        return _empty_response(symbol, timeframe, "Not enough candles to analyze.", macro_context)

    fvgs = detect_fvgs(candles)
    swings = detect_swings(candles, width=2, lookback=120)
    tolerance = _price_tolerance(candles)
    equal_levels = detect_equal_levels(swings, tolerance)
    sweeps = detect_liquidity_sweeps(candles, swings, lookback=60)
    sweep = most_recent_sweep(sweeps)
    direction = str(sweep["direction"]) if sweep else None
    mss = detect_mss(candles, swings, sweep, lookback=80)
    htf_fvg = nearest_active_fvg(candles, fvgs, direction, lookback=120)
    ifvg = detect_ifvg(candles, fvgs, direction, int(mss["index"]), lookback=80) if mss else None
    raw_levels = build_levels(candles, direction, sweep, ifvg, htf_fvg, swings, fvgs)
    macro_context = macro_context or {}
    session_context = macro_context.get("session") or get_session_context()
    economic_news = macro_context.get("economic_news") or {}
    dxy_correlation = macro_context.get("dxy_correlation") or {}
    macro_entry_allowed = bool(session_context["entry_allowed"]) and not bool(economic_news.get("restriction_active"))
    htf_bias = _top_down_bias(top_down_analysis)
    order_blocks = detect_order_blocks(candles, swings, htf_bias=htf_bias, htf_fvg=htf_fvg)
    bias = _bias(direction, sweep)
    liquidity_map = build_liquidity_map(
        current_candles=candles,
        daily_candles=(context_candles or {}).get("D1"),
        weekly_candles=(context_candles or {}).get("W1"),
        equal_levels=equal_levels,
        bias=bias,
    )
    scored_objective_plan = _build_objective_plan(
        direction=direction,
        levels=raw_levels if ifvg is not None else {},
        swings=swings,
        equal_levels=equal_levels,
        fvgs=fvgs,
        context_candles=context_candles or {},
        liquidity_map=liquidity_map,
    )
    scored_levels = _levels_with_objectives(raw_levels, scored_objective_plan)
    checklist_bool = _build_checklist(
        candles,
        direction,
        htf_fvg,
        sweep,
        mss,
        ifvg,
        scored_levels,
        macro_entry_allowed,
    )
    objective_plan = _gate_objective_plan(scored_objective_plan, checklist_bool)
    raw_levels = _levels_with_objectives(raw_levels, objective_plan)
    setup_quality = _macro_adjusted_score(score_setup_quality(checklist_bool), dxy_correlation, economic_news)
    trade_quality = int(objective_plan.get("trade_quality", 0) or 0)
    invalidated = _is_invalidated(candles, direction, sweep, ifvg)
    setup_status, readiness_level, next_confirmation = classify_setup(checklist_bool, invalidated)
    trade_decision = str(objective_plan.get("decision", "PENDING"))
    if _technical_sequence_ready(checklist_bool) and trade_decision == "REJECT" and not invalidated:
        setup_status = "NO TRADE"
        readiness_level = {"step": 5, "percent": 100, "label": "NO TRADE"}
        next_confirmation = str(objective_plan.get("reason", "Available reward is too small."))
    ict_state = classify_ict_state(
        htf_fvg=htf_fvg is not None,
        liquidity_sweep=sweep is not None,
        mss=mss is not None,
        ifvg=ifvg is not None,
        invalidated=invalidated,
    )
    levels_mode = _levels_mode(ict_state, trade_decision)
    levels = _levels_for_state(raw_levels, ict_state, trade_decision)
    active_zone = _active_zone(setup_status, htf_fvg, sweep, mss, ifvg)
    invalidation_level = _invalidation_level(direction, levels, sweep)
    invalidation_reason = _invalidation_reason(setup_status, direction, sweep, ifvg)
    missing_confirmation = _session_missing_confirmation(
        _missing_confirmation(setup_status, direction),
        session_context,
        economic_news,
        setup_status,
    )
    suggested_action = _session_adjusted_action(setup_status, session_context, economic_news)
    if setup_status == "NO TRADE":
        missing_confirmation = str(objective_plan.get("reason", "Available reward is too small."))
        suggested_action = f"No trade. {missing_confirmation}"
    checklist_status = _checklist_status(checklist_bool)
    zones = {
        "htf_fvg": htf_fvg or {},
        "liquidity_zone": _liquidity_zone(sweep, equal_levels),
        "ifvg": ifvg or {},
        "mss": mss or {},
    }
    mss_trigger = _mss_trigger(swings, sweep)
    timeline = build_analysis_timeline(
        zones,
        order_blocks,
        setup_status,
        bias,
        levels=levels,
        current_price=float(candles.iloc[-1]["close"]),
        current_time=candles.iloc[-1]["time"],
        levels_mode=levels_mode,
    )
    mentor_view = _mentor_view(
        symbol=symbol,
        bias=bias,
        setup_status=setup_status,
        score=setup_quality,
        setup_quality=setup_quality,
        trade_quality=trade_quality,
        trade_decision=trade_decision,
        objective_plan=objective_plan,
        checklist=checklist_bool,
        levels=levels,
        levels_mode=levels_mode,
        invalidation_reason=invalidation_reason,
        missing_confirmation=missing_confirmation,
        suggested_action=suggested_action,
        ict_state=ict_state,
        macro_context=macro_context,
        session_context=session_context,
        htf_fvg=htf_fvg,
        sweep=sweep,
        mss=mss,
        ifvg=ifvg,
        order_blocks=order_blocks,
        liquidity_map=liquidity_map,
        mss_trigger=mss_trigger,
        current_price=float(candles.iloc[-1]["close"]),
    )

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bias": bias,
        "setup_status": setup_status,
        "ict_state": ict_state,
        "readiness": readiness_level["percent"],
        "readiness_level": readiness_level,
        "active_zone": active_zone,
        "invalidation_level": invalidation_level,
        "missing_confirmation": missing_confirmation,
        "suggested_action": suggested_action,
        "next_required_confirmation": next_confirmation,
        "levels_mode": levels_mode,
        "invalidation_reason": invalidation_reason,
        "direction": _legacy_direction(bias, setup_status),
        "status": setup_status,
        "score": setup_quality,
        "setup_quality": setup_quality,
        "trade_quality": trade_quality,
        "trade_decision": trade_decision,
        "objective_plan": objective_plan,
        "checklist": checklist_status,
        "checklist_flags": checklist_bool,
        "levels": levels,
        "zones": zones,
        "chart_overlays": _chart_overlays(
            candles,
            htf_fvg,
            sweep,
            mss,
            ifvg,
            levels,
            setup_status,
            levels_mode,
            equal_levels,
            order_blocks,
            mss_trigger,
            ict_state,
        ),
        "market_context": _market_context(candles, direction, htf_fvg, session_context),
        "recent_structure": _recent_structure(swings, sweep, mss, order_blocks),
        "order_blocks": order_blocks,
        "session": session_context,
        "kill_zone": _legacy_kill_zone(session_context),
        "liquidity_map": liquidity_map,
        "analysis_timeline": timeline,
        "mentor": mentor_view,
        "market_narrative": mentor_view["narrative"],
        "macro_dashboard": macro_context,
        "summary": _summary(
            symbol,
            bias,
            setup_status,
            checklist_bool,
            missing_confirmation,
            suggested_action,
        ),
    }


def _build_checklist(
    candles: pd.DataFrame,
    direction: str | None,
    htf_fvg: dict[str, object] | None,
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    levels: dict[str, object],
    entry_allowed: bool,
) -> dict[str, bool]:
    rr1 = levels.get("rr1")

    return {
        "htf_fvg": htf_fvg is not None,
        "liquidity_sweep": sweep is not None,
        "mss": mss is not None,
        "ifvg": ifvg is not None,
        "premium_discount": _premium_discount_alignment(candles, direction),
        "displacement": _strong_displacement(candles),
        "session": entry_allowed,
        "risk_reward": isinstance(rr1, (int, float)) and rr1 >= 1.5,
    }


def _liquidity_zone(
    sweep: dict[str, object] | None,
    equal_levels: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    if sweep is None:
        return {}

    key = "equal_lows" if sweep["direction"] == "bullish" else "equal_highs"
    equal_level = equal_levels[key][-1] if equal_levels[key] else {}

    return {
        "type": sweep["side"],
        "direction": sweep["direction"],
        "time": sweep["time"],
        "swept_level": sweep["swept_level"],
        "swept_price": sweep["swept_price"],
        "equal_level": equal_level,
    }


def _bias(direction: str | None, sweep: dict[str, object] | None) -> str:
    if direction == "bullish":
        return "LONG"
    if direction == "bearish":
        return "SHORT"
    if sweep:
        return "NEUTRAL"
    return "NEUTRAL"


def _legacy_direction(bias: str, setup_status: str) -> str:
    """Keep older UI/debug consumers from breaking."""
    if setup_status == "VALID SETUP" and bias == "LONG":
        return "LONG"
    if setup_status == "VALID SETUP" and bias == "SHORT":
        return "SHORT"
    if bias in {"LONG", "SHORT"}:
        return f"{bias} BIAS"
    return "NO SETUP"


def _levels_for_state(
    levels: dict[str, object],
    ict_state: dict[str, object],
    trade_decision: str = "PENDING",
) -> dict[str, object]:
    """Hide or mark trade levels based on readiness."""
    clean_levels = levels.copy()
    mode = _levels_mode(ict_state, trade_decision)

    if mode == "hidden":
        clean_levels.update(
            {
                "entry_zone": None,
                "stop_loss": None,
                "tp1": None,
                "tp2": None,
                "rr1": None,
                "rr2": None,
                "is_tentative": False,
                "display_note": "Trade levels unavailable because setup is invalidated or incomplete.",
            }
        )
        return clean_levels

    if mode == "projected":
        clean_levels["is_tentative"] = True
        clean_levels["stop_loss"] = None
        clean_levels["tp1"] = None
        clean_levels["tp2"] = None
        clean_levels["rr1"] = None
        clean_levels["rr2"] = None
        clean_levels["display_note"] = "Potential Entry Area - Waiting for IFVG."
        return clean_levels

    clean_levels["is_tentative"] = False
    clean_levels["display_note"] = "Valid setup levels."
    return clean_levels


def _levels_mode(ict_state: dict[str, object], trade_decision: str = "PENDING") -> str:
    """Tell the UI whether levels are final, projected, or hidden."""
    state_key = str(ict_state.get("key"))

    if state_key in {"INVALIDATED", "WATCHING", "LIQUIDITY_SWEEP", "WAITING_MSS"}:
        return "hidden"
    if state_key == "WAITING_IFVG":
        return "projected"
    if state_key in {"ENTRY_READY", "TRADE_ACTIVE", "TRADE_COMPLETE"} and trade_decision == "ACCEPT":
        return "final"
    return "hidden"


def _build_objective_plan(
    *,
    direction: str | None,
    levels: dict[str, object],
    swings: dict[str, list[dict[str, object]]],
    equal_levels: dict[str, list[dict[str, object]]],
    fvgs: list[dict[str, object]],
    context_candles: dict[str, pd.DataFrame],
    liquidity_map: dict[str, object],
) -> dict[str, object]:
    entry_zone = levels.get("entry_zone") or {}
    entry_price = None
    if entry_zone:
        entry_price = (float(entry_zone["top"]) + float(entry_zone["bottom"])) / 2

    return build_objective_plan(
        direction=direction,
        entry_price=entry_price,
        stop_loss=levels.get("stop_loss"),
        swings=swings,
        equal_levels=equal_levels,
        fvgs=fvgs,
        context_candles=context_candles,
        liquidity_map=liquidity_map,
    )


def _levels_with_objectives(
    levels: dict[str, object],
    objective_plan: dict[str, object],
) -> dict[str, object]:
    accepted = levels_from_objective_plan(
        entry_zone=levels.get("entry_zone"),
        stop_loss=levels.get("stop_loss"),
        objective_plan=objective_plan,
    )
    if not objective_plan.get("trade_accepted"):
        return {**levels, "tp1": None, "tp2": None, "rr1": None, "rr2": None}

    return {
        **levels,
        **accepted,
        "primary_objective": objective_plan.get("primary_objective"),
        "secondary_objective": objective_plan.get("secondary_objective"),
        "display_note": objective_plan.get("summary"),
    }


def _technical_sequence_ready(checklist: dict[str, bool]) -> bool:
    required = ("htf_fvg", "liquidity_sweep", "mss", "ifvg", "displacement", "session")
    return all(checklist.get(key, False) for key in required)


def _gate_objective_plan(
    objective_plan: dict[str, object],
    checklist: dict[str, bool],
) -> dict[str, object]:
    """Keep objectives hidden until every pre-trade confirmation is complete."""
    if _technical_sequence_ready(checklist):
        return objective_plan

    return {
        "decision": "PENDING",
        "trade_accepted": False,
        "minimum_rr": objective_plan.get("minimum_rr", 1.5),
        "risk": None,
        "trade_quality": 0,
        "primary_objective": None,
        "secondary_objective": None,
        "best_rejected_objective": None,
        "candidates": [],
        "reason": "Objective scoring waits until the ICT sequence, session, and displacement filters are complete.",
        "summary": "Trade objectives are not available yet.",
    }


def _active_zone(
    setup_status: str,
    htf_fvg: dict[str, object] | None,
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
) -> dict[str, object]:
    if setup_status == "VALID SETUP" and ifvg:
        return {"name": "IFVG Entry Zone", **ifvg}
    if setup_status == "WAITING FOR IFVG" and mss:
        return {"name": "MSS Level", **mss}
    if setup_status == "WAITING FOR MSS" and sweep:
        return {"name": "Liquidity Sweep", **sweep}
    if htf_fvg:
        return {"name": "HTF FVG Context", **htf_fvg}
    return {}


def _invalidation_level(
    direction: str | None,
    levels: dict[str, object],
    sweep: dict[str, object] | None,
) -> float | None:
    if levels.get("stop_loss") is not None:
        return levels["stop_loss"]
    if sweep and direction == "bullish":
        return round(float(sweep["swept_price"]), 6)
    if sweep and direction == "bearish":
        return round(float(sweep["swept_price"]), 6)
    return None


def _is_invalidated(
    candles: pd.DataFrame,
    direction: str | None,
    sweep: dict[str, object] | None,
    ifvg: dict[str, object] | None,
) -> bool:
    if sweep is None:
        return False

    current_close = float(candles.iloc[-1]["close"])

    if direction == "bullish" and current_close < float(sweep["swept_price"]):
        return True
    if direction == "bearish" and current_close > float(sweep["swept_price"]):
        return True

    if ifvg and direction == "bullish" and current_close < float(ifvg["bottom_price"]):
        return True
    if ifvg and direction == "bearish" and current_close > float(ifvg["top_price"]):
        return True

    return False


def _invalidation_reason(
    setup_status: str,
    direction: str | None,
    sweep: dict[str, object] | None,
    ifvg: dict[str, object] | None,
) -> str | None:
    """Explain why trade levels are hidden when a sequence is invalidated."""
    if setup_status != "INVALIDATED":
        return None

    if ifvg and direction == "bullish":
        return "Bullish sequence invalidated because price closed below the IFVG support zone."
    if ifvg and direction == "bearish":
        return "Bearish sequence invalidated because price closed above the IFVG resistance zone."
    if sweep:
        return "Liquidity sweep sequence invalidated because price closed back through the swept level."
    return "Setup invalidated. Wait for a fresh liquidity sweep and structure sequence."


def _missing_confirmation(setup_status: str, direction: str | None) -> str:
    if setup_status == "NO SETUP":
        return "Wait for HTF context and a recent liquidity sweep."
    if setup_status == "HTF CONTEXT FOUND":
        return "Wait for price to sweep liquidity near current price."
    if setup_status == "LIQUIDITY SWEPT":
        return "Wait for HTF FVG context and market structure confirmation."
    if setup_status == "WAITING FOR MSS":
        if direction == "bullish":
            return "Wait for price to close above a recent swing high to confirm bullish MSS."
        if direction == "bearish":
            return "Wait for price to close below a recent swing low to confirm bearish MSS."
        return "Wait for candle-close market structure confirmation."
    if setup_status == "WAITING FOR IFVG":
        return "Wait for IFVG retest and risk/reward confirmation."
    if setup_status == "VALID SETUP":
        return "All required confirmations are present."
    if setup_status == "INVALIDATED":
        return "Current sequence is invalidated. Wait for a fresh sweep and structure sequence."
    return "Wait for the next required confirmation."


def _suggested_action(setup_status: str) -> str:
    actions = {
        "NO SETUP": "No valid trade yet.",
        "HTF CONTEXT FOUND": "No valid trade yet. Wait for liquidity to be swept.",
        "LIQUIDITY SWEPT": "No valid trade yet. Wait for market structure confirmation.",
        "WAITING FOR MSS": "No valid trade yet. Wait for market structure shift.",
        "WAITING FOR IFVG": "No valid trade yet. Wait for IFVG retest.",
        "VALID SETUP": "Setup valid based on current rules.",
        "INVALIDATED": "No valid trade. Setup invalidated.",
    }
    return actions.get(setup_status, "No valid trade yet.")


def _session_adjusted_action(
    setup_status: str,
    session_context: dict[str, object],
    economic_news: dict[str, object],
) -> str:
    session_name = str(session_context["name"])
    expected = str(session_context["expected_behavior"])

    if economic_news.get("restriction_active"):
        return f"No valid entry during high-impact news restriction. {economic_news.get('warning', '')}"

    if not session_context["entry_allowed"]:
        return f"No valid entry during {session_name}. {expected}"

    if setup_status == "VALID SETUP":
        return f"Setup valid during {session_name}. {expected}"

    return f"{_suggested_action(setup_status)} {expected}"


def _session_missing_confirmation(
    current_message: str,
    session_context: dict[str, object],
    economic_news: dict[str, object],
    setup_status: str,
) -> str:
    if setup_status == "VALID SETUP":
        return current_message

    if economic_news.get("restriction_active"):
        return "High-impact news filter active: wait until the restriction window has passed."

    if not session_context["entry_allowed"]:
        return f"Session filter active: {session_context['name']} does not allow new valid entries."

    return current_message


def _legacy_kill_zone(session_context: dict[str, object]) -> dict[str, object]:
    """Keep older frontend/debug consumers compatible during the transition."""
    return {
        "timezone": session_context["timezone"],
        "current_time": session_context["current_time"],
        "current_session": session_context["name"],
        "next_kill_zone": session_context["next_session"],
        "time_remaining": session_context["time_remaining_label"],
        "entry_allowed": session_context["entry_allowed"],
    }


def _checklist_status(checklist: dict[str, bool]) -> dict[str, str]:
    return {
        "htf_fvg": _status_text(checklist["htf_fvg"]),
        "liquidity_sweep": _status_text(checklist["liquidity_sweep"]),
        "mss": _status_text(checklist["mss"]),
        "ifvg": _status_text(checklist["ifvg"]),
        "premium_discount": _status_text(checklist["premium_discount"]),
        "displacement": _status_text(checklist["displacement"]),
        "session": _status_text(checklist["session"]),
        "risk_reward": _status_text(checklist["risk_reward"]),
    }


def _status_text(value: bool) -> str:
    return "detected" if value else "waiting"


def _mentor_view(
    symbol: str,
    bias: str,
    setup_status: str,
    score: int,
    checklist: dict[str, bool],
    levels: dict[str, object],
    levels_mode: str,
    invalidation_reason: str | None,
    missing_confirmation: str,
    suggested_action: str,
    ict_state: dict[str, object],
    macro_context: dict[str, object],
    session_context: dict[str, object],
    htf_fvg: dict[str, object] | None,
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    order_blocks: dict[str, object],
    liquidity_map: dict[str, object],
    mss_trigger: dict[str, object],
    current_price: float,
    setup_quality: int,
    trade_quality: int,
    trade_decision: str,
    objective_plan: dict[str, object],
) -> dict[str, object]:
    """Translate scanner output into a trader-friendly explanation."""
    phase = _mentor_phase(macro_context, session_context)
    market_bias = _mentor_bias(bias)
    trade_status = _trade_lifecycle_status(ict_state, trade_decision)
    journey = _setup_journey(
        checklist,
        ict_state,
        levels_mode,
        liquidity_map,
        htf_fvg,
        sweep,
        mss,
        ifvg,
        order_blocks,
        levels,
        current_price,
        bias,
    )
    current_stage = next((stage for stage in journey if stage["is_current"]), journey[0])
    story_steps = _chronological_story_steps(
        journey,
        bias,
        htf_fvg,
        sweep,
        mss,
        ifvg,
        order_blocks,
        mss_trigger,
    )
    if trade_decision == "REJECT" and str(ict_state.get("key")) == "ENTRY_READY":
        story_steps.append(
            {
                "key": "objective",
                "status": "waiting",
                "text": str(objective_plan.get("summary", "No objective meets the minimum reward-to-risk requirement.")),
            }
        )
    next_trigger = _next_trigger(ict_state, bias, session_context, mss_trigger)
    if_this_happens = _if_this_happens(ict_state, bias, next_trigger)
    what_next = _mentor_next_step(
        setup_status,
        missing_confirmation,
        suggested_action,
        session_context,
        ict_state=ict_state,
        next_trigger=next_trigger,
    )
    if trade_decision == "REJECT" and str(ict_state.get("key")) == "ENTRY_READY":
        next_trigger = "Wait for a fresh setup with at least 1.50R to a meaningful objective."
        if_this_happens = "If a new setup provides sufficient reward to external liquidity, TradeScor can approve a trade plan."
        what_next = "Stand down. The technical setup is complete, but the trade economics are not acceptable."
    elif trade_decision == "PENDING" and str(ict_state.get("key")) == "ENTRY_READY":
        next_trigger = missing_confirmation or suggested_action
        if_this_happens = "Once the remaining setup filters align, TradeScor will score the available objectives."
        what_next = suggested_action or "Wait for the remaining setup filters before evaluating a trade plan."
    opportunity = _mentor_trade_opportunity(
        ict_state,
        levels_mode,
        levels,
        invalidation_reason,
        trade_decision,
        objective_plan,
    )
    narrative = _mentor_narrative(
        symbol,
        market_bias,
        phase,
        trade_status,
        setup_status,
        ict_state,
        sweep,
        mss,
        ifvg,
        order_blocks,
        next_trigger,
        if_this_happens,
        what_next,
        trade_decision,
        objective_plan,
    )

    return {
        "market_bias": market_bias,
        "market_phase": phase,
        "trade_status": trade_status,
        "trade_confidence": setup_quality,
        "setup_quality": setup_quality,
        "trade_quality": trade_quality,
        "trade_decision": trade_decision,
        "objective_plan": objective_plan,
        "current_stage": current_stage,
        "setup_journey": journey,
        "story_steps": story_steps,
        "why": story_steps,
        "next_trigger": next_trigger,
        "if_this_happens": if_this_happens,
        "what_next": what_next,
        "progression": journey,
        "trade_opportunity": opportunity,
        "narrative": narrative,
    }


def _setup_journey(
    checklist: dict[str, bool],
    ict_state: dict[str, object],
    levels_mode: str,
    liquidity_map: dict[str, object],
    htf_fvg: dict[str, object] | None,
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    order_blocks: dict[str, object],
    levels: dict[str, object],
    current_price: float,
    bias: str,
) -> list[dict[str, object]]:
    """Return the institutional setup journey with exactly one current stage."""
    state_key = str(ict_state.get("key"))
    state_order = int(ict_state.get("order", 0))
    setup_stages = [
        ("watching", "Watching", 0),
        ("liquidity_sweep", "Liquidity Sweep", 1),
        ("waiting_mss", "Waiting MSS", 2),
        ("waiting_ifvg", "Waiting IFVG", 3),
        ("entry_ready", "Entry Ready", 4),
    ]

    stages: list[dict[str, object]] = []
    invalidated = state_key == "INVALIDATED"
    current_order = 4 if state_key in {"TRADE_ACTIVE", "TRADE_COMPLETE"} else state_order

    for key, label, required_order in setup_stages:
        if invalidated:
            status = "inactive"
            is_current = False
        elif required_order < current_order:
            status = "completed"
            is_current = False
        elif required_order == current_order:
            status = "current"
            is_current = True
        else:
            status = "inactive"
            is_current = False

        stages.append(
            {
                "key": key,
                "label": label,
                "status": status,
                "is_current": is_current,
                "levels_mode": levels_mode if key in {"waiting_ifvg", "entry_ready"} else "hidden",
            }
        )

    if invalidated:
        stages.append(
            {
                "key": "invalidated",
                "label": "Invalidated",
                "status": "invalidated",
                "is_current": True,
                "levels_mode": "hidden",
            }
        )

    return stages


def _target_reached(
    levels: dict[str, object],
    current_price: float,
    bias: str,
    target_key: str,
    levels_mode: str,
) -> bool:
    target = levels.get(target_key)
    if levels_mode != "final" or target is None:
        return False
    if bias == "LONG":
        return float(current_price) >= float(target)
    if bias == "SHORT":
        return float(current_price) <= float(target)
    return False


def _chronological_story_steps(
    journey: list[dict[str, object]],
    bias: str,
    htf_fvg: dict[str, object] | None,
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    order_blocks: dict[str, object],
    mss_trigger: dict[str, object],
) -> list[dict[str, str]]:
    """Create a chronological story that mirrors the journey stages."""
    current_key = next((stage["key"] for stage in journey if stage["is_current"]), "")
    visible_keys = {str(stage["key"]) for stage in journey}
    order_block = order_blocks.get("nearest") or {}
    story = [
        _story_item(
            "watching",
            current_key,
            _journey_completed(journey, "watching"),
            "The market has moved beyond passive observation and started the ICT sequence.",
            "TradeScor is watching for a clean liquidity sweep before anything else matters.",
        ),
        _story_item(
            "liquidity_sweep",
            current_key,
            bool(sweep),
            _sweep_text(sweep),
            "Price has not swept the target liquidity yet.",
        ),
        _story_item(
            "waiting_mss",
            current_key,
            bool(mss),
            _mss_text(mss),
            _waiting_mss_story(bias, mss_trigger),
        ),
        _story_item(
            "waiting_ifvg",
            current_key,
            bool(ifvg),
            _ifvg_text(ifvg) if not order_block else f"{_ifvg_text(ifvg)} {_order_block_text(order_block)}",
            "MSS has formed. Now TradeScor is waiting for an IFVG confirmation before entry levels exist.",
        ),
        _story_item(
            "entry_ready",
            current_key,
            _journey_completed(journey, "entry_ready"),
            "The ICT setup sequence has reached Entry Ready.",
            "Entry, stop, and targets only appear after IFVG confirmation.",
        ),
    ]

    return [item for item in story if item["key"] in visible_keys]


def _journey_completed(journey: list[dict[str, object]], key: str) -> bool:
    return any(stage["key"] == key and stage["status"] == "completed" for stage in journey)


def _story_item(
    key: str,
    current_key: str,
    completed: bool,
    completed_text: str,
    waiting_text: str,
) -> dict[str, str]:
    if completed:
        status = "completed"
        text = completed_text
    elif key == current_key:
        status = "current"
        text = waiting_text
    else:
        status = "inactive"
        text = waiting_text

    return {"key": key, "status": status, "text": text}


def _waiting_mss_story(
    bias: str,
    mss_trigger: dict[str, object],
) -> str:
    if mss_trigger:
        level = round(float(mss_trigger["level"]), 6)
        if bias == "LONG":
            return f"Market Structure Shift has NOT occurred. TradeScor is waiting for a candle close above {level}."
        if bias == "SHORT":
            return f"Market Structure Shift has NOT occurred. TradeScor is waiting for a candle close below {level}."

    return _missing_mss_text(bias)


def _next_trigger(
    ict_state: dict[str, object],
    bias: str,
    session_context: dict[str, object],
    mss_trigger: dict[str, object],
) -> str:
    """Return the single event that advances the setup journey."""
    state_key = str(ict_state.get("key"))

    if state_key == "INVALIDATED":
        return "Fresh liquidity sweep must form before the sequence can restart."
    if not session_context.get("entry_allowed") and state_key not in {"ENTRY_READY", "TRADE_ACTIVE", "TRADE_COMPLETE"}:
        return f"Wait for an active entry window. Next session: {session_context.get('next_session', 'next kill zone')}."
    if state_key == "WATCHING":
        return "Wait for price to sweep a clear liquidity pool."
    if state_key == "LIQUIDITY_SWEEP":
        return "Confirm higher-timeframe context, then wait for market structure to shift."
    if state_key == "WAITING_MSS" and mss_trigger:
        level = round(float(mss_trigger["level"]), 6)
        if bias == "LONG":
            return f"Close above recent swing high at {level}."
        if bias == "SHORT":
            return f"Close below recent swing low at {level}."
    if state_key == "WAITING_MSS":
        return "Wait for price to close beyond the recent structure level."
    if state_key == "WAITING_IFVG":
        if bias == "LONG":
            return "Form and retest a bullish IFVG."
        if bias == "SHORT":
            return "Form and retest a bearish IFVG."
        return "Form and retest an IFVG."
    if state_key == "ENTRY_READY":
        return "Price must trade into the active entry zone."
    if state_key == "TRADE_ACTIVE":
        return "Manage the active trade toward TP1 and TP2."
    if state_key == "TRADE_COMPLETE":
        return "Wait for a fresh setup sequence before considering another trade."
    return "Wait for the next clean ICT sequence."


def _if_this_happens(
    ict_state: dict[str, object],
    bias: str,
    next_trigger: str,
) -> str:
    state_key = str(ict_state.get("key"))

    if state_key == "INVALIDATED":
        return "If a fresh sweep and new structure sequence forms, TradeScor will rebuild the setup journey from the beginning."
    if state_key in {"WATCHING", "LIQUIDITY_SWEEP"}:
        return "If liquidity is swept cleanly, TradeScor will begin watching for structure to break."
    if state_key == "WAITING_MSS":
        if bias == "LONG":
            return "If price closes above the recent swing high, TradeScor will begin searching for a bullish IFVG."
        if bias == "SHORT":
            return "If price closes below the recent swing low, TradeScor will begin searching for a bearish IFVG."
        return "If structure shifts after a liquidity sweep, TradeScor will begin searching for an IFVG."
    if state_key == "WAITING_IFVG":
        return "If the IFVG forms, entry levels will become visible and the setup moves toward entry readiness."
    if state_key == "ENTRY_READY":
        return "If price trades into the active entry zone, the trade can move from watching to active management."
    if state_key == "TRADE_ACTIVE":
        return "If TP1 or TP2 is reached, TradeScor will update the active management state."
    if state_key == "TRADE_COMPLETE":
        return "If a new sequence starts, the current completed trade context will reset."
    return f"If this happens: {next_trigger}"


def _trade_lifecycle_status(
    ict_state: dict[str, object],
    trade_decision: str = "PENDING",
) -> str:
    labels = {
        "WATCHING": "Watching",
        "LIQUIDITY_SWEEP": "Building Setup",
        "WAITING_MSS": "Building Setup",
        "WAITING_IFVG": "Waiting for IFVG",
        "ENTRY_READY": "Entry Ready",
        "TRADE_ACTIVE": "Trade Active",
        "TRADE_COMPLETE": "Trade Complete",
        "INVALIDATED": "Reset",
    }
    if str(ict_state.get("key")) == "ENTRY_READY" and trade_decision == "REJECT":
        return "No Trade"
    if str(ict_state.get("key")) == "ENTRY_READY" and trade_decision == "PENDING":
        return "Building Setup"
    return labels.get(str(ict_state.get("key")), "Watching")


def _mentor_phase(
    macro_context: dict[str, object],
    session_context: dict[str, object],
) -> str:
    phase = (macro_context.get("market_phase") or {}).get("current_phase")
    if phase:
        return str(phase)
    return str(session_context.get("phase", "Waiting"))


def _mentor_bias(bias: str) -> str:
    if bias == "LONG":
        return "Bullish"
    if bias == "SHORT":
        return "Bearish"
    return "Neutral"


def _mentor_trade_status(setup_status: str) -> str:
    if setup_status in {"VALID SETUP", "ENTRY READY"}:
        return "Entry Ready"
    if setup_status == "INVALIDATED":
        return "Invalidated"
    if setup_status in {"WAITING FOR MSS", "WAITING FOR IFVG", "LIQUIDITY SWEPT"}:
        return "Building Setup"
    return "Waiting"


def _mentor_why(
    checklist: dict[str, bool],
    bias: str,
    htf_fvg: dict[str, object] | None,
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    order_blocks: dict[str, object],
    session_context: dict[str, object],
) -> list[dict[str, str]]:
    order_block = order_blocks.get("nearest") or {}
    bias_text = _mentor_bias(bias).lower()
    context_text = (
        f"Higher-timeframe context supports a {bias_text} idea."
        if bias in {"LONG", "SHORT"}
        else "Higher-timeframe context is present, but directional bias is still neutral."
    )
    why = [
        _why_item(
            checklist["htf_fvg"],
            context_text,
            "No active higher-timeframe fair value gap is guiding this chart yet.",
        ),
        _why_item(
            checklist["liquidity_sweep"],
            _sweep_text(sweep),
            "Price has not swept a clear liquidity pool yet.",
        ),
        _why_item(
            bool(order_block),
            _order_block_text(order_block),
            "No clean order block reaction is active yet.",
        ),
        _why_item(
            checklist["mss"],
            _mss_text(mss),
            _missing_mss_text(bias),
        ),
        _why_item(
            checklist["ifvg"],
            _ifvg_text(ifvg),
            "No IFVG confirmation has formed yet.",
        ),
    ]

    if not session_context.get("entry_allowed"):
        why.append(
            {
                "status": "waiting",
                "text": f"{session_context.get('name', 'Current session')} is a context window, not an entry window.",
            }
        )

    return why


def _why_item(condition: bool, confirmed_text: str, waiting_text: str) -> dict[str, str]:
    return {
        "status": "confirmed" if condition else "waiting",
        "text": confirmed_text if condition else waiting_text,
    }


def _sweep_text(sweep: dict[str, object] | None) -> str:
    if not sweep:
        return "Price has not swept a clear liquidity pool yet."
    side = "sell-side" if sweep.get("side") == "sell-side" else "buy-side"
    return f"Price swept {side} liquidity and closed back inside the range."


def _order_block_text(order_block: dict[str, object]) -> str:
    label = str(order_block.get("label", "order block")).lower()
    direction = str(order_block.get("direction", "")).lower()
    if direction in {"bullish", "bearish"}:
        return f"Price is respecting a {direction} {label.replace(direction, '').strip()} zone."
    return "A nearby order block is part of the current reaction area."


def _mss_text(mss: dict[str, object] | None) -> str:
    if not mss:
        return "No market structure shift has formed yet."
    return f"Market structure shifted {str(mss.get('direction', '')).lower()} after the sweep."


def _missing_mss_text(bias: str) -> str:
    if bias == "LONG":
        return "No bullish Market Structure Shift has formed yet."
    if bias == "SHORT":
        return "No bearish Market Structure Shift has formed yet."
    return "No Market Structure Shift has formed yet."


def _ifvg_text(ifvg: dict[str, object] | None) -> str:
    if not ifvg:
        return "No IFVG confirmation has formed yet."
    return f"A {str(ifvg.get('type', '')).lower()} IFVG entry zone is present."


def _mentor_next_step(
    setup_status: str,
    missing_confirmation: str,
    suggested_action: str,
    session_context: dict[str, object],
    ict_state: dict[str, object],
    next_trigger: str = "",
) -> str:
    state_key = str(ict_state.get("key"))

    if not session_context.get("entry_allowed") and state_key not in {"ENTRY_READY", "TRADE_ACTIVE", "TRADE_COMPLETE"}:
        return f"Wait for an active entry window. Next session: {session_context.get('next_session', 'next kill zone')}."
    if state_key == "ENTRY_READY":
        return "All confirmations have aligned. Wait for price to trade into the active entry zone."
    if state_key == "TRADE_ACTIVE":
        return "The setup is active. Manage the trade against the visible levels only."
    if state_key == "TRADE_COMPLETE":
        return "The trade sequence is complete. Wait for the next fresh liquidity sweep."
    if state_key == "INVALIDATED":
        return "Stand down and wait for a fresh liquidity sweep and structure sequence."
    if state_key == "WAITING_MSS":
        return next_trigger or missing_confirmation
    if state_key == "WAITING_IFVG":
        return next_trigger or "Wait for price to retest or confirm the IFVG before treating the setup as ready."
    if state_key == "LIQUIDITY_SWEEP":
        return "Wait for market structure to shift in the direction of the intended move."
    return suggested_action or "Wait for context, liquidity, and structure to align."


def _mentor_trade_opportunity(
    ict_state: dict[str, object],
    levels_mode: str,
    levels: dict[str, object],
    invalidation_reason: str | None,
    trade_decision: str,
    objective_plan: dict[str, object],
) -> dict[str, object]:
    state_key = str(ict_state.get("key"))

    if state_key == "INVALIDATED":
        return {
            "status": "Invalidated",
            "message": invalidation_reason or "Setup invalidated. No trade is available.",
            "levels_mode": "hidden",
            "levels": {},
            "objective_plan": objective_plan,
        }
    if state_key == "ENTRY_READY" and trade_decision == "REJECT":
        return {
            "status": "No Trade",
            "message": str(objective_plan.get("reason", "The available reward is too small.")),
            "levels_mode": "hidden",
            "levels": {},
            "objective_plan": objective_plan,
        }
    if state_key == "TRADE_COMPLETE":
        return {
            "status": "Trade Complete",
            "message": "The visible trade sequence has completed. Wait for a fresh setup.",
            "levels_mode": levels_mode,
            "levels": levels,
            "objective_plan": objective_plan,
        }
    if state_key == "TRADE_ACTIVE":
        return {
            "status": "Trade Active",
            "message": "Trade is active. Manage the visible levels only.",
            "levels_mode": levels_mode,
            "levels": levels,
            "objective_plan": objective_plan,
        }
    if state_key == "ENTRY_READY" and levels_mode == "final":
        return {
            "status": "Entry Ready",
            "message": "Entry-ready levels are available.",
            "levels_mode": levels_mode,
            "levels": levels,
            "objective_plan": objective_plan,
        }
    if state_key == "WAITING_IFVG" and levels_mode == "projected":
        return {
            "status": "Potential Entry Area",
            "message": "Potential Entry Area - Waiting for IFVG.",
            "levels_mode": levels_mode,
            "levels": levels,
            "objective_plan": objective_plan,
        }
    return {
        "status": "No Trade",
        "message": "No valid trade yet.",
        "levels_mode": "hidden",
        "levels": {},
        "objective_plan": objective_plan,
    }


def _mentor_progression(
    checklist: dict[str, bool],
    setup_status: str,
    levels_mode: str,
) -> list[dict[str, str]]:
    invalidated = setup_status == "INVALIDATED"
    return [
        _progress_step("Market Context", checklist["htf_fvg"], False, invalidated),
        _progress_step("Liquidity Sweep", checklist["liquidity_sweep"], checklist["htf_fvg"], invalidated),
        _progress_step("Market Structure Shift", checklist["mss"], checklist["liquidity_sweep"], invalidated),
        _progress_step("IFVG Confirmation", checklist["ifvg"], checklist["mss"], invalidated),
        _progress_step("Entry", levels_mode == "final", checklist["ifvg"], invalidated),
        {"label": "Trade Active", "status": "inactive" if not invalidated else "invalidated"},
    ]


def _progress_step(
    label: str,
    confirmed: bool,
    waiting: bool,
    invalidated: bool,
) -> dict[str, str]:
    if invalidated:
        return {"label": label, "status": "invalidated"}
    if confirmed:
        return {"label": label, "status": "confirmed"}
    if waiting:
        return {"label": label, "status": "waiting"}
    return {"label": label, "status": "inactive"}


def _mentor_narrative(
    symbol: str,
    market_bias: str,
    phase: str,
    trade_status: str,
    setup_status: str,
    ict_state: dict[str, object],
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    order_blocks: dict[str, object],
    next_trigger: str,
    if_this_happens: str,
    what_next: str,
    trade_decision: str,
    objective_plan: dict[str, object],
) -> str:
    state_key = str(ict_state.get("key"))
    bias_text = market_bias.lower()
    pieces = [f"{symbol} is currently trading with a {bias_text} bias during a {phase.lower()} phase."]

    if state_key == "INVALIDATED":
        pieces.append("The prior setup has been invalidated, so TradeScor is waiting for a fresh sequence.")
        pieces.append("No trade is recommended.")
        pieces.append(f"Next trigger: {next_trigger}")
        return " ".join(pieces)

    if sweep and state_key != "WATCHING":
        swept = "sell-side" if sweep.get("side") == "sell-side" else "buy-side"
        pieces.append(f"Price has swept {swept} liquidity.")
    else:
        pieces.append("The scanner has not seen a clean liquidity sweep yet.")

    order_block = order_blocks.get("nearest") or {}
    if order_block and state_key in {"WAITING_IFVG", "ENTRY_READY", "TRADE_ACTIVE", "TRADE_COMPLETE"}:
        pieces.append(f"Price is near a {str(order_block.get('direction', '')).lower()} order block.")

    if state_key in {"WAITING_IFVG", "ENTRY_READY", "TRADE_ACTIVE", "TRADE_COMPLETE"} and mss:
        pieces.append("Market structure has shifted after the sweep.")
    elif state_key == "WAITING_MSS":
        pieces.append("Market Structure Shift has not been confirmed.")

    if state_key in {"ENTRY_READY", "TRADE_ACTIVE", "TRADE_COMPLETE"} and ifvg:
        pieces.append("An IFVG confirmation is present.")
    elif state_key == "WAITING_IFVG":
        pieces.append("IFVG confirmation is still missing.")

    if state_key == "ENTRY_READY" and trade_decision == "REJECT":
        reason = str(objective_plan.get("reason", "the available reward is too small")).lower()
        pieces.append(f"The technical sequence is complete, but no trade is recommended because {reason}")
    elif state_key == "ENTRY_READY" and trade_decision == "PENDING":
        pieces.append("The ICT sequence has reached IFVG confirmation, but TradeScor is waiting for the remaining filters before scoring a trade objective.")
    elif state_key == "ENTRY_READY":
        pieces.append("A trade can be considered only if price returns to the active entry zone.")
    elif state_key == "TRADE_ACTIVE":
        pieces.append("The trade is active, so TradeScor is focused on management levels.")
    elif state_key == "TRADE_COMPLETE":
        pieces.append("The trade sequence has completed.")
    else:
        pieces.append("No trade is recommended yet.")

    pieces.append(f"Next trigger: {next_trigger}")
    pieces.append(if_this_happens or what_next)
    return " ".join(pieces)


def _macro_adjusted_score(
    base_score: int,
    dxy_correlation: dict[str, object],
    economic_news: dict[str, object],
) -> int:
    score = base_score + int(dxy_correlation.get("score_impact", 0) or 0)

    if economic_news.get("restriction_active"):
        score -= 15

    return max(0, min(100, score))


def _top_down_bias(top_down_analysis: dict[str, object] | None) -> str:
    if not top_down_analysis:
        return "NEUTRAL"

    alignment = str(top_down_analysis.get("overall_alignment", "Neutral"))
    if "Bullish" in alignment:
        return "LONG"
    if "Bearish" in alignment:
        return "SHORT"
    return "NEUTRAL"


def _chart_overlays(
    candles: pd.DataFrame,
    htf_fvg: dict[str, object] | None,
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    levels: dict[str, object],
    setup_status: str,
    levels_mode: str,
    equal_levels: dict[str, list[dict[str, object]]],
    order_blocks: dict[str, object],
    mss_trigger: dict[str, object] | None = None,
    ict_state: dict[str, object] | None = None,
) -> dict[str, object]:
    current_price = float(candles.iloc[-1]["close"])
    current_time = candles.iloc[-1]["time"]
    entry_source_zone = ifvg or htf_fvg
    state_key = str((ict_state or {}).get("key", "WATCHING"))
    final_states = {"ENTRY_READY", "TRADE_ACTIVE", "TRADE_COMPLETE"}
    show_context_fvg = state_key in {"WATCHING", "LIQUIDITY_SWEEP", "WAITING_MSS", "WAITING_IFVG"}
    show_sweep = state_key in {"LIQUIDITY_SWEEP", "WAITING_MSS"}
    show_mss_trigger = state_key == "WAITING_MSS"
    show_entry_zone = state_key in {"WAITING_IFVG", *final_states}
    show_trade_levels = levels_mode == "final" and state_key in final_states

    trade_levels = None
    if levels_mode in {"final", "projected"} and show_entry_zone:
        trade_levels = {
            "entry_zone": levels.get("entry_zone") or None,
            "stop_loss": levels.get("stop_loss") if show_trade_levels else None,
            "tp1": levels.get("tp1") if show_trade_levels else None,
            "tp2": levels.get("tp2") if show_trade_levels else None,
            "mode": levels_mode,
        }

    active_fvg = _zone_overlay(
        htf_fvg,
        _fvg_label(htf_fvg, "HTF FVG"),
        current_time,
    ) if show_context_fvg else None
    ifvg_zone = _zone_overlay(
        ifvg,
        "IFVG Entry Zone",
        current_time,
    ) if state_key in final_states else None
    entry_zone = _entry_zone_overlay(levels, entry_source_zone, current_time, levels_mode) if show_entry_zone else None
    order_block = _zone_overlay(
        order_blocks.get("nearest") or {},
        (order_blocks.get("nearest") or {}).get("label", "Order Block"),
        current_time,
    ) if state_key in {"WAITING_IFVG", *final_states} else None

    return {
        "current_price": {"price": round(current_price, 6), "time": _to_unix_seconds(current_time)},
        "active_fvg": active_fvg,
        "liquidity_sweep": _liquidity_zone(sweep, equal_levels) if show_sweep else {},
        "mss_level": (mss_trigger or mss or {}) if show_mss_trigger else {},
        "ifvg_zone": ifvg_zone,
        "entry_zone": entry_zone,
        "order_block": order_block,
        "stop_loss": levels.get("stop_loss") if show_trade_levels else None,
        "tp1": levels.get("tp1") if show_trade_levels else None,
        "tp2": levels.get("tp2") if show_trade_levels else None,
        "levels_mode": levels_mode,
        "trade_levels": trade_levels,
    }


def _zone_overlay(
    zone: dict[str, object] | None,
    label: str,
    current_time,
) -> dict[str, object] | None:
    """Convert scanner zones to frontend rectangle overlays."""
    if not zone:
        return None

    top = zone.get("top_price", zone.get("top"))
    bottom = zone.get("bottom_price", zone.get("bottom"))
    start_time = zone.get("start_time")

    if top is None or bottom is None or start_time is None:
        return None

    end_time = zone.get("rectangle_end_time") or zone.get("mitigated_time") or current_time

    return {
        "type": zone.get("type", ""),
        "label": label,
        "tag": _chart_tag(label, zone.get("type", "")),
        "tooltip": label,
        "start_time": _to_unix_seconds(start_time),
        "end_time": _to_unix_seconds(end_time),
        "top": round(float(top), 6),
        "bottom": round(float(bottom), 6),
        "top_price": round(float(top), 6),
        "bottom_price": round(float(bottom), 6),
        "status": zone.get("status", "active"),
    }


def _entry_zone_overlay(
    levels: dict[str, object],
    source_zone: dict[str, object] | None,
    current_time,
    levels_mode: str,
) -> dict[str, object] | None:
    """Build the entry zone rectangle only when levels are visible."""
    if levels_mode not in {"final", "projected"}:
        return None

    entry_zone = levels.get("entry_zone")
    if not entry_zone:
        return None

    source = source_zone or {}
    start_time = source.get("start_time") or current_time

    return {
        "type": "entry_zone",
        "label": "Entry Zone" if levels_mode == "final" else "Projected Entry Zone",
        "tag": "ENTRY",
        "tooltip": "Entry Zone" if levels_mode == "final" else "Potential Entry Area - Waiting for IFVG",
        "start_time": _to_unix_seconds(start_time),
        "end_time": _to_unix_seconds(current_time),
        "top": round(float(entry_zone["top"]), 6),
        "bottom": round(float(entry_zone["bottom"]), 6),
        "status": levels_mode,
    }


def _fvg_label(zone: dict[str, object] | None, fallback: str) -> str:
    if not zone:
        return fallback

    zone_type = str(zone.get("type", "")).title()
    if zone_type in {"Bullish", "Bearish"}:
        return f"HTF {zone_type} FVG"
    return fallback


def _chart_tag(label: str, zone_type: object) -> str:
    text = f"{label} {zone_type}".lower()
    if "ifvg" in text:
        return "IFVG"
    if "order block" in text or "breaker" in text or "ob" in text:
        return "OB"
    if "fvg" in text:
        return "FVG"
    return "ZONE"


def _to_unix_seconds(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)

    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")

    return int(timestamp.timestamp())


def _market_context(
    candles: pd.DataFrame,
    direction: str | None,
    htf_fvg: dict[str, object] | None,
    session_context: dict[str, object],
) -> dict[str, object]:
    recent = candles.tail(80)
    high = float(recent["high"].max())
    low = float(recent["low"].min())
    midpoint = (high + low) / 2
    current = float(candles.iloc[-1]["close"])

    return {
        "bias_source": "Recent liquidity sweep" if direction else "No recent sweep",
        "active_fvg_type": htf_fvg.get("type") if htf_fvg else None,
        "dealing_range_high": round(high, 6),
        "dealing_range_low": round(low, 6),
        "premium_discount": "discount" if current <= midpoint else "premium",
        "current_session": session_context["name"],
        "entry_allowed": session_context["entry_allowed"],
        "session_phase": session_context["phase"],
    }


def _recent_structure(
    swings: dict[str, list[dict[str, object]]],
    sweep: dict[str, object] | None,
    mss: dict[str, object] | None,
    order_blocks: dict[str, object],
) -> dict[str, object]:
    return {
        "last_swing_high": swings["highs"][-1] if swings["highs"] else {},
        "last_swing_low": swings["lows"][-1] if swings["lows"] else {},
        "liquidity_sweep": sweep or {},
        "mss": mss or {},
        "order_block": order_blocks.get("nearest") or {},
    }


def _mss_trigger(
    swings: dict[str, list[dict[str, object]]],
    sweep: dict[str, object] | None,
    lookback: int = 80,
) -> dict[str, object]:
    """Return the swing level that must break to confirm MSS."""
    if sweep is None:
        return {}

    sweep_index = int(sweep["index"])

    if sweep["direction"] == "bullish":
        reference = _last_swing_before_index(swings["highs"], sweep_index, lookback)
        if not reference:
            return {}
        return {
            "direction": "bullish",
            "index": sweep_index,
            "time": reference["time"],
            "level": float(reference["price"]),
            "label": "MSS Trigger",
            "tag": "MSS",
            "tooltip": "Close above this swing high to confirm bullish MSS.",
            "status": "waiting",
        }

    if sweep["direction"] == "bearish":
        reference = _last_swing_before_index(swings["lows"], sweep_index, lookback)
        if not reference:
            return {}
        return {
            "direction": "bearish",
            "index": sweep_index,
            "time": reference["time"],
            "level": float(reference["price"]),
            "label": "MSS Trigger",
            "tag": "MSS",
            "tooltip": "Close below this swing low to confirm bearish MSS.",
            "status": "waiting",
        }

    return {}


def _last_swing_before_index(
    swings: list[dict[str, object]],
    index: int,
    lookback: int,
) -> dict[str, object] | None:
    previous = [
        swing
        for swing in swings
        if int(swing["index"]) < index and int(swing["index"]) >= index - lookback
    ]
    if not previous:
        return None
    return previous[-1]


def _summary(
    symbol: str,
    bias: str,
    setup_status: str,
    checklist: dict[str, bool],
    missing_confirmation: str,
    suggested_action: str,
) -> str:
    if setup_status == "INVALIDATED":
        return f"{symbol} has an invalidated {bias.lower()} sequence. Entry, stop, and targets are cleared. {suggested_action}"

    if bias == "NEUTRAL":
        return f"{symbol} is neutral because the current chart does not have a complete recent ICT sequence. {suggested_action}"

    pieces = [f"{symbol} currently has a {bias.lower()} bias. Status: {setup_status}."]

    if checklist["liquidity_sweep"]:
        pieces.append("Liquidity has been swept.")
    if checklist["mss"]:
        pieces.append("Market structure has shifted.")
    if checklist["ifvg"]:
        pieces.append("An IFVG entry zone is present.")
    else:
        pieces.append(f"The setup is not valid yet because {missing_confirmation.lower()}")

    pieces.append(f"Action: {suggested_action}")
    return " ".join(pieces)


def _price_tolerance(candles: pd.DataFrame) -> float:
    average_range = float((candles["high"] - candles["low"]).tail(50).mean())
    return max(average_range * 0.2, float(candles.iloc[-1]["close"]) * 0.00005)


def _premium_discount_alignment(candles: pd.DataFrame, direction: str | None) -> bool:
    recent = candles.tail(80)
    dealing_range_high = float(recent["high"].max())
    dealing_range_low = float(recent["low"].min())
    midpoint = (dealing_range_high + dealing_range_low) / 2
    current_price = float(candles.iloc[-1]["close"])

    if direction == "bullish":
        return current_price <= midpoint
    if direction == "bearish":
        return current_price >= midpoint
    return False


def _strong_displacement(candles: pd.DataFrame) -> bool:
    bodies = (candles["close"] - candles["open"]).abs()
    recent_body = float(bodies.tail(5).max())
    average_body = float(bodies.tail(20).mean())
    return average_body > 0 and recent_body >= average_body * 1.5


def _session_filter(candles: pd.DataFrame) -> bool:
    latest_time = pd.Timestamp(candles.iloc[-1]["time"])
    hour = latest_time.hour
    return 7 <= hour <= 20


def _empty_response(
    symbol: str,
    timeframe: str,
    summary: str,
    macro_context: dict[str, object] | None = None,
) -> dict[str, object]:
    macro_context = macro_context or {}
    session_context = macro_context.get("session") or get_session_context()
    checklist = {
        "htf_fvg": False,
        "liquidity_sweep": False,
        "mss": False,
        "ifvg": False,
        "premium_discount": False,
        "displacement": False,
        "session": False,
        "risk_reward": False,
    }
    mentor_view = {
        "market_bias": "Neutral",
        "market_phase": session_context.get("phase", "Waiting"),
        "trade_status": "Watching",
        "trade_confidence": 0,
        "setup_quality": 0,
        "trade_quality": 0,
        "trade_decision": "PENDING",
        "objective_plan": {
            "decision": "PENDING",
            "trade_accepted": False,
            "trade_quality": 0,
            "primary_objective": None,
            "secondary_objective": None,
            "candidates": [],
            "reason": "Not enough candle history to select an objective.",
        },
        "current_stage": {"key": "watching", "label": "Watching", "status": "current", "is_current": True},
        "setup_journey": [
            {"key": "watching", "label": "Watching", "status": "current", "is_current": True},
            {"key": "liquidity_sweep", "label": "Liquidity Sweep", "status": "inactive", "is_current": False},
            {"key": "waiting_mss", "label": "Waiting MSS", "status": "inactive", "is_current": False},
            {"key": "waiting_ifvg", "label": "Waiting IFVG", "status": "inactive", "is_current": False},
            {"key": "entry_ready", "label": "Entry Ready", "status": "inactive", "is_current": False},
        ],
        "story_steps": [
            {"key": "watching", "status": "current", "text": "There is not enough candle history to read the market clearly yet."},
            {"key": "liquidity_sweep", "status": "inactive", "text": "No liquidity sweep, structure shift, or IFVG confirmation is available yet."},
        ],
        "why": [
            {"key": "watching", "status": "current", "text": "There is not enough candle history to read the market clearly yet."},
            {"key": "liquidity_sweep", "status": "inactive", "text": "No liquidity sweep, structure shift, or IFVG confirmation is available yet."},
        ],
        "next_trigger": "Load more candles or wait for more candle history.",
        "if_this_happens": "If more candles load, TradeScor will restart the journey from higher-timeframe context.",
        "what_next": "Load more candles or wait for more candle history before judging the setup.",
        "progression": [],
        "trade_opportunity": {
            "status": "No Trade",
            "message": "No valid trade yet.",
            "levels_mode": "hidden",
            "levels": {},
        },
        "narrative": summary,
    }

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bias": "NEUTRAL",
        "setup_status": "NO SETUP",
        "readiness": 0,
        "readiness_level": {"step": 0, "percent": 0, "label": "NO SETUP"},
        "active_zone": {},
        "invalidation_level": None,
        "missing_confirmation": "Wait for HTF context and a recent liquidity sweep.",
        "suggested_action": "No valid trade yet.",
        "next_required_confirmation": "Wait for HTF context and a liquidity sweep.",
        "levels_mode": "hidden",
        "invalidation_reason": None,
        "direction": "NO SETUP",
        "status": "NO SETUP",
        "score": 0,
        "setup_quality": 0,
        "trade_quality": 0,
        "trade_decision": "PENDING",
        "objective_plan": mentor_view["objective_plan"],
        "checklist": _checklist_status(checklist),
        "checklist_flags": checklist,
        "levels": {
            "entry_zone": None,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "rr1": None,
            "rr2": None,
            "is_tentative": False,
            "display_note": "Not available until setup is valid.",
        },
        "zones": {"htf_fvg": {}, "liquidity_zone": {}, "ifvg": {}, "mss": {}},
        "chart_overlays": {
            "current_price": {},
            "active_fvg": None,
            "liquidity_sweep": {},
            "mss_level": {},
            "ifvg_zone": None,
            "entry_zone": None,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "levels_mode": "hidden",
            "trade_levels": None,
        },
        "market_context": {
            "current_session": session_context["name"],
            "entry_allowed": session_context["entry_allowed"],
            "session_phase": session_context["phase"],
        },
        "recent_structure": {},
        "session": session_context,
        "kill_zone": _legacy_kill_zone(session_context),
        "order_blocks": {"nearest": {}, "active": [], "mitigated_count": 0, "breaker_count": 0},
        "liquidity_map": {"current_price": None, "buy_side": [], "sell_side": [], "current_target": {}},
        "analysis_timeline": [],
        "mentor": mentor_view,
        "market_narrative": mentor_view["narrative"],
        "macro_dashboard": macro_context,
        "summary": summary,
    }
