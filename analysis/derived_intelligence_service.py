"""Cached top-down intelligence orchestration and completed-M5 refreshes."""
from __future__ import annotations
import threading
import pandas as pd
from analysis.derived_engine import analyze_derived_index

class DerivedIntelligenceService:
    def __init__(self,provider):self.provider=provider;self._lock=threading.RLock();self._frames={};self._results={}
    def analyze(self,symbol,display_name=None,timeframe="M5",force=False):
        with self._lock:
            frames=self._frames.setdefault(symbol,{})
            for tf in ("D1","H4","H1","M15","M5"):
                if force or tf not in frames:frames[tf]=self.provider.fetch_candles(symbol,tf,180 if tf=="D1" else 300)
            result=analyze_derived_index(symbol=symbol,metadata={"provider_symbol":symbol,"display_name":display_name or symbol},candles_by_timeframe={key:value.copy() for key,value in frames.items()},analysis_time=pd.Timestamp.now(tz="UTC"))["intelligence"]
            self._results[symbol]=result;return result
    def completed_m5(self,symbol,timeframe,candle):
        if timeframe!="M5":return
        with self._lock:
            frames=self._frames.get(symbol)
            if not frames:return
            row={key:candle.get(key) for key in ("time","open","high","low","close")};row.update({"complete":True,"provider":"deriv","symbol":symbol,"timeframe":"M5"});incoming=pd.DataFrame([row]);incoming["time"]=pd.to_datetime(incoming["time"],unit="s",utc=True)
            current=frames.get("M5",pd.DataFrame());merged=pd.concat([current,incoming],ignore_index=True);merged=merged.drop_duplicates(subset=["time"],keep="last").sort_values("time").tail(500);frames["M5"]=merged
            self._results[symbol]=analyze_derived_index(symbol=symbol,metadata={"provider_symbol":symbol,"display_name":symbol},candles_by_timeframe={key:value.copy() for key,value in frames.items()},analysis_time=pd.Timestamp.now(tz="UTC"))["intelligence"]

_service=None
def get_derived_intelligence_service(provider):
    global _service
    if _service is None or _service.provider is not provider:_service=DerivedIntelligenceService(provider)
    return _service
