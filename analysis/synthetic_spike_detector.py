"""Family-aware abnormal-event detection; never predicts when a spike is due."""
from __future__ import annotations
import math
import pandas as pd

def detect_synthetic_spike(candles:pd.DataFrame,*,family="OTHER_DERIVED",atr=None,profile=None,expected_direction=None,tick_acceleration=None,cooldown_bars=3,search_window=100):
    base={"spike_detected":False,"direction":None,"magnitude_points":None,"magnitude_atr":None,"range_multiple":None,"origin_price":None,"extreme_price":None,"formed_at":None,"timestamp":None,"family_expected":False,"classification":"none","cooldown_recommended":False,"cooldown_active":False,"confidence":0.0,"evidence":[],"warnings":[]}
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if len(rows)<15:return {**base,"warnings":["Insufficient completed candles for spike detection."]}
    ranges=pd.to_numeric(rows.high)-pd.to_numeric(rows.low);reference=ranges.iloc[:-1].tail(100);baseline=float(atr or (profile or {}).get("atr") or reference.tail(14).mean() or 0);median=float(reference.median() or 0)
    candidates=[]
    for pos in range(max(0,len(rows)-int(search_window)),len(rows)):
        row=rows.iloc[pos];width=float(ranges.iloc[pos]);body=float(row.close-row.open);atr_mult=width/max(baseline,1e-12);range_mult=width/max(median,1e-12);body_ratio=abs(body)/max(width,1e-12);close_location=(float(row.close)-float(row.low))/max(width,1e-12)
        if atr_mult>=2.5 and range_mult>=2.5 and (body_ratio>=.45 or close_location>=.85 or close_location<=.15):candidates.append((pos,row,width,body,atr_mult,range_mult,body_ratio,close_location))
    if not candidates:return base
    pos,row,width,body,atr_mult,range_mult,body_ratio,close_location=candidates[-1];direction="up" if body>0 else "down";expected=expected_direction or {"BOOM":"up","CRASH":"down","JUMP":"both","DEX":"both"}.get(str(family).upper(),"none");family_expected=expected in {direction,"both"};follow=rows.iloc[pos+1:];follow_through=bool(len(follow) and ((follow.close.iloc[-1]>row.close) if direction=="up" else (follow.close.iloc[-1]<row.close)))
    classification="expected_family_spike" if family_expected else "abnormal_move";confidence=min(.99,.55+min(atr_mult,6)*.06+(body_ratio*.08)+(0.05 if follow_through else 0))
    formed=str(row.time) if "time" in row else None;evidence=[f"Range was {atr_mult:.2f} ATR.",f"Range was {range_mult:.2f} times its rolling median.",f"Close location was {close_location:.2f}."]
    if tick_acceleration is not None:evidence.append(f"Observed tick acceleration: {float(tick_acceleration):.2f}.")
    return {**base,"spike_detected":True,"direction":direction,"magnitude_points":width,"magnitude_atr":atr_mult,"range_multiple":range_mult,"origin_price":float(row.open),"extreme_price":float(row.high if direction=="up" else row.low),"formed_at":formed,"timestamp":formed,"family_expected":family_expected,"classification":classification,"cooldown_recommended":pos>=len(rows)-1-cooldown_bars,"cooldown_active":pos>=len(rows)-1-cooldown_bars,"confidence":confidence,"evidence":evidence}
