"""Centralized human-readable translations for internal lifecycle and blocker codes.

Raw codes (e.g. "plan_geometry", "TARGET_SCOPE_MISMATCH") are diagnostic
identifiers, not user-facing text. Anything shown in the decision panel or a
chart tooltip must go through this module; raw codes stay under Diagnostics.
"""
from __future__ import annotations

BLOCKER_TEXT = {
    "history": "Waiting for enough completed candle history to analyze.",
    "h1_structure": "Waiting for a completed H1 directional structure break.",
    "m15_pullback": "Waiting for an M15 pullback against the H1 structure.",
    "m15_location": "Waiting for the M15 pullback to reach a valid location.",
    "m5_displacement_break": "Waiting for a completed M5 displacement and structure break.",
    "m5_retrace": "Waiting for the M5 retracement after the completed structure break.",
    "plan_geometry": "No valid structural target currently belongs to this setup.",
    "chase": "Price has moved too far from the entry to chase.",
    "m15_range_position": "Price is at a hostile extreme of the M15 dealing range.",
}

NEXT_REQUIREMENT_TEXT = {
    "": "Validate stop, target and reward-to-risk.",
    "ENTRY_OR_STOP_MISSING": "Wait for a confirmed entry and stop before a target can be evaluated.",
    "NO_CONFIRMED_SWINGS": "Wait for a confirmed swing to form a structural target.",
    "NO_TARGET_REFERENCES_CREATED": "Wait for a qualifying structural reference to appear.",
    "ALL_TARGETS_WRONG_SIDE": "Wait for a structural target on the profitable side of the entry.",
    "ALL_TARGETS_RR_REJECTED": "Wait for a target that meets the minimum reward-to-risk.",
    "ALL_TARGETS_ALREADY_CONSUMED": "Wait for a fresh, unswept structural target.",
    "ALL_TARGETS_EVENT_INVALIDATED": "Wait for event risk to clear before a target can be selected.",
}


def translate_blocker(code):
    """Human-readable text for a `first_blocking_gate`-style internal code."""
    if not code:
        return None
    return BLOCKER_TEXT.get(code, str(code).replace("_", " ").capitalize() + ".")


def translate_next_requirement(code, *, direction=None, fallback=None):
    """Human-readable text for a `target_trace.first_blocker`-style internal code.

    TARGET_SCOPE_MISMATCH is direction-aware: it names the side the next
    qualifying objective must sit on relative to the proposed entry.
    """
    code = code or ""
    if code == "TARGET_SCOPE_MISMATCH" and direction in {"bullish", "bearish"}:
        side = "above" if direction == "bullish" else "below"
        trade_word = "buy" if direction == "bullish" else "sell"
        return f"Wait for a fresh unswept structural objective {side} the proposed {trade_word} entry."
    if code in NEXT_REQUIREMENT_TEXT:
        return NEXT_REQUIREMENT_TEXT[code]
    if not code:
        return fallback or NEXT_REQUIREMENT_TEXT[""]
    return fallback or (str(code).replace("_", " ").capitalize() + ".")
