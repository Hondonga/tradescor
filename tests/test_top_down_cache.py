from unittest.mock import patch

import pandas as pd

from providers import multi_timeframe


def _frame() -> pd.DataFrame:
    times = pd.date_range("2025-01-01", periods=40, freq="5min", tz="UTC")
    return pd.DataFrame({"time": times, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05})


def test_selected_timeframe_is_reused_and_each_context_frame_fetches_once():
    calls = []

    def fake_get_candles(*, symbol, timeframe, bars):
        calls.append(timeframe)
        return _frame()

    multi_timeframe._CONTEXT_CACHE.clear()
    with patch.object(multi_timeframe, "get_candles", side_effect=fake_get_candles):
        result = multi_timeframe.get_multi_timeframe_context("BTC/USD", "M15", 300, depth="balanced", selected_candles=_frame())

    assert set(result["context"]) == {"M5", "M15", "H1", "H4", "D1"}
    assert "15min" not in calls
    assert len(calls) == 4
    assert len(set(calls)) == 4


def test_second_top_down_request_reuses_context_cache():
    calls = []

    def fake_get_candles(*, symbol, timeframe, bars):
        calls.append(timeframe)
        return _frame()

    multi_timeframe._CONTEXT_CACHE.clear()
    with patch.object(multi_timeframe, "get_candles", side_effect=fake_get_candles):
        multi_timeframe.get_multi_timeframe_context("BTC/USD", "M15", 300, depth="balanced", selected_candles=_frame())
        multi_timeframe.get_multi_timeframe_context("BTC/USD", "M15", 300, depth="balanced", selected_candles=_frame())

    assert len(calls) == 4


def test_focused_deriv_context_uses_one_m1_source_for_execution_frames():
    calls=[]
    m1=pd.DataFrame({"time":pd.date_range("2026-01-01",periods=5000,freq="1min",tz="UTC"),"open":range(5000),"high":[x+1 for x in range(5000)],"low":[x-1 for x in range(5000)],"close":[x+.5 for x in range(5000)]})
    class Provider:
        def fetch_candles(self,symbol,timeframe,bars):
            calls.append((timeframe,bars));return m1 if timeframe=="M1" else _frame()
    multi_timeframe._CONTEXT_CACHE.clear()
    with patch.object(multi_timeframe,"get_provider",return_value=Provider()):
        result=multi_timeframe.get_multi_timeframe_context("R_75","M5",300,provider="deriv",asset_class="derived_index")
    assert calls[0]==("M1",5000)
    assert not ({"M5","M15","H1"}&{timeframe for timeframe,_ in calls})
    assert all(result["cache"][timeframe]=="derived_from_m1" for timeframe in ("M5","M15","H1"))
    assert len(result["context"]["M5"])>len(result["context"]["M15"])>len(result["context"]["H1"])
