"""Strategy-neutral market structure analysis."""

from __future__ import annotations

import pandas as pd


def analyze_structure(candles: pd.DataFrame, swings: dict[str, object]) -> dict[str, object]:
    """Detect structure progression, BOS, and CHoCH-style breaks."""
    if candles.empty:
        return {}

    current_close = float(candles.iloc[-1]["close"])
    highs = swings.get("highs", [])
    lows = swings.get("lows", [])
    last_high = highs[-1] if highs else {}
    last_low = lows[-1] if lows else {}
    previous_high = highs[-2] if len(highs) >= 2 else {}
    previous_low = lows[-2] if len(lows) >= 2 else {}

    bos = {}
    if last_high and current_close > float(last_high["price"]):
        bos = _break("bullish", "BOS", last_high, current_close)
    elif last_low and current_close < float(last_low["price"]):
        bos = _break("bearish", "BOS", last_low, current_close)

    choch = {}
    if previous_low and last_low and float(last_low["price"]) < float(previous_low["price"]) and current_close > float(last_high.get("price", current_close + 1)):
        choch = _break("bullish", "CHoCH", last_high, current_close)
    elif previous_high and last_high and float(last_high["price"]) > float(previous_high["price"]) and current_close < float(last_low.get("price", current_close - 1)):
        choch = _break("bearish", "CHoCH", last_low, current_close)

    return {
        "last_swing_high": last_high,
        "last_swing_low": last_low,
        "previous_swing_high": previous_high,
        "previous_swing_low": previous_low,
        "higher_high": _higher(last_high, previous_high),
        "higher_low": _higher(last_low, previous_low),
        "lower_high": _lower(last_high, previous_high),
        "lower_low": _lower(last_low, previous_low),
        "bos": bos,
        "choch": choch,
        "minor_swing_high": last_high,
        "minor_swing_low": last_low,
    }


def _higher(current: dict[str, object], previous: dict[str, object]) -> bool:
    return bool(current and previous and float(current["price"]) > float(previous["price"]))


def _lower(current: dict[str, object], previous: dict[str, object]) -> bool:
    return bool(current and previous and float(current["price"]) < float(previous["price"]))


def _break(direction: str, break_type: str, level: dict[str, object], close: float) -> dict[str, object]:
    return {
        "direction": direction,
        "type": break_type,
        "level": float(level.get("price", close)),
        "time": level.get("time", ""),
        "close": close,
    }
