"""Phase 7 Part 17: the closed set of allowed hypothesis verdicts.

Guards against ever assigning a forbidden positive verdict (PRODUCTION_READY,
LIVE_READY, AUTO_ELIGIBLE, PAPER_ELIGIBLE, CONFIRMED_PROFITABLE,
GUARANTEED_EDGE) to any Phase 7+ research-hypothesis evaluation. The single
maximum positive outcome any hypothesis may ever reach is
ELIGIBLE_FOR_SECOND_INDEPENDENT_REPLICATION -- one promising untouched-history
result is never production evidence.
"""
from __future__ import annotations

ALLOWED_VERDICTS = frozenset({
    "FAILED_CAUSALITY_AUDIT",
    "REJECTED_INSUFFICIENT_UNTOUCHED_HISTORY",
    "REJECTED_INSUFFICIENT_SAMPLE",
    "REJECTED_NO_EDGE_AFTER_COSTS",
    "REJECTED_NO_IMPROVEMENT_OVER_PARENT",
    "REJECTED_NO_DIRECTIONAL_EDGE",
    "REJECTED_GEOMETRY_ONLY_EFFECT",
    "REJECTED_RANDOM_CONTROL",
    "REJECTED_UNSTABLE_ACROSS_FOLDS",
    "REJECTED_UNSTABLE_BY_DIRECTION",
    "REJECTED_EXCESSIVE_DRAWDOWN",
    "RESEARCH_EXTENSION_REQUIRED",
    "RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY",
    "RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_SAMPLE",
    "ELIGIBLE_FOR_SECOND_INDEPENDENT_REPLICATION",
})

MAXIMUM_POSITIVE_VERDICT = "ELIGIBLE_FOR_SECOND_INDEPENDENT_REPLICATION"

FORBIDDEN_VERDICTS = frozenset({
    "PRODUCTION_READY",
    "LIVE_READY",
    "AUTO_ELIGIBLE",
    "PAPER_ELIGIBLE",
    "CONFIRMED_PROFITABLE",
    "GUARANTEED_EDGE",
})


def assign_verdict(verdict: str) -> str:
    """Returns verdict unchanged if it is in the allowed closed set;
    raises ValueError otherwise -- including for every forbidden verdict,
    and for any string that is not literally one of the allowed values."""
    if verdict in FORBIDDEN_VERDICTS:
        raise ValueError(f"{verdict!r} is a forbidden positive verdict and may never be assigned to a Phase 7 hypothesis.")
    if verdict not in ALLOWED_VERDICTS:
        raise ValueError(f"{verdict!r} is not one of the allowed Phase 7 hypothesis verdicts: {sorted(ALLOWED_VERDICTS)}")
    return verdict
