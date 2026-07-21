"""Completed-candle, volatility-and-structure gated spike cooldown."""
from __future__ import annotations
import pandas as pd
def evaluate_spike_cooldown(candles,spike,volatility,structure,config=None):
    cfg=config or {};minimum=int(cfg.get("minimum_cooldown_candles",3));rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if not spike:return {"active":False,"started_at":None,"ends_after_candles":None,"completed_candles_elapsed":0,"minimum_required_candles":minimum,"minimum_candles_passed":False,"volatility_stabilized":False,"fresh_swings_available":False,"fresh_structure_available":False,"structure_reformed":False,"no_new_event":True,"data_quality_passed":bool(len(rows)),"release_allowed":False,"reasons":["No locked spike."]}
    after=rows[rows.time>pd.Timestamp(spike["completed_at"])] if "time" in rows else rows.iloc[0:0];elapsed=len(after);vol_stable=volatility.get("regime") not in {"EXTREME","UNSTABLE","RISING"};structure_ok=bool(structure and structure.get("formed_after_spike") and structure.get("direction") in {"bullish","bearish"});release=elapsed>=minimum and vol_stable and structure_ok;reasons=[]
    if elapsed<minimum:reasons.append("Minimum completed post-spike candles have not elapsed.")
    if not vol_stable:reasons.append("Post-spike volatility remains uncontrolled.")
    if not structure_ok:reasons.append("Fresh post-spike structure has not reformed.")
    minimum_ok=elapsed>=minimum;swings_ok=bool((structure or {}).get("fresh_swings_available",structure_ok));no_new=not bool((structure or {}).get("new_spike_detected"));data_ok=bool(len(rows));release=minimum_ok and vol_stable and swings_ok and structure_ok and no_new and data_ok
    return {"active":not release,"started_at":spike["completed_at"],"ends_after_candles":minimum,"completed_candles_elapsed":elapsed,"minimum_required_candles":minimum,"minimum_candles_passed":minimum_ok,"volatility_stabilized":vol_stable,"fresh_swings_available":swings_ok,"fresh_structure_available":structure_ok,"structure_reformed":structure_ok,"no_new_event":no_new,"data_quality_passed":data_ok,"release_allowed":release,"reasons":reasons}
