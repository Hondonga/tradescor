"""Hard validation shared by all normalized strategy candidates."""

from __future__ import annotations


def validate_candidate(candidate: dict[str, object]) -> dict[str, object]:
    reasons = list(candidate.get("rejection_reasons") or [])
    direction = candidate.get("direction"); zone = candidate.get("zone") or {}
    if direction not in {"buy", "sell"}: reasons.append("Candidate direction is unavailable.")
    if zone.get("low") is None or zone.get("high") is None or float(zone.get("low") or 0) > float(zone.get("high") or 0): reasons.append("Candidate zone bounds are unavailable or invalid.")
    if candidate.get("execution_timeframe") != "M5": reasons.append("Every candidate must execute on M5.")
    return {"valid": not reasons and bool(candidate.get("eligible")), "rejection_reasons": list(dict.fromkeys(reasons)), "candidate": candidate}
