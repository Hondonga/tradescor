"""Canonical trade direction and user-facing status helpers."""

from __future__ import annotations


BUY_ALIASES = {"buy", "bullish", "long"}
SELL_ALIASES = {"sell", "bearish", "short"}
USER_STATUSES = {
    "READY TO BUY",
    "READY TO SELL",
    "BUY SETUP FORMING",
    "SELL SETUP FORMING",
    "NO CLEAN ENTRY",
}


def normalize_direction(value: object) -> str:
    """Return Buy, Sell, or Neutral without inferring a missing side."""
    normalized = str(value or "").strip().lower().replace("_", " ")
    if normalized in BUY_ALIASES:
        return "Buy"
    if normalized in SELL_ALIASES:
        return "Sell"
    return "Neutral"


def format_user_status(
    *,
    status: object,
    direction: object,
    trade_ready: bool,
    forming: bool = True,
    timing_status: object = "",
    timing_available: bool = False,
    trade_decision: object = "PENDING",
) -> str:
    """Map internal strategy state to one safe action-oriented label."""
    side = normalize_direction(direction)
    internal = str(status or "").strip().upper().replace(" ", "_")
    timing = str(timing_status or "").strip().lower()
    decision = str(trade_decision or "PENDING").strip().upper()
    blocked = (
        (timing_available and timing in {"too_late", "missed", "invalid"})
        or decision == "REJECT"
        or any(token in internal for token in ("NO_TRADE", "INVALID", "FAILED"))
    )
    if blocked or side == "Neutral":
        return "NO CLEAN ENTRY"
    if trade_ready:
        return "READY TO BUY" if side == "Buy" else "READY TO SELL"
    if forming:
        return "BUY SETUP FORMING" if side == "Buy" else "SELL SETUP FORMING"
    return "NO CLEAN ENTRY"


def directional_geometry_warnings(
    direction: object,
    levels: dict[str, object] | None,
) -> list[str]:
    """Validate that stop and target geometry agrees with trade direction."""
    levels = levels or {}
    entry = _entry_price(levels.get("entry_zone"))
    stop = _number(levels.get("stop_loss", levels.get("invalidation")))
    targets = [
        target
        for target in (_number(levels.get("tp1")), _number(levels.get("tp2")))
        if target is not None
    ]
    if entry is None or (stop is None and not targets):
        return []

    side = normalize_direction(direction)
    if side == "Neutral":
        return ["Trade levels require a clear buy or sell direction."]

    warnings: list[str] = []
    if stop is not None:
        if side == "Buy" and stop >= entry:
            warnings.append("Buy setup stop loss must be below the entry zone.")
        if side == "Sell" and stop <= entry:
            warnings.append("Sell setup stop loss must be above the entry zone.")
    for index, target in enumerate(targets, start=1):
        if side == "Buy" and target <= entry:
            warnings.append(f"Buy setup TP{index} must be above the entry zone.")
        if side == "Sell" and target >= entry:
            warnings.append(f"Sell setup TP{index} must be below the entry zone.")
    return warnings


def build_direction_debug(
    strategy_result: dict[str, object],
    analysis: dict[str, object],
) -> dict[str, object]:
    """Explain the authoritative direction and visible status decision."""
    answers = analysis.get("trader_answers") or {}
    raw_bias = strategy_result.get("bias", "Neutral")
    strategy_direction = normalize_direction(raw_bias)
    geometry_warnings = directional_geometry_warnings(
        strategy_direction,
        strategy_result.get("levels") or analysis.get("levels") or {},
    )
    unclear_context = _unclear_direction_context(analysis)
    directional_setup_forming = _directional_setup_forming(strategy_direction, strategy_result, analysis)
    final_direction = "Neutral" if geometry_warnings or (unclear_context and not directional_setup_forming) else strategy_direction
    trade_status = answers.get("trade_status") or strategy_result.get("trade_status") or strategy_result.get("state")
    state = strategy_result.get("state") or analysis.get("setup_status") or trade_status
    decision = strategy_result.get("trade_decision") or analysis.get("trade_decision") or "PENDING"
    levels_mode = str(strategy_result.get("levels_mode") or analysis.get("levels_mode") or "hidden").lower()
    timing = analysis.get("entry_timing") or strategy_result.get("entry_timing") or {}
    ready = (
        not geometry_warnings
        and levels_mode == "final"
        and str(decision).upper() == "ACCEPT"
        and str(trade_status) in {"Entry Ready", "Trade Active"}
    )
    user_status = format_user_status(
        status=state,
        direction=final_direction,
        trade_ready=ready,
        forming=not geometry_warnings,
        timing_status=timing.get("entry_timing_status"),
        timing_available=bool(timing.get("available")),
        trade_decision="PENDING" if directional_setup_forming and str(decision).upper() == "REJECT" else decision,
    )

    if geometry_warnings:
        reason = "Trade level geometry conflicts with the strategy direction."
    elif strategy_direction == "Neutral":
        reason = "Strategy direction is neutral or unclear; no side was inferred."
    elif unclear_context and directional_setup_forming:
        reason = "A directional setup is forming from local entry context, but confirmation is still missing."
    elif unclear_context:
        reason = "Higher-timeframe bias and execution trend are both unclear, so no side was inferred."
    elif user_status == "NO CLEAN ENTRY":
        reason = "A directional bias exists, but the current entry is blocked or invalid."
    elif ready:
        reason = f"The strategy confirmed a {strategy_direction.lower()} plan with valid levels."
    else:
        reason = f"The strategy returned a {strategy_direction.lower()} direction while confirmation is still forming."

    return {
        "raw_bias": raw_bias,
        "strategy_direction": strategy_direction,
        "final_direction": final_direction,
        "user_status": user_status,
        "reason": reason,
        "geometry_warnings": geometry_warnings,
        "unclear_context": unclear_context,
        "directional_setup_forming": directional_setup_forming,
    }


def _unclear_direction_context(analysis: dict[str, object]) -> bool:
    """Block buy/sell wording when top-down and execution context are both unclear."""
    answers = analysis.get("trader_answers") or {}
    top_down = analysis.get("top_down_context") or {}
    rows = top_down.get("timeframes") if isinstance(top_down, dict) else {}
    selected_timeframe = str(
        analysis.get("selected_timeframe")
        or top_down.get("selected_timeframe")
        or answers.get("execution_timeframe")
        or ""
    )
    selected_row = rows.get(selected_timeframe) if isinstance(rows, dict) else {}

    higher_bias = str(
        answers.get("higher_timeframe_bias")
        or _higher_bias_from_rows(rows if isinstance(rows, dict) else {})
        or top_down.get("overall_alignment")
        or "Neutral"
    )
    execution = str(
        answers.get("execution_timeframe_trend")
        or (selected_row or {}).get("bias")
        or answers.get("trend")
        or "Neutral"
    )

    higher_unclear = higher_bias not in {"Bullish", "Bearish"}
    execution_unclear = execution not in {"Bullish", "Bearish"}
    return higher_unclear and execution_unclear


def _higher_bias_from_rows(rows: dict[str, dict[str, object]]) -> str:
    score = 0
    for timeframe in ("D1", "H4", "H1"):
        value = str((rows.get(timeframe) or {}).get("bias", "Neutral"))
        if value == "Bullish":
            score += 1
        elif value == "Bearish":
            score -= 1
    if score > 0:
        return "Bullish"
    if score < 0:
        return "Bearish"
    return "Neutral"


def _directional_setup_forming(
    strategy_direction: str,
    strategy_result: dict[str, object],
    analysis: dict[str, object],
) -> bool:
    """Allow a local forming setup to keep its side even when macro context is mixed."""
    if strategy_direction == "Neutral":
        return False

    state = str(strategy_result.get("state") or analysis.get("setup_status") or "").upper().replace(" ", "_")
    if any(token in state for token in ("NO_TRADE", "INVALID", "FAILED")):
        return False

    timing = analysis.get("entry_timing") or strategy_result.get("entry_timing") or {}
    timing_status = str(timing.get("entry_timing_status") or "").lower()
    if bool(timing.get("available")) and timing_status in {"at_entry", "near_entry", "extended"}:
        return True

    levels = strategy_result.get("levels") or analysis.get("levels") or {}
    has_trigger = _number((levels or {}).get("trigger_level")) is not None
    has_invalidation = _number((levels or {}).get("invalidation")) is not None or _number((levels or {}).get("stop_loss")) is not None
    has_entry_zone = _entry_price((levels or {}).get("entry_zone")) is not None
    if has_trigger and (has_invalidation or has_entry_zone):
        return True

    overlays = strategy_result.get("overlays") or analysis.get("overlays") or {}
    setup_keys = (
        "active_fvg",
        "fvg_zone",
        "ifvg_zone",
        "demand_zone",
        "supply_zone",
        "important_zone",
        "entry_zone",
        "confirmation_level",
        "trigger_level",
    )
    return any(bool((overlays or {}).get(key)) for key in setup_keys)


def _entry_price(value: object) -> float | None:
    if not isinstance(value, dict):
        return _number(value)
    top = _number(value.get("top", value.get("top_price")))
    bottom = _number(value.get("bottom", value.get("bottom_price")))
    if top is None or bottom is None:
        return None
    return (top + bottom) / 2


def _number(value: object) -> float | None:
    if isinstance(value, dict):
        value = value.get("price", value.get("level"))
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
