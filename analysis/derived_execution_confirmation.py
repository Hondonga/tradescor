"""Post-interaction M5 execution-zone and completed confirmation logic."""
from __future__ import annotations
import pandas as pd
_ENTRY_LOCKS={}

def build_m5_execution_zone(candles,direction,m15_zone,zone_reached_at=None):
    rows=_completed(candles);base={"low":None,"high":None,"type":"","direction":direction,"formed_at":None,"source_timeframe":"M5","valid":False,"rejection_reasons":[]}
    if not m15_zone or not m15_zone.get("valid") or len(rows)<6:return {**base,"rejection_reasons":["Valid M15 setup zone and M5 history are required."]}
    touched=rows[(rows.low<=m15_zone["high"])&(rows.high>=m15_zone["low"])]
    if zone_reached_at is not None:touched=touched[touched.time>=pd.Timestamp(zone_reached_at)]
    if touched.empty:return {**base,"rejection_reasons":["Price has not reached the current M15 setup zone."]}
    touch_idx=rows.index.get_loc(touched.index[-1]);after=rows.iloc[touch_idx:];reaction=after.iloc[-3:] if len(after)>=3 else after
    row=reaction.iloc[(reaction.close-reaction.open).idxmax()-reaction.index[0]] if direction=="buy" else reaction.iloc[(reaction.open-reaction.close).idxmax()-reaction.index[0]]
    low=min(float(row.open),float(row.close));high=max(float(row.open),float(row.close));width=high-low;m15_width=float(m15_zone["high"]-m15_zone["low"]);valid=width>0 and width<m15_width
    return {**base,"low":low,"high":high,"type":"m5_demand" if direction=="buy" else "m5_supply","formed_at":_time(row),"valid":valid,"rejection_reasons":[] if valid else ["M5 execution zone is not narrower than the M15 setup zone."]}

def confirm_m5_execution(candles,direction,m15_zone,execution_zone,setup_id,zone_reached_at):
    base={"type":"","direction":direction,"trigger_price":None,"formed_at":None,"candle_time":None,"complete":False,"valid":False,"valid_for_setup_id":None,"evidence":[],"rejection_reasons":[]}
    rows=_completed(candles)
    if zone_reached_at is None:return {**base,"rejection_reasons":["Confirmation cannot precede zone interaction."]}
    if not execution_zone or not execution_zone.get("valid"):return {**base,"rejection_reasons":["A valid M5 execution zone is required."]}
    after=rows[rows.time>pd.Timestamp(zone_reached_at)] if "time" in rows else rows.iloc[0:0]
    if len(after)<3:return {**base,"rejection_reasons":["Waiting for completed M5 candles after zone interaction."]}
    prior=after.iloc[:-1].tail(5);last=after.iloc[-1];trigger=float(prior.high.max()) if direction=="buy" else float(prior.low.min());valid=float(last.close)>trigger if direction=="buy" else float(last.close)<trigger
    return {**base,"type":"bullish_micro_bos" if direction=="buy" else "bearish_micro_bos","trigger_price":trigger,"formed_at":_time(last) if valid else None,"candle_time":_time(last),"complete":True,"valid":valid,"valid_for_setup_id":setup_id if valid else None,"evidence":["Completed M5 close broke post-interaction micro structure."] if valid else [],"rejection_reasons":[] if valid else ["No completed post-interaction M5 structure break."]}

def lock_confirmed_entry(confirmation,setup_id,existing=None,price=None):
    if setup_id in _ENTRY_LOCKS:return dict(_ENTRY_LOCKS[setup_id])
    if existing and existing.get("valid") and existing.get("setup_id")==setup_id:return existing
    valid=bool(confirmation and confirmation.get("valid") and confirmation.get("complete") and confirmation.get("valid_for_setup_id")==setup_id and price is not None)
    result={"price":float(price) if valid else None,"source":"confirmation_close" if valid else "","confirmed_at":confirmation.get("formed_at") if valid else None,"setup_id":setup_id,"valid":valid}
    if valid:_ENTRY_LOCKS[setup_id]=dict(result)
    return result

def _completed(candles):
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    return rows
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
