"""Fresh structure formed strictly after the locked spike candle."""
from __future__ import annotations
import pandas as pd
from analysis.derived_regime_detector import detect_derived_structure
def analyze_post_spike_structure(candles,spike):
    base={"direction":"neutral","state":"INSUFFICIENT_STRUCTURE","last_swing_high":None,"last_swing_low":None,"bullish_structure_break":None,"bearish_structure_break":None,"formed_after_spike":False,"valid_for_spike_id":spike.get("spike_id") if spike else None,"evidence":[],"contradictions":[]}
    if not spike:return base
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if "time" in rows:rows=rows[rows.time>pd.Timestamp(spike["completed_at"])]
    if len(rows)<7:return base
    structure=detect_derived_structure(rows);direction=structure.get("direction","neutral");state="POST_SPIKE_BULLISH" if direction=="bullish" else "POST_SPIKE_BEARISH" if direction=="bearish" else "RANGE_FORMING" if structure.get("structure")=="range_or_transition" else "UNSTABLE"
    return {**base,"direction":direction,"state":state,"last_swing_high":structure.get("last_confirmed_swing_high"),"last_swing_low":structure.get("last_confirmed_swing_low"),"bullish_structure_break":structure.get("bullish_break"),"bearish_structure_break":structure.get("bearish_break"),"formed_after_spike":direction in {"bullish","bearish"},"evidence":structure.get("evidence",[]),"contradictions":structure.get("contradictions",[])}
