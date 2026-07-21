"""Persisted raw-candle audit for the Forex Twelve Data boundary."""
from __future__ import annotations
import json,os,time
from pathlib import Path
import pandas as pd
import requests
from dotenv import load_dotenv
from providers.twelvedata import normalize_time_series_payload

URL="https://api.twelvedata.com/time_series"
INTERVALS={"M1":("1min",pd.Timedelta(minutes=1)),"M5":("5min",pd.Timedelta(minutes=5)),"M15":("15min",pd.Timedelta(minutes=15)),"H1":("1h",pd.Timedelta(hours=1))}
DEPTH={"M1":1200,"M5":500,"M15":500,"H1":400}

def audit_symbol(symbol="GBP/USD",root="data/forex_audits",session=requests):
    run_id=f"{symbol.replace('/','_').lower()}-{pd.Timestamp.now(tz='UTC').floor('s').strftime('%Y%m%dT%H%M%SZ')}";folder=Path(root)/run_id;folder.mkdir(parents=True,exist_ok=False);reports={}
    for timeframe in INTERVALS:reports[timeframe]=audit_timeframe(symbol,timeframe,folder,session=session)
    result={"audit_id":run_id,"provider":"twelve_data","symbol":symbol,"analysis_allowed":all(row["validation_passed"] for row in reports.values()),"timeframes":reports};(folder/"audit.json").write_text(json.dumps(result,indent=2,default=str)+"\n");return result

def audit_timeframe(symbol,timeframe,folder,session=requests,now=None):
    load_dotenv();key=os.getenv("TWELVE_DATA_API_KEY","").strip()
    if not key:raise RuntimeError("Missing TWELVE_DATA_API_KEY.")
    interval,step=INTERVALS[timeframe];requested=DEPTH[timeframe];requested_at=time.time();response=session.get(URL,params={"symbol":symbol,"interval":interval,"outputsize":requested,"timezone":"UTC","apikey":key},timeout=20)
    if getattr(response,"status_code",200)>=400:raise RuntimeError(f"Twelve Data HTTP {response.status_code} while auditing {symbol} {timeframe}; request credentials were omitted.")
    payload=response.json()
    if payload.get("status")=="error":raise RuntimeError(f"Twelve Data API error: {payload.get('message','unknown error')}")
    safe={**payload,"request":{"provider":"twelve_data","symbol":symbol,"interval":interval,"outputsize":requested,"timezone":"UTC","requested_at":pd.Timestamp(requested_at,unit='s',tz='UTC').isoformat()}};path=Path(folder)/f"{timeframe.lower()}-raw.json";path.write_text(json.dumps(safe,indent=2,default=str)+"\n")
    values=payload.get("values") or [];raw=pd.DataFrame(values);raw_times=pd.to_datetime(raw.get("datetime",pd.Series(dtype=str)),errors="coerce",utc=True);duplicates=int(raw_times.duplicated().sum());candles,metadata=normalize_time_series_payload(payload,interval=interval,requested_timezone="UTC");current=pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC");current=current.tz_localize("UTC") if current.tzinfo is None else current.tz_convert("UTC");complete=candles.loc[candles.time+step<=current].copy();ohlc=(complete.high>=complete[["open","close","low"]].max(axis=1))&(complete.low<=complete[["open","close","high"]].min(axis=1));invalid=int((~ohlc).sum());valid=complete.loc[ohlc];missing=_missing(valid.time,step);precision=max((_precision(value) for column in ("open","high","low","close") for value in raw.get(column,[])),default=0);ascending=bool(valid.time.is_monotonic_increasing);meta=payload.get("meta") or {};provider_symbol=meta.get("symbol") or symbol
    return {"provider":"twelve_data","symbol":provider_symbol,"requested_symbol":symbol,"timeframe":timeframe,"requested_interval":interval,"requested_history_depth":requested,"raw_rows":len(values),"valid_rows":len(valid),"duplicates":duplicates,"missing_intervals":missing,"invalid_ohlc":invalid,"first_time":valid.iloc[0].time.isoformat() if len(valid) else None,"last_completed_time":valid.iloc[-1].time.isoformat() if len(valid) else None,"incomplete_final_candle":len(complete)<len(candles),"ascending":ascending,"timestamp_timezone":metadata["normalized_timezone"],"source_timezone":metadata["source_timezone"],"decimal_precision":precision,"cache_source":"live_provider","cache_age_seconds":round(time.time()-requested_at,3),"raw_response_path":str(path),"validation_passed":bool(provider_symbol==symbol and len(valid)>=20 and not duplicates and not invalid and ascending)}

def _missing(times,step):
    rows=[];values=list(pd.to_datetime(times,utc=True))
    for left,right in zip(values[:-1],values[1:]):
        expected=left+step
        if right>expected and not (left.weekday()==4 and right.weekday() in {6,0}):rows.append({"after":left.isoformat(),"before":right.isoformat(),"missing_intervals":max(0,int((right-left)/step)-1)})
    return rows
def _precision(value):
    text=str(value);return len(text.rstrip("0").split(".",1)[1]) if "." in text else 0
