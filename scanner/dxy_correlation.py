"""DXY correlation analysis for USD-related markets."""

from __future__ import annotations

import pandas as pd


USD_BASE_SYMBOLS = {"USD/JPY", "USD/CHF", "USD/CAD"}
USD_QUOTE_SYMBOLS = {"EUR/USD", "GBP/USD", "AUD/USD", "NZD/USD", "XAU/USD", "BTC/USD", "ETH/USD"}


def analyze_dxy_correlation(
    symbol: str,
    directional_bias: str,
    dxy_candles: pd.DataFrame | None,
) -> dict[str, object]:
    """Compare DXY direction with the current symbol bias."""
    normalized_symbol = symbol.upper().strip()

    if not _is_usd_related(normalized_symbol):
        return {
            "enabled": False,
            "dxy_trend": "Disabled",
            "correlation_status": "Not applicable",
            "confidence_impact": "No impact",
            "score_impact": 0,
            "message": "DXY correlation is only shown for USD-related symbols.",
        }

    if dxy_candles is None or dxy_candles.empty or len(dxy_candles) < 30:
        return {
            "enabled": True,
            "dxy_trend": "Unavailable",
            "correlation_status": "Waiting",
            "confidence_impact": "No impact",
            "score_impact": 0,
            "message": "DXY unavailable — not included in analysis.",
        }

    dxy_trend = _trend(dxy_candles)
    expected_symbol_bias = _expected_symbol_bias(normalized_symbol, dxy_trend)
    correlation_status = _correlation_status(directional_bias, expected_symbol_bias)
    score_impact = _score_impact(correlation_status)

    return {
        "enabled": True,
        "dxy_trend": dxy_trend,
        "correlation_status": correlation_status,
        "confidence_impact": _confidence_text(correlation_status),
        "score_impact": score_impact,
        "expected_symbol_bias": expected_symbol_bias,
        "message": _message(normalized_symbol, dxy_trend, expected_symbol_bias, correlation_status),
    }


def symbol_needs_dxy(symbol: str) -> bool:
    """Return True when DXY correlation can help the selected market."""
    return _is_usd_related(symbol.upper().strip())


def _is_usd_related(symbol: str) -> bool:
    if symbol in USD_BASE_SYMBOLS or symbol in USD_QUOTE_SYMBOLS:
        return True

    parts = symbol.split("/")
    return "USD" in parts


def _trend(candles: pd.DataFrame) -> str:
    clean = candles.copy().sort_values("time").reset_index(drop=True)
    close = clean["close"].astype(float)
    ema_fast = close.ewm(span=20, adjust=False).mean()
    ema_slow = close.ewm(span=50, adjust=False).mean()
    current = float(close.iloc[-1])

    if current > float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1]):
        return "Bullish"
    if current < float(ema_fast.iloc[-1]) < float(ema_slow.iloc[-1]):
        return "Bearish"
    return "Neutral"


def _expected_symbol_bias(symbol: str, dxy_trend: str) -> str:
    if dxy_trend == "Neutral":
        return "NEUTRAL"

    parts = symbol.split("/")
    if len(parts) == 2 and parts[0] == "USD":
        return "LONG" if dxy_trend == "Bullish" else "SHORT"
    if len(parts) == 2 and parts[1] == "USD":
        return "SHORT" if dxy_trend == "Bullish" else "LONG"
    return "NEUTRAL"


def _correlation_status(directional_bias: str, expected_symbol_bias: str) -> str:
    if directional_bias not in {"LONG", "SHORT"} or expected_symbol_bias == "NEUTRAL":
        return "Neutral"
    if directional_bias == expected_symbol_bias:
        return "Confirms"
    return "Conflicts"


def _score_impact(status: str) -> int:
    if status == "Confirms":
        return 5
    if status == "Conflicts":
        return -10
    return 0


def _confidence_text(status: str) -> str:
    if status == "Confirms":
        return "Adds confidence"
    if status == "Conflicts":
        return "Reduces confidence"
    return "No impact"


def _message(
    symbol: str,
    dxy_trend: str,
    expected_symbol_bias: str,
    status: str,
) -> str:
    if dxy_trend == "Neutral":
        return "DXY is neutral, so correlation is not adding a directional filter."

    return f"DXY {dxy_trend} expects {expected_symbol_bias} bias on {symbol}; current macro status: {status}."
