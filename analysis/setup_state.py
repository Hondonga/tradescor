"""Deterministic setup identity and completed-event reconstruction."""

from __future__ import annotations

import hashlib

import pandas as pd

from analysis.time_context import as_utc_timestamp


def build_setup_state(
    *,
    strategy: str,
    direction: str,
    created_at: object,
    current_state: str,
    completed_events: list[dict[str, object]] | None = None,
    active_zone: dict[str, object] | None = None,
    trigger_level: dict[str, object] | None = None,
    confirmation_event: dict[str, object] | None = None,
    entry_zone: dict[str, object] | None = None,
    invalidation: object = None,
    targets: list[dict[str, object]] | None = None,
    invalidated: bool = False,
    invalidation_reason: str | None = None,
) -> dict[str, object]:
    """Return a stable setup object reconstructed from available candles."""
    created = as_utc_timestamp(created_at)
    anchor = _zone_anchor(active_zone or {})
    identity = f"{strategy}|{direction.lower()}|{created.isoformat()}|{anchor}"
    setup_id = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]
    confirmation = confirmation_event or {}
    return {
        "setup_id": setup_id,
        "strategy": strategy,
        "direction": direction.lower(),
        "created_at": created.isoformat(),
        "current_state": current_state,
        "completed_events": completed_events or [],
        "active_zone": active_zone or {},
        "trigger_level": trigger_level or {},
        "confirmation_time": confirmation.get("time"),
        "entry_zone": entry_zone or active_zone or {},
        "invalidation": invalidation,
        "targets": targets or [],
        "invalidated": invalidated,
        "invalidation_reason": invalidation_reason,
    }


def select_trigger_after_zone(
    swings: dict[str, list[dict[str, object]]],
    direction: str,
    zone_index: int,
) -> dict[str, object]:
    """Lock the first confirmed reaction swing formed after the zone."""
    if direction not in {"Bullish", "Bearish"}:
        return {}
    key = "highs" if direction == "Bullish" else "lows"
    candidates = [
        swing
        for swing in swings.get(key, [])
        if int(swing.get("index", -1)) > int(zone_index)
    ]
    return dict(candidates[0]) if candidates else {}


def find_confirmation_event(
    candles: pd.DataFrame,
    direction: str,
    trigger: dict[str, object] | None,
    *,
    after_index: int | None = None,
) -> dict[str, object]:
    """Find the first close through a trigger and preserve its timestamp."""
    if direction not in {"Bullish", "Bearish"} or not trigger or trigger.get("price") is None:
        return {}
    trigger_index = int(trigger.get("confirmed_index", trigger.get("index", -1)))
    start = max(trigger_index + 1, int(after_index or 0))
    level = float(trigger["price"])
    for index in range(max(0, start), len(candles)):
        close = float(candles.iloc[index]["close"])
        confirmed = close > level if direction == "Bullish" else close < level
        if confirmed:
            return {
                "type": "confirmation",
                "index": index,
                "time": as_utc_timestamp(candles.iloc[index]["time"]).isoformat(),
                "level": level,
                "close": close,
                "direction": direction.lower(),
            }
    return {}


def find_zone_reaction(
    candles: pd.DataFrame,
    zone: dict[str, object],
    direction: str,
    *,
    after_index: int,
) -> dict[str, object]:
    """Find the first directional reaction candle inside a zone."""
    if direction not in {"Bullish", "Bearish"}:
        return {}
    top, bottom = _zone_bounds(zone)
    if top is None or bottom is None:
        return {}
    for index in range(max(0, after_index), len(candles)):
        candle = candles.iloc[index]
        touched = float(candle["low"]) <= top and float(candle["high"]) >= bottom
        directional = float(candle["close"]) > float(candle["open"])
        directional = directional if direction == "Bullish" else not directional
        if touched and directional:
            return {
                "type": "zone_reaction",
                "index": index,
                "time": as_utc_timestamp(candle["time"]).isoformat(),
                "direction": direction.lower(),
            }
    return {}


def current_price_near_zone(price: float, zone: dict[str, object] | None, buffer: float = 0.0) -> bool:
    top, bottom = _zone_bounds(zone or {})
    if top is None or bottom is None:
        return False
    return bottom - max(buffer, 0.0) <= float(price) <= top + max(buffer, 0.0)


def invalidation_event(
    candles: pd.DataFrame,
    direction: str,
    invalidation: float | None,
    *,
    after_index: int,
) -> dict[str, object]:
    """Find the first close through setup invalidation after confirmation."""
    if direction not in {"Bullish", "Bearish"} or invalidation is None:
        return {}
    for index in range(max(0, after_index), len(candles)):
        close = float(candles.iloc[index]["close"])
        invalid = close < invalidation if direction == "Bullish" else close > invalidation
        if invalid:
            return {
                "type": "invalidation",
                "index": index,
                "time": as_utc_timestamp(candles.iloc[index]["time"]).isoformat(),
                "level": float(invalidation),
                "close": close,
            }
    return {}


def event_record(event_type: str, timestamp: object, **details: object) -> dict[str, object]:
    return {"type": event_type, "time": as_utc_timestamp(timestamp).isoformat(), **details}


def _zone_anchor(zone: dict[str, object]) -> str:
    return str(zone.get("start_time") or zone.get("time") or zone.get("start_index") or "unanchored")


def _zone_bounds(zone: dict[str, object]) -> tuple[float | None, float | None]:
    top = zone.get("top", zone.get("top_price"))
    bottom = zone.get("bottom", zone.get("bottom_price"))
    if top is None or bottom is None:
        return None, None
    high, low = sorted((float(top), float(bottom)), reverse=True)
    return high, low
