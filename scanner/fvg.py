"""Fair Value Gap helpers for the current-chart analyzer."""

from __future__ import annotations

import pandas as pd


def detect_fvgs(candles: pd.DataFrame) -> list[dict[str, object]]:
    """Return bullish and bearish 3-candle FVG zones."""
    zones: list[dict[str, object]] = []

    for index in range(2, len(candles)):
        candle_1 = candles.iloc[index - 2]
        candle_3 = candles.iloc[index]

        if candle_1["high"] < candle_3["low"]:
            zones.append(
                _zone(
                    zone_type="bullish",
                    start_index=index - 2,
                    end_index=index,
                    start_time=candle_1["time"],
                    end_time=candle_3["time"],
                    top_price=candle_3["low"],
                    bottom_price=candle_1["high"],
                )
            )

        if candle_1["low"] > candle_3["high"]:
            zones.append(
                _zone(
                    zone_type="bearish",
                    start_index=index - 2,
                    end_index=index,
                    start_time=candle_1["time"],
                    end_time=candle_3["time"],
                    top_price=candle_1["low"],
                    bottom_price=candle_3["high"],
                )
            )

    return _mark_mitigation(candles, zones)


def nearest_active_fvg(
    candles: pd.DataFrame,
    zones: list[dict[str, object]],
    direction: str | None,
    lookback: int = 120,
) -> dict[str, object] | None:
    """Pick one nearby active FVG instead of drawing every historical zone."""
    if not zones or candles.empty:
        return None

    current_price = float(candles.iloc[-1]["close"])
    average_range = _average_range(candles)
    max_distance = max(average_range * 12, abs(current_price) * 0.002)
    preferred_type = _preferred_fvg_type(direction)
    candidates = []

    for zone in zones:
        if int(zone["end_index"]) < len(candles) - lookback:
            continue

        if zone.get("status") == "mitigated":
            continue

        if preferred_type and zone["type"] != preferred_type:
            continue

        if not _is_active_now(current_price, zone):
            continue

        midpoint = (float(zone["top_price"]) + float(zone["bottom_price"])) / 2
        distance = abs(current_price - midpoint)
        if distance > max_distance:
            continue

        recency = int(zone["end_index"])
        candidates.append((distance, -recency, zone))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def select_ict_fvg(
    candles: pd.DataFrame,
    zones: list[dict[str, object]],
    direction: str | None,
    after_index: int | None = None,
    lookback: int = 120,
) -> dict[str, object] | None:
    """Select one active directional FVG for the current ICT sequence."""
    filtered = []
    for zone in zones:
        if after_index is not None and int(zone.get("end_index", -1)) < after_index:
            continue
        filtered.append(zone)
    return nearest_active_fvg(candles, filtered, direction, lookback=lookback)


def _preferred_fvg_type(direction: str | None) -> str | None:
    if direction == "bullish":
        return "bullish"
    if direction == "bearish":
        return "bearish"
    return None


def _is_active_now(current_price: float, zone: dict[str, object]) -> bool:
    """A simple invalidation check for current-chart relevance."""
    if zone["type"] == "bullish":
        return current_price >= float(zone["bottom_price"])
    return current_price <= float(zone["top_price"])


def _mark_mitigation(
    candles: pd.DataFrame,
    zones: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Attach mitigation status and rectangle end time to each zone."""
    if candles.empty:
        return zones

    current_time = str(candles.iloc[-1]["time"])

    for zone in zones:
        mitigation_index = _mitigation_index(candles, zone)

        if mitigation_index is None:
            zone["status"] = "active"
            zone["mitigated_index"] = None
            zone["mitigated_time"] = None
            zone["rectangle_end_time"] = current_time
            continue

        zone["status"] = "mitigated"
        zone["mitigated_index"] = mitigation_index
        zone["mitigated_time"] = str(candles.iloc[mitigation_index]["time"])
        zone["rectangle_end_time"] = zone["mitigated_time"]

    return zones


def _mitigation_index(
    candles: pd.DataFrame,
    zone: dict[str, object],
) -> int | None:
    """Return the first candle that fully fills the FVG."""
    start = int(zone["end_index"]) + 1

    for index in range(start, len(candles)):
        candle = candles.iloc[index]

        if zone["type"] == "bullish" and float(candle["low"]) <= float(zone["bottom_price"]):
            return index

        if zone["type"] == "bearish" and float(candle["high"]) >= float(zone["top_price"]):
            return index

    return None


def _average_range(candles: pd.DataFrame) -> float:
    ranges = candles["high"].astype(float) - candles["low"].astype(float)
    average = float(ranges.tail(50).mean())
    if pd.isna(average) or average <= 0:
        return max(abs(float(candles.iloc[-1]["close"])) * 0.001, 0.0001)
    return average


def _zone(
    zone_type: str,
    start_index: int,
    end_index: int,
    start_time,
    end_time,
    top_price,
    bottom_price,
) -> dict[str, object]:
    return {
        "type": zone_type,
        "start_index": start_index,
        "end_index": end_index,
        "start_time": str(start_time),
        "end_time": str(end_time),
        "top_price": float(top_price),
        "bottom_price": float(bottom_price),
    }
