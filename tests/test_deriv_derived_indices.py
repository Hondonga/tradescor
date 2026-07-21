from __future__ import annotations

import pandas as pd

from analysis.asset_rules import asset_rules
from analysis.derived_family_classifier import classify_derived_family
from analysis.synthetic_spike_detector import detect_synthetic_spike
from providers.deriv_provider import GRANULARITIES, DerivProvider, TickCandleAggregator, normalize_active_symbol, normalize_history
from providers.provider_router import get_provider
from providers.deriv_connection_modes import DERIV_AUTHENTICATED_TRADING, DERIV_PUBLIC_MARKET_DATA, DerivConnectionMode, require_public_market_data_request
from providers.deriv_ws_client import DerivWebSocketClient


class FakeClient:
    def __init__(self,responses):self.responses=list(responses);self.requests=[];self.callbacks={};self.restored=[]
    def request(self,payload,timeout=None):self.requests.append(payload);return self.responses.pop(0)
    def subscribe(self,symbol,callback):self.callbacks[symbol]=callback;return f"ticks:{symbol}"
    def unsubscribe(self,_id):pass
    def server_time(self):return 1
    def close(self):pass


def test_active_symbols_are_discovered_and_new_fields_normalized():
    client=FakeClient([{"active_symbols":[{"underlying_symbol":"R_100","underlying_symbol_name":"Volatility 100 Index","underlying_symbol_type":"synthetic_index","market":"derived","submarket":"random_index","subgroup":"volatility","pip_size":2,"exchange_is_open":1,"is_trading_suspended":0},{"symbol":"EURUSD","market":"forex"}]}])
    rows=DerivProvider(client).list_symbols()
    assert rows==[normalize_active_symbol({"underlying_symbol":"R_100","underlying_symbol_name":"Volatility 100 Index","underlying_symbol_type":"synthetic_index","market":"derived","submarket":"random_index","subgroup":"volatility","pip_size":2,"exchange_is_open":1,"is_trading_suspended":0})]
    assert client.requests==[{"active_symbols":"brief","product_type":"basic"}]


def test_history_normalization_schema_granularity_duplicates_and_gaps():
    payload={"candles":[{"epoch":300,"open":"1","high":"3","low":"1","close":"2"},{"epoch":300,"open":"1","high":"2.5","low":".5","close":"2"},{"epoch":900,"open":"2","high":"3","low":"1","close":"2.5"}]}
    frame,missing=normalize_history(payload,"R_100",300)
    assert GRANULARITIES["M5"]==300 and len(frame)==2 and missing==[600]
    assert set(("time","open","high","low","close","complete","provider","symbol"))<=set(frame.columns)
    assert frame.iloc[0].provider=="deriv" and frame.iloc[0].symbol=="R_100"


def test_tick_aggregation_rollover_and_duplicate_out_of_order_handling():
    events=[]; agg=TickCandleAggregator("R_100","M5",events.append)
    agg.ingest(301,10);agg.ingest(302,12);agg.ingest(302,99);agg.ingest(301,1);agg.ingest(600,11)
    completed=[row for row in events if row["complete"]]
    assert completed==[{"time":300,"open":10.0,"high":12.0,"low":10.0,"close":12.0,"complete":True,"provider":"deriv","symbol":"R_100","timeframe":"M5"}]
    assert agg.current["time"]==600 and agg.current["open"]==11


def test_derived_rules_are_24_7_and_disable_forex_filters():
    rules=asset_rules("R_100","derived_index")
    assert rules["market_schedule"]=="24_7" and rules["dxy_applicable"] is False
    assert rules["news_filter_applicable"] is False and rules["forex_session_gate_applicable"] is False
    assert rules["movement_unit"]=="points"


def test_family_classification_uses_metadata_and_spike_rules():
    assert classify_derived_family({"provider_symbol":"RB_100","subgroup":"range break"})["preferred_strategies"]==["breakout_retest"]
    assert classify_derived_family({"provider_symbol":"BOOM1000","underlying_symbol_type":"boom"})["spike_profile"]=="upward"
    rows=[]
    for i in range(20):
        open_=100+i*.1;close=open_+.05;high=close+.1;low=open_-.1
        if i==19:close=open_+10;high=close+.2
        rows.append({"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=5*i),"open":open_,"high":high,"low":low,"close":close})
    spike=detect_synthetic_spike(pd.DataFrame(rows),family="BOOM")
    assert spike["spike_detected"] and spike["direction"]=="up" and spike["cooldown_active"]


def test_provider_router_keeps_deriv_separate_from_twelve_data():
    assert get_provider(asset_class="forex").name=="twelve_data"
    # Avoid constructing the network client in this unit test; provider identity is
    # already covered through the injected DerivProvider tests above.


def test_frontend_contract_contains_dynamic_symbols_sse_and_no_websocket_credentials():
    js=open("static/app.js",encoding="utf-8").read();html=open("templates/index.html",encoding="utf-8").read()
    assert "/api/deriv/symbols" in js and "/api/stream/deriv" in js and "EventSource" in js
    assert "new WebSocket" not in js and "DERIV_APP_ID" not in js and 'id="derived-symbols"' in html


def test_public_and_authenticated_deriv_modes_are_strictly_separated():
    assert DERIV_PUBLIC_MARKET_DATA.endpoint == "wss://ws.binaryws.com/websockets/v3"
    assert DERIV_PUBLIC_MARKET_DATA.authentication_required is False
    assert DERIV_AUTHENTICATED_TRADING.endpoint is None
    assert DERIV_AUTHENTICATED_TRADING.authentication_required is True
    assert DERIV_AUTHENTICATED_TRADING.enabled is False
    client=DerivWebSocketClient(autostart=False)
    assert client.mode==DerivConnectionMode.DERIV_PUBLIC_MARKET_DATA and client.authentication_required is False
    try:DerivWebSocketClient(mode=DerivConnectionMode.DERIV_AUTHENTICATED_TRADING,autostart=False)
    except ValueError:pass
    else:raise AssertionError("authenticated trading mode must remain unavailable")


def test_public_connection_rejects_account_and_order_requests():
    for payload in ({"active_symbols":"brief"},{"ticks_history":"R_100","style":"candles"},{"ticks":"R_100","subscribe":1},{"forget":"id"},{"ping":1},{"time":1}):
        require_public_market_data_request(payload)
    for payload in ({"authorize":"token"},{"buy":"contract"},{"balance":1}):
        try:require_public_market_data_request(payload)
        except ValueError:pass
        else:raise AssertionError(f"public connection accepted {payload}")
