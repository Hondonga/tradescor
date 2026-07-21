"""Wick, attempt, reclaim, acceptance, and failure classification."""
from __future__ import annotations
import pandas as pd
def classify_breakout(candles,locked_range,atr,config=None):
    cfg=config or {};base={"event_type":"NO_BREAKOUT","direction":None,"boundary":None,"breakout_close":None,"breakout_high":None,"breakout_low":None,"breakout_time":None,"buffer_points":None,"buffer_atr":None,"body_strength":None,"acceptance_score":None,"accepted":False,"evidence":[],"rejection_reasons":[]}
    if not locked_range:return {**base,"rejection_reasons":["A pre-breakout locked range is required."]}
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if "time" in rows:rows=rows[rows.time>pd.Timestamp(locked_range["locked_at"])]
    if rows.empty:return base
    last=rows.iloc[-1];high=float(locked_range["high"]);low=float(locked_range["low"]);buffer=max(float(atr or 0)*float(cfg.get("breakout_buffer_atr",.1)),1e-12);width=max(float(last.high-last.low),1e-12);body=abs(float(last.close-last.open))/width
    direction="bullish" if float(last.high)>high else "bearish" if float(last.low)<low else None;boundary=high if direction=="bullish" else low if direction=="bearish" else None
    if not direction:return base
    close_out=float(last.close)>high+buffer if direction=="bullish" else float(last.close)<low-buffer;close_inside=low<=float(last.close)<=high
    if close_inside:event="SWEEP_RECLAIM";accepted=False
    elif not close_out:event="BREAKOUT_ATTEMPT";accepted=False
    elif body<float(cfg.get("minimum_breakout_body_ratio",.45)):event="BREAKOUT_ATTEMPT";accepted=False
    else:event="ACCEPTED_BREAKOUT";accepted=True
    if len(rows)>=2:
        previous=rows.iloc[-2];previous_out=float(previous.close)>high+buffer if direction=="bullish" else float(previous.close)<low-buffer
        if previous_out and close_inside:event="FAILED_BREAKOUT";accepted=False
    if event=="SWEEP_RECLAIM" and not close_inside:event="WICK_EXCURSION"
    score=min(1,.45+body*.35+(abs(float(last.close)-boundary)/buffer)*.1) if accepted else min(.5,body)
    return {**base,"event_type":event,"direction":direction,"boundary":boundary,"breakout_close":float(last.close),"breakout_high":float(last.high),"breakout_low":float(last.low),"breakout_time":_time(last),"buffer_points":buffer,"buffer_atr":buffer/atr if atr else None,"body_strength":body,"acceptance_score":score,"accepted":accepted,"evidence":["Completed close passed the locked boundary and volatility buffer."] if accepted else [],"rejection_reasons":[] if accepted else ["Boundary event did not achieve accepted breakout conditions."]}
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
