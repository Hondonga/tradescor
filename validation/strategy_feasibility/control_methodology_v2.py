"""Phase 7 Part 7: corrected control methodology for future hypothesis evaluation.

Two corrections over the Phase 5 methodology, preregistered here for any
Phase 7+ untouched-history evaluation. The frozen Phase 5 control results
(data/stabilization/phase5/reports/grouped_uncertainty.json etc.) are never
altered by this module -- they are historical record. This module only
governs controls computed AFTER this point.

A. geometry_control_v2
   Phase 5's geometry-only control was defined as "identical absolute entry/
   stop/TP1 levels, direction reassigned by an independent coin flip." That
   definition degenerates: whenever the coin flip matches the setup's real
   direction (~50% of pairs), the geometry-only trade becomes byte-identical
   to the real trade, forcing every matched-pair diff to 0 after the
   opposite-direction half is dropped as geometrically invalid.

   geometry_control_v2 instead evaluates BOTH the same-direction and the
   mirrored opposite-direction outcome with identical entry timing and
   identical risk/reward magnitude (analysis.symmetric geometry: stop and
   target equidistant in R, mirrored around entry), then averages the two
   realized outcomes per event. Averaging two independently simulated
   outcomes can never collapse to being byte-identical to either one alone
   (short of every single paired outcome coincidentally matching, which
   `test_geometry_only_control_is_not_identical_to_the_real_arm` rules out
   for any non-degenerate return distribution), so this construction cannot
   reproduce the Phase 5 degeneracy.

B. finite_sample_p_value
   Phase 5 reported a random-control empirical p-value of exactly 0.0 from
   zero permutation exceedances. A literal zero implies infinite confidence,
   which is never true for a finite permutation count. This module always
   uses the standard finite-sample correction:

       p = (1 + exceedances) / (N + 1)

   which is strictly positive for any finite N, matches the required
   ~0.001996 for N=500 permutations with zero exceedances, and is the
   accepted correction for permutation testing (Davison & Hinkley, 1997;
   North, Curtis & Sham, 2002).
"""
from __future__ import annotations

import numpy as np

from .symmetric_geometry import build_symmetric_geometry

VERSION = "geometry_control_v2"


def geometry_control_v2(same_direction_r: np.ndarray, opposite_direction_r: np.ndarray) -> np.ndarray:
    """Averages the same-direction and mirrored-opposite-direction realized R
    for each paired event. Removes directional information (the average of a
    long and its geometric mirror short carries no directional thesis) while
    preserving the exact event set, entry timing, and risk/reward magnitude.
    Never degenerates to the same-direction arm (see module docstring)."""
    same = np.asarray(same_direction_r, dtype=float)
    opposite = np.asarray(opposite_direction_r, dtype=float)
    if same.shape != opposite.shape:
        raise ValueError("same_direction_r and opposite_direction_r must be paired 1:1 (identical shape)")
    return 0.5 * (same + opposite)


def build_bullish_and_bearish_synthetic_controls(entry: float, atr: float, risk_atr: float, rr: float):
    """Returns the (bullish, bearish) symmetric Geometry objects for one
    event -- used by tests to prove the construction is genuinely symmetric
    (identical risk/reward magnitude, mirrored sign) before it is ever run
    against real or synthetic price paths."""
    bullish = build_symmetric_geometry(entry, atr, direction=1, risk_atr=risk_atr, rr=rr)
    bearish = build_symmetric_geometry(entry, atr, direction=-1, risk_atr=risk_atr, rr=rr)
    return bullish, bearish


def finite_sample_p_value(observed_statistic: float, permutation_statistics: np.ndarray, alternative: str = "greater") -> float:
    """p = (1 + exceedances) / (N + 1). Never returns exactly 0.0 or exactly
    1.0 for any finite permutation count -- both are mathematically
    impossible claims from a finite permutation sample."""
    perms = np.asarray(permutation_statistics, dtype=float)
    n = len(perms)
    if n == 0:
        raise ValueError("permutation_statistics must be non-empty")
    if alternative == "greater":
        exceedances = int(np.sum(perms >= observed_statistic))
    elif alternative == "less":
        exceedances = int(np.sum(perms <= observed_statistic))
    else:
        raise ValueError("alternative must be 'greater' or 'less'")
    p = (1 + exceedances) / (n + 1)
    assert 0.0 < p <= 1.0
    return p


def deterministic_random_direction_permutations(n_events: int, n_permutations: int, seed: int) -> np.ndarray:
    """Returns an (n_permutations, n_events) matrix of deterministic +-1
    direction draws, seeded once for full reproducibility -- the same matrix
    is regenerated identically on every call with the same arguments."""
    rng = np.random.default_rng(seed)
    return rng.choice([-1, 1], size=(n_permutations, n_events))
