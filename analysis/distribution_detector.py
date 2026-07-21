"""Volatility-normalized distribution and structure-break detection."""

from __future__ import annotations

import pandas as pd


def detect_distribution(candles: pd.DataFrame, accumulation: dict[str, object], manipulation: dict[str, object]) -> dict[str, object]:
    if not manipulation.get("detected") or not manipulation.get("reclaim_time"): return _empty()
    rows = candles.reset_index(drop=True); times = pd.to_datetime(rows["time"], utc=True); reclaim = pd.Timestamp(manipulation["reclaim_time"]); reclaim = reclaim.tz_localize("UTC") if reclaim.tzinfo is None else reclaim.tz_convert("UTC")
    direction = "up" if manipulation["side"] == "low" else "down"; atr = float(accumulation["atr"])
    for index in range(4, len(rows)):
        if times.iloc[index] <= reclaim: continue
        candle = rows.iloc[index]; body = abs(float(candle["close"] - candle["open"])); prior = rows.iloc[index-4:index]
        directional = float(candle["close"]) > float(candle["open"]) if direction == "up" else float(candle["close"]) < float(candle["open"])
        displacement = directional and body >= atr * 1.1
        break_price = float(prior["high"].max()) if direction == "up" else float(prior["low"].min()); structure_break = float(candle["close"]) > break_price if direction == "up" else float(candle["close"]) < break_price
        if displacement:
            fvg = _fvg(rows, index, direction)
            return {"detected": bool(structure_break), "forming": True, "direction": direction, "displacement_start": candle["time"].isoformat(), "displacement_end": candle["time"].isoformat(), "structure_break_price": break_price if structure_break else None, "structure_break_time": candle["time"].isoformat() if structure_break else None, "fvg": fvg, "expansion_atr": body / max(atr, 1e-12), "quality_score": min(20, 9 + int(structure_break) * 7 + int(fvg is not None) * 4)}
    return _empty()


def _fvg(rows, index, direction):
    if index < 2: return None
    first, third = rows.iloc[index-2], rows.iloc[index]
    if direction == "up" and float(third["low"]) > float(first["high"]): return {"low": float(first["high"]), "high": float(third["low"]), "formation_time": third["time"].isoformat(), "direction": "bullish"}
    if direction == "down" and float(third["high"]) < float(first["low"]): return {"low": float(third["high"]), "high": float(first["low"]), "formation_time": third["time"].isoformat(), "direction": "bearish"}
    return None
def _empty(): return {"detected": False, "forming": False, "direction": None, "displacement_start": None, "displacement_end": None, "structure_break_price": None, "structure_break_time": None, "fvg": None, "expansion_atr": None, "quality_score": 0}
