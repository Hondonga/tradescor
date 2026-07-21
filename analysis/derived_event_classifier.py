"""Bidirectional completed-candle abnormal-event classification."""
import pandas as pd
def classify_derived_event(candles,profile,config=None,tick_acceleration=None):
    cfg=(config or {}).get("event",config or {});rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows;base={"qualified":False,"classification":"INSUFFICIENT_DATA","direction":None,"magnitude_points":None,"magnitude_atr":None,"range_multiple":None,"body_ratio":None,"tick_acceleration":tick_acceleration,"confidence":0.0,"origin_price":None,"extreme_price":None,"completed_at":None,"evidence":[],"rejection_reasons":[]}
    if len(rows)<20:return {**base,"rejection_reasons":["Completed-candle history is insufficient."]}
    atr=float(profile.get("atr") or 0);median=float(profile.get("median_range") or profile.get("median_candle_range") or 0);candidates=[]
    for i in range(max(0,len(rows)-12),len(rows)-1):
        row=rows.iloc[i];width=float(row.high-row.low);body=float(row.close-row.open);atr_mult=width/max(atr,1e-12);range_mult=width/max(median,1e-12);body_ratio=abs(body)/max(width,1e-12);follow=rows.iloc[i+1:min(len(rows),i+3)];follow_ok=bool(len(follow) and ((follow.close.iloc[-1]>row.close) if body>0 else (follow.close.iloc[-1]<row.close)));confidence=min(.98,.4+min(atr_mult/8,.25)+min(range_mult/10,.2)+body_ratio*.15+(.1 if follow_ok else 0));qualified=atr_mult>=float(cfg.get("minimum_magnitude_atr",2.25)) and range_mult>=float(cfg.get("minimum_range_multiple",2.5)) and confidence>=float(cfg.get("minimum_confidence",.65)) and body_ratio>=.35
        if qualified:candidates.append((i,row,width,body,atr_mult,range_mult,body_ratio,confidence))
    if not candidates:return {**base,"classification":"ORDINARY_EXPANSION","rejection_reasons":["No completed abnormal move passes event thresholds."]}
    i,row,width,body,atr_mult,range_mult,body_ratio,confidence=candidates[-1];direction="up" if body>0 else "down";multi=bool(i>0 and float(rows.iloc[i-1].high-rows.iloc[i-1].low)>=atr*1.5);classification="MULTI-CANDLE_EVENT" if multi else "QUALIFIED_UP_EVENT" if direction=="up" else "QUALIFIED_DOWN_EVENT";time=_time(row)
    return {**base,"qualified":True,"classification":classification,"direction":direction,"magnitude_points":width,"magnitude_atr":atr_mult,"range_multiple":range_mult,"body_ratio":body_ratio,"confidence":confidence,"origin_price":float(row.open),"extreme_price":float(row.high if direction=="up" else row.low),"completed_at":time,"source_candle_time":time,"evidence":["Completed displacement, normalized magnitude, and follow-through qualify the event."],"rejection_reasons":[]}
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
