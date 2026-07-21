"""Synchronized, UTC-normalized candle bundle shared by every expert model."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from analysis.top_down_engine import STACK, completed_candles


def build_candle_bundle(*, symbol: str, asset_class: str, analysis_time: object, candles_by_timeframe: dict[str, pd.DataFrame], provider: str = "Twelve Data", metadata: dict[str, object] | None = None) -> dict[str, object]:
    boundary = _utc(analysis_time)
    warnings: list[str] = []
    frames: dict[str, dict[str, object]] = {}
    for timeframe in STACK:
        raw = candles_by_timeframe.get(timeframe, pd.DataFrame())
        clean, frame_warnings = _clean(raw, timeframe, boundary)
        confirmed = completed_candles(clean, timeframe, boundary)
        warnings.extend(frame_warnings)
        frames[timeframe] = {
            "candles": confirmed,
            "available_candles": clean,
            "last_completed_time": confirmed.iloc[-1]["time"].isoformat() if not confirmed.empty else None,
            "timezone": "UTC",
            "valid": len(confirmed) >= 20,
        }
        if len(confirmed) < 20:
            warnings.append(f"{timeframe} has fewer than 20 completed candles.")
    return {"symbol": symbol, "asset_class": asset_class, "analysis_time_utc": boundary.isoformat(), "provider": provider, "provider_metadata": metadata or {}, "timeframes": frames, "data_quality": "valid" if not warnings else "partial" if all(frame["candles"].shape[0] for frame in frames.values()) else "invalid", "warnings": sorted(set(warnings))}


def bundle_contract(bundle: dict[str, object]) -> dict[str, object]:
    """Return a JSON-safe summary without duplicating response candle payloads."""
    return {**{key: bundle[key] for key in ("symbol", "asset_class", "analysis_time_utc", "provider", "provider_metadata", "data_quality", "warnings")}, "timeframes": {timeframe: {"last_completed_time": row["last_completed_time"], "timezone": row["timezone"], "valid": row["valid"], "candle_count": len(row["candles"])} for timeframe, row in bundle["timeframes"].items()}}


def _clean(frame: pd.DataFrame, timeframe: str, boundary: pd.Timestamp) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close"]), [f"{timeframe} data is missing."]
    clean = frame.copy()
    clean["time"] = pd.to_datetime(clean["time"], utc=True, errors="coerce")
    for column in ("open", "high", "low", "close"):
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
    before = len(clean)
    clean = clean.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time", keep="last")
    if len(clean) != before:
        warnings.append(f"{timeframe} contained duplicate or malformed rows.")
    integrity = (clean["high"] >= clean[["open", "close", "low"]].max(axis=1)) & (clean["low"] <= clean[["open", "close", "high"]].min(axis=1))
    if not bool(integrity.all()):
        warnings.append(f"{timeframe} contains invalid OHLC geometry; affected rows were excluded.")
        clean = clean.loc[integrity]
    return clean.loc[clean["time"] <= boundary].reset_index(drop=True), warnings


def _utc(value: object) -> pd.Timestamp:
    stamp = pd.Timestamp(value if value is not None else datetime.now(timezone.utc))
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
