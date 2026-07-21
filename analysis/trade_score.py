"""User-facing trade score rules.

Setup quality answers "did the pattern form?" Trade score answers "is this a
trade worth acting on?" The Scanner card should use trade score.
"""

from __future__ import annotations

from analysis.confluence import confidence_from_score


def build_trade_score(
    *,
    setup_quality: object,
    trade_quality: object,
    trade_decision: object,
    levels_mode: object,
    state: object = "",
    objective_plan: dict[str, object] | None = None,
    trade_metrics: dict[str, object] | None = None,
    entry_timing: dict[str, object] | None = None,
    setup_stage: object = "",
) -> dict[str, object]:
    """Return a capped score that reflects trade quality, not only setup quality."""
    setup_score = _clamp(setup_quality)
    objective_score = _clamp(trade_quality)
    decision = str(trade_decision or "PENDING").upper()
    mode = str(levels_mode or "hidden").lower()
    normalized_state = str(state or "").upper()
    objective_plan = objective_plan or {}
    trade_metrics = trade_metrics or {}
    entry_timing = entry_timing or {}
    stage = str(setup_stage or "").replace("_", " ").upper()

    cap_reason = ""
    score = setup_score

    timing_status = str(entry_timing.get("entry_timing_status") or "").lower()
    timing_available = bool(entry_timing.get("available"))
    if any(token in normalized_state for token in ("FAILED", "INVALIDATED", "NO_TRADE")):
        score = min(setup_score, 25)
        cap_reason = "The setup state is not tradeable."
    elif timing_available and timing_status in {"invalid", "missed"}:
        score = min(setup_score, 25)
        cap_reason = "Entry timing invalidated the setup."
    elif timing_available and timing_status == "too_late":
        score = min(setup_score, 45)
        cap_reason = "Price is too far from the entry area."
    elif timing_available and timing_status == "extended":
        score = min(setup_score, 64)
        cap_reason = "Price has moved away from the entry area."
    elif decision == "ACCEPT" and mode == "final":
        score = round((setup_score * 0.65) + ((_objective_or_setup(objective_score, setup_score)) * 0.35))
    elif _has_no_acceptable_target(decision, objective_plan, trade_metrics):
        score = min(setup_score, _usable_rejected_score(objective_score, 55))
        cap_reason = "No acceptable target is available."
    elif _has_weak_reward(decision, objective_plan, trade_metrics):
        score = min(setup_score, _usable_rejected_score(objective_score, 64))
        cap_reason = "Reward is too small compared to risk."
    elif decision == "REJECT":
        score = min(setup_score, _usable_rejected_score(objective_score, 49))
        cap_reason = "Trade quality rejected the setup."

    score = _clamp(score)
    valid_rr = _has_acceptable_rr(decision, objective_plan, trade_metrics)
    if stage == "SETUP CONFIRMED" and not valid_rr:
        score = min(score, 64)
        cap_reason = "Confirmation is too late for a clean entry or no acceptable target remains."
    stage_cap = _stage_cap(stage)
    if stage_cap is not None and score > stage_cap:
        score = stage_cap
        cap_reason = f"Setup readiness is capped while the stage is {stage.title()}."
    return {
        "score": score,
        "confidence": _stage_confidence(stage, score, valid_rr),
        "cap_reason": cap_reason,
        "setup_quality": setup_score,
        "trade_quality": objective_score,
    }


def _stage_cap(stage: str) -> int | None:
    caps = {
        "DIRECTION ONLY": 40,
        "DIRECTION AND ZONE IDENTIFIED": 60,
        "WATCHING AREA": 60,
        "IN SETUP AREA": 70,
        "REACTION FORMING": 80,
        "CONFIRMATION FORMING": 80,
        "SETUP CONFIRMED": 90,
    }
    return caps.get(stage)


def _has_acceptable_rr(
    decision: str,
    objective_plan: dict[str, object],
    trade_metrics: dict[str, object],
) -> bool:
    if decision != "ACCEPT":
        return False
    values = [_target_rr(trade_metrics.get("tp1")), _target_rr(trade_metrics.get("tp2"))]
    if any(value is not None and value >= 1.0 for value in values):
        return True
    try:
        return float(objective_plan.get("minimum_rr", 0) or 0) >= 1.0 and bool(objective_plan.get("accepted"))
    except (TypeError, ValueError):
        return False


def _stage_confidence(stage: str, score: int, valid_rr: bool) -> str:
    if stage == "WATCHING AREA":
        return "Medium" if score >= 55 else "Low"
    if stage in {"IN SETUP AREA", "REACTION FORMING", "CONFIRMATION FORMING"}:
        return "Medium"
    if stage == "SETUP CONFIRMED":
        return "High" if valid_rr else "Medium"
    return confidence_from_score(score)


def _has_no_acceptable_target(
    decision: str,
    objective_plan: dict[str, object],
    trade_metrics: dict[str, object],
) -> bool:
    text = _combined_text(objective_plan, trade_metrics)
    if "no acceptable target" in text:
        return True
    if "no directional liquidity objective" in text:
        return True
    if "all directional liquidity objectives" in text:
        return True
    if decision == "REJECT" and "best available objective offers only" in text:
        return True

    tp1_rr = _target_rr(trade_metrics.get("tp1"))
    tp2_rr = _target_rr(trade_metrics.get("tp2"))
    return (
        decision == "REJECT"
        and (tp1_rr is None or tp1_rr < 1.0)
        and (tp2_rr is None or tp2_rr < 1.0)
    )


def _has_weak_reward(
    decision: str,
    objective_plan: dict[str, object],
    trade_metrics: dict[str, object],
) -> bool:
    text = _combined_text(objective_plan, trade_metrics)
    if any(phrase in text for phrase in ("weak reward", "reward is too weak", "risk/reward", "requires at least")):
        return True
    tp1_rr = _target_rr(trade_metrics.get("tp1"))
    return tp1_rr is not None and tp1_rr < 1.0 or decision == "REJECT" and "reward" in text


def _combined_text(
    objective_plan: dict[str, object],
    trade_metrics: dict[str, object],
) -> str:
    warnings = trade_metrics.get("warnings") or []
    return " ".join(
        [
            str(objective_plan.get("reason", "")),
            str(objective_plan.get("summary", "")),
            " ".join(str(warning) for warning in warnings if warning),
        ]
    ).lower()


def _objective_or_setup(objective_score: int, setup_score: int) -> int:
    return objective_score if objective_score > 0 else setup_score


def _usable_rejected_score(objective_score: int, cap: int) -> int:
    floor = 35 if cap <= 55 else 45
    return max(floor, min(cap, objective_score if objective_score > 0 else cap))


def _target_rr(target: object) -> float | None:
    if not isinstance(target, dict):
        return None
    try:
        return float(target.get("risk_reward"))
    except (TypeError, ValueError):
        return None


def _clamp(value: object) -> int:
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, int(number)))
