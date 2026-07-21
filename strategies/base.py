"""Base helpers for strategy modules."""

from __future__ import annotations

from analysis.confluence import confidence_from_score

STRATEGY_VERSIONS = {"ict_2022": "ict_2022_v2", "supply_demand": "supply_demand_v1", "breakout_retest": "breakout_retest_v1"}


def empty_candidate(strategy_id: str) -> dict[str, object]:
    """Return the frozen common candidate schema used by Auto research."""
    return {"strategy_id": strategy_id, "strategy_version": STRATEGY_VERSIONS[strategy_id], "eligible": False, "eligibility_score": 0, "eligibility_reasons": [], "rejection_reasons": [], "direction": "neutral", "setup_type": "", "setup_timeframe": "M15", "execution_timeframe": "M5", "stage": "not_eligible", "zone": {"low": None, "high": None, "origin_time": None, "type": "", "freshness": None, "touch_count": 0}, "confirmation_requirements": [], "m5_trigger": None, "invalidation": None, "targets": [], "structural_quality": 0, "location_quality": 0, "confirmation_quality": 0, "target_quality": 0, "projected_rr": None, "candidate_score": 0, "present_quality_score": 0, "evidence_multiplier": 0.70, "confidence": "low", "status": "not_eligible"}


def research_candidate(context: dict[str, object], strategy_id: str) -> dict[str, object]:
    return next((row for row in context.get("candidates", []) if row.get("strategy_id") == strategy_id), empty_candidate(strategy_id))


def research_eligible(context: dict[str, object], strategy_id: str) -> dict[str, object]:
    candidate = research_candidate(context, strategy_id)
    return {"eligible": bool(candidate["eligible"]), "score": candidate["eligibility_score"], "reasons": candidate["eligibility_reasons"], "rejections": candidate["rejection_reasons"]}


def research_explain(candidate: dict[str, object]) -> str:
    reasons = candidate.get("eligibility_reasons") or candidate.get("rejection_reasons") or ["No reproducible strategy context is available."]
    return " ".join(str(reason) for reason in reasons)


EMPTY_LEVELS = {
    "entry_zone": None,
    "stop_loss": None,
    "tp1": None,
    "tp2": None,
    "rr1": None,
    "rr2": None,
}

STANDARD_LEVELS = {
    "important_zone": None,
    "trigger_level": None,
    "invalidation": None,
    **EMPTY_LEVELS,
}


def make_strategy_result(
    *,
    strategy_name: str,
    bias: str,
    state: str,
    score: int,
    market_story: str,
    next_trigger: str,
    levels_mode: str = "hidden",
    levels: dict[str, object] | None = None,
    overlays: dict[str, object] | None = None,
    progress: list[dict[str, object]] | None = None,
    why: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Return the standardized strategy result shape."""
    clean_score = max(0, min(100, int(score)))

    trade_status = _trade_status(state, levels_mode)
    return {
        "strategy_name": strategy_name,
        "bias": bias,
        "state": state,
        "trade_status": trade_status,
        "market_clarity": _market_clarity(clean_score),
        "trade_readiness": "Ready" if trade_status in {"Entry Ready", "Trade Active"} else "Building" if trade_status in {"Wait", "Almost Ready"} else "Not Ready",
        "score": clean_score,
        "confidence": confidence_from_score(clean_score),
        "market_story": market_story,
        "next_action": next_trigger,
        "next_trigger": next_trigger,
        "levels_mode": levels_mode,
        "levels": {**STANDARD_LEVELS, **(levels or {})},
        "overlays": overlays or {},
        "progress": progress or [],
        "why": why or [],
        "trader_answers": {},
        "timeline": [],
        "setup_state": {},
        "validation": {"valid": True, "warnings": []},
    }


def _trade_status(state: str, levels_mode: str) -> str:
    if state in {"TRADE_ACTIVE"}:
        return "Trade Active"
    if state in {"INVALIDATED", "FAILED_BREAKOUT"}:
        return "Invalidated"
    if levels_mode == "final" and state == "ENTRY_READY":
        return "Entry Ready"
    if state in {"NO_SETUP", "NO_TRADE"}:
        return "No Trade"
    if state in {"WAITING_FOR_CONFIRMATION", "WAITING_FOR_REJECTION", "RETEST_ACTIVE", "PRICE_IN_ZONE"}:
        return "Almost Ready"
    return "Wait"


def _market_clarity(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def strategy_bias_to_legacy(bias: str) -> str:
    if bias == "Bullish":
        return "LONG"
    if bias == "Bearish":
        return "SHORT"
    return "NEUTRAL"


def legacy_bias_to_strategy(bias: str) -> str:
    if bias == "LONG":
        return "Bullish"
    if bias == "SHORT":
        return "Bearish"
    return "Neutral"


def risk_reward(direction: str, entry: float, stop: float | None, target: float | None) -> float | None:
    if stop is None or target is None:
        return None

    if direction not in {"Bullish", "Bearish"}:
        return None

    risk = abs(entry - stop)
    reward = target - entry if direction == "Bullish" else entry - target

    if risk <= 0 or reward <= 0:
        return None

    return round(reward / risk, 2)
