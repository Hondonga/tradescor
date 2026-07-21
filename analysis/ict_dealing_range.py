"""Confirmed higher-timeframe dealing range and premium/discount location."""

from __future__ import annotations

import pandas as pd

from analysis.ict_state import evidence_result, stable_id


def identify_dealing_range(candles: pd.DataFrame, *, timeframe: str = "H4", minimum_atr: float = 2.0):
    if candles is None or len(candles) < 20: return evidence_result(timeframe=timeframe, rejection_reason="Insufficient completed candles.", data_quality="invalid", state="unavailable")
    rows = candles.reset_index(drop=True); atr = _atr(rows)
    pivots_low, pivots_high = _pivots(rows)
    pairs = [(low, high) for low in pivots_low for high in pivots_high if low[0] < high[0] and high[1] - low[1] >= atr * minimum_atr]
    pairs += [(low, high) for high in pivots_high for low in pivots_low if high[0] < low[0] and high[1] - low[1] >= atr * minimum_atr]
    if not pairs: return evidence_result(timeframe=timeframe, rejection_reason="No chronologically valid significant dealing range.")
    low, high = max(pairs, key=lambda pair: max(pair[0][0], pair[1][0])); current = float(rows.iloc[-1]["close"]); equilibrium = (low[1] + high[1]) / 2
    result = {"range_id": stable_id("ict-range", {"timeframe": timeframe, "low_time": low[2], "high_time": high[2], "low": low[1], "high": high[1]}), "low": low[1], "high": high[1], "low_time": low[2], "high_time": high[2], "equilibrium": equilibrium, "location": "premium" if current > equilibrium else "discount" if current < equilibrium else "equilibrium", "source_timeframe": timeframe, "created_at": max(low[2], high[2]), "locked": True, "atr_distance": (high[1]-low[1])/atr}
    return evidence_result(result=result, timestamp=result["created_at"], timeframe=timeframe, valid=True, evidence=["Confirmed swing extremes are chronological.", "Range width passes the ATR threshold."])


def _atr(rows):
    previous = rows["close"].shift(); tr = pd.concat([rows["high"]-rows["low"], (rows["high"]-previous).abs(), (rows["low"]-previous).abs()], axis=1).max(axis=1); return float(tr.tail(14).mean())
def _pivots(rows):
    lows=[]; highs=[]
    for i in range(2, len(rows)-2):
        window=rows.iloc[i-2:i+3]; candle=rows.iloc[i]
        if float(candle.low) == float(window.low.min()): lows.append((i,float(candle.low),candle.time.isoformat()))
        if float(candle.high) == float(window.high.max()): highs.append((i,float(candle.high),candle.time.isoformat()))
    return lows, highs
