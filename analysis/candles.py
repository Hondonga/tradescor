"""Strategy-neutral candle helpers."""

from __future__ import annotations

import pandas as pd


def normalize_candles(candles: pd.DataFrame) -> pd.DataFrame:
    """Return clean OHLC candles sorted from oldest to newest."""
    clean = candles.copy()
    clean["time"] = pd.to_datetime(clean["time"], errors="coerce")

    for column in ["open", "high", "low", "close"]:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    if "volume" in clean.columns:
        clean["volume"] = pd.to_numeric(clean["volume"], errors="coerce")

    clean = clean.dropna(subset=["time", "open", "high", "low", "close"])
    clean = clean.sort_values("time").drop_duplicates(subset=["time"], keep="last")
    return clean.reset_index(drop=True)


def current_price_context(candles: pd.DataFrame) -> dict[str, object]:
    """Summarize the current candle and recent range."""
    if candles.empty:
        return {}

    recent = candles.tail(min(len(candles), 80))
    current = candles.iloc[-1]
    high = float(recent["high"].max())
    low = float(recent["low"].min())
    close = float(current["close"])
    midpoint = (high + low) / 2

    if close > midpoint:
        location = "premium"
    elif close < midpoint:
        location = "discount"
    else:
        location = "equilibrium"

    return {
        "time": str(current["time"]),
        "current_price": close,
        "open": float(current["open"]),
        "high": float(current["high"]),
        "low": float(current["low"]),
        "range_high": high,
        "range_low": low,
        "range_midpoint": midpoint,
        "range_location": location,
    }


def to_unix_seconds(value) -> int:
    """Convert a candle timestamp to Lightweight Charts seconds."""
    if isinstance(value, (int, float)):
        return int(value)

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return int(timestamp.timestamp())
