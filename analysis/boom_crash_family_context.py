"""Measured family behavior without assuming drift or spike trades."""
import pandas as pd
def build_boom_crash_family_context(family,candles):
    family=str(family).upper();expected="up" if family=="BOOM" else "down" if family=="CRASH" else "none";rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    if len(rows)<10:return {"family":family,"expected_spike_direction":expected,"current_drift_direction":"neutral","spike_alignment_context":"insufficient completed drift history","family_behavior_confidence":0.0}
    close=pd.to_numeric(rows.close).tail(20);change=close.diff().dropna();up=float((change>0).mean());down=float((change<0).mean())
    drift="bullish" if up>=.62 else "bearish" if down>=.62 else "mixed";confidence=max(up,down) if drift!="mixed" else 1-abs(up-down)
    return {"family":family,"expected_spike_direction":expected,"current_drift_direction":drift,"spike_alignment_context":f"Measured {drift} completed-candle drift; no automatic trade implication.","family_behavior_confidence":confidence}
