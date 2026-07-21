"""Strategy-neutral zone analysis."""

from __future__ import annotations

from scanner.fvg import detect_fvgs
from scanner.order_blocks import detect_order_blocks


def analyze_zones(candles, swings: dict[str, object], volatility: dict[str, object]) -> dict[str, object]:
    """Detect reusable support, resistance, FVG, and order-block style zones."""
    atr = float(volatility.get("atr") or _average_range(candles))
    buffer = max(atr * 0.35, abs(float(candles.iloc[-1]["close"])) * 0.00005)
    current_time = candles.iloc[-1]["time"]

    support_zones = [
        _swing_zone("support", swing, buffer, current_time)
        for swing in swings.get("lows", [])[-5:]
    ]
    resistance_zones = [
        _swing_zone("resistance", swing, buffer, current_time)
        for swing in swings.get("highs", [])[-5:]
    ]

    fvgs = detect_fvgs(candles)
    order_blocks = detect_order_blocks(
        candles,
        {"highs": swings.get("highs", []), "lows": swings.get("lows", [])},
        htf_bias="NEUTRAL",
    )

    return {
        "support": support_zones,
        "resistance": resistance_zones,
        "demand": support_zones,
        "supply": resistance_zones,
        "fvg": fvgs,
        "order_blocks": order_blocks,
        "nearest_support": _nearest_zone(candles, support_zones),
        "nearest_resistance": _nearest_zone(candles, resistance_zones),
    }


def _swing_zone(kind: str, swing: dict[str, object], buffer: float, current_time) -> dict[str, object]:
    price = float(swing["price"])
    return {
        "type": kind,
        "direction": "bullish" if kind == "support" else "bearish",
        "start_index": swing["index"],
        "confirmed_index": swing.get("confirmed_index", swing["index"]),
        "start_time": swing["time"],
        "confirmed_at": swing.get("confirmed_at", swing["time"]),
        "end_time": str(current_time),
        "top_price": price + buffer,
        "bottom_price": price - buffer,
        "price": price,
        "label": "Demand Zone" if kind == "support" else "Supply Zone",
        "status": "active",
    }


def _nearest_zone(candles, zones: list[dict[str, object]]) -> dict[str, object]:
    if not zones:
        return {}

    current = float(candles.iloc[-1]["close"])
    return sorted(zones, key=lambda zone: abs(current - float(zone["price"])))[0]


def _average_range(candles) -> float:
    ranges = candles["high"].astype(float) - candles["low"].astype(float)
    value = float(ranges.tail(20).mean())
    if value <= 0:
        return max(abs(float(candles.iloc[-1]["close"])) * 0.001, 0.0001)
    return value
