from __future__ import annotations

from datetime import timedelta

import pandas as pd

from analysis.top_down_engine import analyze_top_down_market, completed_candles


def _candles(timeframe: str, direction: str, count: int = 80, start: float = 100.0) -> pd.DataFrame:
    frequency = {"D1": "1D", "H4": "4h", "H1": "1h", "M15": "15min", "M5": "5min"}[timeframe]
    times = pd.date_range("2025-01-01", periods=count, freq=frequency, tz="UTC")
    step = 0.25 if direction == "bullish" else -0.25 if direction == "bearish" else 0.0
    rows = []
    price = start
    for index, timestamp in enumerate(times):
        open_price = price
        close = price + step + ((index % 3) - 1) * 0.01
        rows.append({"time": timestamp, "open": open_price, "high": max(open_price, close) + 0.08, "low": min(open_price, close) - 0.08, "close": close})
        price = close
    return pd.DataFrame(rows)


def _boundary(context: dict[str, pd.DataFrame]) -> pd.Timestamp:
    return max(frame.iloc[-1]["time"] for frame in context.values()) + timedelta(days=2)


def test_bullish_htf_and_bearish_m15_is_pullback_not_primary_sell():
    context = {"D1": _candles("D1", "bullish"), "H4": _candles("H4", "bullish"), "H1": _candles("H1", "bullish"), "M15": _candles("M15", "bearish", start=120), "M5": _candles("M5", "bearish", start=120)}
    result = analyze_top_down_market(symbol="BTC/USD", candles_by_timeframe=context, analysis_timestamp=_boundary(context))

    assert result["regime"]["value"] == "bullish"
    assert result["alignment"]["state"] == "pullback"
    assert result["alignment"]["primary_direction"] == "buy"
    assert result["m15_setup"]["direction"] == "buy"


def test_bearish_htf_and_bullish_m15_is_pullback_not_primary_buy():
    context = {"D1": _candles("D1", "bearish", start=150), "H4": _candles("H4", "bearish", start=150), "H1": _candles("H1", "bearish", start=150), "M15": _candles("M15", "bullish"), "M5": _candles("M5", "bullish")}
    result = analyze_top_down_market(symbol="EUR/USD", candles_by_timeframe=context, analysis_timestamp=_boundary(context))

    assert result["regime"]["value"] == "bearish"
    assert result["alignment"]["state"] == "pullback"
    assert result["alignment"]["primary_direction"] == "sell"
    assert result["m15_setup"]["direction"] == "sell"


def test_conflicting_d1_h4_returns_no_primary_trade():
    context = {"D1": _candles("D1", "bullish"), "H4": _candles("H4", "bearish", start=150), "H1": _candles("H1", "bullish"), "M15": _candles("M15", "bullish"), "M5": _candles("M5", "bullish")}
    result = analyze_top_down_market(symbol="BTC/USD", candles_by_timeframe=context, analysis_timestamp=_boundary(context))

    assert result["regime"]["value"] == "transition"
    assert result["alignment"]["primary_direction"] == "neutral"
    assert result["primary_scenario"]["status"] == "no_trade_direction"


def test_completed_candles_excludes_live_and_future_candles():
    candles = _candles("H1", "bullish", count=10)
    boundary = candles.iloc[7]["time"] + timedelta(minutes=30)
    sliced = completed_candles(candles, "H1", boundary)

    assert sliced.iloc[-1]["time"] == candles.iloc[6]["time"]
    assert all(sliced["time"] < boundary)


def test_countertrend_alternative_is_disabled_by_default():
    context = {timeframe: _candles(timeframe, "bullish") for timeframe in ("D1", "H4", "H1", "M15", "M5")}
    result = analyze_top_down_market(symbol="BTC/USD", candles_by_timeframe=context, analysis_timestamp=_boundary(context))

    assert result["alternative_scenario"]["enabled"] is False
    assert "Countertrend" in result["alternative_scenario"]["label"]

