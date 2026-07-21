"""Display-to-provider symbol mapping.

The UI can show friendly names while Twelve Data receives the symbol format it
expects. Keep this list small so the app only requests the selected market.
"""

from __future__ import annotations


def _normalize_symbol(symbol: str) -> str:
    """Normalize symbols for case-insensitive matching."""
    return " ".join(symbol.strip().upper().split())


SYMBOL_MAP = {
    "EUR/USD": {"api_symbol": "EUR/USD", "type": "forex"},
    "GBP/USD": {"api_symbol": "GBP/USD", "type": "forex"},
    "USD/JPY": {"api_symbol": "USD/JPY", "type": "forex"},
    "AUD/USD": {"api_symbol": "AUD/USD", "type": "forex"},
    "USD/CAD": {"api_symbol": "USD/CAD", "type": "forex"},
    "GBP/JPY": {"api_symbol": "GBP/JPY", "type": "forex"},
    "BTC/USD": {"api_symbol": "BTC/USD", "type": "crypto"},
    "ETH/USD": {"api_symbol": "ETH/USD", "type": "crypto"},
    "NASDAQ 100": {"api_symbol": "NDX", "type": "index"},
    "Dow Jones 30": {"api_symbol": "DJI", "type": "index"},
    "S&P 500": {"api_symbol": "SPX", "type": "index"},
    "Russell 2000": {"api_symbol": "RUT", "type": "index"},
}

_NORMALIZED_SYMBOL_MAP = {
    _normalize_symbol(display_symbol): {
        "display_symbol": display_symbol,
        "api_symbol": details["api_symbol"],
        "asset_type": details["type"],
    }
    for display_symbol, details in SYMBOL_MAP.items()
}


def _forex_aliases(api_symbol: str) -> list[str]:
    """Alternate spellings a caller might send for a slash-delimited forex
    pair (e.g. Twelve-Data-native or TradingView-style forms). These all
    normalize to the SAME canonical identity the slash form already
    resolves to -- they are not separate frontend symbols (Phase 4 §2)."""
    concatenated = api_symbol.replace("/", "")
    return [concatenated, api_symbol.replace("/", "-"), f"FX:{concatenated}", f"FX:{api_symbol}"]


_ALIAS_SYMBOL_MAP = {
    _normalize_symbol(alias): canonical
    for display_symbol, details in SYMBOL_MAP.items()
    if details["type"] == "forex"
    for canonical in [_NORMALIZED_SYMBOL_MAP[_normalize_symbol(display_symbol)]]
    for alias in _forex_aliases(details["api_symbol"])
}


def resolve_symbol(symbol: str | None) -> dict[str, str]:
    """Return display/API symbol details for the selected market."""
    cleaned = " ".join((symbol or "EUR/USD").strip().split()) or "EUR/USD"
    normalized = _normalize_symbol(cleaned)
    mapped = _NORMALIZED_SYMBOL_MAP.get(normalized) or _ALIAS_SYMBOL_MAP.get(normalized)

    if mapped:
        return mapped.copy()

    if "/" in cleaned and " " not in cleaned:
        direct_symbol = cleaned.upper()
        asset_type = "crypto" if direct_symbol.startswith(("BTC/", "ETH/")) else "forex"
        return {
            "display_symbol": direct_symbol,
            "api_symbol": direct_symbol,
            "asset_type": asset_type,
        }

    supported = ", ".join(SYMBOL_MAP)
    raise ValueError(f"Unsupported symbol '{cleaned}'. Use one of: {supported}")
