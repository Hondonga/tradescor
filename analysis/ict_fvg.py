"""Exact three-candle displacement FVG lifecycle with rejection diagnostics."""

from __future__ import annotations

import pandas as pd

from analysis.ict_state import evidence_result, stable_id


def identify_displacement_fvg(candles: pd.DataFrame, displacement: dict | None, *, direction: str, tick_size: float, minimum_ticks=2, max_age=36, spread=0.0):
    thresholds={"minimum_ticks":minimum_ticks,"tick_size":tick_size,"minimum_size":max(tick_size*minimum_ticks,float(spread)),"max_age_bars":max_age}
    if not displacement:return evidence_result(timeframe="M15",rejection_reason="A displacement event is required.",state="waiting",thresholds_used=thresholds)
    rows=candles.reset_index(drop=True); start=int(displacement.get("start_index",displacement["candle_index"])); end=int(displacement["candle_index"]); candidates=[]; active=[]
    # The middle candle must be inside the impulse or immediately adjacent.
    for middle in range(max(1,start-1),min(len(rows)-1,end+2)):
        first,third=rows.iloc[middle-1],rows.iloc[middle+1]
        if direction=="buy" and float(first.high)<float(third.low):low,high=float(first.high),float(third.low)
        elif direction=="sell" and float(first.low)>float(third.high):low,high=float(third.high),float(first.low)
        else:continue
        formation=third.time.isoformat(); later=rows.iloc[middle+2:]; touched=later.loc[(later.low.astype(float)<=high)&(later.high.astype(float)>=low)]; fully=later.loc[later.low.astype(float)<=low] if direction=="buy" else later.loc[later.high.astype(float)>=high]; age=len(rows)-(middle+2); size=high-low; reasons=[]
        if size<thresholds["minimum_size"]:reasons.append("FVG smaller than tick/spread-normalized minimum.")
        if not fully.empty:reasons.append("FVG was fully mitigated before the decision.")
        if age>max_age:reasons.append("FVG is stale.")
        candidate={"fvg_id":stable_id("fvg",{"displacement":displacement["displacement_id"],"time":formation,"low":low,"high":high}),"formation_time":formation,"direction":"bullish" if direction=="buy" else "bearish","low":low,"high":high,"consequent_encroachment":(low+high)/2,"displacement_id":displacement["displacement_id"],"mitigation_percentage":1.0 if not fully.empty else .5 if not touched.empty else 0.0,"first_touch_time":touched.iloc[0].time.isoformat() if not touched.empty else None,"fully_filled_time":fully.iloc[0].time.isoformat() if not fully.empty else None,"active":not reasons,"age_bars":age,"size":size,"middle_candle_time":rows.iloc[middle].time.isoformat(),"rejection_reasons":reasons}
        candidates.append(candidate)
        if not reasons:active.append(candidate)
    if not active:
        reasons=[reason for row in candidates for reason in row["rejection_reasons"]] or ["No exact three-candle FVG formed during or immediately after displacement."]
        return evidence_result(timeframe="M15",rejection_reason="No active exact three-candle FVG belongs to displacement.",state="fail" if candidates else "waiting",detected_candidates=candidates,rejection_reasons=list(dict.fromkeys(reasons)),thresholds_used=thresholds)
    result=active[0]; return evidence_result(result=result,timestamp=result["formation_time"],timeframe="M15",valid=True,evidence=["Exact candle-1/candle-3 geometry passed.","FVG is linked to the displacement ID and remains active."],detected_candidates=candidates,rejection_reasons=[reason for row in candidates if row is not result for reason in row["rejection_reasons"]],thresholds_used=thresholds)
