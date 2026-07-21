"""One primary M15 post-spike area and a narrower M5 execution area."""
from __future__ import annotations
import pandas as pd
def build_post_spike_zone(candles,direction,spike,structure,atr,current_price=None,config=None,timeframe="M15"):
    base={"low":None,"high":None,"direction":direction,"type":"","formed_at":None,"formed_after_spike":False,"valid_for_spike_id":spike.get("spike_id") if spike else None,"source_timeframe":timeframe,"freshness":0.0,"touch_count":0,"mitigation_depth":None,"distance_points":None,"distance_atr":None,"quality":0.0,"valid":False,"rejection_reasons":[]}
    if not spike or not structure.get("formed_after_spike") or direction not in {"buy","sell"}:return {**base,"rejection_reasons":["Fresh post-spike directional structure is required."]}
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if "time" in rows:rows=rows[rows.time>pd.Timestamp(spike["completed_at"])]
    if len(rows)<3:return {**base,"rejection_reasons":["Insufficient post-spike candles for a zone."]}
    width=max(float(atr or 0)*float((config or {}).get("zone_width_atr",.2)),1e-12);anchor=(structure.get("last_swing_low") or {}).get("price") if direction=="buy" else (structure.get("last_swing_high") or {}).get("price");anchor=float(anchor if anchor is not None else rows.low.tail(5).min() if direction=="buy" else rows.high.tail(5).max());low=anchor if direction=="buy" else anchor-width;high=anchor+width if direction=="buy" else anchor;touches=int(((rows.low<=high)&(rows.high>=low)).sum());fresh=max(0,1-touches*.15);quality=min(1,.55+fresh*.25+min(len(rows),10)*.02);distance=0 if current_price is not None and low<=current_price<=high else min(abs(current_price-low),abs(current_price-high)) if current_price is not None else None;valid=quality>=float((config or {}).get("minimum_zone_quality",.6))
    return {**base,"low":low,"high":high,"type":"post_spike_demand" if direction=="buy" else "post_spike_supply","formed_at":_time(rows.iloc[-1]),"formed_after_spike":True,"freshness":fresh,"touch_count":touches,"mitigation_depth":None,"distance_points":distance,"distance_atr":distance/atr if distance is not None and atr else None,"quality":quality,"valid":valid,"rejection_reasons":[] if valid else ["Post-spike zone quality is insufficient."]}
def narrow_post_spike_execution_zone(zone,atr):
    if not zone or not zone.get("valid"):return None
    midpoint=(zone["low"]+zone["high"])/2;width=min((zone["high"]-zone["low"])*.5,float(atr or 0)*.1);return {**zone,"low":midpoint-width/2,"high":midpoint+width/2,"type":"m5_post_spike_execution","source_timeframe":"M5","valid":width>0}
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
