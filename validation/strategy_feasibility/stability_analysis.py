"""Stability and concentration checks.

A pooled positive must not pass when one symbol or one period generated almost
all of the profit. These functions expose that.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def per_group_expectancy(rows: list[dict], arm: str, group_col: str) -> dict:
    frame = pd.DataFrame(rows)
    result = {}
    for key, sub in frame.groupby(group_col):
        vals = sub[arm].values
        result[str(key)] = {"n": int(len(vals)), "mean_R": round(float(vals.mean()), 4),
                            "total_R": round(float(vals.sum()), 3)}
    return result


def direction_consistency(rows: list[dict], arm: str) -> dict:
    """Fraction of symbols whose mean has the same sign as the pooled mean."""
    frame = pd.DataFrame(rows)
    pooled = frame[arm].mean()
    per_symbol = frame.groupby("symbol")[arm].mean()
    if pooled == 0 or len(per_symbol) == 0:
        agree = 0.0
    else:
        agree = float((np.sign(per_symbol) == np.sign(pooled)).mean())
    return {"pooled_sign": int(np.sign(pooled)),
            "symbols_agreeing_%": round(agree * 100, 1),
            "per_symbol_mean_R": {k: round(float(v), 4) for k, v in per_symbol.items()}}


def profit_concentration(rows: list[dict], arm: str, group_col: str) -> dict:
    """Share of total positive R contributed by the single best group."""
    frame = pd.DataFrame(rows)
    totals = frame.groupby(group_col)[arm].sum()
    positive_total = totals[totals > 0].sum()
    if positive_total <= 0:
        return {"top_group": None, "top_group_profit_share": None, "positive_total_R": 0.0}
    top = totals.idxmax()
    share = float(totals.max() / positive_total)
    return {"top_group": str(top), "top_group_profit_share": round(share, 3),
            "positive_total_R": round(float(positive_total), 3)}
