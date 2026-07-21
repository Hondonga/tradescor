"""Confirmation bound to spike, setup, cooldown, and zone interaction."""
from __future__ import annotations
import pandas as pd
from analysis.derived_execution_confirmation import confirm_m5_execution,lock_confirmed_entry
def post_spike_zone_interaction(candles,zone,after_time):
    if not zone:return None
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if "time" in rows:rows=rows[rows.time>pd.Timestamp(after_time)]
    touched=rows[(rows.low<=zone["high"])&(rows.high>=zone["low"])]
    return touched.iloc[-1].time if len(touched) else None
def confirm_post_spike(candles,direction,zone,setup_id,spike_id,interaction_time,cooldown):
    if not cooldown or not cooldown.get("release_allowed") or interaction_time is None:return None
    result=confirm_m5_execution(candles,direction,zone,zone,setup_id,interaction_time);result["valid_for_spike_id"]=spike_id if result.get("valid") else None;return result
def lock_post_spike_entry(confirmation,setup_id,spike_id,price,existing=None):
    entry=lock_confirmed_entry(confirmation,setup_id,existing,price);entry["spike_id"]=spike_id;return entry
