"""Forward outcome simulation — causal, conservative, no lookahead.

Walks completed candles after the entry bar and resolves the trade at whichever
of stop/target is touched first. Same-bar ambiguity (both touched in one
candle) is resolved stop-first, the conservative choice. If neither resolves
within the window the trade is marked-to-market at the window's last close.
"""
from __future__ import annotations

import pandas as pd

from .symmetric_geometry import Geometry
from .cost_model import cost_in_R


def simulate_outcome(candles: pd.DataFrame, entry_index: int, geo: Geometry,
                     outcome_window: int, cost_model: dict, atr: float) -> dict | None:
    if geo.risk <= 0:
        return None
    fwd = candles.iloc[entry_index + 1: entry_index + 1 + outcome_window]
    if len(fwd) == 0:
        return None
    d = geo.direction
    realized_r = None
    bars_held = 0
    resolution = "window_end"
    for _, row in fwd.iterrows():
        bars_held += 1
        hi, lo = float(row.high), float(row.low)
        if d > 0:
            if lo <= geo.stop:
                realized_r, resolution = -1.0, "stop"; break
            if hi >= geo.target:
                realized_r, resolution = geo.rr, "target"; break
        else:
            if hi >= geo.stop:
                realized_r, resolution = -1.0, "stop"; break
            if lo <= geo.target:
                realized_r, resolution = geo.rr, "target"; break
    if realized_r is None:
        last = float(fwd.close.iloc[-1])
        realized_r = (d * (last - geo.entry)) / geo.risk
    net_r = realized_r - cost_in_R(cost_model, geo.risk, atr)
    return {"realized_r": realized_r, "net_r": net_r, "resolution": resolution, "bars_held": bars_held}
