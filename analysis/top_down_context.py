"""Multi-timeframe top-down context analysis."""

from __future__ import annotations

import pandas as pd

from analysis import build_shared_analysis


MAJOR_TIMEFRAMES = ["D1", "H4", "H1"]
TIMING_TIMEFRAMES = ["M15", "M5", "M1"]


def analyze_top_down_context(
    candles_by_timeframe: dict[str, pd.DataFrame],
    selected_timeframe: str,
) -> dict[str, object]:
    """Analyze each loaded timeframe and summarize alignment."""
    timeframes: dict[str, dict[str, object]] = {}

    for timeframe, candles in candles_by_timeframe.items():
        if candles is None or candles.empty:
            continue

        shared = build_shared_analysis(candles)
        timeframes[timeframe] = _timeframe_row(timeframe, shared)

    overall_alignment = _overall_alignment(timeframes)
    conflicts = _conflicts(timeframes)

    return {
        "overall_alignment": overall_alignment,
        "summary": _summary(timeframes, selected_timeframe, overall_alignment),
        "timeframes": timeframes,
        "conflicts": conflicts,
        "selected_timeframe": selected_timeframe,
    }


def _timeframe_row(timeframe: str, shared: dict[str, object]) -> dict[str, object]:
    trend = shared.get("trend", {})
    structure = shared.get("structure", {})
    zones = shared.get("zones", {})
    current = shared.get("current", {})
    bias = str(trend.get("direction", "Neutral"))
    status = _status(bias, current, zones)

    return {
        "timeframe": timeframe,
        "bias": bias,
        "trend": _trend_label(bias),
        "structure": _structure_label(structure),
        "key_zone": _key_zone(bias, zones),
        "status": status,
        "last_close": current.get("current_price"),
    }


def _trend_label(bias: str) -> str:
    if bias == "Bullish":
        return "Uptrend"
    if bias == "Bearish":
        return "Downtrend"
    return "Sideways"


def _structure_label(structure: dict[str, object]) -> str:
    if structure.get("higher_high") and structure.get("higher_low"):
        return "Higher highs / higher lows"
    if structure.get("lower_high") and structure.get("lower_low"):
        return "Lower highs / lower lows"
    return "Mixed structure"


def _key_zone(bias: str, zones: dict[str, object]) -> str:
    if bias == "Bullish" and zones.get("nearest_support"):
        return "Demand"
    if bias == "Bearish" and zones.get("nearest_resistance"):
        return "Supply"
    if zones.get("nearest_support"):
        return "Support"
    if zones.get("nearest_resistance"):
        return "Resistance"
    return "None"


def _status(bias: str, current: dict[str, object], zones: dict[str, object]) -> str:
    price = current.get("current_price")
    if price is None:
        return "Waiting"

    if bias == "Bullish" and _inside_zone(float(price), zones.get("nearest_support")):
        return "Pullback"
    if bias == "Bearish" and _inside_zone(float(price), zones.get("nearest_resistance")):
        return "Pullback"
    if bias in {"Bullish", "Bearish"}:
        return "Trend"
    return "Waiting"


def _inside_zone(price: float, zone: dict[str, object] | None) -> bool:
    if not zone:
        return False
    return float(zone["bottom_price"]) <= price <= float(zone["top_price"])


def _overall_alignment(timeframes: dict[str, dict[str, object]]) -> str:
    major_rows = [timeframes[tf] for tf in MAJOR_TIMEFRAMES if tf in timeframes]
    rows = major_rows or list(timeframes.values())
    scores = [_bias_score(row.get("bias")) for row in rows]

    if not scores:
        return "Neutral"

    total = sum(scores)
    if total >= max(2, len(scores)):
        return "Bullish"
    if total <= -max(2, len(scores)):
        return "Bearish"
    if any(score > 0 for score in scores) and any(score < 0 for score in scores):
        return "Mixed"
    return "Neutral"


def _conflicts(timeframes: dict[str, dict[str, object]]) -> list[str]:
    conflicts: list[str] = []
    major_bias = _major_bias(timeframes)

    if major_bias not in {"Bullish", "Bearish"}:
        return conflicts

    for timeframe in TIMING_TIMEFRAMES:
        row = timeframes.get(timeframe)
        if not row:
            continue
        bias = row.get("bias")
        if bias in {"Bullish", "Bearish"} and bias != major_bias:
            conflicts.append(f"{timeframe} {str(bias).lower()} against {major_bias.lower()} higher timeframe context")

    return conflicts


def _major_bias(timeframes: dict[str, dict[str, object]]) -> str:
    rows = [timeframes[tf] for tf in MAJOR_TIMEFRAMES if tf in timeframes]
    scores = [_bias_score(row.get("bias")) for row in rows]
    total = sum(scores)
    if total > 0:
        return "Bullish"
    if total < 0:
        return "Bearish"
    return "Neutral"


def _summary(
    timeframes: dict[str, dict[str, object]],
    selected_timeframe: str,
    alignment: str,
) -> str:
    if not timeframes:
        return "Top-down context is not loaded."

    major_parts = []
    for timeframe in MAJOR_TIMEFRAMES:
        row = timeframes.get(timeframe)
        if row and row.get("bias") in {"Bullish", "Bearish"}:
            major_parts.append(f"{timeframe} {str(row['bias']).lower()}")

    selected = timeframes.get(selected_timeframe)
    selected_text = ""
    if selected:
        selected_text = f", {selected_timeframe} is {str(selected.get('status', 'waiting')).lower()}"

    if major_parts:
        return f"{'/'.join(major_parts)} with {alignment.lower()} alignment{selected_text}."

    return f"Top-down alignment is {alignment.lower()}{selected_text}."


def _bias_score(value: object) -> int:
    if value == "Bullish":
        return 1
    if value == "Bearish":
        return -1
    return 0
