"""ICT Optimal Trade Entry retracement zone."""

from __future__ import annotations

import pandas as pd


def analyze_ote(
    candles: pd.DataFrame,
    direction: str | None,
    lookback: int = 80,
) -> dict[str, object]:
    """Calculate the 62%-79% retracement zone of the recent dealing range."""
    normalized = _direction(direction)
    if candles.empty or normalized is None:
        return _empty()

    recent = candles.tail(min(len(candles), lookback))
    high = float(recent["high"].max())
    low = float(recent["low"].min())
    current = float(candles.iloc[-1]["close"])
    price_range = high - low
    if price_range <= 0:
        return _empty()

    if normalized == "bullish":
        top = high - (price_range * 0.62)
        bottom = high - (price_range * 0.79)
        location = "discount" if current <= (high + low) / 2 else "premium"
    else:
        bottom = low + (price_range * 0.62)
        top = low + (price_range * 0.79)
        location = "premium" if current >= (high + low) / 2 else "discount"

    in_zone = min(bottom, top) <= current <= max(bottom, top)
    start_time = str(recent.iloc[0]["time"])
    end_time = str(candles.iloc[-1]["time"])
    return {
        "available": True,
        "in_zone": in_zone,
        "status": "in_zone" if in_zone else "waiting",
        "direction": normalized,
        "location": location,
        "range_high": round(high, 6),
        "range_low": round(low, 6),
        "zone": {
            "type": f"{normalized}_ote",
            "label": "OTE Zone",
            "tag": "OTE",
            "tooltip": "ICT 62%-79% retracement zone",
            "start_time": start_time,
            "end_time": end_time,
            "top_price": round(max(top, bottom), 6),
            "bottom_price": round(min(top, bottom), 6),
        },
    }


def _empty() -> dict[str, object]:
    return {
        "available": False,
        "in_zone": False,
        "status": "waiting",
        "direction": None,
        "location": "unknown",
        "zone": {},
    }


def _direction(value: str | None) -> str | None:
    text = str(value or "").lower()
    if text in {"bullish", "long"}:
        return "bullish"
    if text in {"bearish", "short"}:
        return "bearish"
    return None
