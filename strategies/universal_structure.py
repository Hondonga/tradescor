"""Universal Structure Strategy.

This strategy is deliberately not ICT-specific. It uses trend, structure,
pullback zones, and confirmation breaks.
"""

from __future__ import annotations

import pandas as pd

from analysis.candles import to_unix_seconds
from analysis.confluence import score_confluence
from analysis.objectives import analyze_objectives
from analysis.setup_state import (
    build_setup_state,
    event_record,
    find_confirmation_event,
    invalidation_event,
    select_trigger_after_zone,
)
from scanner.objective_engine import levels_from_objective_plan
from strategies.base import EMPTY_LEVELS, make_strategy_result


STRATEGY_NAME = "Universal Structure Strategy"


def analyze(
    candles: pd.DataFrame,
    shared_analysis: dict[str, object],
    macro_context: dict[str, object] | None = None,
    multi_timeframe_context: dict[str, pd.DataFrame] | None = None,
    top_down_context: dict[str, object] | None = None,
    analysis_timestamp: object | None = None,
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Apply Universal Structure rules to shared market analysis."""
    if len(candles) < 30:
        return _no_setup("Not enough candles to analyze structure.")

    macro_context = macro_context or {}
    trend = shared_analysis.get("trend", {})
    structure = shared_analysis.get("structure", {})
    zones = shared_analysis.get("zones", {})
    volatility = shared_analysis.get("volatility", {})
    session = macro_context.get("session", {})
    current_price = float(candles.iloc[-1]["close"])
    direction = str(trend.get("direction", "Neutral"))
    top_down_context = top_down_context or {}
    top_down_alignment = str(top_down_context.get("overall_alignment", "Neutral"))
    top_down_conflicts = list(top_down_context.get("conflicts", []) or [])

    if direction not in {"Bullish", "Bearish"}:
        story = "The market is not showing clean bullish or bearish structure yet. TradeScor is waiting for a clearer trend before considering pullback logic."
        return (
            make_strategy_result(
                strategy_name=STRATEGY_NAME,
                bias="Neutral",
                state="NO_SETUP",
                score=0,
                market_story=story,
                next_trigger="Wait for a clearer trend with structure alignment.",
                levels_mode="hidden",
                progress=_progress("NO_SETUP"),
                why=[{"key": "trend", "status": "current", "text": story}],
            ),
            None,
        )

    pullback_zone = _select_pullback_zone(direction, zones, current_price)
    touched = _zone_touched_recently(candles, pullback_zone, lookback=len(candles)) if pullback_zone else False
    in_zone = _price_in_zone(current_price, pullback_zone)
    zone_index = int((pullback_zone or {}).get("start_index", 0))
    confirmation_level = select_trigger_after_zone(shared_analysis.get("swings") or {}, direction, zone_index)
    if not confirmation_level:
        confirmation_level = _confirmation_level(direction, structure)
    confirmation_event = find_confirmation_event(
        candles,
        direction,
        confirmation_level,
        after_index=zone_index + 1,
    )
    confirmed = bool(confirmation_event)
    state = _state(direction, pullback_zone, touched, in_zone, confirmed)
    provisional_levels = _entry_and_stop(direction, pullback_zone, volatility) if pullback_zone else EMPTY_LEVELS.copy()
    invalidation = provisional_levels.get("stop_loss")
    invalidated_event = invalidation_event(
        candles,
        direction,
        float(invalidation) if invalidation is not None else None,
        after_index=int(confirmation_event.get("index", len(candles))) + 1,
    ) if confirmed else {}
    if invalidated_event:
        state = "INVALIDATED"
    objective_plan = _objective_plan(
        direction,
        provisional_levels,
        shared_analysis,
        multi_timeframe_context or {},
        candles,
    )
    trade_accepted = state == "ENTRY_READY" and bool(objective_plan.get("trade_accepted"))
    levels_mode = "final" if trade_accepted else "hidden"
    levels = _accepted_levels(provisional_levels, objective_plan) if trade_accepted else EMPTY_LEVELS.copy()
    rr1 = levels.get("rr1") if levels_mode == "final" else None
    confluence = score_confluence(
        trend_aligned=direction in {"Bullish", "Bearish"},
        structure_clear=bool(structure.get("last_swing_high") and structure.get("last_swing_low")),
        zone_quality=bool(pullback_zone),
        confirmation=confirmed,
        volatility_health=str(volatility.get("health", "Unknown")),
        risk_reward=None,
        session_allowed=session.get("entry_allowed"),
    )
    confluence = _adjust_for_top_down(confluence, direction, top_down_alignment, top_down_conflicts)
    setup_quality = int(confluence["score"])
    trade_quality = int(objective_plan.get("trade_quality", 0) or 0)
    story = _story(direction, state, pullback_zone, confirmation_level, top_down_context, objective_plan)
    next_trigger = _next_trigger(direction, state, pullback_zone, confirmation_level, objective_plan)

    result = make_strategy_result(
        strategy_name=STRATEGY_NAME,
        bias=direction,
        state=state,
        score=setup_quality,
        market_story=story,
        next_trigger=next_trigger,
        levels_mode=levels_mode,
        levels=levels,
        overlays=_overlays(candles, direction, pullback_zone, confirmation_level, levels, levels_mode),
        progress=_progress(state),
        why=_why(direction, state, trend, pullback_zone, confirmation_level, confirmed, top_down_context, objective_plan),
    )
    result["confluence"] = confluence
    result["top_down_context"] = top_down_context
    result["setup_quality"] = setup_quality
    result["trade_quality"] = trade_quality
    result["trade_decision"] = objective_plan.get("decision", "PENDING")
    result["objective_plan"] = objective_plan
    result["confirmation_achieved"] = confirmed
    result["entry_zone_available"] = pullback_zone is not None
    result["entry_proximity"] = in_zone
    completed_events = []
    if pullback_zone:
        completed_events.append(event_record("zone_identified", pullback_zone.get("confirmed_at", pullback_zone.get("start_time", candles.iloc[0]["time"]))))
    if confirmation_level:
        completed_events.append(event_record("trigger_identified", confirmation_level.get("confirmed_at", confirmation_level.get("time", candles.iloc[0]["time"])), level=confirmation_level.get("price")))
    if confirmation_event:
        completed_events.append(confirmation_event)
    if invalidated_event:
        completed_events.append(invalidated_event)
    result["setup_state"] = build_setup_state(
        strategy="universal_structure",
        direction=direction,
        created_at=(pullback_zone or {}).get("confirmed_at", (pullback_zone or {}).get("start_time", analysis_timestamp or candles.iloc[0]["time"])),
        current_state=state,
        completed_events=completed_events,
        active_zone=pullback_zone,
        trigger_level=confirmation_level,
        confirmation_event=confirmation_event,
        entry_zone=pullback_zone,
        invalidation=invalidation,
        targets=objective_plan.get("targets", []),
        invalidated=bool(invalidated_event),
        invalidation_reason="Price closed beyond the active zone invalidation." if invalidated_event else None,
    )
    if trade_accepted:
        result["levels"]["display_note"] = objective_plan.get("summary")
    return result, None


def _no_setup(reason: str) -> tuple[dict[str, object], None]:
    return (
        make_strategy_result(
            strategy_name=STRATEGY_NAME,
            bias="Neutral",
            state="NO_SETUP",
            score=0,
            market_story=reason,
            next_trigger="Load more candles or wait for clearer structure.",
            levels_mode="hidden",
            progress=_progress("NO_SETUP"),
            why=[{"key": "data", "status": "current", "text": reason}],
        ),
        None,
    )


def _state(
    direction: str,
    zone: dict[str, object] | None,
    touched: bool,
    in_zone: bool,
    confirmed: bool,
) -> str:
    if not zone:
        return "TREND_DETECTED"
    if confirmed and in_zone:
        return "ENTRY_READY"
    if confirmed:
        return "CONFIRMED_WAITING_FOR_ENTRY"
    if touched and not confirmed:
        return "WAITING_FOR_CONFIRMATION"
    if in_zone:
        return "AT_IMPORTANT_ZONE"
    return "WAITING_FOR_ZONE"


def _select_pullback_zone(
    direction: str,
    zones: dict[str, object],
    current_price: float,
) -> dict[str, object] | None:
    candidates = zones.get("support", []) if direction == "Bullish" else zones.get("resistance", [])
    if not candidates:
        return None

    if direction == "Bullish":
        preferred = [zone for zone in candidates if float(zone["bottom_price"]) <= current_price]
    else:
        preferred = [zone for zone in candidates if float(zone["top_price"]) >= current_price]

    search = preferred or candidates
    return sorted(search, key=lambda zone: abs(current_price - float(zone["price"])))[0]


def _price_in_zone(price: float, zone: dict[str, object] | None) -> bool:
    if not zone:
        return False
    return float(zone["bottom_price"]) <= price <= float(zone["top_price"])


def _zone_touched_recently(candles: pd.DataFrame, zone: dict[str, object] | None, lookback: int = 12) -> bool:
    if not zone:
        return False

    top = float(zone["top_price"])
    bottom = float(zone["bottom_price"])
    for _, candle in candles.tail(lookback).iterrows():
        if float(candle["low"]) <= top and float(candle["high"]) >= bottom:
            return True
    return False


def _confirmation_level(direction: str, structure: dict[str, object]) -> dict[str, object]:
    if direction == "Bullish":
        return structure.get("minor_swing_high") or {}
    return structure.get("minor_swing_low") or {}


def _confirmation_closed(direction: str, current_price: float, level: dict[str, object]) -> bool:
    if not level:
        return False
    if direction == "Bullish":
        return current_price > float(level["price"])
    return current_price < float(level["price"])


def _entry_and_stop(
    direction: str,
    zone: dict[str, object] | None,
    volatility: dict[str, object],
) -> dict[str, object]:
    if not zone:
        return EMPTY_LEVELS.copy()

    entry_top = round(float(zone["top_price"]), 6)
    entry_bottom = round(float(zone["bottom_price"]), 6)
    entry = (entry_top + entry_bottom) / 2
    atr = float(volatility.get("atr") or abs(entry) * 0.001)
    buffer = max(atr * 0.3, abs(entry) * 0.00005)

    if direction == "Bullish":
        stop = entry_bottom - buffer
    else:
        stop = entry_top + buffer

    return {
        "entry_zone": {"top": entry_top, "bottom": entry_bottom},
        "stop_loss": _round(stop),
        "tp1": None,
        "tp2": None,
        "rr1": None,
        "rr2": None,
    }


def _objective_plan(
    direction: str,
    provisional_levels: dict[str, object],
    shared_analysis: dict[str, object],
    context_candles: dict[str, pd.DataFrame],
    analysis_candles: pd.DataFrame,
) -> dict[str, object]:
    entry_zone = provisional_levels.get("entry_zone") or {}
    entry = None
    if entry_zone:
        entry = (float(entry_zone["top"]) + float(entry_zone["bottom"])) / 2

    return analyze_objectives(
        direction=direction,
        entry_price=entry,
        stop_loss=provisional_levels.get("stop_loss"),
        shared_analysis=shared_analysis,
        context_candles=context_candles,
        analysis_candles=analysis_candles,
    )


def _accepted_levels(
    provisional_levels: dict[str, object],
    objective_plan: dict[str, object],
) -> dict[str, object]:
    levels = levels_from_objective_plan(
        entry_zone=provisional_levels.get("entry_zone"),
        stop_loss=provisional_levels.get("stop_loss"),
        objective_plan=objective_plan,
    )
    levels["primary_objective"] = objective_plan.get("primary_objective")
    levels["secondary_objective"] = objective_plan.get("secondary_objective")
    return levels


def _overlays(
    candles: pd.DataFrame,
    direction: str,
    pullback_zone: dict[str, object] | None,
    confirmation_level: dict[str, object],
    levels: dict[str, object],
    levels_mode: str,
) -> dict[str, object]:
    show_trade_levels = levels_mode == "final"
    return {
        "current_price": {"price": round(float(candles.iloc[-1]["close"]), 6), "time": to_unix_seconds(candles.iloc[-1]["time"])},
        "pullback_zone": _zone_overlay(pullback_zone, "PB", "Pullback Zone") if pullback_zone else None,
        "confirmation_level": _line_overlay(confirmation_level, direction),
        "entry_zone": _entry_zone(candles, levels) if show_trade_levels else None,
        "stop_loss": levels.get("stop_loss") if show_trade_levels else None,
        "tp1": levels.get("tp1") if show_trade_levels else None,
        "tp2": levels.get("tp2") if show_trade_levels else None,
        "levels_mode": levels_mode,
    }


def _zone_overlay(zone: dict[str, object], tag: str, tooltip: str) -> dict[str, object]:
    return {
        "type": zone.get("type", "pullback"),
        "label": zone.get("label", "Pullback Zone"),
        "tag": tag,
        "tooltip": tooltip,
        "start_time": to_unix_seconds(zone["start_time"]),
        "end_time": to_unix_seconds(zone["end_time"]),
        "top": round(float(zone["top_price"]), 6),
        "bottom": round(float(zone["bottom_price"]), 6),
    }


def _line_overlay(level: dict[str, object], direction: str) -> dict[str, object]:
    if not level:
        return {}
    return {
        "price": round(float(level["price"]), 6),
        "label": "Break Above" if direction == "Bullish" else "Break Below",
        "direction": direction,
    }


def _entry_zone(candles: pd.DataFrame, levels: dict[str, object]) -> dict[str, object] | None:
    entry_zone = levels.get("entry_zone")
    if not entry_zone:
        return None
    return {
        "type": "entry_zone",
        "label": "Entry Zone",
        "tag": "ENTRY",
        "tooltip": "Confirmed Entry Zone",
        "start_time": to_unix_seconds(candles.iloc[-1]["time"]),
        "end_time": to_unix_seconds(candles.iloc[-1]["time"]),
        "top": entry_zone["top"],
        "bottom": entry_zone["bottom"],
    }


def _story(
    direction: str,
    state: str,
    zone: dict[str, object] | None,
    confirmation_level: dict[str, object],
    top_down_context: dict[str, object],
    objective_plan: dict[str, object],
) -> str:
    direction_text = direction.lower()
    context_text = _context_phrase(top_down_context)
    if state == "ENTRY_READY":
        if not objective_plan.get("trade_accepted"):
            return f"{context_text} The technical {direction_text} setup is complete, but TradeScor rejected the trade because {str(objective_plan.get('reason', 'the available reward is too small')).lower()}"
        return f"{context_text} The selected chart is in a {direction_text} structure. Price has pulled back into the active zone and closed beyond the confirmation level, so the Universal Structure setup is entry ready."
    if state == "CONFIRMED_WAITING_FOR_ENTRY":
        return f"{context_text} The selected chart is in a {direction_text} structure and confirmation has completed, but price is extended away from the active zone. TradeScor is waiting for a pullback before considering an entry."
    if state in {"AT_IMPORTANT_ZONE", "WAITING_FOR_CONFIRMATION"}:
        level_text = _level_text(direction, confirmation_level)
        return f"{context_text} The selected chart is in a {direction_text} structure and price has pulled back into the active zone. TradeScor is waiting for {level_text} before showing final trade levels."
    if zone:
        return f"{context_text} The selected chart is in a {direction_text} structure. TradeScor has identified the pullback zone and is waiting for price to interact with it."
    return f"{context_text} The selected chart is in a {direction_text} structure, but no clean pullback zone is close enough yet."


def _next_trigger(
    direction: str,
    state: str,
    zone: dict[str, object] | None,
    confirmation_level: dict[str, object],
    objective_plan: dict[str, object],
) -> str:
    if state == "ENTRY_READY":
        if not objective_plan.get("trade_accepted"):
            return "No trade. Wait for a fresh setup with at least 1.50R to a meaningful objective."
        return "Entry levels are available because trend, pullback, and confirmation are aligned."
    if state == "CONFIRMED_WAITING_FOR_ENTRY":
        if zone:
            return f"Wait for price to pull back into the active zone between {float(zone['bottom_price']):.6f} and {float(zone['top_price']):.6f}."
        return "Wait for price to return to the active entry area before considering a trade."
    if state in {"AT_IMPORTANT_ZONE", "WAITING_FOR_CONFIRMATION"}:
        return _level_text(direction, confirmation_level)
    if zone:
        return "Wait for price to pull back into the highlighted zone."
    return "Wait for a clean support or resistance pullback zone."


def _level_text(direction: str, confirmation_level: dict[str, object]) -> str:
    if not confirmation_level:
        return "a clean confirmation break"
    price = round(float(confirmation_level["price"]), 6)
    if direction == "Bullish":
        return f"a candle close above {price}"
    return f"a candle close below {price}"


def _why(
    direction: str,
    state: str,
    trend: dict[str, object],
    zone: dict[str, object] | None,
    confirmation_level: dict[str, object],
    confirmed: bool,
    top_down_context: dict[str, object],
    objective_plan: dict[str, object],
) -> list[dict[str, str]]:
    items = [
        {
            "key": "top_down",
            "status": "completed" if _top_down_supports(direction, top_down_context) else "waiting",
            "text": top_down_context.get("summary") or "Top-down context is not loaded.",
        },
        {
            "key": "trend",
            "status": "completed" if direction in {"Bullish", "Bearish"} else "current",
            "text": str(trend.get("reason", "Trend is still forming.")),
        },
        {
            "key": "pullback_zone",
            "status": "completed" if zone else "current",
            "text": "A pullback zone is active." if zone else "No clean pullback zone is active yet.",
        },
        {
            "key": "confirmation",
            "status": "completed" if confirmed else "current" if state in {"AT_IMPORTANT_ZONE", "WAITING_FOR_CONFIRMATION"} else "inactive",
            "text": "Confirmation break is complete." if confirmed else _level_text(direction, confirmation_level),
        },
    ]

    conflicts = top_down_context.get("conflicts") or []
    if conflicts:
        items.append(
            {
                "key": "top_down_conflict",
                "status": "waiting",
                "text": f"Conflict: {conflicts[0]}",
            }
        )

    if state == "ENTRY_READY":
        primary = objective_plan.get("primary_objective") or objective_plan.get("best_rejected_objective") or {}
        accepted = bool(objective_plan.get("trade_accepted"))
        objective_text = objective_plan.get("summary") or "No meaningful target is available yet."
        if primary:
            objective_text = f"{primary.get('name')} offers {primary.get('rr')}R. {objective_plan.get('reason', '')}".strip()
        items.append(
            {
                "key": "objective",
                "status": "completed" if accepted else "waiting",
                "text": str(objective_text),
            }
        )

    if state == "CONFIRMED_WAITING_FOR_ENTRY":
        items.append(
            {
                "key": "entry_location",
                "status": "waiting",
                "text": "Confirmation is complete, but price is outside the active entry zone.",
            }
        )

    return items


def _adjust_for_top_down(
    confluence: dict[str, object],
    direction: str,
    alignment: str,
    conflicts: list[str],
) -> dict[str, object]:
    adjusted = confluence.copy()
    score = int(adjusted.get("score", 0))

    if _alignment_supports(direction, alignment):
        score += 8
    elif alignment in {"Bullish", "Bearish"} and alignment != direction:
        score -= 15

    if conflicts:
        score -= min(20, 8 + (len(conflicts) * 4))

    score = max(0, min(100, score))
    adjusted["score"] = score
    adjusted["confidence"] = _confidence(score)
    adjusted["top_down_alignment"] = alignment
    adjusted["top_down_conflicts"] = conflicts
    return adjusted


def _context_phrase(top_down_context: dict[str, object]) -> str:
    summary = str(top_down_context.get("summary", "")).strip()
    if summary:
        return summary
    return "Top-down context is not loaded."


def _top_down_supports(direction: str, top_down_context: dict[str, object]) -> bool:
    return _alignment_supports(direction, str(top_down_context.get("overall_alignment", "Neutral")))


def _alignment_supports(direction: str, alignment: str) -> bool:
    return direction in {"Bullish", "Bearish"} and alignment == direction


def _confidence(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 55:
        return "Medium"
    if score >= 30:
        return "Low"
    return "Waiting"


def _progress(state: str) -> list[dict[str, object]]:
    order = [
        ("trend", "Trend Detected", "TREND_DETECTED"),
        ("pullback_wait", "Waiting for Zone", "WAITING_FOR_ZONE"),
        ("pullback_active", "At Important Zone", "AT_IMPORTANT_ZONE"),
        ("confirmation", "Confirmation", "WAITING_FOR_CONFIRMATION"),
        ("entry_location", "Waiting Entry Location", "CONFIRMED_WAITING_FOR_ENTRY"),
        ("entry_ready", "Entry Ready", "ENTRY_READY"),
    ]
    state_order = _state_order(state)
    progress = []
    for key, label, stage_state in order:
        order_value = _state_order(stage_state)
        if state == "NO_SETUP":
            status = "current" if key == "trend" else "inactive"
        elif order_value < state_order:
            status = "completed"
        elif order_value == state_order:
            status = "current"
        else:
            status = "inactive"
        progress.append({"key": key, "label": label, "status": status, "is_current": status == "current"})
    return progress


def _state_order(state: str) -> int:
    order = {
        "NO_SETUP": 0,
        "TREND_DETECTED": 1,
        "WAITING_FOR_ZONE": 2,
        "AT_IMPORTANT_ZONE": 3,
        "WAITING_FOR_CONFIRMATION": 4,
        "CONFIRMED_WAITING_FOR_ENTRY": 5,
        "ENTRY_READY": 6,
        "TRADE_ACTIVE": 7,
        "TP1_HIT": 8,
        "TP2_HIT": 9,
        "INVALIDATED": 99,
    }
    return order.get(state, 0)


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)
