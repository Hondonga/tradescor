"""Finnhub-backed DXY confirmation contract.

The first pass is intentionally conservative: it returns an unavailable state
unless live DXY candles are explicitly wired in later.
"""

from __future__ import annotations


def unavailable_dxy_confirmation() -> dict[str, object]:
    """Return the standard DXY filter shape without faking data."""
    return {
        "available": False,
        "source": "Finnhub",
        "dxy_bias": "unavailable",
        "supports_trade": None,
        "conflicts_with_trade": None,
        "message": "DXY unavailable — not included in analysis.",
    }
