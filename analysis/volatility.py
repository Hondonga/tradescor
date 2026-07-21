"""Strategy-neutral volatility analysis."""

from __future__ import annotations

import pandas as pd


def analyze_volatility(candles: pd.DataFrame, period: int = 14) -> dict[str, object]:
    """Calculate ATR and a simple volatility health label."""
    if len(candles) < 2:
        return {"atr": None, "health": "Unknown", "current_range": None}

    high = candles["high"].astype(float)
    low = candles["low"].astype(float)
    close = candles["close"].astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = float(true_range.tail(period).mean())
    current_range = float(high.iloc[-1] - low.iloc[-1])

    if atr <= 0:
        health = "Unknown"
    elif current_range > atr * 2.5:
        health = "Hot"
    elif current_range < atr * 0.35:
        health = "Quiet"
    else:
        health = "Healthy"

    return {
        "atr": round(atr, 6),
        "current_range": round(current_range, 6),
        "health": health,
    }
