from __future__ import annotations
from unittest.mock import patch
import pytest
from app import app
from providers.deriv_provider import normalize_active_symbol,normalize_deriv_candles
from providers.deriv_ws_client import DerivAPIError

def test_actual_provider_symbol_and_defensive_fields_are_preserved():
    row=normalize_active_symbol({"symbol":"R_100","display_name":"Volatility 100 Index","market":"synthetic_index","pip":.01})
    assert row["provider_symbol"]=="R_100" and row["display_name"]=="Volatility 100 Index" and row["pip_size"]==.01 and row["raw"]["symbol"]=="R_100"
    assert normalize_active_symbol({"display_name":"Missing code"}) is None

def test_lightweight_chart_normalizer_sorts_deduplicates_and_rejects_invalid():
    rows=normalize_deriv_candles([{"epoch":"2000000000000","open":"2","high":"3","low":"1","close":"2.5"},{"epoch":"1000","open":"1","high":"2","low":".5","close":"1.5"},{"epoch":"1000","open":"1.1","high":"2","low":"1","close":"1.5"},{"epoch":"900","open":"1","high":".5","low":"0","close":"2"},{"epoch":"800","open":"nan","high":"2","low":"0","close":"1"}])
    assert rows==[{"time":1000,"open":1.1,"high":2.0,"low":1.0,"close":1.5},{"time":2000000000,"open":2.0,"high":3.0,"low":1.0,"close":2.5}]
    with pytest.raises(DerivAPIError):normalize_deriv_candles([])

def test_candle_route_success_and_provider_failure_are_explicit():
    class Provider:
        def fetch_chart_candles(self,symbol,timeframe,count):
            assert symbol=="R_100" and timeframe=="M5";return {"granularity":300,"received_count":2,"valid_count":1,"candles":[{"time":1000,"open":1.,"high":2.,"low":.5,"close":1.5}]}
    with patch("app.get_provider",return_value=Provider()):
        response=app.test_client().get("/api/deriv/candles?symbol=R_100&timeframe=M5&count=500");payload=response.get_json();assert response.status_code==200 and payload["ok"] and payload["valid_count"]==1
    class Failed:
        def fetch_chart_candles(self,*args):raise DerivAPIError("timeout","Deriv timed out")
    with patch("app.get_provider",return_value=Failed()):
        response=app.test_client().get("/api/deriv/candles?symbol=R_100&timeframe=M5&count=500");assert response.status_code==502 and response.get_json()["ok"] is False

def test_unsupported_timeframe_is_400():
    response=app.test_client().get("/api/deriv/candles?symbol=R_100&timeframe=W1&count=500")
    assert response.status_code==400 and "Unsupported Deriv timeframe" in response.get_json()["error_message"]

def test_frontend_is_history_first_and_race_safe():
    js=open("static/app.js",encoding="utf-8").read();loader=js.split("async function loadDerivChart",1)[1].split("async function analyzeMarket",1)[0]
    assert "const requestId=++currentChartRequestId" in loader
    assert "payload.candles.length===0" in loader
    assert "requestId!==currentChartRequestId" in loader
    assert "candleSeries.setData(candles)" in loader
    assert loader.index("candleSeries.setData(candles)")<loader.index("startDerivStream()")
    assert "DERIV_CHART_SET_DATA_SUCCESS" in loader and "DERIV_LIVE_STREAM_START" in loader
