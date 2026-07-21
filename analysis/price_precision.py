"""Display precision rules shared with the TradeScor frontend."""

from __future__ import annotations


JPY_PAIRS = {"USD/JPY", "GBP/JPY"}


def display_precision(
    symbol: str,
    asset_type: str,
    current_price: float | None = None,
) -> int:
    """Return the decimal precision used for chart and level display."""
    normalized = str(symbol or "").strip().upper()
    normalized_asset = str(asset_type or "").strip().lower()

    if normalized in JPY_PAIRS or normalized.endswith("/JPY"):
        return 3
    if normalized_asset == "index":
        return 2
    if normalized_asset == "crypto":
        if current_price is not None and 0 < abs(float(current_price)) < 1:
            return 6
        return 2
    if _is_forex_pair(normalized):
        return 5
    if current_price is not None and abs(float(current_price)) >= 100:
        return 2
    return 5


def _is_forex_pair(symbol: str) -> bool:
    parts = symbol.split("/")
    return len(parts) == 2 and all(len(part) == 3 and part.isalpha() for part in parts)
