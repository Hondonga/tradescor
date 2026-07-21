"""ATR/tick-normalized ICT liquidity pools, including realistic clusters."""

from __future__ import annotations

import pandas as pd

from analysis.ict_state import evidence_result, stable_id


def identify_liquidity(candles: pd.DataFrame, *, timeframe="M15", direction="neutral", minimum_age=3, prominence_atr=.35, tolerance_atr=.12, tick_size=0.0):
    thresholds={"minimum_age_bars":minimum_age,"prominence_atr":prominence_atr,"cluster_tolerance_atr":tolerance_atr,"tick_size":tick_size}
    if candles is None or len(candles)<12:return evidence_result(timeframe=timeframe,rejection_reason="Insufficient liquidity history.",data_quality="invalid",state="unavailable",thresholds_used=thresholds)
    rows=candles.reset_index(drop=True); atr=_atr(rows); tolerance=max(float(tick_size)*2,atr*float(tolerance_atr)); pivots=[]; rejected=[]
    for i in range(2,len(rows)-2-minimum_age+1):
        window=rows.iloc[i-2:i+3]; candle=rows.iloc[i]
        for side,column in (("buy_side","high"),("sell_side","low")):
            value=float(candle[column]); is_pivot=value>=float(window.high.max()) if side=="buy_side" else value<=float(window.low.min())
            if not is_pivot:continue
            neighbors=pd.concat([window[column].iloc[:2],window[column].iloc[3:]]).astype(float); prominence=(value-float(neighbors.max())) if side=="buy_side" else (float(neighbors.min())-value)
            candidate={"price":value,"side":side,"formed_at":candle.time.isoformat(),"pivot_index":i,"prominence":prominence,"prominence_atr":prominence/max(atr,1e-12)}
            pivots.append(candidate)
    pools=[]
    for side in ("buy_side","sell_side"):
        side_pivots=[row for row in pivots if row["side"]==side]; used=set()
        for index,pivot in enumerate(side_pivots):
            if index in used:continue
            cluster=[(index,pivot)]
            for other_index,other in enumerate(side_pivots[index+1:],index+1):
                if abs(other["price"]-pivot["price"])<=tolerance:cluster.append((other_index,other))
            used.update(item[0] for item in cluster); members=[item[1] for item in cluster]
            prominence_pass=max(row["prominence"] for row in members)>=atr*prominence_atr
            cluster_pass=len(members)>=2 and max(row["prominence"] for row in members)>=atr*prominence_atr*.20
            if not (prominence_pass or cluster_pass):
                rejected.append({**pivot,"touches":len(members),"rejection_reason":"Pivot prominence below threshold and no qualifying near-equal cluster."}); continue
            price=max(row["price"] for row in members) if side=="buy_side" else min(row["price"] for row in members); formed=max(row["formed_at"] for row in members); formation_index=max(row["pivot_index"] for row in members)
            later=rows.iloc[formation_index+1:]; crossed=(later.high.astype(float)>price+tolerance*.05) if side=="buy_side" else (later.low.astype(float)<price-tolerance*.05); swept=bool(crossed.any()); swept_at=later.loc[crossed].iloc[0].time.isoformat() if swept else None
            pool_type="near_equal_highs" if side=="buy_side" and len(members)>=2 else "near_equal_lows" if len(members)>=2 else "prominent_swing"
            pools.append({"liquidity_id":stable_id("liq",{"tf":timeframe,"members":[row["formed_at"] for row in members],"price":price,"side":side}),"price":price,"side":side,"type":pool_type,"formed_at":formed,"source_timeframe":timeframe,"quality":min(10,round(5+len(members)+max(row["prominence_atr"] for row in members)*2)),"touches":len(members),"tolerance_used":tolerance,"prominence":max(row["prominence"] for row in members),"swept":swept,"swept_at":swept_at,"pivot_index":formation_index,"members":members})
    pools.extend(_previous_day(rows,timeframe,tolerance))
    target_side="buy_side" if direction=="buy" else "sell_side" if direction=="sell" else None; opposing_side="sell_side" if direction=="buy" else "buy_side" if direction=="sell" else None; current=float(rows.iloc[-1].close)
    directional=[p for p in pools if p["side"]==target_side and not p["swept"] and ((p["price"]>current) if direction=="buy" else (p["price"]<current))]
    opposing=[p for p in pools if p["side"]==opposing_side and p["formed_at"]<rows.iloc[-1].time.isoformat()]
    # Prefer the latest pool that was actually raided; otherwise retain the
    # latest known pool so the first missing event is reported as the sweep.
    opposing.sort(key=lambda p:(bool(p["swept"]),p["formed_at"]),reverse=True)
    result={"directional_target":min(directional,key=lambda p:abs(p["price"]-current)) if directional else None,"opposing_pool":opposing[0] if opposing else None,"candidate_pools":pools}
    reason=None if result["opposing_pool"] else "No meaningful opposing liquidity pool."
    return evidence_result(result=result,timestamp=(result["opposing_pool"] or {}).get("formed_at"),timeframe=timeframe,valid=bool(result["directional_target"] and result["opposing_pool"]),evidence=[f"{len(pools)} normalized liquidity pools; {sum(p['touches']>1 for p in pools)} clusters."],rejection_reason=reason,detected_candidates=pools,rejection_reasons=[row["rejection_reason"] for row in rejected[:10]]+([reason] if reason else []),thresholds_used={**thresholds,"atr":atr,"tolerance_price":tolerance})


def _previous_day(rows,timeframe,tolerance):
    dates=pd.to_datetime(rows.time,utc=True).dt.date
    if dates.nunique()<2:return []
    prior_date=sorted(dates.unique())[-2]; prior=rows.loc[dates==prior_date]
    formed=prior.iloc[-1].time.isoformat(); formation_index=int(prior.index[-1]); later=rows.iloc[formation_index+1:]; result=[]
    for side,price in (("buy_side",float(prior.high.max())),("sell_side",float(prior.low.min()))):
        crossed=(later.high.astype(float)>price+tolerance*.05) if side=="buy_side" else (later.low.astype(float)<price-tolerance*.05); swept=bool(crossed.any())
        result.append({"liquidity_id":stable_id("liq",{"tf":timeframe,"type":"previous_day","date":str(prior_date),"side":side,"price":price}),"price":price,"side":side,"type":"previous_day_high" if side=="buy_side" else "previous_day_low","formed_at":formed,"source_timeframe":timeframe,"quality":8,"touches":1,"tolerance_used":tolerance,"prominence":None,"swept":swept,"swept_at":later.loc[crossed].iloc[0].time.isoformat() if swept else None,"pivot_index":formation_index,"members":[]})
    return result
def _atr(rows):
    previous=rows.close.shift(); return max(1e-12,float(pd.concat([rows.high-rows.low,(rows.high-previous).abs(),(rows.low-previous).abs()],axis=1).max(axis=1).tail(14).mean()))
