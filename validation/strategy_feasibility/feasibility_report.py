"""Assemble the report and assign the outcome verdict.

The most positive verdict this harness can ever return is
ELIGIBLE_FOR_FORMAL_WALK_FORWARD. It never returns "production ready".
"""
from __future__ import annotations

from enum import Enum


class Outcome(str, Enum):
    REJECTED_INSUFFICIENT_SAMPLE = "REJECTED_INSUFFICIENT_SAMPLE"
    REJECTED_NO_EDGE_AFTER_COSTS = "REJECTED_NO_EDGE_AFTER_COSTS"
    REJECTED_NO_DIRECTIONAL_EDGE = "REJECTED_NO_DIRECTIONAL_EDGE"
    REJECTED_GEOMETRY_ONLY_EFFECT = "REJECTED_GEOMETRY_ONLY_EFFECT"
    REJECTED_UNSTABLE_ACROSS_SYMBOLS = "REJECTED_UNSTABLE_ACROSS_SYMBOLS"
    REJECTED_UNSTABLE_ACROSS_PERIODS = "REJECTED_UNSTABLE_ACROSS_PERIODS"
    RESEARCH_EXTENSION_REQUIRED = "RESEARCH_EXTENSION_REQUIRED"
    ELIGIBLE_FOR_FORMAL_WALK_FORWARD = "ELIGIBLE_FOR_FORMAL_WALK_FORWARD"


def classify(spec, comparison: dict, stability: dict, n_periods: int) -> tuple[str, list[str]]:
    """Apply the acceptance sequence. First failing gate wins.

    Ordered so that the cheapest / most fundamental disqualifiers are checked
    first (sample, costs), then direction, then geometry attribution, then
    stability, before the single positive verdict.
    """
    reasons = []
    same = comparison["arms"].get("same_direction", {})
    n = same.get("n", 0)
    ci = same.get("ci_grouped", {})

    # 1. sample size
    if n < spec.min_resolved_trades or n_periods < spec.min_independent_periods:
        reasons.append(f"n={n} (<{spec.min_resolved_trades}) or periods={n_periods} (<{spec.min_independent_periods}).")
        return Outcome.REJECTED_INSUFFICIENT_SAMPLE, reasons

    # 2. survive costs / beat zero (grouped CI must exclude zero on the positive side)
    if not (ci.get("lo") is not None and ci["lo"] > 0):
        reasons.append(f"same-direction grouped CI [{ci.get('lo')}, {ci.get('hi')}] does not exclude zero after costs.")
        return Outcome.REJECTED_NO_EDGE_AFTER_COSTS, reasons

    # 3. direction must add value vs paired opposite
    diff = comparison.get("same_minus_opposite", {})
    if not diff.get("excludes_zero", False) or (diff.get("lo") is not None and diff["lo"] <= 0):
        reasons.append(f"same-minus-opposite CI [{diff.get('lo')}, {diff.get('hi')}] spans zero: direction adds nothing.")
        return Outcome.REJECTED_NO_DIRECTIONAL_EDGE, reasons

    # 4. must beat geometry-only (edge is prediction, not selective geometry)
    geo = comparison.get("same_minus_geometry_only", {})
    if not geo.get("excludes_zero", False) or (geo.get("lo") is not None and geo["lo"] <= 0):
        reasons.append("effect not separable from geometry-only baseline.")
        return Outcome.REJECTED_GEOMETRY_ONLY_EFFECT, reasons

    # 5. must also beat random
    rnd = comparison.get("same_minus_random", {})
    if not rnd.get("excludes_zero", False) or (rnd.get("lo") is not None and rnd["lo"] <= 0):
        reasons.append("does not beat random-direction control.")
        return Outcome.REJECTED_NO_DIRECTIONAL_EDGE, reasons

    # 6. symbol stability
    consistency = stability["symbol_consistency"]["symbols_agreeing_%"]
    if consistency < 60.0:
        reasons.append(f"only {consistency}% of symbols agree with pooled sign.")
        return Outcome.REJECTED_UNSTABLE_ACROSS_SYMBOLS, reasons

    # 7. concentration (one symbol or period generating the profit)
    sym_share = stability["symbol_concentration"].get("top_group_profit_share")
    per_share = stability["period_concentration"].get("top_group_profit_share")
    if sym_share is not None and sym_share > spec.max_single_symbol_profit_share:
        reasons.append(f"one symbol contributed {sym_share:.0%} of profit.")
        return Outcome.REJECTED_UNSTABLE_ACROSS_SYMBOLS, reasons
    if per_share is not None and per_share > spec.max_single_period_profit_share:
        reasons.append(f"one period contributed {per_share:.0%} of profit.")
        return Outcome.REJECTED_UNSTABLE_ACROSS_PERIODS, reasons

    reasons.append("Passed all feasibility gates. Not proven — eligible for formal walk-forward only.")
    return Outcome.ELIGIBLE_FOR_FORMAL_WALK_FORWARD, reasons


def build_report(spec, comparison, stability, n_periods) -> dict:
    outcome, reasons = classify(spec, comparison, stability, n_periods)
    return {"experiment_id": spec.experiment_id, "strategy_id": spec.strategy_id,
            "strategy_version": spec.strategy_version, "engine_version": spec.engine_version,
            "parameter_hash": spec.parameter_hash(), "symbols": spec.symbols,
            "outcome": outcome.value, "reasons": reasons,
            "comparison": comparison, "stability": stability,
            "n_independent_periods": n_periods,
            "promotion": "BLOCKED" if outcome != Outcome.ELIGIBLE_FOR_FORMAL_WALK_FORWARD
                         else "ELIGIBLE_FOR_FORMAL_WALK_FORWARD_ONLY"}
