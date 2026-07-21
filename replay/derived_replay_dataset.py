from __future__ import annotations
import hashlib,json
import pandas as pd
from models.derived_replay_models import DerivedReplayDataset

SECONDS={"M1":60,"M5":300}

def normalize_replay_candles(candles,base_timeframe="M5"):
    rows=candles.copy() if isinstance(candles,pd.DataFrame) else pd.DataFrame(candles or [])
    required={"time","open","high","low","close"}
    if not required.issubset(rows.columns):raise ValueError("Replay candles require time, open, high, low, and close.")
    rows=rows[list(required)].copy();numeric=pd.to_numeric(rows.time,errors="coerce");rows["time"]=pd.to_datetime(numeric,unit="s",utc=True,errors="coerce") if numeric.notna().all() else pd.to_datetime(rows.time,utc=True,errors="coerce")
    for key in ("open","high","low","close"):rows[key]=pd.to_numeric(rows[key],errors="coerce")
    rows=rows.dropna().sort_values("time").drop_duplicates("time",keep="last").reset_index(drop=True)
    valid=(rows.high>=rows[["open","close","low"]].max(axis=1))&(rows.low<=rows[["open","close","high"]].min(axis=1))
    if not valid.all():raise ValueError("Replay dataset contains malformed OHLC candles.")
    rows["time"]=rows.time.map(lambda value:int(value.timestamp())).astype("int64");rows["complete"]=True
    return rows

def build_replay_dataset(*,provider_symbol,display_name,family,candles,base_timeframe="M5",metadata=None,data_source_id="deriv_public"):
    tf=base_timeframe.upper()
    if tf not in SECONDS:raise ValueError("Replay base timeframe must be M1 or M5.")
    rows=normalize_replay_candles(candles,tf);interval=SECONDS[tf];times=rows.time.tolist();missing=[]
    for left,right in zip(times,times[1:]):
        if right-left>interval:missing.append({"after":int(left),"before":int(right),"missing_count":int((right-left)//interval-1)})
    serial=rows[["time","open","high","low","close"]].to_json(orient="records",double_precision=15);checksum=hashlib.sha256(serial.encode()).hexdigest();quality="invalid" if rows.empty else "partial" if missing else "good";warnings=[f"{sum(x['missing_count'] for x in missing)} base candle interval(s) are missing."] if missing else []
    identity=hashlib.sha256(json.dumps([provider_symbol,tf,times[0] if times else None,times[-1] if times else None,checksum],separators=(",",":")).encode()).hexdigest()[:24]
    descriptor=DerivedReplayDataset("dataset-"+identity,"deriv",provider_symbol,display_name,family,tf,pd.Timestamp(times[0],unit="s",tz="UTC").isoformat() if times else None,pd.Timestamp(times[-1]+interval,unit="s",tz="UTC").isoformat() if times else None,len(rows),checksum,tuple(missing),quality,tuple(warnings),{"tick_size":(metadata or {}).get("tick_size"),"price_precision":(metadata or {}).get("price_precision"),"data_source_id":data_source_id,"download_timestamp":(metadata or {}).get("download_timestamp"),"execution_resolution":"high" if tf=="M1" else "reduced","ambiguity_policy":"mark_ambiguous"})
    return descriptor,rows

def acquire_deriv_dataset(provider,*,provider_symbol,display_name,family,start_time,end_time,base_timeframe="M1",batch_size=5000,cache_dir="data/replay_datasets"):
    """Download bounded public candles in backwards chronological batches."""
    from pathlib import Path
    tf=base_timeframe.upper();granularity=SECONDS[tf];start=int(pd.Timestamp(start_time).timestamp());cursor=int(pd.Timestamp(end_time).timestamp());raw=[]
    while cursor>start:
        response=provider.client.request({"ticks_history":provider_symbol,"end":cursor,"count":min(batch_size,max(1,(cursor-start)//granularity+1)),"style":"candles","granularity":granularity})
        batch=response.get("candles") or []
        if not batch:break
        raw.extend(batch);earliest=min(int(row.get("epoch",row.get("time",cursor))) for row in batch);cursor=earliest-1
    normalized=[{"time":row.get("epoch",row.get("time")),"open":row.get("open"),"high":row.get("high"),"low":row.get("low"),"close":row.get("close")} for row in raw if start<=int(row.get("epoch",row.get("time",0)))<int(pd.Timestamp(end_time).timestamp())]
    descriptor,rows=build_replay_dataset(provider_symbol=provider_symbol,display_name=display_name,family=family,candles=normalized,base_timeframe=tf,metadata={"download_timestamp":pd.Timestamp.now(tz="UTC").isoformat()})
    path=Path(cache_dir);path.mkdir(parents=True,exist_ok=True);rows.to_json(path/f"{descriptor.dataset_id}.json",orient="records");return descriptor,rows
