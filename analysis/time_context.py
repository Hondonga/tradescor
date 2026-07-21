"""Temporal boundaries shared by live analysis and replay."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd


TIMEFRAME_DURATIONS = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H2": timedelta(hours=2),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
    "W1": timedelta(days=7),
}


def as_utc_timestamp(value: object) -> pd.Timestamp:
    """Return one timezone-aware UTC timestamp."""
    if isinstance(value, (int, float)):
        timestamp = pd.to_datetime(value, unit="s", utc=True)
    else:
        timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp


def get_analysis_timestamp(selected_candles: pd.DataFrame) -> pd.Timestamp:
    """Use the latest available selected-timeframe candle as replay time."""
    if selected_candles is None or selected_candles.empty:
        raise ValueError("Analysis requires at least one candle timestamp.")
    return as_utc_timestamp(selected_candles.sort_values("time").iloc[-1]["time"])


def slice_candles_until(
    candles: pd.DataFrame,
    timestamp: object,
    *,
    timeframe: str | None = None,
    require_closed: bool = False,
) -> pd.DataFrame:
    """Remove candles that were not available at the analysis timestamp."""
    if candles is None or candles.empty:
        return pd.DataFrame(columns=getattr(candles, "columns", None))

    boundary = as_utc_timestamp(timestamp)
    clean = candles.copy()
    clean["time"] = pd.to_datetime(clean["time"], errors="coerce", utc=True)
    clean = clean.dropna(subset=["time"]).sort_values("time")

    if require_closed:
        duration = TIMEFRAME_DURATIONS.get(str(timeframe or "").upper())
        if duration is not None:
            available = clean["time"] + duration <= boundary
        else:
            available = clean["time"] <= boundary
    else:
        available = clean["time"] <= boundary

    sliced = clean.loc[available].reset_index(drop=True)
    sliced.attrs.update(getattr(candles, "attrs", {}))
    return sliced


def slice_multi_timeframe_context_until(
    context: dict[str, pd.DataFrame],
    timestamp: object,
    *,
    selected_timeframe: str,
) -> dict[str, pd.DataFrame]:
    """Slice every context frame to what was closed by replay time."""
    selected = selected_timeframe.upper()
    return {
        timeframe: slice_candles_until(
            candles,
            timestamp,
            timeframe=timeframe,
            require_closed=timeframe.upper() != selected,
        )
        for timeframe, candles in context.items()
    }


def build_temporal_context(
    *,
    selected_candles: pd.DataFrame,
    context: dict[str, pd.DataFrame],
    selected_timeframe: str,
    replay: bool,
    live_timestamp: object | None = None,
) -> dict[str, object]:
    """Build the authoritative timestamp and safely sliced candle context."""
    analysis_timestamp = (
        get_analysis_timestamp(selected_candles)
        if replay
        else as_utc_timestamp(live_timestamp or pd.Timestamp.now(tz="UTC"))
    )
    selected = slice_candles_until(selected_candles, analysis_timestamp)
    sliced_context = slice_multi_timeframe_context_until(
        context,
        analysis_timestamp,
        selected_timeframe=selected_timeframe,
    )
    sliced_context[selected_timeframe.upper()] = selected

    return {
        "analysis_timestamp": analysis_timestamp,
        "analysis_timestamp_epoch": int(analysis_timestamp.timestamp()),
        "analysis_timestamp_iso": analysis_timestamp.isoformat(),
        "selected_candles": selected,
        "context": sliced_context,
        "mode": "replay" if replay else "live",
    }
