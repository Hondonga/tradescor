"""Grouped (block) bootstrap.

Individual trades are NOT independent — several can come from the same event,
structural episode, day, or symbol-period block. Bootstrapping single trades
would understate uncertainty. This resamples whole groups so the confidence
interval reflects the real correlation structure.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def grouped_bootstrap_ci(values: np.ndarray, group_labels: np.ndarray,
                         n_boot: int = 3000, seed: int = 1, alpha: float = 0.05) -> dict:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0, "n_groups": 0}
    frame = pd.DataFrame({"v": values, "g": group_labels})
    groups = {k: v["v"].values for k, v in frame.groupby("g")}
    keys = list(groups.keys())
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        picked = rng.choice(keys, size=len(keys), replace=True)
        sample = np.concatenate([groups[k] for k in picked])
        boot_means[b] = sample.mean()
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"mean": float(values.mean()), "median": float(np.median(values)),
            "lo": float(lo), "hi": float(hi), "n": int(len(values)),
            "n_groups": int(len(keys)), "excludes_zero": bool(lo > 0 or hi < 0)}


def paired_diff_ci(values_a: np.ndarray, values_b: np.ndarray, group_labels: np.ndarray,
                   n_boot: int = 3000, seed: int = 2, alpha: float = 0.05) -> dict:
    """CI for the per-event paired difference A - B, resampled by group."""
    diff = np.asarray(values_a, dtype=float) - np.asarray(values_b, dtype=float)
    return grouped_bootstrap_ci(diff, group_labels, n_boot=n_boot, seed=seed, alpha=alpha)
