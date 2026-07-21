"""UTC tick-to-OHLC aggregation with history joining and diagnostics."""
from __future__ import annotations
import math
from collections import deque

class LiveCandleAggregator:
    def __init__(self,provider_symbol,timeframe,granularity,history=None,on_completed=None):
        self.provider_symbol=provider_symbol;self.timeframe=timeframe;self.granularity=int(granularity);self.on_completed=on_completed
        self.candles={int(row["time"]):{**row,"time":int(row["time"]),"complete":bool(row.get("complete",True)),"symbol":provider_symbol,"timeframe":timeframe} for row in (history or [])}
        self.current_time=max(self.candles,default=None);self.last_tick_epoch=None;self.recent=deque(maxlen=512);self.recent_set=set();self.completed_emitted=set();self.missing_intervals=[]
        self.diagnostics={"duplicate_ticks":0,"out_of_order_ticks":0,"stale_symbol_ticks":0,"resync_count":0,"completed_candles_emitted":0,"analysis_triggers":0}

    def ingest(self,tick):
        symbol=tick.get("symbol");epoch=tick.get("epoch");quote=tick.get("quote");subscription_id=str(tick.get("subscription_id") or "")
        if symbol!=self.provider_symbol:self.diagnostics["stale_symbol_ticks"]+=1;return []
        try:epoch=int(epoch);quote=float(quote)
        except (TypeError,ValueError):return []
        if not math.isfinite(quote):return []
        identity=(subscription_id,epoch,quote)
        if identity in self.recent_set:self.diagnostics["duplicate_ticks"]+=1;return []
        if self.last_tick_epoch is not None and epoch<=self.last_tick_epoch:self.diagnostics["out_of_order_ticks"]+=1;return []
        if len(self.recent)==self.recent.maxlen:self.recent_set.discard(self.recent[0])
        self.recent.append(identity);self.recent_set.add(identity);self.last_tick_epoch=epoch
        bucket=(epoch//self.granularity)*self.granularity;events=[]
        if self.current_time is not None and bucket<self.current_time:self.diagnostics["out_of_order_ticks"]+=1;return []
        if self.current_time is not None and bucket>self.current_time:
            prior=self.candles[self.current_time]
            if not prior.get("complete"):
                prior["complete"]=True
                if self.current_time not in self.completed_emitted:
                    self.completed_emitted.add(self.current_time);self.diagnostics["completed_candles_emitted"]+=1;events.append(("candle_closed",dict(prior)))
                    if self.on_completed:self.on_completed(dict(prior));self.diagnostics["analysis_triggers"]+=1
            expected=self.current_time+self.granularity
            if bucket>expected:self.missing_intervals.extend(range(expected,bucket,self.granularity));events.append(("resync_required",{"missing_intervals":list(range(expected,bucket,self.granularity))}))
        candle=self.candles.get(bucket)
        if candle is None:candle={"time":bucket,"open":quote,"high":quote,"low":quote,"close":quote,"complete":False,"symbol":self.provider_symbol,"timeframe":self.timeframe};self.candles[bucket]=candle
        else:
            candle["high"]=max(float(candle["high"]),quote);candle["low"]=min(float(candle["low"]),quote);candle["close"]=quote;candle["complete"]=False
        self.current_time=bucket;events.append(("candle_update",dict(candle)));return events

    def merge_history(self,rows):
        for row in rows:
            time=int(row["time"]);existing=self.candles.get(time)
            if existing and time==self.current_time and not existing.get("complete"):continue
            self.candles[time]={**row,"time":time,"complete":bool(row.get("complete",True)),"symbol":self.provider_symbol,"timeframe":self.timeframe}
        self.diagnostics["resync_count"]+=1;self.missing_intervals=[];return [self.candles[key] for key in sorted(self.candles)]

    @property
    def current(self):return self.candles.get(self.current_time) if self.current_time is not None else None
