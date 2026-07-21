"""ICT Power of Three / market phase detection."""

from __future__ import annotations

import pandas as pd


def detect_market_phase(
    candles: pd.DataFrame,
    session_context: dict[str, object],
) -> dict[str, object]:
    """Classify the current market phase from recent candle behavior."""
    if candles.empty or len(candles) < 30:
        return _phase("Waiting", "Not enough candle history to classify the current phase.", "Load more candles.")

    clean = candles.copy().sort_values("time").reset_index(drop=True)
    recent = clean.tail(60)
    close = recent["close"].astype(float)
    high = float(recent["high"].max())
    low = float(recent["low"].min())
    current = float(close.iloc[-1])
    start = float(close.iloc[0])
    total_range = max(high - low, 0.0000001)
    directional_move = abs(current - start)
    trend_strength = directional_move / total_range
    session_name = str(session_context.get("name", ""))
    session_phase = str(session_context.get("phase", ""))

    if session_name == "Asian Session":
        return _phase(
            "Accumulation",
            "Price is building the Asia range and defining liquidity.",
            "Mark range high, range low, and resting liquidity.",
        )

    if session_name == "London Kill Zone":
        if trend_strength < 0.35:
            return _phase(
                "Manipulation",
                "London is likely probing liquidity before direction is confirmed.",
                "Watch for liquidity sweep and CHOCH.",
            )
        return _phase(
            "Trend",
            "London has directional movement after the initial range.",
            "Track displacement and continuation into HTF draw.",
        )

    if session_name == "New York Kill Zone":
        return _phase(
            "Distribution",
            "New York is looking for continuation or distribution from earlier manipulation.",
            "Focus on entry confirmation aligned with HTF liquidity.",
        )

    if session_name == "London Close":
        return _phase(
            "Distribution",
            "London close often brings continuation, rebalancing, or profit taking.",
            "Avoid chasing late entries; manage context and liquidity objectives.",
        )

    if trend_strength >= 0.72:
        return _phase(
            "Trend",
            "Price is expanding directionally outside the main kill zones.",
            "Update context, but keep entries blocked by the session filter.",
        )

    if session_phase == "Context Only":
        return _phase(
            "Range",
            "Price is outside active entry windows and may be balancing.",
            "Maintain macro context and wait for the next kill zone.",
        )

    return _phase(
        "Range",
        "Price is rotating without strong displacement.",
        "Wait for manipulation or displacement before judging entries.",
    )


def _phase(name: str, behavior: str, focus: str) -> dict[str, object]:
    return {
        "current_phase": name,
        "expected_behavior": behavior,
        "recommended_focus": focus,
    }
