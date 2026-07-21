"""Macro Dashboard aggregation for TradeScor."""

from __future__ import annotations


def build_macro_dashboard(
    session: dict[str, object],
    top_down: dict[str, object],
    dxy_correlation: dict[str, object],
    economic_news: dict[str, object],
    market_phase: dict[str, object],
) -> dict[str, object]:
    """Package institutional macro context before setup evaluation."""
    return {
        "session": session,
        "top_down_bias": top_down,
        "overall_market_alignment": top_down.get("overall_alignment", "Neutral"),
        "dxy_correlation": dxy_correlation,
        "economic_news": economic_news,
        "market_phase": market_phase,
        "entry_allowed": bool(session.get("entry_allowed")) and not bool(economic_news.get("restriction_active")),
        "context_summary": _context_summary(
            top_down.get("overall_alignment", "Neutral"),
            dxy_correlation,
            economic_news,
            market_phase,
        ),
    }


def directional_bias_from_alignment(alignment: str) -> str:
    """Convert top-down alignment into LONG/SHORT/NEUTRAL."""
    if "Bullish" in alignment:
        return "LONG"
    if "Bearish" in alignment:
        return "SHORT"
    return "NEUTRAL"


def _context_summary(
    alignment: str,
    dxy_correlation: dict[str, object],
    economic_news: dict[str, object],
    market_phase: dict[str, object],
) -> str:
    pieces = [f"Overall alignment is {alignment}."]

    if dxy_correlation.get("enabled"):
        pieces.append(f"DXY correlation {str(dxy_correlation.get('correlation_status', 'Neutral')).lower()}.")

    if economic_news.get("restriction_active"):
        pieces.append("High-impact news restriction is active.")

    pieces.append(f"Market phase: {market_phase.get('current_phase', 'Waiting')}.")
    return " ".join(pieces)
