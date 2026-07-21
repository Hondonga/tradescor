"""Strategy-neutral trend analysis."""

from __future__ import annotations

import pandas as pd


def analyze_trend(candles: pd.DataFrame, swings: dict[str, object]) -> dict[str, object]:
    """Classify trend using moving averages and swing progression."""
    if len(candles) < 20:
        return {"direction": "Neutral", "strength": "Weak", "reason": "Not enough candles."}

    closes = candles["close"].astype(float)
    fast_ma = float(closes.tail(20).mean())
    slow_window = min(50, len(closes))
    slow_ma = float(closes.tail(slow_window).mean())
    current = float(closes.iloc[-1])
    previous = float(closes.iloc[-min(len(closes), 20)])
    slope = current - previous

    highs = swings.get("highs", [])[-3:]
    lows = swings.get("lows", [])[-3:]
    higher_highs = _rising(highs)
    higher_lows = _rising(lows)
    lower_highs = _falling(highs)
    lower_lows = _falling(lows)

    bullish_votes = sum([current > slow_ma, fast_ma > slow_ma, slope > 0, higher_highs, higher_lows])
    bearish_votes = sum([current < slow_ma, fast_ma < slow_ma, slope < 0, lower_highs, lower_lows])

    if bullish_votes >= 3 and bullish_votes > bearish_votes:
        direction = "Bullish"
        strength = _strength(bullish_votes)
    elif bearish_votes >= 3 and bearish_votes > bullish_votes:
        direction = "Bearish"
        strength = _strength(bearish_votes)
    else:
        direction = "Neutral"
        strength = "Weak"

    return {
        "direction": direction,
        "strength": strength,
        "fast_ma": round(fast_ma, 6),
        "slow_ma": round(slow_ma, 6),
        "slope": round(slope, 6),
        "higher_highs": higher_highs,
        "higher_lows": higher_lows,
        "lower_highs": lower_highs,
        "lower_lows": lower_lows,
        "bullish_votes": bullish_votes,
        "bearish_votes": bearish_votes,
        "reason": _reason(direction, strength),
    }


def _rising(points: list[dict[str, object]]) -> bool:
    return len(points) >= 2 and all(float(first["price"]) < float(second["price"]) for first, second in zip(points, points[1:]))


def _falling(points: list[dict[str, object]]) -> bool:
    return len(points) >= 2 and all(float(first["price"]) > float(second["price"]) for first, second in zip(points, points[1:]))


def _strength(votes: int) -> str:
    if votes >= 5:
        return "Strong"
    if votes >= 4:
        return "Medium"
    return "Developing"


def _reason(direction: str, strength: str) -> str:
    if direction == "Bullish":
        return f"{strength} bullish trend based on moving average and structure alignment."
    if direction == "Bearish":
        return f"{strength} bearish trend based on moving average and structure alignment."
    return "Trend is mixed or sideways."
