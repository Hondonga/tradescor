"""Phase 7 Part 7: corrected control methodology for future hypothesis
evaluation. These are synthetic proofs of the methodology's properties --
they never touch the frozen Phase 5 dataset or its results.
"""
import numpy as np
import pytest

from validation.strategy_feasibility.control_methodology_v2 import (
    build_bullish_and_bearish_synthetic_controls,
    deterministic_random_direction_permutations,
    finite_sample_p_value,
    geometry_control_v2,
)


def test_geometry_only_control_is_not_identical_to_the_real_arm():
    rng = np.random.default_rng(1)
    same = rng.normal(0.1, 1.0, size=2000)
    opposite = rng.normal(-0.1, 1.0, size=2000)
    geometry = geometry_control_v2(same, opposite)
    assert not np.array_equal(geometry, same)
    # Not just element-wise different -- genuinely not the same distribution.
    assert abs(geometry.mean() - same.mean()) > 1e-6


def test_geometry_only_control_never_collapses_even_when_directions_partially_agree():
    # Phase 5's degeneracy occurred whenever a coin-flip reassignment happened
    # to match the real direction (~50% of pairs), making that half of the
    # pairs byte-identical to the real trade. geometry_control_v2 instead
    # always averages two independently realized outcomes -- reproduce the
    # adversarial case (half of "opposite" outcomes coincidentally equal to
    # "same") and confirm the arm still isn't collapsed to the same arm.
    rng = np.random.default_rng(2)
    same = rng.normal(0.2, 1.0, size=1000)
    opposite = same.copy()
    opposite[::2] = rng.normal(-0.2, 1.0, size=500)  # only half actually differ
    geometry = geometry_control_v2(same, opposite)
    assert not np.array_equal(geometry, same)


def test_geometry_only_null_remains_centered_around_zero_when_there_is_no_real_edge():
    # No genuine directional edge in this synthetic universe: same-direction
    # and opposite-direction outcomes are both drawn from the same
    # zero-mean distribution. The geometry-only control should also be
    # centered near zero -- it must not manufacture an edge out of noise.
    rng = np.random.default_rng(3)
    same = rng.normal(0.0, 1.0, size=5000)
    opposite = rng.normal(0.0, 1.0, size=5000)
    geometry = geometry_control_v2(same, opposite)
    assert abs(geometry.mean()) < 0.05


def test_bullish_and_bearish_genuine_edges_beat_geometry_only():
    rng = np.random.default_rng(4)
    n = 4000
    # Bullish universe: real edge sits with the same-direction (long) arm.
    same_bullish = rng.normal(0.30, 1.0, size=n)
    opposite_bullish = rng.normal(-0.30, 1.0, size=n)
    geometry_bullish = geometry_control_v2(same_bullish, opposite_bullish)
    assert same_bullish.mean() > geometry_bullish.mean()

    # Bearish universe: mirror image -- real edge sits with the same-direction
    # (short) arm this time. The control construction must be symmetric.
    same_bearish = rng.normal(0.30, 1.0, size=n)
    opposite_bearish = rng.normal(-0.30, 1.0, size=n)
    geometry_bearish = geometry_control_v2(same_bearish, opposite_bearish)
    assert same_bearish.mean() > geometry_bearish.mean()
    assert abs(geometry_bullish.mean()) < 0.05 and abs(geometry_bearish.mean()) < 0.05


def test_symmetric_geometry_is_genuinely_mirrored_for_bullish_and_bearish():
    bullish, bearish = build_bullish_and_bearish_synthetic_controls(entry=100.0, atr=2.0, risk_atr=1.0, rr=1.5)
    assert bullish.stop < bullish.entry < bullish.target
    assert bearish.target < bearish.entry < bearish.stop
    assert bullish.risk == bearish.risk
    assert abs((bullish.target - bullish.entry) - (bearish.entry - bearish.target)) < 1e-9


def test_empirical_p_value_is_never_exactly_zero():
    rng = np.random.default_rng(5)
    permutations = rng.normal(0.0, 1.0, size=500)
    observed = 100.0  # far larger than any permutation -> zero exceedances
    p = finite_sample_p_value(observed, permutations, alternative="greater")
    assert p > 0.0
    assert round(p, 6) == round(1 / 501, 6)
    assert round(p, 3) == 0.002


def test_empirical_p_value_matches_the_required_500_permutation_example():
    permutations = np.full(500, -1.0)  # zero exceedances by construction
    p = finite_sample_p_value(0.0, permutations, alternative="greater")
    assert round(p, 6) == round(0.0019960079840319361, 6)


def test_empirical_p_value_is_never_exactly_zero_even_with_many_exceedances():
    rng = np.random.default_rng(6)
    permutations = rng.normal(5.0, 1.0, size=1000)
    p = finite_sample_p_value(0.0, permutations, alternative="greater")
    assert p > 0.0


def test_finite_sample_p_value_rejects_empty_permutation_set():
    with pytest.raises(ValueError):
        finite_sample_p_value(1.0, np.array([]))


def test_deterministic_random_direction_permutations_are_reproducible_and_at_least_500():
    matrix_a = deterministic_random_direction_permutations(n_events=326, n_permutations=1000, seed=99)
    matrix_b = deterministic_random_direction_permutations(n_events=326, n_permutations=1000, seed=99)
    assert np.array_equal(matrix_a, matrix_b)
    assert matrix_a.shape == (1000, 326)
    assert set(np.unique(matrix_a).tolist()) <= {-1, 1}
