"""Shared strategy-neutral analysis engine."""

from __future__ import annotations

import pandas as pd

from analysis.candles import current_price_context, normalize_candles
from analysis.liquidity import analyze_liquidity
from analysis.structure import analyze_structure
from analysis.swings import detect_swing_points
from analysis.trend import analyze_trend
from analysis.volatility import analyze_volatility
from analysis.zones import analyze_zones


def build_shared_analysis(candles: pd.DataFrame) -> dict[str, object]:
    """Analyze candles once and return reusable market context."""
    clean = normalize_candles(candles)
    swings = detect_swing_points(clean)
    volatility = analyze_volatility(clean)
    trend = analyze_trend(clean, swings)
    structure = analyze_structure(clean, swings)
    tolerance = _price_tolerance(clean, volatility)
    liquidity = analyze_liquidity(clean, swings, tolerance)
    zones = analyze_zones(clean, swings, volatility)

    return {
        "candles_count": len(clean),
        "current": current_price_context(clean),
        "swings": swings,
        "trend": trend,
        "structure": structure,
        "zones": zones,
        "liquidity": liquidity,
        "volatility": volatility,
    }


def _price_tolerance(candles: pd.DataFrame, volatility: dict[str, object]) -> float:
    atr = volatility.get("atr")
    if atr:
        return max(float(atr) * 0.25, abs(float(candles.iloc[-1]["close"])) * 0.00005)
    ranges = candles["high"].astype(float) - candles["low"].astype(float)
    return max(float(ranges.tail(20).mean()) * 0.25, abs(float(candles.iloc[-1]["close"])) * 0.00005)
