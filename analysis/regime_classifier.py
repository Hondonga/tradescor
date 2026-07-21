"""Deterministic multi-timeframe market-regime classification."""

from __future__ import annotations


def classify_regime(features: dict[str, object]) -> dict[str, object]:
    frames = features.get("timeframes") or {}
    if not all(_valid(frames.get(tf, {}), "structure_direction") for tf in ("D1", "H4", "H1")):
        return {"regime": "UNCLEAR", "confidence": "low", "evidence": [], "contradictions": ["Insufficient completed D1/H4/H1 feature history."]}
    directions = {tf: _value(frames[tf], "structure_direction") for tf in ("D1", "H4", "H1")}
    efficiency = sum(float(_value(frames[tf], "directional_efficiency") or 0) for tf in ("D1", "H4", "H1")) / 3
    h1_compression = bool((_value(frames["H1"], "compression") or {}).get("active")); h1_displacement = _value(frames["H1"], "displacement") or {}
    high_vol = any(_value(frames[tf], "volatility_regime") == "high" and bool(_value(frames[tf], "abnormal_candle")) for tf in ("H4", "H1"))
    contradictions = [f"{tf} is {direction}." for tf, direction in directions.items() if direction != directions["D1"]]
    if high_vol and len(set(directions.values())) > 1: regime = "HIGH_VOLATILITY_DISORDER"
    elif directions["D1"] == directions["H4"] == "bullish" and directions["H1"] == "bearish": regime = "PULLBACK_BULLISH_REGIME"
    elif directions["D1"] == directions["H4"] == "bearish" and directions["H1"] == "bullish": regime = "PULLBACK_BEARISH_REGIME"
    elif directions["D1"] == directions["H4"] == directions["H1"] == "bullish" and efficiency >= .25: regime = "TRENDING_BULLISH"
    elif directions["D1"] == directions["H4"] == directions["H1"] == "bearish" and efficiency >= .25: regime = "TRENDING_BEARISH"
    elif h1_compression: regime = "COMPRESSION"
    elif bool(h1_displacement.get("active")) and ((_value(frames["H1"], "range") or {}).get("position", .5) > 1 or (_value(frames["H1"], "range") or {}).get("position", .5) < 0): regime = "BREAKOUT_EXPANSION"
    elif efficiency < .2: regime = "RANGING"
    elif directions["D1"] != directions["H4"]: regime = "REVERSAL_TRANSITION"
    else: regime = "UNCLEAR"
    confidence = "high" if not contradictions and regime not in {"UNCLEAR", "REVERSAL_TRANSITION"} else "medium" if regime not in {"UNCLEAR", "HIGH_VOLATILITY_DISORDER"} else "low"
    return {"regime": regime, "confidence": confidence, "evidence": [f"D1 {directions['D1']}, H4 {directions['H4']}, H1 {directions['H1']}.", f"Mean directional efficiency {efficiency:.2f}."], "contradictions": contradictions}


def _value(frame: dict[str, object], name: str): return (frame.get(name) or {}).get("value")
def _valid(frame: dict[str, object], name: str) -> bool: return bool((frame.get(name) or {}).get("valid"))
