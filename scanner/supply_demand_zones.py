"""Supply and demand zones formed by a base and directional displacement."""

from __future__ import annotations

import pandas as pd


def detect_supply_demand_zones(
    candles: pd.DataFrame,
    *,
    atr: float | None = None,
    lookback: int = 180,
) -> dict[str, list[dict[str, object]]]:
    """Detect fresh base-origin zones that caused meaningful displacement."""
    if candles is None or len(candles) < 8:
        return {"demand": [], "supply": []}

    clean = candles.sort_values("time").reset_index(drop=True)
    ranges = clean["high"].astype(float) - clean["low"].astype(float)
    default_atr = float(atr or ranges.tail(14).mean())
    rolling_atr = ranges.rolling(14, min_periods=5).mean().fillna(default_atr)
    start = max(2, len(clean) - lookback)
    demand: list[dict[str, object]] = []
    supply: list[dict[str, object]] = []

    for base_index in range(start, len(clean) - 3):
        base = clean.iloc[base_index]
        local_atr = max(float(rolling_atr.iloc[base_index]), abs(float(base["close"])) * 0.00001)
        base_range = float(base["high"] - base["low"])
        base_body = abs(float(base["close"] - base["open"]))
        if base_range > local_atr * 1.45 or base_body > local_atr * 0.85:
            continue

        departure = clean.iloc[base_index + 1 : base_index + 4]
        bullish_move = float(departure["close"].max()) - float(base["high"])
        bearish_move = float(base["low"]) - float(departure["close"].min())
        largest_body = (departure["close"].astype(float) - departure["open"].astype(float)).abs()
        has_displacement = bool((largest_body >= local_atr * 0.65).any())
        if not has_displacement:
            continue

        if bullish_move >= local_atr * 1.25 and bullish_move > bearish_move:
            departure_index = _departure_index(departure, "demand")
            demand.append(_build_zone(clean, base_index, departure_index, "demand", bullish_move / local_atr, local_atr))
        elif bearish_move >= local_atr * 1.25:
            departure_index = _departure_index(departure, "supply")
            supply.append(_build_zone(clean, base_index, departure_index, "supply", bearish_move / local_atr, local_atr))

    return {
        "demand": _deduplicate(demand, default_atr),
        "supply": _deduplicate(supply, default_atr),
    }


def _departure_index(departure: pd.DataFrame, zone_type: str) -> int:
    bodies = departure["close"].astype(float) - departure["open"].astype(float)
    index = bodies.idxmax() if zone_type == "demand" else bodies.idxmin()
    return int(index)


def _build_zone(
    candles: pd.DataFrame,
    base_index: int,
    departure_index: int,
    zone_type: str,
    impulse_atr: float,
    atr: float,
) -> dict[str, object]:
    base = candles.iloc[base_index]
    if zone_type == "demand":
        distal = float(base["low"])
        proximal = max(float(base["open"]), float(base["close"]))
    else:
        distal = float(base["high"])
        proximal = min(float(base["open"]), float(base["close"]))

    top = max(proximal, distal)
    bottom = min(proximal, distal)
    touch_count, first_touch, invalidated_at = _zone_history(
        candles,
        zone_type,
        top,
        bottom,
        departure_index + 1,
    )
    status = "invalidated" if invalidated_at else "fresh" if touch_count == 0 else "tested" if touch_count <= 2 else "overused"
    departure = candles.iloc[departure_index]
    base_quality = max(0.0, 1.0 - ((float(base["high"] - base["low"])) / max(atr * 1.45, 1e-12)))
    return {
        "type": zone_type,
        "direction": "bullish" if zone_type == "demand" else "bearish",
        "label": "Demand Zone" if zone_type == "demand" else "Supply Zone",
        "start_index": base_index,
        "confirmed_index": departure_index,
        "departure_index": departure_index,
        "start_time": str(base["time"]),
        "confirmed_at": str(departure["time"]),
        "departure_time": str(departure["time"]),
        "top_price": round(top, 8),
        "bottom_price": round(bottom, 8),
        "proximal_price": round(proximal, 8),
        "distal_price": round(distal, 8),
        "price": round((top + bottom) / 2, 8),
        "impulse_atr": round(float(impulse_atr), 2),
        "base_quality": round(base_quality, 2),
        "touch_count": touch_count,
        "first_touch_time": first_touch,
        "invalidated_at": invalidated_at,
        "fresh": touch_count == 0 and invalidated_at is None,
        "status": status,
    }


def _zone_history(
    candles: pd.DataFrame,
    zone_type: str,
    top: float,
    bottom: float,
    start_index: int,
) -> tuple[int, str | None, str | None]:
    touches = 0
    first_touch = None
    invalidated_at = None
    was_inside = False
    for index in range(max(0, start_index), len(candles)):
        candle = candles.iloc[index]
        intersects = float(candle["low"]) <= top and float(candle["high"]) >= bottom
        if intersects and not was_inside:
            touches += 1
            first_touch = first_touch or str(candle["time"])
        was_inside = intersects
        close = float(candle["close"])
        invalid = close < bottom if zone_type == "demand" else close > top
        if invalid:
            invalidated_at = str(candle["time"])
            break
    return touches, first_touch, invalidated_at


def _deduplicate(zones: list[dict[str, object]], atr: float) -> list[dict[str, object]]:
    tolerance = max(float(atr) * 0.3, 1e-12)
    selected: list[dict[str, object]] = []
    for zone in sorted(zones, key=lambda item: (int(item["start_index"]), float(item["impulse_atr"])), reverse=True):
        midpoint = float(zone["price"])
        if any(abs(midpoint - float(existing["price"])) <= tolerance for existing in selected):
            continue
        selected.append(zone)
    return sorted(selected, key=lambda item: int(item["start_index"]))
