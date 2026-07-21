"""Independent quality measurement for each immutable range boundary."""
from __future__ import annotations
import pandas as pd
def evaluate_boundary_quality(candles,locked_range,side,atr,config=None):
    cfg=config or {};price=float(locked_range["high"] if side=="upper" else locked_range["low"]);rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    tol=max(float(atr or 0)*.18,(locked_range["high"]-locked_range["low"])*.04);near=(rows.high>=price-tol) if side=="upper" else (rows.low<=price+tol);reactions=int(near.sum());close_reject=int(((rows.high>price)&(rows.close<=price)).sum()) if side=="upper" else int(((rows.low<price)&(rows.close>=price)).sum());wicks=close_reject;breaks=int((rows.close>price+tol).sum()) if side=="upper" else int((rows.close<price-tol).sum());fresh=max(0,1-reactions*.03);stability=max(0,1-breaks*.3);quality=min(1,.25+min(reactions,5)*.1+min(close_reject,4)*.1+stability*.15);reasons=[]
    if reactions<int(cfg.get("minimum_boundary_reactions",2)):reasons.append("Boundary reactions are insufficient.")
    if breaks>int(cfg.get("maximum_decisive_breaks",0)):reasons.append("Boundary has a decisive completed break.")
    if quality<float(cfg.get("minimum_boundary_quality",.65)):reasons.append("Boundary quality is below requirement.")
    last=rows[near].iloc[-1] if near.any() else None;formed=(last.get("time") if last is not None else None);formed=formed.isoformat() if hasattr(formed,"isoformat") else str(formed) if formed is not None else None
    return {"price":price,"side":side,"reaction_count":reactions,"completed_close_rejections":close_reject,"wick_rejections":wicks,"decisive_breaks":breaks,"last_reaction_at":formed,"freshness":fresh,"stability":stability,"quality":quality,"valid":not reasons,"rejection_reasons":reasons}
