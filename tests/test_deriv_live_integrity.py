from analysis.live_candle_aggregator import LiveCandleAggregator
from providers.deriv_subscription_manager import DerivSubscriptionManager
from providers.deriv_provider import GRANULARITIES
from providers.deriv_ws_client import DerivWebSocketClient

def tick(symbol,epoch,quote,subscription_id="s1"):return {"symbol":symbol,"epoch":epoch,"quote":quote,"subscription_id":subscription_id}

def test_m5_deterministic_aggregation_and_exactly_once_close():
    completed=[];a=LiveCandleAggregator("R_100","M5",300,on_completed=completed.append)
    events=[]
    for epoch,quote in ((36005,100),(36030,101.5),(36070,99.2),(36299,100.8),(36301,102)):events.extend(a.ingest(tick("R_100",epoch,quote)))
    closed=[c for kind,c in events if kind=="candle_closed"]
    assert closed==[{"time":36000,"open":100.,"high":101.5,"low":99.2,"close":100.8,"complete":True,"symbol":"R_100","timeframe":"M5"}]
    assert a.current=={"time":36300,"open":102.,"high":102.,"low":102.,"close":102.,"complete":False,"symbol":"R_100","timeframe":"M5"}
    assert completed==closed and a.diagnostics["analysis_triggers"]==1

def test_history_and_matching_live_bucket_merge_without_duplicate():
    history=[{"time":36000,"open":100,"high":101,"low":99,"close":100.5}];a=LiveCandleAggregator("R_100","M5",300,history=history)
    events=a.ingest(tick("R_100",36100,102));assert len(a.candles)==1 and a.current["open"]==100 and a.current["high"]==102 and events[-1][0]=="candle_update"

def test_duplicates_out_of_order_and_old_symbols_are_ignored():
    a=LiveCandleAggregator("R_100","M5",300);assert a.ingest(tick("OLD",100,5))==[];a.ingest(tick("R_100",100,5));assert a.ingest(tick("R_100",100,5))==[];assert a.ingest(tick("R_100",99,6))==[]
    assert a.diagnostics=={"duplicate_ticks":1,"out_of_order_ticks":1,"stale_symbol_ticks":1,"resync_count":0,"completed_candles_emitted":0,"analysis_triggers":0}

def test_all_timeframes_align_to_utc_boundaries():
    for timeframe in ("M1","M5","M15","M30","H1","H4"):
        granularity=GRANULARITIES[timeframe];a=LiveCandleAggregator("R_100",timeframe,granularity);a.ingest(tick("R_100",1234567,1));assert a.current["time"]==(1234567//granularity)*granularity

def test_large_legitimate_spikes_preserve_extremes():
    a=LiveCandleAggregator("BOOM1000","M5",300);a.ingest(tick("BOOM1000",301,100));a.ingest(tick("BOOM1000",302,1000000));a.ingest(tick("BOOM1000",303,-500000));assert a.current["high"]==1000000 and a.current["low"]==-500000

def test_gap_reports_missing_intervals_and_backfill_deduplicates():
    a=LiveCandleAggregator("R_100","M5",300);a.ingest(tick("R_100",301,1));events=a.ingest(tick("R_100",1201,2));assert [600,900] in [row[1]["missing_intervals"] for row in events if row[0]=="resync_required"]
    merged=a.merge_history([{"time":600,"open":1,"high":2,"low":1,"close":2},{"time":900,"open":2,"high":2,"low":1,"close":1}]);assert [row["time"] for row in merged]==[300,600,900,1200]

class Client:
    def __init__(self):self.released=[]
    def unsubscribe(self,subscription_id,callback):self.released.append(subscription_id)
    def add_status_listener(self,callback):self.status=callback
class Provider:
    def __init__(self):self.client=Client();self.subscriptions=0;self.callback=None
    def fetch_chart_candles(self,*args):return {"candles":[{"time":300,"open":1,"high":1,"low":1,"close":1}]}
    def subscribe_ticks(self,symbol,callback):self.subscriptions+=1;self.callback=callback;return "ticks:"+symbol

def test_manager_reuses_subscription_and_forgets_when_unused():
    provider=Provider();manager=DerivSubscriptionManager(provider);events=[];one,g1=manager.acquire("R_100","M5",events.append);two,g2=manager.acquire("R_100","M5",events.append)
    assert provider.subscriptions==1 and g1==g2 and manager.health()["subscriptions"][0]["consumer_count"]==2
    manager.release(one);assert not provider.client.released;manager.release(two);assert provider.client.released==["ticks:R_100"] and manager.health()["active_subscription_count"]==0

def test_full_analysis_trigger_only_on_m5_close():
    calls=[];provider=Provider();manager=DerivSubscriptionManager(provider,analysis_callback=lambda *args:calls.append(args));consumer,_=manager.acquire("R_100","M5",lambda event:None)
    for epoch in (301,302,303):provider.callback({"msg_type":"tick","tick":{"symbol":"R_100","epoch":epoch,"quote":2},"subscription":{"id":"p1"}})
    assert calls==[];provider.callback({"msg_type":"tick","tick":{"symbol":"R_100","epoch":601,"quote":3},"subscription":{"id":"p1"}});assert len(calls)==1
    manager.release(consumer)

def test_frontend_filters_symbol_timeframe_generation_and_uses_update():
    js=open("static/app.js",encoding="utf-8").read();stream=js.split("function startDerivStream",1)[1].split("function stopCurrentMarketStream",1)[0]
    assert "payload.provider_symbol===ui.symbol.value" in stream and "payload.timeframe===ui.timeframe.value" in stream and "payload.stream_generation===activeStreamGeneration" in stream
    assert "candleSeries.update(normalized)" in stream and "candleSeries.setData(candles)" in stream

def test_initial_connect_does_not_double_subscribe_pending_row():
    class Socket:
        def __init__(self):self.sent=[]
        def send(self,payload):self.sent.append(payload)
    client=DerivWebSocketClient(autostart=False);client._ws=Socket()
    client._subscriptions={"ticks:R_100":{"symbol":"R_100","callbacks":[],"provider_id":None}}
    client._restore_subscriptions();assert client._ws.sent==[]
    client._subscriptions["ticks:R_100"]["provider_id"]="provider-1"
    client._restore_subscriptions();assert len(client._ws.sent)==1 and client._subscriptions["ticks:R_100"]["provider_id"] is None
