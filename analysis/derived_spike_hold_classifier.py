"""ATR-normalized hold/retrace classification around immutable spike geometry."""
from __future__ import annotations
import pandas as pd
def classify_spike_hold(candles,spike,atr,config=None):
    base={"classification":"UNRESOLVED","hold_level":None,"origin_reclaimed":False,"retracement_percentage":None,"retracement_atr":None,"confidence":0.0,"evidence":[],"contradictions":[]}
    if not spike:return base
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if "time" in rows:rows=rows[rows.time>pd.Timestamp(spike["completed_at"])]
    if rows.empty:return base
    origin=float(spike["origin_price"]);extreme=float(spike["extreme_price"]);last=float(rows.close.iloc[-1]);leg=abs(extreme-origin);direction=spike["direction"];retracement=(extreme-last)/leg if direction=="up" else (last-extreme)/leg;retracement=max(0,retracement);reclaimed=last<=origin if direction=="up" else last>=origin;hold_level=(origin+extreme)/2
    if reclaimed:classification="RECLAIMED" if abs(last-origin)<=max(atr or 0,1e-12)*.25 else "FAILED_HOLD"
    elif retracement>=.9:classification="FULL_RETRACE"
    elif retracement>=.5:classification="PARTIAL_RETRACE"
    else:classification="HOLDING_ABOVE_ORIGIN" if direction=="up" else "HOLDING_BELOW_ORIGIN"
    return {**base,"classification":classification,"hold_level":hold_level,"origin_reclaimed":reclaimed,"retracement_percentage":retracement,"retracement_atr":abs(extreme-last)/max(float(atr or 0),1e-12),"confidence":min(.95,.55+min(len(rows),8)*.04),"evidence":[f"{len(rows)} completed candles evaluated after the locked spike."],"contradictions":[]}
