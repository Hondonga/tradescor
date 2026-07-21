"""Classify range excursions without claiming intentional manipulation."""

from __future__ import annotations

import pandas as pd


def detect_manipulation(candles: pd.DataFrame, accumulation: dict[str, object], liquidity: list[dict[str, object]], *, reclaim_bars: int = 6) -> dict[str, object]:
    rows = candles.reset_index(drop=True); after = rows.iloc[int(accumulation["end_index"]) + 1:]; low, high, atr = float(accumulation["range_low"]), float(accumulation["range_high"]), float(accumulation["atr"]); tolerance = atr * .05
    events = []
    for index, candle in after.iterrows():
        high_excursion = float(candle["high"]) > high + tolerance; low_excursion = float(candle["low"]) < low - tolerance
        if high_excursion: events.append((index, "high", float(candle["high"]), high))
        if low_excursion: events.append((index, "low", float(candle["low"]), low))
    if not events: return _empty("unclear")
    first_index, side, sweep_price, boundary = events[0]; sweep = rows.loc[first_index]; later = rows.iloc[first_index:min(len(rows), first_index + reclaim_bars + 1)]
    inside = later.loc[(later["close"].astype(float) <= high) & (later["close"].astype(float) >= low)]
    reclaimed = not inside.empty; reclaim = inside.iloc[0] if reclaimed else None
    outside_close = float(sweep["close"]) > high if side == "high" else float(sweep["close"]) < low
    outside_series = (later["close"].astype(float) > high) if side == "high" else (later["close"].astype(float) < low)
    acceptance_index = _first_consecutive_index(outside_series, 2)
    accepted = acceptance_index is not None and not reclaimed
    both_sides = len({event[1] for event in events}) > 1
    boundary_event = "accepted_breakout" if accepted else "sweep" if reclaimed else "failed_break" if outside_close else "unclear"
    quality = min(20, 7 + int(reclaimed) * 7 + min(4, round(abs(sweep_price - boundary) / max(atr, 1e-12) * 4))) if boundary_event == "sweep" else 0
    source = next((row for row in liquidity if row["side"] == ("buy_side" if side == "high" else "sell_side")), {})
    acceptance = rows.loc[acceptance_index] if accepted else None
    return {"detected": boundary_event == "sweep", "forming": boundary_event in {"unclear", "failed_break"}, "side": side, "boundary": boundary, "sweep_price": sweep_price, "sweep_time": sweep["time"].isoformat(), "breakout_close": float(acceptance["close"]) if acceptance is not None else None, "breakout_time": acceptance["time"].isoformat() if acceptance is not None else None, "excursion_distance": abs(sweep_price - boundary), "excursion_atr": abs(sweep_price - boundary) / max(atr, 1e-12), "reclaimed_range": reclaimed, "reclaim_time": reclaim["time"].isoformat() if reclaimed else None, "bars_to_reclaim": int(reclaim.name - first_index) if reclaimed else None, "close_back_inside": reclaimed, "liquidity_source": source.get("type", ""), "quality_score": quality, "boundary_event": boundary_event, "both_sides_swept": both_sides}


def _empty(boundary_event): return {"detected": False, "forming": False, "side": None, "boundary": None, "sweep_price": None, "sweep_time": None, "breakout_close": None, "breakout_time": None, "excursion_distance": None, "excursion_atr": None, "reclaimed_range": False, "reclaim_time": None, "bars_to_reclaim": None, "close_back_inside": False, "liquidity_source": "", "quality_score": 0, "boundary_event": boundary_event, "both_sides_swept": False}
def _consecutive(mask: pd.Series, count: int) -> bool:
    run = 0
    for value in mask.tolist():
        run = run + 1 if value else 0
        if run >= count: return True
    return False

def _first_consecutive_index(mask: pd.Series, count: int) -> object | None:
    run = 0
    for index, value in mask.items():
        run = run + 1 if value else 0
        if run >= count: return index
    return None
