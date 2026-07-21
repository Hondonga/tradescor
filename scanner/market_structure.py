"""Market Structure Shift detection."""

from __future__ import annotations

import pandas as pd


def detect_mss(
    candles: pd.DataFrame,
    swings: dict[str, list[dict[str, object]]],
    sweep: dict[str, object] | None,
    lookback: int = 80,
) -> dict[str, object] | None:
    """Detect an MSS only after a liquidity sweep."""
    if sweep is None:
        return None

    sweep_index = int(sweep["index"])

    if sweep["direction"] == "bullish":
        reference = _last_swing_before(swings["highs"], sweep_index, lookback)
        if reference is None:
            return None

        for index in range(sweep_index + 1, len(candles)):
            candle = candles.iloc[index]
            if candle["close"] > reference["price"]:
                return _mss("bullish", index, candle["time"], reference["price"])

    if sweep["direction"] == "bearish":
        reference = _last_swing_before(swings["lows"], sweep_index, lookback)
        if reference is None:
            return None

        for index in range(sweep_index + 1, len(candles)):
            candle = candles.iloc[index]
            if candle["close"] < reference["price"]:
                return _mss("bearish", index, candle["time"], reference["price"])

    return None


def _last_swing_before(
    swings: list[dict[str, object]],
    index: int,
    lookback: int,
) -> dict[str, object] | None:
    previous = [
        swing
        for swing in swings
        if int(swing["index"]) < index and int(swing["index"]) >= index - lookback
    ]
    if not previous:
        return None
    return previous[-1]


def _mss(direction: str, index: int, time, level) -> dict[str, object]:
    return {
        "direction": direction,
        "index": index,
        "time": str(time),
        "level": float(level),
    }
