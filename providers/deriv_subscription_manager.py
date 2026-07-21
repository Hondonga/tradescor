"""Shared backend ownership for symbol/timeframe Deriv streams."""
from __future__ import annotations
import threading,time,uuid
from analysis.live_candle_aggregator import LiveCandleAggregator
from providers.deriv_provider import GRANULARITIES

class DerivSubscriptionManager:
    def __init__(self,provider,analysis_callback=None):
        self.provider=provider;self.analysis_callback=analysis_callback;self._lock=threading.RLock();self._streams={};self._consumers={};self.last_error=None;self.generation=0
        if hasattr(provider.client,"add_status_listener"):provider.client.add_status_listener(self._connection_status)

    def acquire(self,provider_symbol,timeframe,callback,display_name=""):
        key=(provider_symbol,timeframe.upper());granularity=GRANULARITIES.get(key[1])
        if granularity is None:raise ValueError("Unsupported Deriv timeframe")
        with self._lock:
            row=self._streams.get(key)
            if row is None:
                history=self.provider.fetch_chart_candles(provider_symbol,key[1],20)["candles"]
                aggregator=LiveCandleAggregator(provider_symbol,key[1],granularity,history=history,on_completed=lambda candle:self._completed(key,candle))
                tick_callback=lambda payload:self._on_tick(key,payload);subscription_id=self.provider.subscribe_ticks(provider_symbol,tick_callback);self.generation+=1
                row={"subscription_id":subscription_id,"provider_symbol":provider_symbol,"display_name":display_name or provider_symbol,"timeframe":key[1],"granularity":granularity,"consumer_count":0,"last_tick_epoch":None,"connected":True,"aggregator":aggregator,"tick_callback":tick_callback,"callbacks":{},"stream_generation":self.generation,"created_at":time.time()};self._streams[key]=row
            consumer_id=str(uuid.uuid4());row["callbacks"][consumer_id]=callback;row["consumer_count"]+=1;self._consumers[consumer_id]=key
        callback(self._payload(row,"stream_status",None,status="connected"));return consumer_id,row["stream_generation"]

    def release(self,consumer_id):
        with self._lock:
            key=self._consumers.pop(consumer_id,None);row=self._streams.get(key) if key else None
            if not row:return
            row["callbacks"].pop(consumer_id,None);row["consumer_count"]=max(0,row["consumer_count"]-1)
            if row["consumer_count"]:return
            self.provider.client.unsubscribe(row["subscription_id"],row["tick_callback"]);self._streams.pop(key,None)

    def _on_tick(self,key,payload):
        row=self._streams.get(key)
        if not row:return
        if payload.get("msg_type")!="tick" or not isinstance(payload.get("tick"),dict):return
        raw=payload["tick"];subscription_id=str((payload.get("subscription") or {}).get("id") or "")
        tick={"symbol":raw.get("symbol"),"epoch":raw.get("epoch"),"quote":raw.get("quote"),"subscription_id":subscription_id}
        events=row["aggregator"].ingest(tick);row["last_tick_epoch"]=row["aggregator"].last_tick_epoch;row["connected"]=True
        for event_type,candle in events:
            if event_type=="resync_required":self._resync(key,candle.get("missing_intervals",[]));continue
            self._broadcast(row,self._payload(row,event_type,candle))

    def _resync(self,key,missing):
        row=self._streams.get(key)
        if not row:return
        try:
            history=self.provider.fetch_chart_candles(row["provider_symbol"],row["timeframe"],max(20,len(missing)+5))["candles"];merged=row["aggregator"].merge_history(history);self._broadcast(row,self._payload(row,"resync",None,candles=merged))
        except Exception as error:self.last_error=str(error);self._broadcast(row,self._payload(row,"stream_status",None,status="reconnecting",message="Historical resynchronization failed."))

    def _completed(self,key,candle):
        if self.analysis_callback and key[1]=="M5":self.analysis_callback(key[0],key[1],candle)
    def _connection_status(self,status):
        for key,row in list(self._streams.items()):
            row["connected"]=status=="connected";self._broadcast(row,self._payload(row,"stream_status",None,status=status,message="Live stream reconnecting." if status!="connected" else "Live stream connected."))
            if status=="connected":self._resync(key,[])
    def _broadcast(self,row,payload):
        for callback in list(row["callbacks"].values()):
            try:callback(payload)
            except Exception:pass
    def _payload(self,row,event_type,candle,**extra):return {"ok":True,"provider":"deriv","provider_symbol":row["provider_symbol"],"display_name":row["display_name"],"timeframe":row["timeframe"],"event_type":event_type,"stream_generation":row["stream_generation"],"candle":candle,**extra}
    def health(self):
        subscriptions=[]
        for row in list(self._streams.values()):
            diag=row["aggregator"].diagnostics;subscriptions.append({"provider_symbol":row["provider_symbol"],"timeframe":row["timeframe"],"subscription_id":row["subscription_id"],"last_tick_epoch":row["last_tick_epoch"],"last_bucket_time":row["aggregator"].current_time,"consumer_count":row["consumer_count"],"connected":row["connected"],**diag})
        return {"ok":self.last_error is None,"connected":any(row["connected"] for row in self._streams.values()),"active_subscription_count":len(self._streams),"subscriptions":subscriptions,"last_error":self.last_error}
