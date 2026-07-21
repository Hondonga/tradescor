"""Official Deriv public market-data provider and UTC tick aggregation."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Callable

import pandas as pd

from providers.base_provider import MarketDataProvider, normalized_candle
from providers.deriv_ws_client import DerivAPIError, DerivWebSocketClient
from providers.runtime_health import PipelineTrace, runtime_health
from analysis.derived_family_classifier import classify_derived_family

GRANULARITIES={"M1":60,"M5":300,"M15":900,"M30":1800,"H1":3600,"H2":7200,"H4":14400,"D1":86400}


def normalize_active_symbol(row: dict) -> dict[str, object]:
    symbol=str(row.get("underlying_symbol") or row.get("symbol") or "")
    name=str(row.get("underlying_symbol_name") or row.get("display_name") or row.get("display_name") or symbol)
    if not symbol:return None
    classification=classify_derived_family({**row,"provider_symbol":symbol,"display_name":name});supported=bool(classification.get("enabled_strategies") or classification.get("supports_full_smc") or classification.get("supports_post_event_smc"))
    return {"provider_symbol":symbol,"display_name":name,"family":classification["family"],"family_display":_family_display(classification["family"],name),"variant":classification["variant"],
            "pip_size":_float_or_none(row.get("pip") if row.get("pip") is not None else row.get("pip_size")),"market_open":bool(row.get("exchange_is_open",True)),
            "suspended":bool(row.get("is_trading_suspended",False)),"underlying_symbol_type":row.get("underlying_symbol_type"),
            "market":row.get("market"),"submarket":row.get("submarket"),"subgroup":row.get("subgroup"),"smc_adapter":next(iter(classification.get("enabled_strategies") or []),None),"analysis_supported":supported,"analysis_support_status":"SUPPORTED" if supported else "UNSUPPORTED_MODEL","classification":classification,"raw":row}

def normalize_deriv_candles(raw_candles:list[dict])->list[dict[str,object]]:
    """Return the exact Lightweight Charts OHLC contract or raise."""
    import math
    normalized={}
    if not isinstance(raw_candles,list):raise DerivAPIError("malformed_history","Deriv candle response was not a list.")
    for raw in raw_candles:
        try:timestamp=int(raw["epoch"]);open_=float(raw["open"]);high=float(raw["high"]);low=float(raw["low"]);close=float(raw["close"])
        except (KeyError,TypeError,ValueError):continue
        if timestamp>10_000_000_000:timestamp//=1000
        if not all(math.isfinite(value) for value in (open_,high,low,close)):continue
        if high<max(open_,close) or low>min(open_,close) or high<low:continue
        normalized[timestamp]={"time":timestamp,"open":open_,"high":high,"low":low,"close":close}
    result=[normalized[key] for key in sorted(normalized)]
    if not result:raise DerivAPIError("empty_history","Deriv returned zero valid candles.")
    return result


def normalize_history(payload: dict, symbol: str, granularity: int) -> tuple[pd.DataFrame,list[int]]:
    records=[];raw_epochs=[]
    for row in payload.get("candles") or []:
        try:
            epoch=int(row.get("epoch"));raw_epochs.append(epoch)
            candle=normalized_candle(epoch=epoch,open_=float(row.get("open")),high=float(row.get("high")),low=float(row.get("low")),close=float(row.get("close")),complete=epoch+granularity<=int(time.time()),provider="deriv",symbol=symbol,timeframe=next((key for key,value in GRANULARITIES.items() if value==granularity),""))
        except (TypeError,ValueError):continue
        if candle["high"] < max(candle["open"],candle["close"]) or candle["low"] > min(candle["open"],candle["close"]) or candle["high"] < candle["low"]:continue
        records.append(candle)
    records=sorted({row["time"]:row for row in records}.values(),key=lambda row:row["time"])
    missing=[]
    for left,right in zip(records,records[1:]):
        if right["time"]-left["time"]>granularity:
            missing.extend(range(left["time"]+granularity,right["time"],granularity))
    frame=pd.DataFrame(records)
    if frame.empty: frame=pd.DataFrame(columns=["time","open","high","low","close","complete","provider","symbol","timeframe"])
    else: frame["time"]=pd.to_datetime(frame["time"],unit="s",utc=True)
    duplicate_count=max(0,len(raw_epochs)-len(set(raw_epochs)));out_of_order_count=sum(1 for left,right in zip(raw_epochs,raw_epochs[1:]) if right<left)
    frame.attrs["time_metadata"]={"provider":"Deriv","source_timezone":"UTC","normalized_timezone":"UTC","missing_intervals":missing,"duplicate_count":duplicate_count,"out_of_order_count":out_of_order_count,"warnings":[f"{len(missing)} candle interval(s) are missing."] if missing else []}
    return frame,missing


class TickCandleAggregator:
    def __init__(self,symbol: str,timeframe: str,callback: Callable[[dict],None]):
        self.symbol=symbol; self.granularity=GRANULARITIES[timeframe]; self.callback=callback; self.current=None; self.last_epoch=None

    def ingest(self,epoch: int,quote: float) -> list[dict]:
        epoch=int(epoch); quote=float(quote)
        if self.last_epoch is not None and epoch<=self.last_epoch:return []
        self.last_epoch=epoch; bucket=(epoch//self.granularity)*self.granularity; emitted=[]
        if self.current and self.current["time"]!=bucket:
            self.current["complete"]=True; emitted.append(dict(self.current)); self.callback(dict(self.current)); self.current=None
        if self.current is None:self.current=normalized_candle(epoch=bucket,open_=quote,high=quote,low=quote,close=quote,complete=False,provider="deriv",symbol=self.symbol,timeframe=next((key for key,value in GRANULARITIES.items() if value==self.granularity),""))
        else:self.current.update(high=max(self.current["high"],quote),low=min(self.current["low"],quote),close=quote)
        emitted.append(dict(self.current)); self.callback(dict(self.current)); return emitted


class DerivProvider(MarketDataProvider):
    name="deriv"; SYMBOL_TTL=1800; HISTORY_TTL=60
    def __init__(self,client: DerivWebSocketClient | None=None):
        self.client=client or DerivWebSocketClient(); self._symbol_cache=(0.0,[]); self._history_cache={};self._known_good={}; self._lock=threading.RLock(); self._streams={}; self._callbacks=defaultdict(list)

    def list_symbols(self):
        cached_at,rows=self._symbol_cache
        if rows and time.time()-cached_at<self.SYMBOL_TTL:return [dict(row) for row in rows]
        runtime_health.connection("LOADING_SYMBOLS");payload=self.client.request({"active_symbols":"brief","product_type":"basic"}); raw=payload.get("active_symbols") or []
        if not raw:
            if rows:return [dict(row) for row in rows]
            raise DerivAPIError("SYMBOL_UNAVAILABLE","Deriv returned no active symbols.")
        rows=[normalized for row in raw if _is_derived(row) for normalized in [normalize_active_symbol(row)] if normalized]
        self._symbol_cache=(time.time(),rows);runtime_health.connection("CONNECTED"); return [dict(row) for row in rows]

    def resolve_symbol(self,symbol):
        row=next((row for row in self.list_symbols() if row["provider_symbol"]==symbol),None)
        if not row:raise DerivAPIError("SYMBOL_UNAVAILABLE",f"{symbol} is not present in Deriv active_symbols.")
        if not row["analysis_supported"]:raise DerivAPIError("UNSUPPORTED_MODEL",f"No supported SMC adapter exists for {symbol}.")
        return row

    def fetch_candles(self,symbol: str,timeframe: str,count: int):
        tf=str(timeframe).upper(); granularity=GRANULARITIES.get(tf)
        if granularity is None:raise ValueError(f"Unsupported Deriv timeframe '{timeframe}'.")
        count=max(1,min(int(count),5000)); key=(symbol,tf,count); cached=self._history_cache.get(key);trace=PipelineTrace(symbol,tf)
        trace.start("ACTIVE_SYMBOL_RESOLUTION")
        try:self.resolve_symbol(symbol);trace.pass_("ACTIVE_SYMBOL_RESOLUTION",1)
        except DerivAPIError as error:trace.fail("ACTIVE_SYMBOL_RESOLUTION",error.code,error);runtime_health.add_trace(trace);raise
        if cached and time.time()-cached[0]<self.HISTORY_TTL:trace.start("CACHE_READ").pass_("CACHE_READ",len(cached[1]));trace.start("ANALYSIS_READY").pass_("ANALYSIS_READY",len(cached[1])).ready();runtime_health.add_trace(trace);return cached[1].copy()
        started=time.perf_counter();runtime_health.connection("LOADING_HISTORY");trace.start("PROVIDER_CONNECTION").pass_("PROVIDER_CONNECTION");trace.start("HISTORY_REQUEST")
        try:
            payload=self.client.request({"ticks_history":symbol,"end":"latest","count":count,"style":"candles","granularity":granularity});trace.pass_("HISTORY_REQUEST");trace.start("HISTORY_RESPONSE").pass_("HISTORY_RESPONSE",len(payload.get("candles") or []));trace.start("CANDLE_NORMALIZATION")
            frame,_=normalize_history(payload,symbol,granularity);trace.pass_("CANDLE_NORMALIZATION",len(frame));trace.start("COMPLETED_CANDLE_FILTER");completed=frame[frame.complete.astype(bool)].copy() if "complete" in frame else frame.copy();trace.pass_("COMPLETED_CANDLE_FILTER",len(completed))
            if completed.empty:raise DerivAPIError("empty_history",f"Historical data unavailable for {symbol}.")
            trace.start("CACHE_WRITE");self._history_cache[key]=(time.time(),completed.copy());self._known_good[key]=(time.time(),completed.copy());trace.pass_("CACHE_WRITE",len(completed));trace.start("ANALYSIS_READY").pass_("ANALYSIS_READY",len(completed)).ready();runtime_health.connection("READY");return completed
        except Exception as error:
            code=error.code if isinstance(error,DerivAPIError) else "PROVIDER_ERROR";trace.fail("HISTORY_RESPONSE",code,error);known=self._known_good.get(key)
            if known:
                stale=known[1].copy();stale.attrs["stale_data"]=True;stale.attrs["last_successful_update"]=known[0];runtime_health.connection("STALE");return stale
            runtime_health.connection("PROVIDER_ERROR");raise
        finally:runtime_health.observe_history((time.perf_counter()-started)*1000);runtime_health.add_trace(trace)

    def fetch_chart_candles(self,symbol:str,timeframe:str,count:int)->dict[str,object]:
        tf=str(timeframe).upper();granularity=GRANULARITIES.get(tf)
        if granularity is None:raise ValueError("Unsupported Deriv timeframe")
        request={"ticks_history":symbol,"end":"latest","count":max(1,min(int(count),5000)),"style":"candles","granularity":int(granularity)}
        print("DERIV_HISTORY_SENT",{"symbol":symbol,"timeframe":tf,"granularity":granularity})
        payload=self.client.request(request);print("DERIV_HISTORY_RECEIVED",{"keys":sorted(payload),"msg_type":payload.get("msg_type")})
        raw=payload.get("candles")
        if not isinstance(raw,list):raise DerivAPIError("malformed_history","Deriv response did not contain a candle array.",{"response_keys":sorted(payload)})
        candles=normalize_deriv_candles(raw);print("DERIV_HISTORY_NORMALIZED",{"received":len(raw),"valid":len(candles)})
        return {"request":request,"granularity":granularity,"received_count":len(raw),"valid_count":len(candles),"candles":candles,"response_keys":sorted(payload)}

    def subscribe_candles(self,symbol: str,timeframe: str,callback: Callable[[dict],None]):
        key=(symbol,timeframe.upper()); self._callbacks[key].append(callback)
        with self._lock:
            if key not in self._streams:
                aggregator=TickCandleAggregator(symbol,key[1],lambda candle:self._emit(key,candle))
                tick_callback=lambda payload:self._tick(aggregator,payload)
                local_id=self.client.subscribe(symbol,tick_callback); self._streams[key]={"id":local_id,"aggregator":aggregator,"tick_callback":tick_callback,"users":0}
            self._streams[key]["users"]+=1
        return f"{symbol}:{key[1]}:{id(callback)}"

    def subscribe_ticks(self,symbol: str,callback: Callable):return self.client.subscribe(symbol,callback)
    def unsubscribe(self,subscription_id: str):
        parts=subscription_id.split(":")
        if len(parts)<2:return self.client.unsubscribe(subscription_id)
        key=(parts[0],parts[1]); row=self._streams.get(key)
        if not row:return
        row["users"]-=1
        if row["users"]<=0:self.client.unsubscribe(row["id"],row.get("tick_callback"));self._streams.pop(key,None);self._callbacks.pop(key,None)
    def get_server_time(self):
        result=self.client.request({"time":1});return int(result.get("time") or self.client.server_time())
    def close(self):self.client.close()
    def _tick(self,aggregator,payload):
        tick=payload.get("tick") or {}
        try:aggregator.ingest(int(tick["epoch"]),float(tick["quote"]))
        except (KeyError,TypeError,ValueError):return
    def _emit(self,key,candle):
        for callback in list(self._callbacks.get(key,[])):
            try:callback(candle)
            except Exception:pass


def _is_derived(row):
    text=" ".join(str(row.get(key) or "") for key in ("market","submarket","subgroup","underlying_symbol_type")).lower()
    return any(word in text for word in ("synthetic","derived","volatility","boom","crash","step","range break","jump","drift"))
def _float_or_none(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None

def _family_display(family,name):
    if "Bear Market" in name:return "Bear Market"
    if "Bull Market" in name:return "Bull Market"
    return {"VOLATILITY":"Volatility","JUMP":"Jump","BOOM":"Boom","CRASH":"Crash","STEP":"Step","STEP_CLASSIC":"Step","STEP_MULTI":"Step","STEP_SKEW_UP":"Step","STEP_SKEW_DOWN":"Step","HYBRID":"Basket","OTHER_DERIVED":"Other Derived"}.get(family,family.replace("_"," ").title())
