import pandas as pd

from backtesting.top_down_pipeline import run_top_down_execution_backtest


def _frame(frequency: str, count: int = 80) -> pd.DataFrame:
    times = pd.date_range("2025-01-01", periods=count, freq=frequency, tz="UTC")
    prices = [100 + index * 0.1 for index in range(count)]
    return pd.DataFrame({"time": times, "open": prices, "high": [price + 0.1 for price in prices], "low": [price - 0.1 for price in prices], "close": [price + 0.05 for price in prices]})


def test_top_down_backtest_requires_complete_hierarchy():
    result = run_top_down_execution_backtest({"M5": _frame("5min")}, symbol="EUR/USD")

    assert result["metadata"]["valid"] is False
    assert set(result["metadata"]["missing_timeframes"]) == {"D1", "H4", "H1", "M15"}
    assert result["trades"] == []


def test_top_down_backtest_reports_m5_execution_and_no_lookahead():
    context = {"D1": _frame("1D"), "H4": _frame("4h"), "H1": _frame("1h"), "M15": _frame("15min"), "M5": _frame("5min", 100)}
    result = run_top_down_execution_backtest(context, symbol="BTC/USD", asset_type="crypto", spread=0.5, slippage=0.1, fee_per_trade=0.05)

    metadata = result["metadata"]
    assert metadata["valid"] is True
    assert metadata["timeframe_hierarchy"] == ["D1", "H4", "H1", "M15", "M5"]
    assert metadata["execution_timeframe"] == "M5"
    assert metadata["look_ahead"] is False
    assert metadata["same_candle_policy"] == "stop_first_conservative"
    assert "walk_forward" in metadata

