"""Inverted Fair Value Gap detection."""

from __future__ import annotations

import pandas as pd


def detect_ifvg(
    candles: pd.DataFrame,
    fvgs: list[dict[str, object]],
    direction: str | None,
    start_index: int | None,
    lookback: int = 80,
) -> dict[str, object] | None:
    """Find one IFVG entry zone relevant to the current direction."""
    if direction not in {"bullish", "bearish"}:
        return None

    broken_zones: list[dict[str, object]] = []
    if start_index is None:
        return None

    scan_start = max(start_index, len(candles) - lookback)

    for zone in fvgs:
        if direction == "bullish" and zone["type"] == "bearish":
            broken = _first_close_above(candles, zone, scan_start)
            if broken is not None:
                broken_zones.append(_ifvg("bullish", zone, broken))

        if direction == "bearish" and zone["type"] == "bullish":
            broken = _first_close_below(candles, zone, scan_start)
            if broken is not None:
                broken_zones.append(_ifvg("bearish", zone, broken))

    if not broken_zones:
        return None

    return max(broken_zones, key=lambda zone: int(zone["confirmed_index"]))


def _first_close_above(
    candles: pd.DataFrame,
    zone: dict[str, object],
    scan_start: int,
) -> int | None:
    start = max(int(zone["end_index"]) + 1, scan_start)
    for index in range(start, len(candles)):
        if candles.iloc[index]["close"] > float(zone["top_price"]):
            return index
    return None


def _first_close_below(
    candles: pd.DataFrame,
    zone: dict[str, object],
    scan_start: int,
) -> int | None:
    start = max(int(zone["end_index"]) + 1, scan_start)
    for index in range(start, len(candles)):
        if candles.iloc[index]["close"] < float(zone["bottom_price"]):
            return index
    return None


def _ifvg(
    direction: str,
    source_zone: dict[str, object],
    confirmed_index: int,
) -> dict[str, object]:
    return {
        "type": direction,
        "source_fvg_type": source_zone["type"],
        "start_time": source_zone["start_time"],
        "end_time": source_zone["end_time"],
        "confirmed_index": confirmed_index,
        "top_price": float(source_zone["top_price"]),
        "bottom_price": float(source_zone["bottom_price"]),
    }
