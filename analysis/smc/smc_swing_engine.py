import hashlib,json
import pandas as pd
from analysis.smc.smc_models import SMCSwing

def confirmed_swings(candles,*,atr=None,tick_size=.01,left_strength=2,right_strength=2,scope="internal",minimum_prominence_atr=.15,minimum_prominence_ticks=2):
    rows=_completed(candles);values=[]
    if len(rows)<left_strength+right_strength+1:return values
    atr=float(atr or _atr(rows) or tick_size);tick=max(float(tick_size),1e-12);highs=rows.high.astype(float).to_numpy();lows=rows.low.astype(float).to_numpy();times=rows.time.tolist() if "time" in rows else list(range(len(rows)))
    for index in range(left_strength,len(rows)-right_strength):
        left=slice(index-left_strength,index);right=slice(index+1,index+right_strength+1)
        for kind,source,opposing in (("high",highs,lows),("low",lows,highs)):
            price=float(source[index]);others=[*source[left],*source[right]]
            if not (price>max(others) if kind=="high" else price<min(others)):continue
            baseline=max(float(opposing[left].min()),float(opposing[right].min())) if kind=="high" else min(float(opposing[left].max()),float(opposing[right].max()));prominence=abs(price-baseline)
            if prominence/atr<minimum_prominence_atr or prominence/tick<minimum_prominence_ticks:continue
            candle_time=_time_value(times[index]);confirmation=_time_value(times[index+right_strength]);identity=hashlib.sha256(json.dumps([kind,scope,candle_time,price,left_strength,right_strength],default=str).encode()).hexdigest()[:20]
            values.append(SMCSwing("swing-"+identity,kind,scope,price,candle_time,confirmation,left_strength,right_strength,prominence/atr,int(round(prominence/tick))).as_dict())
    return values
def _completed(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame();return rows[rows.complete.astype(bool)].reset_index(drop=True) if "complete" in rows else rows.reset_index(drop=True)
def _atr(rows,period=14):
    if len(rows)<2:return None
    previous=rows.close.shift(1);tr=pd.concat([(rows.high-rows.low).abs(),(rows.high-previous).abs(),(rows.low-previous).abs()],axis=1).max(axis=1);return float(tr.tail(period).mean())
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else int(value) if isinstance(value,(int,float)) else str(value)
def _time_value(value):return value.isoformat() if hasattr(value,"isoformat") else int(value) if isinstance(value,(int,float)) else str(value)
