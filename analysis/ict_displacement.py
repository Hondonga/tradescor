"""ATR-normalized single- or multi-candle displacement after a sweep."""

from __future__ import annotations

import pandas as pd

from analysis.ict_state import evidence_result, stable_id


def detect_displacement(candles: pd.DataFrame, sweep: dict | None, *, direction: str, body_atr_threshold=1.0, range_atr_threshold=1.2, close_location_threshold=.7, impulse_score_threshold=.65, maximum_candles=3, forming_candle=None):
    thresholds={"body_atr":body_atr_threshold,"range_atr":range_atr_threshold,"close_location":close_location_threshold,"impulse_score":impulse_score_threshold,"maximum_candles":maximum_candles}
    if not sweep or not sweep.get("confirmed"):return evidence_result(timeframe="M15",rejection_reason="Confirmed sweep is required before displacement.",state="waiting",thresholds_used=thresholds)
    rows=candles.reset_index(drop=True); times=pd.to_datetime(rows.time,utc=True); after_indices=rows.index[times>pd.Timestamp(sweep["reclaim_time"])].tolist(); atr=_atr(rows); candidates=[]; rejections=[]
    for start_position,start in enumerate(after_indices):
        for length in range(1,maximum_candles+1):
            indices=after_indices[start_position:start_position+length]
            if len(indices)!=length or indices[-1]-indices[0]!=length-1:continue
            impulse=rows.loc[indices]; first,last=impulse.iloc[0],impulse.iloc[-1]; total_range=float(impulse.high.max()-impulse.low.min()); bodies=(impulse.close-impulse.open).abs().astype(float); directional=(impulse.close>impulse.open) if direction=="buy" else (impulse.close<impulse.open); directional_ratio=float(directional.mean()); net=abs(float(last.close-first.open)); path=float(impulse.close.diff().abs().sum())+abs(float(first.close-first.open)); efficiency=net/max(path,1e-12); close_location=(float(last.close-impulse.low.min())/max(total_range,1e-12)) if direction=="buy" else (float(impulse.high.max()-last.close)/max(total_range,1e-12)); prior=rows.iloc[max(0,start-6):start]; structure_level=float(prior.high.max()) if direction=="buy" and not prior.empty else float(prior.low.min()) if not prior.empty else None; broken=structure_level is not None and (float(last.close)>structure_level if direction=="buy" else float(last.close)<structure_level); fvg_created=_has_fvg(rows,indices,direction)
            body_atr=float(bodies.sum()/atr); range_atr=total_range/atr
            score=.25*min(1,body_atr/max(body_atr_threshold,1e-12))+.20*min(1,range_atr/max(range_atr_threshold,1e-12))+.15*close_location+.15*directional_ratio+.15*efficiency+.05*int(broken)+.05*int(fvg_created)
            candidate={"direction":"up" if direction=="buy" else "down","start_time":first.time.isoformat(),"end_time":last.time.isoformat(),"candle_index":int(indices[-1]),"start_index":int(indices[0]),"body_atr":body_atr,"range_atr":range_atr,"close_location":close_location,"directional_efficiency":efficiency,"directional_close_ratio":directional_ratio,"impulse_score":score,"structure_level_broken":structure_level if broken else None,"structure_effect":"local_structure_broken" if broken else "none","fvg_created":fvg_created,"confirmed":False,"candle_count":length}
            candidates.append(candidate)
            valid=directional_ratio>=2/3 and close_location>=close_location_threshold*.85 and broken and (body_atr>=body_atr_threshold or (length>1 and score>=impulse_score_threshold))
            if valid:
                candidate.update({"displacement_id":stable_id("disp",{"sweep":sweep["sweep_time"],"start":candidate["start_time"],"end":candidate["end_time"],"direction":direction}),"confirmed":True})
                return evidence_result(result=candidate,timestamp=candidate["end_time"],timeframe="M15",valid=True,evidence=[f"{length}-candle impulse passed volatility-normalized scoring.","Completed impulse close broke prior local structure."],detected_candidates=candidates,thresholds_used={**thresholds,"atr":atr})
            rejections.append("Impulse rejected: " + ("no completed structural break" if not broken else "normalized impulse score/body threshold not met"))
    state="forming" if forming_candle is not None and not forming_candle.empty else "waiting"; reason="No qualifying post-sweep displacement impulse."
    return evidence_result(timeframe="M15",rejection_reason=reason,state=state,detected_candidates=candidates,rejection_reasons=list(dict.fromkeys(rejections[-10:]+[reason])),thresholds_used={**thresholds,"atr":atr})


def _has_fvg(rows,indices,direction):
    for middle in range(max(1,indices[0]-1),min(len(rows)-1,indices[-1]+2)):
        first,third=rows.iloc[middle-1],rows.iloc[middle+1]
        if direction=="buy" and float(first.high)<float(third.low):return True
        if direction=="sell" and float(first.low)>float(third.high):return True
    return False
def _atr(rows):
    previous=rows.close.shift(); return max(1e-12,float(pd.concat([rows.high-rows.low,(rows.high-previous).abs(),(rows.low-previous).abs()],axis=1).max(axis=1).tail(14).mean()))
