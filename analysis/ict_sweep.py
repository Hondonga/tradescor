"""Liquidity sweep versus accepted-breakout classifier."""

from __future__ import annotations

import pandas as pd

from analysis.ict_state import evidence_result, stable_id


def classify_sweep(candles: pd.DataFrame, pool: dict | None, *, direction: str, reclaim_window=4, accepted_closes=2, forming_candle: pd.DataFrame | None=None, tick_size=0.0, spread=0.0):
    thresholds={"reclaim_window_bars":reclaim_window,"accepted_breakout_closes":accepted_closes,"minimum_penetration":max(float(tick_size)*2,float(spread))}
    if not pool: return evidence_result(timeframe="M15",rejection_reason="No pre-existing opposing liquidity.",state="waiting",thresholds_used=thresholds)
    rows=candles.reset_index(drop=True); formed=pd.Timestamp(pool["formed_at"]); formed=formed.tz_localize("UTC") if formed.tzinfo is None else formed.tz_convert("UTC"); times=pd.to_datetime(rows.time,utc=True); eligible=rows.loc[times>formed]
    level=float(pool["price"]); noise=thresholds["minimum_penetration"]; beyond=(eligible.low.astype(float)<level-noise) if direction=="buy" else (eligible.high.astype(float)>level+noise)
    if not bool(beyond.any()):
        forming=_forming(forming_candle,level,direction)
        return evidence_result(result=forming,timestamp=(forming or {}).get("sweep_time"),timeframe="M15",valid=False,evidence=["Live candle traded beyond liquidity; close/reclaim pending."] if forming else [],state="forming" if forming else "waiting",rejection_reason=None if forming else "Opposing liquidity has not been swept.",detected_candidates=[forming] if forming else [],thresholds_used=thresholds)
    event_index=int(eligible.loc[beyond].index[0]); event=rows.loc[event_index]; after=rows.iloc[event_index:min(len(rows),event_index+reclaim_window+1)]
    inside=(after.close.astype(float)>level) if direction=="buy" else (after.close.astype(float)<level); reclaim=after.loc[inside]
    outside=(after.close.astype(float)<level) if direction=="buy" else (after.close.astype(float)>level); accepted=_consecutive(outside,accepted_closes) and reclaim.empty
    excursion=after.loc[:reclaim.index[0]] if not reclaim.empty else after
    extreme=float(excursion.low.min() if direction=="buy" else excursion.high.max())
    # Phase 4 §8 -- an explicit, stable sweep identity (previously implicit
    # via (liquidity_id, sweep_time) only) plus liquidity_type/active so a
    # sweep can be tracked/invalidated independently of its parent pool.
    # Existing field names (pool_price/sweep_extreme/sweep_time/reclaim_time)
    # are kept unchanged for existing consumers; liquidity_price/sweep_price/
    # swept_at/confirmed_at are added as the Phase 4-named aliases.
    sweep_id=stable_id("sweep",{"liquidity_id":pool["liquidity_id"],"direction":direction,"sweep_time":event.time.isoformat()})
    result={"sweep_id":sweep_id,"liquidity_id":pool["liquidity_id"],"liquidity_type":pool.get("type"),"pool_price":level,"liquidity_price":level,"direction":direction,"sweep_time":event.time.isoformat(),"swept_at":event.time.isoformat(),"sweep_extreme":extreme,"sweep_price":extreme,"reclaim_time":reclaim.iloc[0].time.isoformat() if not reclaim.empty else None,"confirmed_at":reclaim.iloc[0].time.isoformat() if not reclaim.empty else None,"accepted_breakout":accepted,"confirmed":not reclaim.empty and not accepted,"active":not accepted,"pool_formed_at":pool["formed_at"]}
    state="fail" if accepted else "pass" if result["confirmed"] else "forming"
    return evidence_result(result=result,timestamp=result["reclaim_time"] if result["confirmed"] else result["sweep_time"],timeframe="M15",valid=result["confirmed"],evidence=["Price traded beyond pre-existing liquidity.","Range side was reclaimed within the configured multi-candle window."] if result["confirmed"] else ["Consecutive closes accepted beyond liquidity."] if accepted else ["Penetration occurred; reclaim is pending."],rejection_reason="Accepted breakout is not an ICT sweep." if accepted else None,state=state,detected_candidates=[result],thresholds_used=thresholds)


def _forming(frame,level,direction):
    if frame is None or frame.empty:return None
    row=frame.iloc[-1]; crossed=float(row.low)<level if direction=="buy" else float(row.high)>level
    return {"pool_price":level,"direction":direction,"sweep_time":row.time.isoformat(),"sweep_extreme":float(row.low if direction=="buy" else row.high),"confirmed":False} if crossed else None
def _consecutive(mask,count):
    run=0
    for value in mask.tolist():
        run=run+1 if value else 0
        if run>=count:return True
    return False
