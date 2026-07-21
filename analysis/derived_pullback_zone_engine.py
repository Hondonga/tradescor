"""M15 pullback measurement and one-primary-zone selection."""
from __future__ import annotations
import pandas as pd

def detect_pullback(candles,direction,atr,config=None):
    cfg=config or {};rows=_completed(candles);base={"state":"NO_PULLBACK","direction":direction,"impulse_start":None,"impulse_end":None,"retracement_depth_points":None,"retracement_depth_atr":None,"retracement_percentage":None,"valid":False,"rejection_reasons":[]}
    if direction not in {"buy","sell"} or len(rows)<20 or not atr:return {**base,"rejection_reasons":["Direction, ATR, or completed M15 history is unavailable."]}
    look=rows.tail(40).reset_index(drop=True);close=float(look.close.iloc[-1])
    if direction=="buy":end_pos=int(look.high.idxmax());start_pos=int(look.low.iloc[:end_pos+1].idxmin());start=float(look.low.iloc[start_pos]);end=float(look.high.iloc[end_pos]);depth=max(0,end-close)
    else:end_pos=int(look.low.idxmin());start_pos=int(look.high.iloc[:end_pos+1].idxmax());start=float(look.high.iloc[start_pos]);end=float(look.low.iloc[end_pos]);depth=max(0,close-end)
    leg=abs(end-start);pct=depth/max(leg,1e-12);depth_atr=depth/max(float(atr),1e-12);min_atr=float(cfg.get("minimum_pullback_atr",.25));max_atr=float(cfg.get("maximum_pullback_atr",1.5));min_pct=float(cfg.get("minimum_pullback_percentage",.18));max_pct=float(cfg.get("maximum_pullback_percentage",.78));reasons=[]
    if end_pos>=len(look)-2:state="NO_PULLBACK";reasons.append("The impulse has not begun a measurable pullback.")
    elif depth_atr<min_atr or pct<min_pct:state="TOO_SHALLOW";reasons.append("Retracement is too shallow.")
    elif depth_atr>max_atr or pct>max_pct:state="STRUCTURE_INVALIDATED" if pct>=1 else "TOO_DEEP";reasons.append("Retracement exceeds the configured structural depth.")
    else:state="VALID_PULLBACK"
    return {**base,"state":state,"impulse_start":start,"impulse_end":end,"retracement_depth_points":depth,"retracement_depth_atr":depth_atr,"retracement_percentage":pct,"valid":state=="VALID_PULLBACK","rejection_reasons":reasons,"impulse_start_index":start_pos,"impulse_end_index":end_pos}

def select_m15_pullback_zone(candles,direction,pullback,atr,current_price=None,config=None):
    rows=_completed(candles).tail(40).reset_index(drop=True);cfg=config or {};base={"low":None,"high":None,"type":"","direction":direction,"formed_at":None,"source_timeframe":"M15","freshness":0.0,"touch_count":0,"mitigation_depth":None,"displacement_strength":None,"structure_effect":"","distance_points":None,"distance_atr":None,"quality":0.0,"valid":False,"rejection_reasons":[]}
    if not pullback.get("valid") or len(rows)<10:return {**base,"rejection_reasons":["A valid M15 pullback is required."]}
    end=min(int(pullback.get("impulse_end_index",len(rows)-1)),len(rows)-1);opposing=[]
    for i in range(max(0,end-8),end+1):
        row=rows.iloc[i];is_opposing=float(row.close)<float(row.open) if direction=="buy" else float(row.close)>float(row.open)
        if is_opposing:opposing.append(i)
    origin=opposing[-1] if opposing else max(0,end-1);row=rows.iloc[origin];body_low=min(float(row.open),float(row.close));body_high=max(float(row.open),float(row.close));low=float(row.low if direction=="buy" else body_low);high=float(body_high if direction=="buy" else row.high)
    after=rows.iloc[origin+1:];touches=int(((after.low<=high)&(after.high>=low)).sum());mitigation=max(0,min(1,((high-float(after.low.min()))/(high-low)) if direction=="buy" and len(after) else ((float(after.high.max())-low)/(high-low)) if len(after) else 0));departure=(float(after.high.max())-high if direction=="buy" else low-float(after.low.min())) if len(after) else 0;displacement=departure/max(float(atr or 0),1e-12);freshness=max(0,1-touches*.2-mitigation*.25);quality=min(1,.35+freshness*.3+min(displacement,2)*.18);reasons=[]
    if touches>int(cfg.get("maximum_zone_touches",2)):reasons.append("Zone has excessive prior touches.")
    if displacement<.5:reasons.append("Departure lacked measurable displacement.")
    if quality<float(cfg.get("minimum_zone_quality",.65)):reasons.append("Zone quality is below requirement.")
    distance=0 if current_price is not None and low<=current_price<=high else min(abs(float(current_price)-low),abs(float(current_price)-high)) if current_price is not None else None
    return {**base,"low":low,"high":high,"type":"demand" if direction=="buy" else "supply","formed_at":_time(row),"freshness":freshness,"touch_count":touches,"mitigation_depth":mitigation,"displacement_strength":displacement,"structure_effect":"impulse_origin","distance_points":distance,"distance_atr":distance/atr if distance is not None and atr else None,"quality":quality,"valid":not reasons,"rejection_reasons":reasons}

def _completed(candles):
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    return rows
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
