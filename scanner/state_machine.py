"""Strategy state machine for the current ICT setup."""

from __future__ import annotations


ICT_STATE_ORDER = {
    "WATCHING": 0,
    "LIQUIDITY_SWEEP": 1,
    "WAITING_MSS": 2,
    "WAITING_IFVG": 3,
    "ENTRY_READY": 4,
    "TRADE_ACTIVE": 5,
    "TRADE_COMPLETE": 6,
    "INVALIDATED": 99,
}

ICT_STATE_LABELS = {
    "WATCHING": "Watching Market",
    "LIQUIDITY_SWEEP": "Liquidity Sweep",
    "WAITING_MSS": "Waiting for MSS",
    "WAITING_IFVG": "Waiting for IFVG",
    "ENTRY_READY": "Entry Ready",
    "TRADE_ACTIVE": "Trade Active",
    "TRADE_COMPLETE": "Trade Complete",
    "INVALIDATED": "Invalidated",
}

STATES = {
    "NO SETUP": {"step": 0, "percent": 0},
    "HTF CONTEXT FOUND": {"step": 1, "percent": 20},
    "LIQUIDITY SWEPT": {"step": 2, "percent": 40},
    "WAITING FOR MSS": {"step": 3, "percent": 55},
    "WAITING FOR IFVG": {"step": 4, "percent": 75},
    "VALID SETUP": {"step": 5, "percent": 100},
    "INVALIDATED": {"step": 6, "percent": 0},
}


def classify_ict_state(
    *,
    htf_fvg: bool,
    liquidity_sweep: bool,
    mss: bool,
    ifvg: bool,
    invalidated: bool,
    trade_active: bool = False,
    tp2_reached: bool = False,
) -> dict[str, object]:
    """Return the single authoritative ICT state for UI and overlay gating."""
    if invalidated:
        key = "INVALIDATED"
    elif tp2_reached:
        key = "TRADE_COMPLETE"
    elif trade_active:
        key = "TRADE_ACTIVE"
    elif ifvg:
        key = "ENTRY_READY"
    elif mss:
        key = "WAITING_IFVG"
    elif liquidity_sweep:
        key = "WAITING_MSS" if htf_fvg else "LIQUIDITY_SWEEP"
    else:
        key = "WATCHING"

    return {
        "key": key,
        "label": ICT_STATE_LABELS[key],
        "order": ICT_STATE_ORDER[key],
        "is_terminal": key in {"INVALIDATED", "TRADE_COMPLETE"},
    }


def state_at_least(state: dict[str, object], required_key: str) -> bool:
    """Return True when a non-terminal state has reached a required stage."""
    if state.get("key") == "INVALIDATED":
        return False

    return int(state.get("order", 0)) >= ICT_STATE_ORDER[required_key]


def classify_setup(
    checklist: dict[str, bool],
    invalidated: bool,
) -> tuple[str, dict[str, object], str]:
    """Classify the setup into one clear state and next action."""
    if invalidated:
        return _state("INVALIDATED", "Setup invalidated. Wait for a fresh sweep and structure sequence.")

    if not checklist["htf_fvg"] and not checklist["liquidity_sweep"]:
        return _state("NO SETUP", "Wait for HTF context and a liquidity sweep.")

    if checklist["htf_fvg"] and not checklist["liquidity_sweep"]:
        return _state("HTF CONTEXT FOUND", "Wait for price to sweep liquidity.")

    if checklist["liquidity_sweep"] and not checklist["mss"]:
        if checklist["htf_fvg"]:
            return _state("WAITING FOR MSS", "Wait for price to break market structure.")
        return _state("LIQUIDITY SWEPT", "Wait for HTF FVG context and a market structure shift.")

    if checklist["mss"] and not checklist["ifvg"]:
        return _state("WAITING FOR IFVG", "Wait for IFVG retest.")

    if (
        checklist["htf_fvg"]
        and checklist["liquidity_sweep"]
        and checklist["mss"]
        and checklist["ifvg"]
        and checklist["displacement"]
        and checklist["session"]
        and checklist["risk_reward"]
    ):
        return _state("VALID SETUP", "Setup valid based on current rules.")

    if checklist["ifvg"]:
        return _state("WAITING FOR IFVG", "No valid trade yet. Wait for session, displacement, and acceptable risk/reward.")

    return _state("NO SETUP", "Wait for a complete FVG, sweep, MSS, and IFVG sequence.")


def _state(label: str, next_confirmation: str) -> tuple[str, dict[str, object], str]:
    readiness = STATES[label].copy()
    readiness["label"] = label
    return label, readiness, next_confirmation
