"""ICT Power of Three phase interpretation."""

from __future__ import annotations

import pandas as pd

from scanner.market_phase import detect_market_phase


def analyze_amd_phase(
    candles: pd.DataFrame,
    session: dict[str, object],
    liquidity_sweep: dict[str, object],
    choch: dict[str, object],
) -> dict[str, object]:
    """Classify Accumulation, Manipulation, or Distribution from current evidence."""
    session_name = str(session.get("name", ""))
    if session_name == "Asian Session":
        return _phase("Accumulation", "The Asian range is defining liquidity before expansion.")
    if liquidity_sweep.get("swept") and not choch.get("confirmed"):
        return _phase("Manipulation", "Liquidity has been taken, but direction has not confirmed through structure.")
    if liquidity_sweep.get("swept") and choch.get("confirmed"):
        return _phase("Distribution", "Manipulation is complete and price has confirmed directional delivery.")

    fallback = detect_market_phase(candles, session)
    name = str(fallback.get("current_phase", "Range"))
    mapped = "Accumulation" if name == "Range" else "Distribution" if name == "Trend" else name
    return _phase(mapped, str(fallback.get("expected_behavior", "The current AMD phase is still developing.")))


def _phase(name: str, explanation: str) -> dict[str, object]:
    return {
        "phase": name,
        "status": name.lower(),
        "explanation": explanation,
    }
