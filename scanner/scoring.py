"""Trade quality scoring."""

from __future__ import annotations


WEIGHTS = {
    "htf_fvg": 15,
    "liquidity_sweep": 20,
    "mss": 20,
    "ifvg": 15,
    "premium_discount": 10,
    "displacement": 10,
    "session": 5,
    "risk_reward": 5,
}

SETUP_WEIGHTS = {key: weight for key, weight in WEIGHTS.items() if key != "risk_reward"}


def score_setup(checklist: dict[str, bool]) -> int:
    """Calculate a score out of 100 from the checklist."""
    return sum(weight for key, weight in WEIGHTS.items() if checklist.get(key))


def score_setup_quality(checklist: dict[str, bool]) -> int:
    """Score technical setup quality independently from target economics."""
    earned = sum(weight for key, weight in SETUP_WEIGHTS.items() if checklist.get(key))
    available = sum(SETUP_WEIGHTS.values())
    return round((earned / available) * 100) if available else 0
