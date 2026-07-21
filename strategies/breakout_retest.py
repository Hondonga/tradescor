"""Breakout and Retest strategy for the shared TradeScor assistant."""

from __future__ import annotations

import pandas as pd

from analysis.candles import to_unix_seconds
from analysis.objectives import analyze_objectives
from analysis.setup_state import build_setup_state, event_record
from scanner.objective_engine import levels_from_objective_plan
from strategies.base import EMPTY_LEVELS, make_strategy_result, research_candidate, research_eligible, research_explain


STRATEGY_NAME = "Breakout & Retest"
STRATEGY_VERSION = "breakout_retest_v1"

def is_eligible(context): return research_eligible(context, "breakout_retest")
def detect_setup(context): return research_candidate(context, "breakout_retest")
def build_candidate(context, setup): return setup
def explain(candidate): return research_explain(candidate)


def analyze(
    candles: pd.DataFrame,
    shared_analysis: dict[str, object],
    *,
    symbol: str,
    timeframe: str,
    macro_context: dict[str, object] | None = None,
    multi_timeframe_context: dict[str, pd.DataFrame] | None = None,
    top_down_context: dict[str, object] | None = None,
    analysis_timestamp: object | None = None,
) -> tuple[dict[str, object], None]:
    """Analyze the current range, breakout, retest, and rejection sequence."""
    if len(candles) < 35:
        return _empty("Not enough candles to define a stable breakout range.")

    volatility = shared_analysis.get("volatility") or {}
    atr = float(volatility.get("atr") or (candles["high"] - candles["low"]).tail(14).mean())
    locked = _locked_breakout_sequence(candles, atr)
    range_data = locked.get("range") or _range(candles, atr)
    if not range_data:
        return _empty("A stable support and resistance range is not available yet.")

    breakout = locked.get("breakout") or _breakout(candles, range_data, atr)
    if not breakout:
        state = "WAITING_FOR_BREAKOUT"
        direction = _range_bias(shared_analysis, top_down_context or {})
        story = "Price remains inside the active range. TradeScor is waiting for a candle close beyond support or resistance."
        result = _base_result(candles, range_data, direction, state, story)
        result["breakout_retest_details"] = {
            "range": range_data,
            "breakout": {},
            "retest": {},
            "rejection_confirmed": False,
            "failed_breakout": False,
        }
        return result, None

    direction = str(breakout["direction"])
    level = float(breakout["level"])
    retest = _retest(candles, breakout, atr)
    failure = _failure_event(candles, breakout, atr)
    recovered_failure = _failure_recovered(candles, breakout, atr, failure)
    failed = bool(failure) and not recovered_failure
    rejection = _rejection(candles, retest, direction, level) if retest else False
    entry_zone = _entry_zone(level, atr)
    current = float(candles.iloc[-1]["close"])
    entry_proximity = _inside_zone(current, entry_zone)
    technical_state = _state(candles, breakout, retest, failed, rejection, entry_proximity)
    invalidation = _invalidation(level, atr, direction)
    measured_target = level + float(range_data["height"]) if direction == "Bullish" else level - float(range_data["height"])
    objective_plan = analyze_objectives(
        direction=direction,
        entry_price=(entry_zone["top"] + entry_zone["bottom"]) / 2,
        stop_loss=invalidation,
        shared_analysis=shared_analysis,
        context_candles=multi_timeframe_context or {},
        extra_candidates=[
            {
                "name": "Measured Move",
                "price": measured_target,
                "source": "measured_move",
                "probability": 78,
                "reason": "The prior range height projects a strategy-aligned breakout objective.",
                "formed_at": breakout["time"],
                "formed_index": breakout["index"],
                "type": "measured_move",
            }
        ],
        analysis_candles=candles,
    )
    trade_accepted = technical_state == "ENTRY_READY" and bool(objective_plan.get("trade_accepted"))
    state = technical_state if technical_state != "ENTRY_READY" or trade_accepted else "NO_TRADE"
    mode = "final" if trade_accepted else "hidden"
    levels = _levels(entry_zone, invalidation, objective_plan) if trade_accepted else EMPTY_LEVELS.copy()
    decision = "ACCEPT" if trade_accepted else "REJECT" if technical_state == "ENTRY_READY" else "PENDING"
    story = _story(direction, state, range_data, breakout, retest, rejection, entry_proximity, objective_plan)
    next_action = _next_action(direction, state, level, entry_zone, objective_plan)
    result = make_strategy_result(
        strategy_name=STRATEGY_NAME,
        bias=direction,
        state=state,
        score=_setup_quality(range_data, breakout, retest, rejection),
        market_story=story,
        next_trigger=next_action,
        levels_mode=mode,
        levels=levels,
        overlays=_overlays(candles, range_data, breakout, entry_zone, invalidation, levels, mode),
        progress=_progress(state),
        why=_why(direction, range_data, breakout, retest, rejection, entry_proximity, objective_plan),
    )
    result.update(
        {
            "setup_quality": _setup_quality(range_data, breakout, retest, rejection),
            "trade_quality": int(objective_plan.get("trade_quality", 0) or 0),
            "trade_decision": decision,
            "objective_plan": objective_plan,
            "confirmation_achieved": rejection,
            "entry_zone_available": True,
            "entry_proximity": entry_proximity,
            "price_location": "Above broken resistance" if direction == "Bullish" else "Below broken support",
            "market_intent": "Retesting breakout" if retest else "Waiting for breakout retest",
            "breakout_retest_details": {
                "range": range_data,
                "breakout": breakout,
                "retest": retest or {},
                "rejection_confirmed": rejection,
                "entry_zone": entry_zone,
                "failed_breakout": failed,
                "failed_breakout_recovered": recovered_failure,
                "technical_state": technical_state,
                "measured_move": round(measured_target, 6),
            },
            "timeline": _timeline(candles, direction, state, breakout, retest, rejection),
        }
    )
    completed_events = [
        event_record("range_locked", range_data.get("start_time", candles.iloc[0]["time"]), high=range_data["high"], low=range_data["low"]),
        event_record("breakout_confirmed", breakout["time"], level=breakout["level"], close=breakout["close"]),
    ]
    if retest:
        completed_events.append(event_record("retest", retest["time"], level=retest["level"]))
    if rejection:
        rejection_time = candles.iloc[-1]["time"]
        completed_events.append(event_record("rejection_confirmed", rejection_time, level=breakout["level"]))
    if failed:
        if failure:
            completed_events.append(failure)
    result["setup_state"] = build_setup_state(
        strategy="breakout_retest",
        direction=direction,
        created_at=range_data.get("start_time", analysis_timestamp or candles.iloc[0]["time"]),
        current_state=state,
        completed_events=completed_events,
        active_zone=range_data,
        trigger_level={"price": breakout["level"], "time": breakout["time"], "index": breakout["index"]},
        confirmation_event={"time": breakout["time"], "index": breakout["index"], "level": breakout["level"]},
        entry_zone=entry_zone,
        invalidation=invalidation,
        targets=objective_plan.get("targets", []),
        invalidated=failed,
        invalidation_reason="Price closed back inside the locked range." if failed else None,
    )
    return result, None


def _empty(reason: str) -> tuple[dict[str, object], None]:
    return (
        make_strategy_result(
            strategy_name=STRATEGY_NAME,
            bias="Neutral",
            state="NO_TRADE",
            score=0,
            market_story=reason,
            next_trigger="Wait for a stable range with defined support and resistance.",
            progress=_progress("NO_TRADE"),
            why=[{"key": "range", "status": "waiting", "text": reason}],
        ),
        None,
    )


def _base_result(candles, range_data, direction, state, story):
    result = make_strategy_result(
        strategy_name=STRATEGY_NAME,
        bias=direction,
        state=state,
        score=35,
        market_story=story,
        next_trigger="Wait for a candle close outside the active range. Do not enter inside the range.",
        overlays=_range_overlays(candles, range_data),
        progress=_progress(state),
        why=[
            {"key": "range", "status": "completed", "text": "A stable support and resistance range is active."},
            {"key": "breakout", "status": "waiting", "text": "No candle has closed beyond the active range yet."},
            {"key": "entry", "status": "inactive", "text": "Entry requires a breakout, retest, and rejection."},
        ],
    )
    result.update(
        {
            "trade_decision": "PENDING",
            "confirmation_achieved": False,
            "entry_zone_available": False,
            "entry_proximity": False,
            "price_location": "In range",
            "market_intent": "Ranging",
            "timeline": [
                {"time": str(candles.iloc[-1]["time"]), "event_type": "Range Identified", "direction": direction, "explanation": "Support and resistance define the active range."}
            ],
        }
    )
    return result


def _range(candles: pd.DataFrame, atr: float) -> dict[str, object]:
    breakout_window = min(10, max(4, len(candles) // 8))
    baseline_end = len(candles) - breakout_window
    baseline_start = max(0, baseline_end - 60)
    baseline = candles.iloc[baseline_start:baseline_end]
    if len(baseline) < 20:
        return {}
    high = float(baseline["high"].max())
    low = float(baseline["low"].min())
    height = high - low
    if height <= max(atr * 1.5, abs(float(candles.iloc[-1]["close"])) * 0.0001):
        return {}
    return {
        "high": round(high, 6),
        "low": round(low, 6),
        "height": round(height, 6),
        "start_index": baseline_start,
        "end_index": baseline_end - 1,
        "start_time": str(baseline.iloc[0]["time"]),
        "end_time": str(baseline.iloc[-1]["time"]),
    }


def _locked_breakout_sequence(candles: pd.DataFrame, atr: float) -> dict[str, object]:
    """Find a breakout from its pre-breakout range and keep that anchor fixed."""
    if len(candles) < 21:
        return {}
    search_start = 20
    sequence_floor = 0
    latest_failed: dict[str, object] = {}
    for breakout_index in range(search_start, len(candles)):
        if breakout_index - sequence_floor < 20:
            continue
        baseline_start = max(sequence_floor, breakout_index - 60)
        baseline = candles.iloc[baseline_start:breakout_index]
        if len(baseline) < 20:
            continue
        high = float(baseline["high"].max())
        low = float(baseline["low"].min())
        height = high - low
        if height <= max(atr * 1.5, abs(float(candles.iloc[breakout_index]["close"])) * 0.0001):
            continue
        close = float(candles.iloc[breakout_index]["close"])
        buffer = atr * 0.08
        if close > high + buffer:
            direction, level = "Bullish", high
        elif close < low - buffer:
            direction, level = "Bearish", low
        else:
            continue
        range_data = {
            "high": round(high, 6),
            "low": round(low, 6),
            "height": round(height, 6),
            "start_index": baseline_start,
            "end_index": breakout_index - 1,
            "start_time": str(baseline.iloc[0]["time"]),
            "end_time": str(baseline.iloc[-1]["time"]),
            "locked": True,
        }
        sequence = {
            "range": range_data,
            "breakout": _breakout_event(direction, breakout_index, candles.iloc[breakout_index]["time"], level, close),
        }
        failure = _failure_event(candles, sequence["breakout"], atr)
        if not failure:
            return sequence
        sequence["failure"] = failure
        latest_failed = sequence
        sequence_floor = int(failure["index"]) + 1
    return latest_failed


def _breakout(candles: pd.DataFrame, range_data: dict[str, object], atr: float) -> dict[str, object]:
    start = int(range_data["end_index"]) + 1
    buffer = atr * 0.08
    events = []
    for index in range(start, len(candles)):
        candle = candles.iloc[index]
        close = float(candle["close"])
        if close > float(range_data["high"]) + buffer:
            events.append(_breakout_event("Bullish", index, candle["time"], range_data["high"], close))
        elif close < float(range_data["low"]) - buffer:
            events.append(_breakout_event("Bearish", index, candle["time"], range_data["low"], close))
    # Keep the first close outside the range as the authoritative breakout.
    # Later closes belong to the same sequence and must not reset the retest clock.
    return events[0] if events else {}


def _breakout_event(direction, index, time, level, close):
    return {
        "direction": direction,
        "index": index,
        "time": str(time),
        "level": float(level),
        "close": close,
    }


def _retest(candles: pd.DataFrame, breakout: dict[str, object], atr: float) -> dict[str, object] | None:
    level = float(breakout["level"])
    tolerance = atr * 0.3
    for index in range(int(breakout["index"]) + 1, len(candles)):
        candle = candles.iloc[index]
        touched = float(candle["low"]) <= level + tolerance and float(candle["high"]) >= level - tolerance
        if touched:
            return {"index": index, "time": str(candle["time"]), "level": level}
    return None


def _failed_breakout(candles: pd.DataFrame, breakout: dict[str, object], atr: float) -> bool:
    return bool(_failure_event(candles, breakout, atr))


def _failure_event(candles: pd.DataFrame, breakout: dict[str, object], atr: float) -> dict[str, object]:
    post = candles.iloc[int(breakout["index"]) + 1 :]
    if post.empty:
        return {}
    level = float(breakout["level"])
    # A retest often probes back through the broken level before rejecting.
    # Treat only a decisive move back inside the old range as a failed breakout.
    tolerance = atr * 1.5
    for index, candle in post.iterrows():
        close = float(candle["close"])
        failed = close < level - tolerance if breakout["direction"] == "Bullish" else close > level + tolerance
        if failed:
            return event_record("failed_breakout", candle["time"], index=int(index), level=level, close=close)
    return {}


def _failure_recovered(
    candles: pd.DataFrame,
    breakout: dict[str, object],
    atr: float,
    failure: dict[str, object],
) -> bool:
    """Return True when price has returned to the broken level after a failed probe."""
    if not failure:
        return False
    latest_close = float(candles.iloc[-1]["close"])
    level = float(breakout["level"])
    recovery_zone = atr * 1.5
    if breakout["direction"] == "Bullish":
        return latest_close >= level - recovery_zone
    return latest_close <= level + recovery_zone


def _rejection(candles: pd.DataFrame, retest: dict[str, object], direction: str, level: float) -> bool:
    start = int(retest["index"])
    for _, candle in candles.iloc[start:].tail(4).iterrows():
        bullish = float(candle["close"]) > float(candle["open"])
        held = float(candle["close"]) >= level if direction == "Bullish" else float(candle["close"]) <= level
        if held and ((direction == "Bullish" and bullish) or (direction == "Bearish" and not bullish)):
            return True
    return False


def _state(candles, breakout, retest, failed, rejection, proximity):
    if failed:
        return "FAILED_BREAKOUT"
    if int(breakout["index"]) == len(candles) - 1:
        return "BREAKOUT_CONFIRMED"
    if not retest:
        return "WAITING_FOR_RETEST"
    if rejection and proximity:
        return "ENTRY_READY"
    if rejection:
        return "WAITING_FOR_RETEST"
    if int(retest["index"]) == len(candles) - 1:
        return "RETEST_ACTIVE"
    return "WAITING_FOR_REJECTION"


def _entry_zone(level: float, atr: float) -> dict[str, float]:
    return {"top": round(level + atr * 0.25, 6), "bottom": round(level - atr * 0.25, 6)}


def _invalidation(level: float, atr: float, direction: str) -> float:
    value = level - atr * 1.5 if direction == "Bullish" else level + atr * 1.5
    return round(value, 6)


def _levels(entry_zone, invalidation, objective):
    levels = levels_from_objective_plan(
        entry_zone=entry_zone,
        stop_loss=invalidation,
        objective_plan=objective,
    )
    levels["primary_objective"] = objective.get("primary_objective")
    levels["secondary_objective"] = objective.get("secondary_objective")
    return levels


def _overlays(candles, range_data, breakout, entry_zone, invalidation, levels, mode):
    level = float(breakout["level"])
    retest_zone = {
        "type": "breakout_retest",
        "tag": "Zone",
        "label": "Retest Zone",
        "tooltip": "Broken range level retest zone",
        "start_time": to_unix_seconds(breakout["time"]),
        "end_time": to_unix_seconds(candles.iloc[-1]["time"]),
        "top": entry_zone["top"],
        "bottom": entry_zone["bottom"],
    }
    return {
        **_range_overlays(candles, range_data),
        "current_price": {"price": float(candles.iloc[-1]["close"]), "time": to_unix_seconds(candles.iloc[-1]["time"])},
        "breakout_level": {"price": level, "label": "Trigger"},
        "confirmation_level": {"price": level, "label": "Trigger"},
        "retest_zone": retest_zone,
        "pullback_zone": retest_zone,
        "invalidation_level": invalidation,
        "entry_zone": retest_zone if mode == "final" else None,
        "stop_loss": levels.get("stop_loss") if mode == "final" else None,
        "tp1": levels.get("tp1") if mode == "final" else None,
        "tp2": levels.get("tp2") if mode == "final" else None,
        "levels_mode": mode,
    }


def _range_overlays(candles, range_data):
    return {
        "current_price": {"price": float(candles.iloc[-1]["close"]), "time": to_unix_seconds(candles.iloc[-1]["time"])},
        "range_high": {"price": range_data["high"], "label": "Range High"},
        "range_low": {"price": range_data["low"], "label": "Range Low"},
        "confirmation_level": {},
        "invalidation_level": None,
        "entry_zone": None,
        "levels_mode": "hidden",
    }


def _story(direction, state, range_data, breakout, retest, rejection, proximity, objective):
    side = "resistance" if direction == "Bullish" else "support"
    if state == "ENTRY_READY":
        return f"Price broke {side}, retested the broken level, and confirmed a {direction.lower()} rejection while still at the entry zone."
    if state == "NO_TRADE":
        return f"The breakout and retest completed, but TradeScor rejected the trade because {str(objective.get('reason', 'the reward is insufficient')).lower()}"
    if state == "FAILED_BREAKOUT":
        return f"The {direction.lower()} breakout failed because price closed back inside the prior range. No trade is valid."
    if state == "WAITING_FOR_RETEST":
        return f"Price broke {side}, but it is extended away from the broken level. TradeScor is waiting for a retest instead of chasing the breakout."
    if state in {"RETEST_ACTIVE", "WAITING_FOR_REJECTION"}:
        return f"Price is retesting broken {side}. The level has not produced a confirmed directional rejection yet."
    return f"A {direction.lower()} breakout is confirmed. TradeScor is waiting for price to revisit the broken {side}."


def _next_action(direction, state, level, entry_zone, objective):
    relation = "above" if direction == "Bullish" else "below"
    if state == "ENTRY_READY":
        return "Price is holding the confirmed retest zone. Use only the validated trade plan."
    if state == "NO_TRADE":
        return f"Stand aside. {objective.get('reason', 'The available reward does not justify the risk.')}"
    if state == "FAILED_BREAKOUT":
        return "Remain flat and wait for a new range or a fresh breakout sequence."
    if state in {"BREAKOUT_CONFIRMED", "WAITING_FOR_RETEST"}:
        return f"Wait for price to retest {level:.6f}; do not enter while price is extended."
    if state in {"RETEST_ACTIVE", "WAITING_FOR_REJECTION"}:
        return f"Wait for a rejection candle that closes {relation} {level:.6f}."
    return "Wait for a candle close outside the active range."


def _why(direction, range_data, breakout, retest, rejection, proximity, objective):
    side = "range resistance" if direction == "Bullish" else "range support"
    return [
        {"key": "range", "status": "completed", "text": f"The active range spans {range_data['low']} to {range_data['high']}."},
        {"key": "breakout", "status": "completed", "text": f"Price closed beyond {side}."},
        {"key": "retest", "status": "completed" if retest else "waiting", "text": "Price retested the broken level." if retest else "The broken level has not been retested yet."},
        {"key": "rejection", "status": "completed" if rejection else "waiting", "text": "The retest produced directional rejection." if rejection else "Directional rejection is still missing."},
        {"key": "entry", "status": "completed" if rejection and proximity and objective.get("trade_accepted") else "waiting", "text": "Retest location and trade objective are valid." if rejection and proximity and objective.get("trade_accepted") else "Entry location or objective quality is not ready."},
    ]


def _progress(state):
    stages = [
        ("range", "Range Identified", {"RANGE_IDENTIFIED", "WAITING_FOR_BREAKOUT"}),
        ("breakout", "Breakout Confirmed", {"BREAKOUT_CONFIRMED", "WAITING_FOR_RETEST"}),
        ("retest", "Retest Active", {"RETEST_ACTIVE", "WAITING_FOR_REJECTION"}),
        ("rejection", "Rejection", set()),
        ("entry", "Entry Ready", {"ENTRY_READY"}),
    ]
    current = next((index for index, (_key, _label, states) in enumerate(stages) if state in states), -1)
    rows = []
    for index, (key, label, _states) in enumerate(stages):
        status = "completed" if current > index or state == "ENTRY_READY" else "current" if current == index else "inactive"
        if state in {"NO_TRADE", "FAILED_BREAKOUT", "INVALIDATED"} and index == 0:
            status = "invalidated"
        rows.append({"key": key, "label": label, "status": status, "is_current": status == "current"})
    return rows


def _timeline(candles, direction, state, breakout, retest, rejection):
    now = str(candles.iloc[-1]["time"])
    events = [
        {"time": breakout["time"], "event_type": "Breakout Confirmed", "direction": direction, "explanation": "Price closed outside the active range."}
    ]
    if retest:
        events.append({"time": retest["time"], "event_type": "Retest", "direction": direction, "explanation": "Price returned to the broken range level."})
    if rejection:
        events.append({"time": now, "event_type": "Retest Rejection", "direction": direction, "explanation": "The broken level held in the breakout direction."})
    events.append({"time": now, "event_type": state.replace("_", " ").title(), "direction": direction, "explanation": "Current Breakout & Retest state."})
    return events


def _setup_quality(range_data, breakout, retest, rejection):
    score = 30
    score += 20 if range_data else 0
    score += 20 if breakout else 0
    score += 15 if retest else 0
    score += 15 if rejection else 0
    return min(100, score)


def _range_bias(shared, top_down):
    alignment = str(top_down.get("overall_alignment", "Neutral"))
    if alignment in {"Bullish", "Bearish"}:
        return alignment
    trend = str((shared.get("trend") or {}).get("direction", "Neutral"))
    return trend if trend in {"Bullish", "Bearish"} else "Neutral"


def _inside_zone(price, zone):
    return float(zone["bottom"]) <= price <= float(zone["top"])
