"""Fair Value Gap detection for OHLC candle data."""

from __future__ import annotations

import pandas as pd


def detect_fvgs(candles: pd.DataFrame) -> pd.DataFrame:
    """Detect bullish and bearish 3-candle Fair Value Gaps.

    Bullish FVG:
        Candle 1 high is below Candle 3 low.

    Bearish FVG:
        Candle 1 low is above Candle 3 high.
    """
    fvg_zones: list[dict[str, object]] = []

    for index in range(2, len(candles)):
        candle_1 = candles.iloc[index - 2]
        candle_2 = candles.iloc[index - 1]
        candle_3 = candles.iloc[index]

        if candle_1["high"] < candle_3["low"]:
            fvg_zones.append(
                {
                    "type": "bullish",
                    "start_time": candle_1["time"],
                    "end_time": candle_3["time"],
                    "top_price": float(candle_3["low"]),
                    "bottom_price": float(candle_1["high"]),
                    "displacement_time": candle_2["time"],
                }
            )

        if candle_1["low"] > candle_3["high"]:
            fvg_zones.append(
                {
                    "type": "bearish",
                    "start_time": candle_1["time"],
                    "end_time": candle_3["time"],
                    "top_price": float(candle_1["low"]),
                    "bottom_price": float(candle_3["high"]),
                    "displacement_time": candle_2["time"],
                }
            )

    fvgs = pd.DataFrame(fvg_zones)

    for column in ["start_time", "end_time", "displacement_time"]:
        if column in fvgs:
            fvgs[column] = fvgs[column].astype(str)

    return fvgs
