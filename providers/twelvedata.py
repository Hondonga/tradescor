"""Twelve Data response normalization at the provider boundary."""

from __future__ import annotations

import pandas as pd


INTRADAY_INTERVALS = {"1min", "5min", "15min", "30min", "45min", "1h", "2h", "4h", "8h"}


def normalize_time_series_payload(
    payload: dict[str, object],
    *,
    interval: str,
    requested_timezone: str | None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Return UTC candles and timestamp provenance from one API response."""
    values = payload.get("values") or []
    candles = pd.DataFrame(values)
    required = ["datetime", "open", "high", "low", "close"]
    missing = [column for column in required if column not in candles.columns]
    if missing:
        raise RuntimeError(f"Twelve Data response is missing column(s): {', '.join(missing)}.")

    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    exchange_timezone = str(meta.get("exchange_timezone") or "").strip()
    intraday = interval in INTRADAY_INTERVALS
    source_timezone = requested_timezone if intraday and requested_timezone else exchange_timezone
    warnings: list[str] = []
    raw_timestamps = candles["datetime"].astype(str).tolist()

    if not source_timezone:
        source_timezone = "UTC"
        warnings.append("Source timezone was not supplied; UTC was assumed.")

    parsed = pd.to_datetime(candles["datetime"], errors="coerce")
    try:
        if getattr(parsed.dt, "tz", None) is None:
            parsed = parsed.dt.tz_localize(source_timezone, ambiguous="infer", nonexistent="shift_forward")
        parsed = parsed.dt.tz_convert("UTC")
    except (TypeError, ValueError, KeyError):
        parsed = pd.to_datetime(candles["datetime"], errors="coerce", utc=True)
        warnings.append(f"Could not apply source timezone '{source_timezone}'; UTC was assumed.")

    raw_rows=len(candles);duplicate_timestamps=int(parsed.duplicated().sum());candles = candles.rename(columns={"datetime": "time"})
    candles["time"] = parsed
    for column in ["open", "high", "low", "close"]:
        candles[column] = pd.to_numeric(candles[column], errors="coerce")
    malformed=int(candles[["time","open","high","low","close"]].isna().any(axis=1).sum());geometry=(candles["high"]>=candles[["open","close","low"]].max(axis=1))&(candles["low"]<=candles[["open","close","high"]].min(axis=1));invalid_ohlc=int((~geometry & ~candles[["time","open","high","low","close"]].isna().any(axis=1)).sum());candles = candles.dropna(subset=["time", "open", "high", "low", "close"])
    candles=candles.loc[(candles["high"]>=candles[["open","close","low"]].max(axis=1))&(candles["low"]<=candles[["open","close","high"]].min(axis=1))]
    candles = candles.sort_values("time").drop_duplicates(subset=["time"], keep="last")
    candles = candles[["time", "open", "high", "low", "close"]].reset_index(drop=True)

    metadata = {
        "provider": "Twelve Data",
        "raw_provider_first_timestamp": raw_timestamps[-1] if raw_timestamps else None,
        "raw_provider_last_timestamp": raw_timestamps[0] if raw_timestamps else None,
        "source_timezone": source_timezone,
        "exchange_timezone": exchange_timezone or None,
        "normalized_timezone": "UTC",
        "timestamp_policy": "exchange_local_to_utc" if source_timezone != "UTC" else "source_utc_to_utc",
        "timezone_warning": warnings[0] if warnings else None,
        "warnings": warnings,
        "raw_rows":raw_rows,
        "valid_rows":len(candles),
        "duplicate_timestamps":duplicate_timestamps,
        "malformed_rows":malformed,
        "invalid_ohlc":invalid_ohlc,
        "ascending":bool(candles["time"].is_monotonic_increasing),
        "validation_passed":bool(len(candles) and not duplicate_timestamps and not malformed and not invalid_ohlc and candles["time"].is_monotonic_increasing),
    }
    candles.attrs["time_metadata"] = metadata
    return candles, metadata
