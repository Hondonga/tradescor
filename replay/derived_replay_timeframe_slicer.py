from __future__ import annotations
import pandas as pd

TIMEFRAMES={"M5":300,"M15":900,"M30":1800,"H1":3600,"H2":7200,"H4":14400,"D1":86400}

def aggregate_completed(base_candles,timeframe,replay_time,base_interval):
    size=TIMEFRAMES[timeframe];t=int(pd.Timestamp(replay_time).timestamp());rows=base_candles.copy();rows=rows[rows.time.astype("int64")+int(base_interval)<=t]
    if rows.empty:return pd.DataFrame(columns=["time","open","high","low","close","complete"])
    rows["bucket"]=(rows.time.astype("int64")//size)*size;group=rows.groupby("bucket",sort=True).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"));group=group[group.index+size<=t].reset_index().rename(columns={"bucket":"time"});group["time"]=pd.to_datetime(group.time,unit="s",utc=True);group["complete"]=True;return group

def slice_timeframes(base_candles,replay_time,base_timeframe="M5"):
    interval=60 if base_timeframe.upper()=="M1" else 300;frames={name:aggregate_completed(base_candles,name,replay_time,interval) for name in TIMEFRAMES}
    def last(name):return frames[name].iloc[-1].time.isoformat() if len(frames[name]) else None
    audit={"replay_time":pd.Timestamp(replay_time).isoformat(),"d1_last_complete":last("D1"),"h4_last_complete":last("H4"),"h1_last_complete":last("H1"),"m15_last_complete":last("M15"),"m5_last_complete":last("M5"),"incomplete_candles_excluded":True}
    return frames,audit

def available_after(record,replay_time):
    value=record.get("first_available_at") or record.get("confirmed_at") or record.get("formed_at")
    return bool(value and pd.Timestamp(value)<=pd.Timestamp(replay_time))
