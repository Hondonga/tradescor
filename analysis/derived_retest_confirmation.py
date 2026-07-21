"""Post-retest M5 confirmation bound to setup and range identities."""
from __future__ import annotations
import pandas as pd
from analysis.derived_execution_confirmation import confirm_m5_execution,lock_confirmed_entry
def retest_interaction_time(candles,retest_zone,breakout_time):
    if not retest_zone:return None
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if "time" in rows:rows=rows[rows.time>pd.Timestamp(breakout_time)]
    touched=rows[(rows.low<=retest_zone["high"])&(rows.high>=retest_zone["low"])]
    return touched.iloc[-1].time if len(touched) else None
def confirm_retest(candles,direction,retest_zone,setup_id,range_id,interaction_time):
    if interaction_time is None:return None
    execution={**retest_zone,"valid":bool(retest_zone and retest_zone.get("valid"))};confirmation=confirm_m5_execution(candles,"buy" if direction=="bullish" else "sell",retest_zone,execution,setup_id,interaction_time)
    confirmation["valid_for_range_id"]=range_id if confirmation.get("valid") else None;return confirmation
def lock_range_entry(confirmation,setup_id,range_id,price,existing=None):
    entry=lock_confirmed_entry(confirmation,setup_id,existing,price);entry["range_id"]=range_id;return entry
