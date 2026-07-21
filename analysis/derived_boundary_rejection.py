"""Completed-candle rejection evidence at an immutable range boundary."""
from __future__ import annotations
import pandas as pd

def detect_boundary_rejection(candles, locked_range, side, interaction_time=None, atr=None):
    rows = candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows: rows = rows[rows.complete.astype(bool)]
    base = {"side": side, "direction": "bullish" if side == "lower" else "bearish", "type":"none", "boundary":None,
            "interaction_started_at": None, "confirmed_at": None, "complete":False, "interaction_time": None,
            "rejection_time": None, "rejection_extreme": None, "strength": 0.0, "valid": False,
            "event_type": "UNRESOLVED", "evidence": [], "rejection_reasons": []}
    if not locked_range or rows.empty:
        return {**base, "rejection_reasons": ["A locked range and completed M5 candles are required."]}
    boundary = float(locked_range["low" if side == "lower" else "high"])
    tolerance = max(float(atr or 0) * .08, abs(locked_range["high"]-locked_range["low"]) * .015)
    touched = rows[(rows.low <= boundary+tolerance) & (rows.high >= boundary-tolerance)]
    if interaction_time is not None and "time" in touched: touched = touched[touched.time >= pd.Timestamp(interaction_time)]
    if touched.empty: return {**base, "rejection_reasons": ["Price has not interacted with this boundary."]}
    row = touched.iloc[-1]; idx = rows.index.get_loc(row.name); after = rows.iloc[idx+1:idx+4]
    accepted = float(row.close) < boundary-tolerance if side == "lower" else float(row.close) > boundary+tolerance
    wick = float(row.low) < boundary and float(row.close) >= boundary if side == "lower" else float(row.high) > boundary and float(row.close) <= boundary
    follow = bool((after.close > float(row.high)).any()) if side == "lower" and len(after) else bool((after.close < float(row.low)).any()) if len(after) else False
    valid = bool(wick and follow and not accepted); strength = .75 if valid else .4 if wick else 0.0
    return {**base, "boundary":boundary,"interaction_started_at":_time(row),"confirmed_at":_time(after.iloc[-1]) if valid else None,"complete":bool(len(after)),"type":"wick_rejection" if wick else "none", "interaction_time": _time(row), "rejection_time": _time(after.iloc[-1]) if valid else None,
            "rejection_extreme": float(row.low if side == "lower" else row.high), "strength": strength,
            "valid": valid, "event_type": "VALID_REJECTION" if valid else "ACCEPTED_BREAKOUT" if accepted else "WICK_ONLY" if wick else "NO_REACTION",
            "evidence": ["Boundary wick closed back inside and completed follow-through displaced away."] if valid else [],
            "rejection_reasons": [] if valid else ["A completed rejection and follow-through are required."]}

def _time(row):
    value=row.get("time"); return value.isoformat() if hasattr(value,"isoformat") else str(value)
