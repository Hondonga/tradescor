"""Summary statistics and control comparisons."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .grouped_resampling import grouped_bootstrap_ci, paired_diff_ci


def trade_summary(net_r: np.ndarray) -> dict:
    net_r = np.asarray(net_r, dtype=float)
    if len(net_r) == 0:
        return {"n": 0}
    wins = net_r[net_r > 0].sum()
    losses = -net_r[net_r < 0].sum()
    equity = np.cumprod(1 + net_r)  # R-multiple compounding proxy for drawdown shape
    peak = np.maximum.accumulate(equity)
    max_dd = float((equity / peak - 1).min())
    return {"n": int(len(net_r)),
            "mean_R": round(float(net_r.mean()), 4),
            "median_R": round(float(np.median(net_r)), 4),
            "total_R": round(float(net_r.sum()), 3),
            "win_rate_%": round(float((net_r > 0).mean() * 100), 1),
            "profit_factor": round(float(wins / losses), 3) if losses > 0 else float("inf"),
            "max_drawdown": round(max_dd, 3)}


def control_comparison(rows: list[dict], grouping_unit: str) -> dict:
    frame = pd.DataFrame(rows)
    group_col = {"event_id": "event_id", "structural_episode": "structural_episode",
                 "day": "day", "symbol_period": "period"}.get(grouping_unit, "event_id")
    groups = frame[group_col].values

    arms = [c for c in ("same_direction", "paired_opposite_direction",
                        "random_direction", "geometry_only") if c in frame]
    out = {"grouping_unit": grouping_unit, "arms": {}}
    for arm in arms:
        vals = frame[arm].values
        s = trade_summary(vals)
        s["ci_grouped"] = grouped_bootstrap_ci(vals, groups)
        out["arms"][arm] = s

    if "same_direction" in frame and "paired_opposite_direction" in frame:
        out["same_minus_opposite"] = paired_diff_ci(
            frame["same_direction"].values, frame["paired_opposite_direction"].values, groups)
    if "same_direction" in frame and "random_direction" in frame:
        out["same_minus_random"] = paired_diff_ci(
            frame["same_direction"].values, frame["random_direction"].values, groups)
    if "same_direction" in frame and "geometry_only" in frame:
        out["same_minus_geometry_only"] = paired_diff_ci(
            frame["same_direction"].values, frame["geometry_only"].values, groups)
    return out
