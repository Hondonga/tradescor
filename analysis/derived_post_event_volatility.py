"""Short-term volatility recalibration strictly after a locked event."""
import pandas as pd
def recalibrate_post_event_volatility(candles,event,config=None):
    base={"pre_event_atr":None,"post_event_atr":None,"atr_ratio":None,"volatility_state":"uncontrolled","stabilization_score":0.0,"sample_size":0,"release_allowed":False,"evidence":[],"warnings":[]}
    if not event:return base
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows;cut=pd.Timestamp(event["completed_at"]);pre=rows[rows.time<cut].tail(14);post=rows[rows.time>cut].tail(12)
    if len(pre)<5 or len(post)<3:return {**base,"sample_size":len(post),"warnings":["Post-event volatility sample is incomplete."]}
    pre_atr=float((pre.high-pre.low).mean());post_atr=float((post.high-post.low).mean());ratio=post_atr/max(pre_atr,1e-12);slope=float((post.high-post.low).tail(3).mean()/max((post.high-post.low).head(3).mean(),1e-12));score=max(0,min(1,1-abs(ratio-1)*.35+(1-min(slope,2))*.2));state="uncontrolled" if ratio>2.2 or slope>1.45 else "elevated" if ratio>1.5 else "stabilizing" if score<.65 else "stable";release=state in {"stabilizing","stable"}
    return {**base,"pre_event_atr":pre_atr,"post_event_atr":post_atr,"atr_ratio":ratio,"volatility_state":state,"stabilization_score":score,"sample_size":len(post),"release_allowed":release,"evidence":[f"{len(post)} completed post-event candles recalibrated volatility."]}
