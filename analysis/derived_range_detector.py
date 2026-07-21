"""Completed-candle consolidation detection without future breakout leakage."""
from __future__ import annotations
import pandas as pd

def detect_derived_range(candles,atr,config=None):
    cfg=config or {};rows=_completed(candles);duration=int(cfg.get("minimum_range_duration",18));base={"low":None,"high":None,"midpoint":None,"width_points":None,"width_atr":None,"started_at":None,"ended_at":None,"duration_candles":len(rows),"touches_high":0,"touches_low":0,"internal_close_ratio":None,"wick_excursions":0,"directional_efficiency":None,"compression_score":None,"boundary_stability":None,"false_break_count":0,"quality":0.0,"valid":False,"rejection_reasons":[]}
    if len(rows)<duration:return {**base,"rejection_reasons":["Range duration is below requirement."]}
    look=rows.tail(max(duration,min(len(rows),40))).copy();low=float(look.low.quantile(.05));high=float(look.high.quantile(.95));width=high-low;tol=max(float(atr or 0)*.18,width*.04);touch_low=int((look.low<=low+tol).sum());touch_high=int((look.high>=high-tol).sum());inside=((look.close>=low)&(look.close<=high));internal=float(inside.mean());wick=int(((look.high>high)&(look.close<=high)).sum()+((look.low<low)&(look.close>=low)).sum());path=float(look.close.diff().abs().sum());eff=abs(float(look.close.iloc[-1]-look.close.iloc[0]))/path if path else 0;range_series=look.high-look.low;compression=max(0,min(1,1-float(range_series.tail(6).mean())/max(float(range_series.mean()),1e-12)+.5));stability=max(0,min(1,1-float(range_series.std())/max(width,1e-12)));width_atr=width/max(float(atr or 0),1e-12);reaction_score=min(1,(touch_low+touch_high)/max(int(cfg.get("minimum_boundary_reactions",3)),1));quality=.25*internal+.2*(1-min(eff,1))+.2*reaction_score+.15*stability+.2*compression;reasons=[]
    if touch_low<int(cfg.get("minimum_reactions_per_side",1)) or touch_high<int(cfg.get("minimum_reactions_per_side",1)):reasons.append("Each boundary needs a meaningful reaction.")
    if touch_low+touch_high<int(cfg.get("minimum_boundary_reactions",3)):reasons.append("Total boundary reactions are insufficient.")
    if width_atr<float(cfg.get("minimum_width_atr",.75)) or width_atr>float(cfg.get("maximum_width_atr",5)):reasons.append("Normalized range width is outside configured limits.")
    if quality<float(cfg.get("minimum_range_quality",.65)):reasons.append("Range quality is below requirement.")
    return {**base,"low":low,"high":high,"midpoint":(low+high)/2,"width_points":width,"width_atr":width_atr,"started_at":_time(look.iloc[0]),"ended_at":_time(look.iloc[-1]),"duration_candles":len(look),"touches_high":touch_high,"touches_low":touch_low,"internal_close_ratio":internal,"wick_excursions":wick,"directional_efficiency":eff,"compression_score":compression,"boundary_stability":stability,"false_break_count":wick,"quality":quality,"valid":not reasons,"rejection_reasons":reasons}

def _completed(candles):
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    return rows
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
