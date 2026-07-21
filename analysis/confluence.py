"""Reusable confluence scoring."""

from __future__ import annotations


def score_confluence(
    *,
    trend_aligned: bool,
    structure_clear: bool,
    zone_quality: bool,
    confirmation: bool,
    volatility_health: str,
    risk_reward: float | None,
    session_allowed: bool | None = None,
) -> dict[str, object]:
    """Score reusable analysis factors out of 100."""
    components = {
        "trend_alignment": 20 if trend_aligned else 0,
        "structure_clarity": 20 if structure_clear else 0,
        "pullback_zone_quality": 20 if zone_quality else 0,
        "confirmation_strength": 15 if confirmation else 0,
        "volatility_health": _volatility_points(volatility_health),
        "risk_reward": _rr_points(risk_reward),
        "session_context": 5 if session_allowed else 0,
    }
    score = min(sum(components.values()), 100)

    return {
        "score": score,
        "confidence": confidence_from_score(score),
        "components": components,
    }


def confidence_from_score(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 55:
        return "Medium"
    if score >= 30:
        return "Low"
    return "Waiting"


def _volatility_points(health: str) -> int:
    if health == "Healthy":
        return 10
    if health in {"Quiet", "Hot"}:
        return 5
    return 0


def _rr_points(risk_reward: float | None) -> int:
    if risk_reward is None:
        return 0
    if risk_reward >= 2:
        return 10
    if risk_reward >= 1.5:
        return 7
    if risk_reward >= 1:
        return 4
    return 0
