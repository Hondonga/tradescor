from datetime import timedelta

import pandas as pd

from app import _apply_fixed_m5_execution_pipeline


def _trend(timeframe: str, step: float = 0.1) -> pd.DataFrame:
    frequency = {"D1": "1D", "H4": "4h", "H1": "1h", "M15": "15min", "M5": "5min"}[timeframe]
    times = pd.date_range("2025-01-01", periods=80, freq=frequency, tz="UTC")
    rows, price = [], 100.0
    for timestamp in times:
        close = price + step
        rows.append({"time": timestamp, "open": price, "high": close + 0.05, "low": price - 0.05, "close": close})
        price = close
    return pd.DataFrame(rows)


def test_display_m15_cannot_preserve_legacy_actionable_prices():
    context = {timeframe: _trend(timeframe) for timeframe in ("D1", "H4", "H1", "M15", "M5")}
    boundary = max(frame.iloc[-1]["time"] for frame in context.values()) + timedelta(days=2)
    analysis = {
        "analysis_timestamp_epoch": int(boundary.timestamp()),
        "shared_analysis": {"current": {"spread": 0}},
        "levels": {"entry_zone": {"low": 111, "high": 112}, "stop_loss": 110, "tp1": 115},
        "trade_metrics": {"entry_price": 111, "stop_loss": 110, "tp1": {"price": 115}},
    }
    strategy = {"bias": "Buy", "levels_mode": "final", "trade_decision": "ACCEPT"}

    top_down, execution = _apply_fixed_m5_execution_pipeline(
        analysis=analysis,
        strategy_result=strategy,
        context_candles=context,
        analysis_timestamp=boundary,
        query={"display_symbol": "BTC/USD", "asset_type": "crypto", "timeframe": "M15"},
        session_context={"entry_allowed": True},
        market_filters={},
    )

    assert execution["execution_timeframe"] == "M5"
    assert analysis["display_analysis"]["display_timeframe"] == "M15"
    assert analysis["display_analysis"]["execution_timeframe"] == "M5"
    assert analysis["trade_score"] <= 70 or execution.get("confirmed_signal")
    if analysis["possible_setups"]:
        assert analysis["possible_setups"][0]["setup_zone"] == top_down["m15_setup"]["zone"]
    if execution["state"] != "entry_valid":
        assert analysis["trade_metrics"]["entry_price"] is None
        assert analysis["levels"]["entry_zone"] is None
        assert analysis["trade_decision"] == "PENDING"


def test_frontend_direction_contract_is_backend_top_down_direction():
    context = {timeframe: _trend(timeframe) for timeframe in ("D1", "H4", "H1", "M15", "M5")}
    boundary = max(frame.iloc[-1]["time"] for frame in context.values()) + timedelta(days=2)
    analysis = {"analysis_timestamp_epoch": int(boundary.timestamp()), "shared_analysis": {"current": {}}}
    strategy = {}

    top_down, execution = _apply_fixed_m5_execution_pipeline(
        analysis=analysis,
        strategy_result=strategy,
        context_candles=context,
        analysis_timestamp=boundary,
        query={"display_symbol": "BTC/USD", "asset_type": "crypto", "timeframe": "H1"},
        session_context={"entry_allowed": True},
        market_filters={},
    )

    expected = "Buy" if top_down["alignment"]["primary_direction"] == "buy" else "Sell" if top_down["alignment"]["primary_direction"] == "sell" else "Neutral"
    assert analysis["trade_direction"] == expected
