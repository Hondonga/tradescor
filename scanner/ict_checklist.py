"""Pass/fail ICT checklist and authoritative setup state."""

from __future__ import annotations


ICT_STATES = {
    "NO_TRADE",
    "WAITING_FOR_KILL_ZONE",
    "WAITING_FOR_LIQUIDITY_SWEEP",
    "WAITING_FOR_CHOCH",
    "WAITING_FOR_FVG_OR_OB",
    "WAITING_FOR_OTE",
    "CONFIRMED_WAITING_FOR_ENTRY",
    "ENTRY_READY",
    "TRADE_ACTIVE",
    "INVALIDATED",
}


def build_ict_checklist(
    *,
    htf_bias_confirmed: bool,
    kill_zone_active: bool,
    liquidity_pool_identified: bool,
    liquidity_swept: bool,
    choch_confirmed: bool,
    fvg_present: bool,
    order_block_present: bool,
    order_block_valid: bool,
    ote_available: bool,
    ote_aligned: bool,
    dxy_status: str,
    news_enabled: bool,
    news_restricted: bool,
    risk_reward: float | None,
) -> dict[str, str]:
    """Return explicit ICT pass/fail/waiting statuses."""
    return {
        "htf_bias": "pass" if htf_bias_confirmed else "fail",
        "kill_zone": "pass" if kill_zone_active else "fail",
        "liquidity_pool": "pass" if liquidity_pool_identified else "waiting",
        "liquidity_swept": "pass" if liquidity_swept else "waiting",
        "choch": "pass" if choch_confirmed else "waiting",
        "fvg": "pass" if fvg_present else "waiting",
        "ob_valid": "pass" if order_block_valid else "fail" if order_block_present else "waiting",
        "ote": "pass" if ote_aligned else "waiting" if ote_available else "unknown",
        "dxy": _dxy_check(dxy_status),
        "news": "fail" if news_restricted else "pass" if news_enabled else "unknown",
        "risk_reward": "pass" if isinstance(risk_reward, (int, float)) and risk_reward >= 1.5 else "fail" if isinstance(risk_reward, (int, float)) else "waiting",
    }


def classify_ict_state(
    checklist: dict[str, str],
    *,
    invalidated: bool = False,
    trade_active: bool = False,
) -> str:
    """Return one state from the strict ICT progression."""
    if invalidated:
        return "INVALIDATED"
    if trade_active:
        return "TRADE_ACTIVE"
    if checklist.get("htf_bias") != "pass":
        return "NO_TRADE"
    if checklist.get("news") == "fail" or checklist.get("dxy") == "fail":
        return "NO_TRADE"
    if checklist.get("kill_zone") != "pass":
        return "WAITING_FOR_KILL_ZONE"
    if checklist.get("liquidity_pool") != "pass" or checklist.get("liquidity_swept") != "pass":
        return "WAITING_FOR_LIQUIDITY_SWEEP"
    if checklist.get("choch") != "pass":
        return "WAITING_FOR_CHOCH"
    if checklist.get("fvg") != "pass" and checklist.get("ob_valid") != "pass":
        return "WAITING_FOR_FVG_OR_OB"
    if checklist.get("ote") != "pass":
        return "WAITING_FOR_OTE"
    if checklist.get("risk_reward") != "pass":
        return "NO_TRADE"
    return "ENTRY_READY"


def next_ict_action(state: str, checklist: dict[str, str], choch_level: float | None = None) -> str:
    actions = {
        "NO_TRADE": "Stand aside until direction, confirmation, and trade quality align.",
        "WAITING_FOR_KILL_ZONE": "Wait for the London or New York Kill Zone before considering an entry.",
        "WAITING_FOR_LIQUIDITY_SWEEP": "Wait for price to take the directional liquidity pool and close back inside the range.",
        "WAITING_FOR_CHOCH": f"Wait for price to close beyond the CHoCH level at {choch_level:.6f}." if choch_level is not None else "Wait for a clear CHoCH after the liquidity sweep.",
        "WAITING_FOR_FVG_OR_OB": "Wait for a directional FVG or valid order block reaction.",
        "WAITING_FOR_OTE": "Wait for price to retrace into the 62%-79% OTE zone.",
        "CONFIRMED_WAITING_FOR_ENTRY": "Confirmation is complete. Wait for price to return to the active ICT entry zone.",
        "ENTRY_READY": "All ICT confirmations pass. Wait for price to enter the confirmed entry zone.",
        "TRADE_ACTIVE": "Manage the active trade against its confirmed invalidation and objectives.",
        "INVALIDATED": "The ICT sequence is invalidated. Wait for a fresh liquidity sweep.",
    }
    return actions.get(state, "Wait for the next ICT confirmation.")


def _dxy_check(status: str) -> str:
    text = str(status or "").lower()
    if text == "confirms":
        return "pass"
    if text == "conflicts":
        return "fail"
    return "unknown"
