"""M5-only execution confirmation and trade-plan construction."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from analysis.asset_rules import asset_rules, normalize_price
from analysis.top_down_engine import completed_candles


DEFAULT_MINIMUM_RR = 1.5


def build_m5_execution_plan(
    *,
    top_down_analysis: dict[str, object],
    m5_candles: pd.DataFrame,
    analysis_timestamp: object,
    current_price: object = None,
    spread: object = 0,
    asset_type: str = "forex",
    news_filters: dict[str, object] | None = None,
    session_context: dict[str, object] | None = None,
    minimum_rr: float = DEFAULT_MINIMUM_RR,
    mode: str = "conservative",
) -> dict[str, object]:
    """Return an execution plan whose actionable prices come only from M5."""
    direction = str((top_down_analysis.get("alignment") or {}).get("primary_direction", "neutral"))
    setup = top_down_analysis.get("m15_setup") or {}
    base = _empty_plan(direction)
    if direction not in {"buy", "sell"} or not setup.get("enabled") or setup.get("countertrend"):
        if not setup.get("enabled") or setup.get("countertrend"):
            base["direction"] = "neutral"
        base["message"] = "No aligned M15 location is available for M5 execution."
        return base

    zone = setup.get("zone") or {}
    low, high = _number(zone.get("low")), _number(zone.get("high"))
    if low is None or high is None or low > high:
        base["message"] = "The M15 setup area is unavailable."
        return base

    completed = completed_candles(m5_candles, "M5", analysis_timestamp)
    all_available = _available_candles(m5_candles, analysis_timestamp)
    valid_after = _timestamp(zone.get("valid_after"))
    if valid_after is not None:
        completed = completed.loc[pd.to_datetime(completed["time"], utc=True, errors="coerce") > valid_after].reset_index(drop=True)
        all_available = all_available.loc[pd.to_datetime(all_available["time"], utc=True, errors="coerce") > valid_after].reset_index(drop=True)
    if len(completed) < 8:
        base["message"] = "Not enough completed M5 candles are available."
        return base

    current = _number(current_price) or float(all_available.iloc[-1]["close"] if not all_available.empty else completed.iloc[-1]["close"])
    spread_value = max(0.0, _number(spread) or 0.0)
    atr = _atr(completed)
    tolerance = max(spread_value * 2, atr * 0.15)
    recent = all_available.tail(min(36, len(all_available)))
    touched = bool(((recent["low"].astype(float) <= high + tolerance) & (recent["high"].astype(float) >= low - tolerance)).any()) if not recent.empty else False

    failure_boundary=_number(zone.get("failure_boundary"))
    last_completed_close=float(completed.iloc[-1]["close"]) if not completed.empty else None
    invalidated = ((last_completed_close < failure_boundary-tolerance if direction=="buy" else last_completed_close > failure_boundary+tolerance) if failure_boundary is not None and last_completed_close is not None else (current < low-tolerance if direction=="buy" else current > high+tolerance))
    if invalidated:
        return {**base, "state": "invalidated", "entry_timing": "INVALIDATED", "message": "The M15 setup area was invalidated before M5 entry."}
    if not touched:
        return {**base, "state": "waiting_for_zone", "entry_timing": "WAITING FOR M15 AREA", "message": "Wait for price to reach the M15 setup area."}

    confirmed = _confirmed_trigger(completed, direction, low, high, tolerance)
    forming = _forming_trigger(all_available, completed, direction, low, high, tolerance)
    if confirmed is None:
        inside = low - tolerance <= current <= high + tolerance
        state = "trigger_forming" if forming else "in_zone" if inside else "waiting_for_trigger"
        timing = "WAITING FOR M5 CLOSE" if forming else "IN M15 AREA" if inside else "REACTION FORMING"
        return {**base, "state": state, "entry_timing": timing, "forming_signal": forming or None, "message": "Wait for a completed M5 confirmation candle."}

    entry = float(confirmed["trigger"])
    execution_zone={"low":entry-tolerance,"high":entry+tolerance,"type":"m5_confirmation_retest","formed_at":confirmed["candle_time"]}
    stop = _normalize_price(_m5_stop(completed, direction, low, high, spread_value, atr, int(confirmed["index"])), asset_type, direction, is_stop=True)
    targets = _targets(top_down_analysis, completed, direction, entry, current, atr)
    risk = entry - stop if direction == "buy" else stop - entry
    for target in targets:
        reward = float(target["price"]) - entry if direction == "buy" else entry - float(target["price"])
        target["risk_reward"] = round(reward / risk, 3) if risk > 0 and reward > 0 else None
        target["valid"] = bool(target["risk_reward"] is not None and target["risk_reward"] >= minimum_rr)
    nearest = targets[0] if targets else None
    if nearest is None or not nearest["valid"]:
        return {
            **base,
            "state": "too_late",
            "trigger": entry,
            "entry":entry,
            "entry_zone":execution_zone,
            "stop": stop,
            "targets": targets,
            "risk_reward": nearest.get("risk_reward") if nearest else None,
            "entry_timing": "TOO LATE",
            "confirmed_signal": confirmed,
            "message": "Remaining reward from the M5 entry is below the required minimum.",
        }

    if _filters_block(asset_type, news_filters or {}, session_context or {}):
        return {**base, "state": "waiting_for_trigger", "trigger": entry,"entry":entry,"entry_zone":execution_zone, "stop": stop, "targets": targets, "risk_reward": nearest["risk_reward"], "entry_timing": "M5 CONFIRMED", "confirmed_signal": confirmed, "message": "M5 confirmed, but a market filter blocks entry."}

    chase = max(0.0,current-entry) if direction=="buy" else max(0.0,entry-current)
    if chase > max(atr * 0.75, risk * 0.5):
        return {**base, "state": "entry_extended", "trigger": entry,"entry":entry,"entry_zone":execution_zone, "stop": stop, "targets": targets, "risk_reward": nearest["risk_reward"], "entry_distance": chase, "entry_timing": "ENTRY EXTENDED", "confirmed_signal": confirmed, "message": "The M5 entry is extended; wait for a retest rather than chasing."}

    retested = abs(current - entry) <= max(atr * 0.25, spread_value * 2)
    if str(mode).lower() != "aggressive" and not retested:
        return {**base, "state": "trigger_confirmed", "trigger": entry,"entry":entry,"entry_zone":execution_zone, "stop": stop, "targets": targets, "risk_reward": nearest["risk_reward"], "entry_distance": chase, "entry_timing": "M5 CONFIRMED", "confirmed_signal": confirmed, "message": "M5 confirmation is locked. Wait for a conservative retest."}

    return {
        **base,
        "state": "entry_valid",
        "entry": entry,
        "entry_zone": execution_zone,
        "trigger": entry,
        "stop": stop,
        "targets": targets,
        "risk_reward": nearest["risk_reward"],
        "entry_distance": chase,
        "entry_timing": "ENTRY AVAILABLE",
        "confirmed_signal": confirmed,
        "message": "M5 entry is confirmed and remains within acceptable distance.",
    }


def _confirmed_trigger(candles: pd.DataFrame, direction: str, zone_low: float, zone_high: float, tolerance: float) -> dict[str, object] | None:
    start = max(4, len(candles) - 30)
    bodies = (candles["close"].astype(float) - candles["open"].astype(float)).abs()
    median_body = max(float(bodies.tail(20).median()), 1e-12)
    for index in range(start, len(candles)):
        candle = candles.iloc[index]
        prior = candles.iloc[max(0, index - 4):index]
        touched = float(candle["low"]) <= zone_high + tolerance and float(candle["high"]) >= zone_low - tolerance
        recent_touch = touched or bool(((prior["low"].astype(float) <= zone_high + tolerance) & (prior["high"].astype(float) >= zone_low - tolerance)).any())
        body = abs(float(candle["close"]) - float(candle["open"]))
        if direction == "buy":
            trigger = float(prior["high"].max())
            valid = recent_touch and float(candle["close"]) > trigger and float(candle["close"]) > float(candle["open"]) and body >= median_body
        else:
            trigger = float(prior["low"].min())
            valid = recent_touch and float(candle["close"]) < trigger and float(candle["close"]) < float(candle["open"]) and body >= median_body
        if valid:
            return {"direction": direction, "trigger": trigger, "candle_close": float(candle["close"]), "candle_time": candle["time"].isoformat(), "index": index, "completed": True}
    return None


def _forming_trigger(all_candles: pd.DataFrame, completed: pd.DataFrame, direction: str, zone_low: float, zone_high: float, tolerance: float) -> dict[str, object] | None:
    if all_candles.empty or len(all_candles) <= len(completed):
        return None
    candle = all_candles.iloc[-1]
    prior = completed.tail(4)
    if prior.empty:
        return None
    trigger = float(prior["high"].max()) if direction == "buy" else float(prior["low"].min())
    touched = float(candle["low"]) <= zone_high + tolerance and float(candle["high"]) >= zone_low - tolerance
    recent_touch = touched or bool(((prior["low"].astype(float) <= zone_high + tolerance) & (prior["high"].astype(float) >= zone_low - tolerance)).any())
    crossed = recent_touch and (float(candle["close"]) > trigger if direction == "buy" else float(candle["close"]) < trigger)
    if not crossed:
        return None
    return {"direction": direction, "trigger": trigger, "candle_time": candle["time"].isoformat(), "completed": False}


def _m5_stop(candles: pd.DataFrame, direction: str, zone_low: float, zone_high: float, spread: float, atr: float, trigger_index: int) -> float:
    structure = candles.iloc[max(0, trigger_index - 6):trigger_index + 1]
    buffer = max(spread, atr * 0.1)
    if direction == "buy":
        anchor = min(float(structure["low"].min()), zone_low)
        return anchor - buffer
    anchor = max(float(structure["high"].max()), zone_high)
    return anchor + buffer


def _targets(top_down: dict[str, object], m5: pd.DataFrame, direction: str, entry: float, current: float, atr: float) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    context = (top_down.get("m15_setup") or {}).get("target_context") or {}
    price = _number(context.get("price"))
    if price is not None:
        candidates.append({"name": "TP1", "price": price, "timeframe": "M15", "reason": context.get("reason", "M15 objective"), "swept": False})
    for name, timeframe in (("TP2", "H1"), ("TP3", "H4")):
        frame = (top_down.get("timeframes") or {}).get(timeframe) or {}
        swings = frame.get("unswept_highs" if direction == "buy" else "unswept_lows") or []
        eligible = [row for row in swings if _number(row.get("price")) is not None and (float(row["price"]) > entry if direction == "buy" else float(row["price"]) < entry)]
        if eligible:
            nearest_swing = min(eligible, key=lambda row: abs(float(row["price"]) - entry))
            candidates.append({"name": name, "price": float(nearest_swing["price"]), "timeframe": timeframe, "reason": f"Unswept {timeframe} structure objective", "origin_time": nearest_swing.get("time"), "swept": False})
    unique: list[dict[str, object]] = []
    for candidate in candidates:
        target = float(candidate["price"])
        correct_side = target > max(entry, current) if direction == "buy" else target < min(entry, current)
        reachable = abs(target - current) <= atr * 20
        if correct_side and reachable and all(abs(target - float(existing["price"])) > 1e-12 for existing in unique):
            unique.append(candidate)
    return sorted(unique, key=lambda target: abs(float(target["price"]) - entry))[:3]


def _filters_block(asset_type: str, news: dict[str, object], session: dict[str, object]) -> bool:
    if bool((news.get("news_risk") or news).get("restriction_active")):
        return True
    if str(asset_type).lower() == "crypto":
        return False
    return not bool(session.get("entry_allowed", True))


def _available_candles(candles: pd.DataFrame, boundary: object) -> pd.DataFrame:
    if candles is None or candles.empty:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close"])
    clean = candles.copy()
    clean["time"] = pd.to_datetime(clean["time"], utc=True, errors="coerce")
    cutoff = pd.Timestamp(boundary)
    cutoff = cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
    return clean.loc[clean["time"] <= cutoff].dropna().sort_values("time").reset_index(drop=True)


def _atr(candles: pd.DataFrame) -> float:
    high, low, close = candles["high"].astype(float), candles["low"].astype(float), candles["close"].astype(float)
    previous = close.shift(1)
    true_range = pd.concat([(high - low), (high - previous).abs(), (low - previous).abs()], axis=1).max(axis=1)
    return max(float(true_range.tail(14).mean()), 1e-12)


def _empty_plan(direction: str) -> dict[str, object]:
    return {"execution_timeframe": "M5", "timeframe": "M5", "direction": direction if direction in {"buy", "sell"} else "neutral", "state": "waiting_for_zone", "entry": None, "entry_zone": None, "trigger": None, "stop": None, "targets": [], "risk_reward": None, "entry_timing": "WAITING FOR M15 AREA", "forming_signal": None, "confirmed_signal": None, "message": ""}


def _normalize_price(value: float, asset_type: str, direction: str, *, is_stop: bool = False) -> float:
    rounding = "down" if is_stop and direction == "buy" else "up" if is_stop and direction == "sell" else "nearest"
    return float(normalize_price(value, asset_rules("", asset_type), rounding=rounding))


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None

def _timestamp(value: object) -> pd.Timestamp | None:
    if value is None: return None
    stamp=pd.Timestamp(value)
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
