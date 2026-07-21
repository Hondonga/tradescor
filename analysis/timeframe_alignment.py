"""Shared higher-timeframe and execution-timeframe direction language."""

from __future__ import annotations


HIGHER_TIMEFRAMES = ("D1", "H4", "H1")
DIRECTIONAL = {"Bullish", "Bearish"}


def describe_timeframe_alignment(
    top_down_context: dict[str, object],
    selected_timeframe: str,
    execution_fallback: object = "Neutral",
) -> dict[str, str]:
    """Separate higher-timeframe bias from the selected execution trend."""
    rows = top_down_context.get("timeframes") or {}
    higher_bias = _higher_timeframe_bias(rows, top_down_context)
    selected_row = rows.get(selected_timeframe) or {}
    execution_trend = str(selected_row.get("bias") or execution_fallback or "Neutral")
    if execution_trend not in DIRECTIONAL:
        execution_trend = "Neutral"

    if higher_bias in DIRECTIONAL and execution_trend in DIRECTIONAL:
        alignment = "Aligned" if higher_bias == execution_trend else "Counter-trend"
    elif higher_bias in DIRECTIONAL:
        alignment = "Waiting"
    else:
        alignment = "Unconfirmed"

    if alignment == "Counter-trend":
        execution_description = f"{execution_trend} pullback"
        summary = (
            f"Higher-timeframe bias is {higher_bias.lower()}, but {selected_timeframe} "
            f"execution is {execution_trend.lower()} and not aligned yet."
        )
    elif alignment == "Aligned":
        execution_description = execution_trend
        summary = (
            f"Higher-timeframe bias is {higher_bias.lower()} and {selected_timeframe} "
            f"execution is aligned {execution_trend.lower()}."
        )
    elif higher_bias in DIRECTIONAL:
        execution_description = "Waiting"
        summary = (
            f"Higher-timeframe bias is {higher_bias.lower()}, while {selected_timeframe} "
            "execution direction is not confirmed yet."
        )
    else:
        execution_description = execution_trend if execution_trend in DIRECTIONAL else "Unclear"
        summary = "Higher-timeframe bias is not confirmed."

    return {
        "higher_timeframe_bias": higher_bias,
        "execution_timeframe": selected_timeframe,
        "execution_timeframe_trend": execution_trend,
        "execution_description": execution_description,
        "timeframe_alignment": alignment,
        "alignment_summary": summary,
    }


def _higher_timeframe_bias(
    rows: dict[str, dict[str, object]],
    top_down_context: dict[str, object],
) -> str:
    values = [str((rows.get(timeframe) or {}).get("bias", "Neutral")) for timeframe in HIGHER_TIMEFRAMES if timeframe in rows]
    score = sum(1 if value == "Bullish" else -1 if value == "Bearish" else 0 for value in values)
    if score > 0:
        return "Bullish"
    if score < 0:
        return "Bearish"

    if not values:
        alignment = str(top_down_context.get("overall_alignment", "Neutral"))
        if "Bullish" in alignment:
            return "Bullish"
        if "Bearish" in alignment:
            return "Bearish"
    return "Neutral"
