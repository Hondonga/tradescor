"""Liquidity, swing, and sweep detection."""

from __future__ import annotations

import pandas as pd


def detect_swings(
    candles: pd.DataFrame,
    width: int = 2,
    lookback: int = 120,
) -> dict[str, list[dict[str, object]]]:
    """Detect confirmed swing highs and swing lows near the current chart.

    A swing needs candles on both its left and right side, so the last few
    candles are intentionally not eligible until confirmed.
    """
    swing_highs: list[dict[str, object]] = []
    swing_lows: list[dict[str, object]] = []
    start_index = max(width, len(candles) - lookback)

    for index in range(start_index, len(candles) - width):
        window = candles.iloc[index - width : index + width + 1]
        candle = candles.iloc[index]

        if candle["high"] == window["high"].max():
            swing_highs.append(_swing("high", index, candle["time"], candle["high"], index + width, candles.iloc[index + width]["time"]))

        if candle["low"] == window["low"].min():
            swing_lows.append(_swing("low", index, candle["time"], candle["low"], index + width, candles.iloc[index + width]["time"]))

    return {"highs": swing_highs, "lows": swing_lows}


def detect_equal_levels(
    swings: dict[str, list[dict[str, object]]],
    tolerance: float,
) -> dict[str, list[dict[str, object]]]:
    """Detect nearby equal highs and equal lows from recent swings."""
    return {
        "equal_highs": _find_equal_levels(swings["highs"], tolerance),
        "equal_lows": _find_equal_levels(swings["lows"], tolerance),
    }


def detect_liquidity_sweeps(
    candles: pd.DataFrame,
    swings: dict[str, list[dict[str, object]]],
    lookback: int = 60,
) -> list[dict[str, object]]:
    """Detect buy-side and sell-side liquidity sweeps.

    Bullish sweep: price takes a previous low and closes back above it.
    Bearish sweep: price takes a previous high and closes back below it.
    """
    sweeps: list[dict[str, object]] = []
    start_index = max(1, len(candles) - lookback)

    for index in range(start_index, len(candles)):
        candle = candles.iloc[index]
        previous_low = _last_swing_before(swings["lows"], index, lookback)
        previous_high = _last_swing_before(swings["highs"], index, lookback)

        if previous_low and candle["low"] < previous_low["price"] < candle["close"]:
            sweeps.append(
                {
                    "direction": "bullish",
                    "side": "sell-side",
                    "index": index,
                    "time": str(candle["time"]),
                    "swept_level": float(previous_low["price"]),
                    "swept_price": float(candle["low"]),
                }
            )

        if previous_high and candle["high"] > previous_high["price"] > candle["close"]:
            sweeps.append(
                {
                    "direction": "bearish",
                    "side": "buy-side",
                    "index": index,
                    "time": str(candle["time"]),
                    "swept_level": float(previous_high["price"]),
                    "swept_price": float(candle["high"]),
                }
            )

    return sweeps


def most_recent_sweep(sweeps: list[dict[str, object]]) -> dict[str, object] | None:
    """Return the latest detected sweep."""
    if not sweeps:
        return None
    return max(sweeps, key=lambda sweep: int(sweep["index"]))


def _swing(kind: str, index: int, time, price, confirmed_index: int, confirmed_at) -> dict[str, object]:
    return {
        "type": kind,
        "index": index,
        "time": str(time),
        "price": float(price),
        "confirmed_index": confirmed_index,
        "confirmed_at": str(confirmed_at),
    }


def _last_swing_before(
    swings: list[dict[str, object]],
    index: int,
    lookback: int | None = None,
) -> dict[str, object] | None:
    previous = [swing for swing in swings if int(swing["index"]) < index]
    if lookback is not None:
        previous = [swing for swing in previous if int(swing["index"]) >= index - lookback]
    if not previous:
        return None
    return previous[-1]


def _find_equal_levels(
    levels: list[dict[str, object]],
    tolerance: float,
) -> list[dict[str, object]]:
    equal_levels: list[dict[str, object]] = []

    for previous, current in zip(levels, levels[1:]):
        if abs(float(previous["price"]) - float(current["price"])) <= tolerance:
            equal_levels.append(
                {
                    "start_time": previous["time"],
                    "end_time": current.get("confirmed_at", current["time"]),
                    "price": round((float(previous["price"]) + float(current["price"])) / 2, 6),
                }
            )

    return equal_levels
