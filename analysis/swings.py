"""Strategy-neutral swing detection."""

from __future__ import annotations

import pandas as pd


def detect_swing_points(
    candles: pd.DataFrame,
    width: int = 2,
    lookback: int = 180,
) -> dict[str, list[dict[str, object]]]:
    """Detect confirmed swing highs and lows."""
    swing_highs: list[dict[str, object]] = []
    swing_lows: list[dict[str, object]] = []
    start_index = max(width, len(candles) - lookback)

    for index in range(start_index, len(candles) - width):
        window = candles.iloc[index - width : index + width + 1]
        candle = candles.iloc[index]

        if float(candle["high"]) == float(window["high"].max()):
            swing_highs.append(_swing("high", index, candle["time"], candle["high"], index + width, candles.iloc[index + width]["time"]))

        if float(candle["low"]) == float(window["low"].min()):
            swing_lows.append(_swing("low", index, candle["time"], candle["low"], index + width, candles.iloc[index + width]["time"]))

    return {
        "highs": swing_highs,
        "lows": swing_lows,
        "last_high": swing_highs[-1] if swing_highs else {},
        "last_low": swing_lows[-1] if swing_lows else {},
    }


def _swing(kind: str, index: int, time, price, confirmed_index: int, confirmed_at) -> dict[str, object]:
    return {
        "type": kind,
        "index": index,
        "time": str(time),
        "price": float(price),
        "confirmed_index": confirmed_index,
        "confirmed_at": str(confirmed_at),
    }
