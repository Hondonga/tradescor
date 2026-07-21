"""Completed-candle readiness checks shared by live and replay SMC analysis."""
from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

# M5 is the authoritative execution timeframe. M1 is optional enrichment and
# must not deadlock an otherwise complete M5/M15/H1/H4 analysis.
REQUIRED_COUNTS={"M1":0,"M5":60,"M15":40,"H1":20,"H4":6,"D1":0}

def evaluate_data_readiness(candles_by_timeframe,analysis_time=None,required_counts=None,source="deriv_public"):
    required={**REQUIRED_COUNTS,**(required_counts or {})};cutoff=pd.Timestamp(analysis_time or datetime.now(timezone.utc))
    if cutoff.tzinfo is None:cutoff=cutoff.tz_localize("UTC")
    else:cutoff=cutoff.tz_convert("UTC")
    timeframes={};missing=[];duplicates=[];warnings=[];stale_frames=[];last_successful=[]
    for timeframe in ("M1","M5","M15","H1","H4","D1"):
        frame=(candles_by_timeframe or {}).get(timeframe);attrs=getattr(frame,"attrs",{}).copy();frame=frame.copy() if isinstance(frame,pd.DataFrame) else pd.DataFrame(frame or []);required_count=int(required.get(timeframe,0));available=0;last=None;passed=required_count==0
        if attrs.get("stale_data"):stale_frames.append(timeframe);last_successful.append(attrs.get("last_successful_update"))
        if not frame.empty and "time" in frame:
            times=pd.to_datetime(frame["time"],utc=True,errors="coerce");complete=frame.get("complete",pd.Series(True,index=frame.index)).fillna(False).astype(bool);future=times>cutoff
            valid=times.notna()&complete&~future;available=int(valid.sum());passed=available>=required_count;last=times[valid].max().isoformat() if available else None
            counts=times[valid].value_counts();duplicates.extend({"timeframe":timeframe,"time":str(value),"count":int(count)} for value,count in counts.items() if count>1)
            interval=_seconds(timeframe);ordered=sorted(int(value.timestamp()) for value in times[valid].drop_duplicates())
            for left,right in zip(ordered,ordered[1:]):
                if right-left>interval:missing.append({"timeframe":timeframe,"after":left,"before":right,"missing_count":int((right-left)//interval-1)})
            if future.any():warnings.append(f"{timeframe} excluded {int(future.sum())} future candle(s).")
            if (~complete).any():warnings.append(f"{timeframe} excluded {int((~complete).sum())} incomplete candle(s).")
        timeframes[timeframe]={"available":available,"required":required_count,"passed":passed,"last_completed_time":last}
    required_rows=[row for name,row in timeframes.items() if required.get(name,0)>0]
    sufficient=all(row["passed"] for row in required_rows) and not duplicates;state="stale" if sufficient and stale_frames else "ready" if sufficient else "insufficient"
    return {"state":state,"source":source,"as_of":cutoff.isoformat(),"timeframes":timeframes,"missing_intervals":missing,"duplicate_intervals":duplicates,"warnings":warnings,"stale_timeframes":stale_frames,"last_successful_update":max((x for x in last_successful if x is not None),default=None),"analysis_paused":state=="stale"}

def _seconds(timeframe):return {"M1":60,"M5":300,"M15":900,"H1":3600,"H4":14400,"D1":86400}[timeframe]
