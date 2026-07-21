"""Close-confirmed market-structure shift known at decision time."""

from __future__ import annotations

import pandas as pd

from analysis.ict_state import evidence_result


def detect_mss(candles: pd.DataFrame, sweep: dict | None, displacement: dict | None, *, direction: str, forming_candle=None):
    thresholds={"pivot_left":2,"pivot_right":2,"completed_close_required":True}
    if not sweep or not displacement: return evidence_result(timeframe="M15",rejection_reason="Sweep and displacement must precede MSS.",state="waiting",thresholds_used=thresholds)
    rows=candles.reset_index(drop=True); sweep_time=pd.Timestamp(sweep["sweep_time"]); sweep_time=sweep_time.tz_localize("UTC") if sweep_time.tzinfo is None else sweep_time.tz_convert("UTC"); times=pd.to_datetime(rows.time,utc=True)
    before=rows.loc[times<sweep_time]; pivots=[]
    for i in range(2,len(before)-2):
        window=before.iloc[i-2:i+3]; row=before.iloc[i]
        if direction=="buy" and float(row.high)==float(window.high.max()):pivots.append(row)
        if direction=="sell" and float(row.low)==float(window.low.min()):pivots.append(row)
    if not pivots:return evidence_result(timeframe="M15",rejection_reason="MSS candidate rejected: pivot prominence below threshold or no pivot was known before the sweep.",detected_candidates=[],thresholds_used=thresholds)
    pivot=pivots[-1]; level=float(pivot.high if direction=="buy" else pivot.low); after=rows.loc[times>=pd.Timestamp(displacement["start_time"])]
    breaks=after.loc[(after.close.astype(float)>level) if direction=="buy" else (after.close.astype(float)<level)]
    candidate={"direction":direction,"level":level,"pivot_price":level,"pivot_time":pivot.time.isoformat(),"pivot_formation_time":pivot.time.isoformat(),"pivot_known_at_sweep":True,"break_time":None,"break_candle":None,"close_price":None,"close_confirmed":False,"displacement_supported":True}
    if breaks.empty:return evidence_result(result=candidate,timeframe="M15",rejection_reason="A completed candle has not closed through the pre-sweep pivot.",state="forming" if forming_candle is not None and not forming_candle.empty else "waiting",detected_candidates=[candidate],thresholds_used=thresholds)
    row=breaks.iloc[0]; result={**candidate,"break_time":row.time.isoformat(),"break_candle":row.time.isoformat(),"close_price":float(row.close),"close_confirmed":True}
    return evidence_result(result=result,timestamp=result["break_time"],timeframe="M15",valid=True,evidence=["Pivot was confirmed and known before the sweep.","Completed post-displacement candle closed beyond the pivot."],detected_candidates=[result],thresholds_used=thresholds)
