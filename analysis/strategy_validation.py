"""Shared contradiction checks for every TradeScor strategy."""

from __future__ import annotations

from analysis.direction import directional_geometry_warnings


FINAL_STATUSES = {"Entry Ready", "Trade Active"}


def validate_strategy(
    *,
    trader_answers: dict[str, object],
    strategy_result: dict[str, object],
    analysis: dict[str, object],
    top_down_context: dict[str, object],
) -> dict[str, object]:
    """Validate the visible answer, state, and level contract."""
    warnings: list[str] = []
    trade_status = str(trader_answers.get("trade_status", "No Trade"))
    trend = str(trader_answers.get("trend", "Unclear"))
    price_location = str(trader_answers.get("price_location", "No clear level"))
    market_intent = str(trader_answers.get("market_intent", "Ranging / undecided"))
    next_action = str(trader_answers.get("next_action", "")).strip()
    market_story = str(trader_answers.get("market_story", ""))

    if trade_status == "Entry Ready":
        if trend not in {"Bullish", "Bearish"}:
            warnings.append("Entry Ready requires a clear bullish or bearish trend.")
        if not confirmation_exists(strategy_result, analysis):
            warnings.append("Entry Ready requires a visible confirmation trigger.")
        if not confirmation_achieved(strategy_result, analysis):
            warnings.append("Entry Ready requires the confirmation trigger to be achieved.")
        if not entry_zone(strategy_result, analysis):
            warnings.append("Entry Ready requires a valid entry zone.")
        if invalidation(strategy_result, analysis) is None:
            warnings.append("Entry Ready requires an invalidation or stop-loss level.")
        if target(strategy_result, analysis) is None:
            warnings.append("Entry Ready requires a valid target.")

        reward = risk_reward(strategy_result, analysis)
        if reward is None:
            warnings.append("Entry Ready requires a calculated risk/reward ratio.")
        elif reward < 1.5:
            warnings.append(f"Entry Ready requires at least 1.50R; current reward is {reward:.2f}R.")

        if any(phrase in market_story.lower() for phrase in ("mixed", "unclear", "no reliable trend")):
            warnings.append("Entry Ready conflicts with an unclear or mixed market story.")
        if not price_near_entry(strategy_result, analysis):
            warnings.append("Entry Ready requires price to be inside or near the valid entry zone.")
        if target_closer_than_stop(strategy_result, analysis):
            warnings.append("Entry Ready target is closer than the stop loss.")

        warnings.extend(
            directional_geometry_warnings(
                strategy_result.get("bias", "Neutral"),
                strategy_result.get("levels") or analysis.get("levels") or {},
            )
        )

    if trade_status not in FINAL_STATUSES and trade_levels_visible(strategy_result, analysis):
        warnings.append(f"{trade_status} must not expose entry, stop-loss, or target levels.")

    strategy_bias = str(strategy_result.get("bias", "Neutral"))
    alignment = str(top_down_context.get("overall_alignment", "Neutral"))
    if trend == "Range" and strategy_bias in {"Bullish", "Bearish"} and alignment != strategy_bias:
        warnings.append(
            f"Range conflicts with a strong {strategy_bias.lower()} strategy bias that is not supported by higher-timeframe context."
        )

    if price_location == "No clear level" and any(
        phrase in market_intent.lower()
        for phrase in ("retesting demand", "pulling back into support", "pulling back into resistance")
    ):
        warnings.append("No clear level cannot claim a support, resistance, or demand retest.")

    if trade_status in {"Wait", "Almost Ready"} and not next_action:
        warnings.append(f"{trade_status} requires a next action.")

    allowed_statuses = {"No Trade", "Wait", "Almost Ready", "Entry Ready", "Trade Active", "Invalidated"}
    if trade_status not in allowed_statuses:
        warnings.append(f"Unsupported trade status: {trade_status}.")

    why = trader_answers.get("why") or []
    if not 3 <= len(why) <= 5:
        warnings.append("Why must contain between three and five concise reasons.")

    return {"valid": not warnings, "warnings": warnings}


def confirmation_exists(strategy: dict[str, object], analysis: dict[str, object]) -> bool:
    overlays = strategy.get("overlays") or analysis.get("overlays") or analysis.get("chart_overlays") or {}
    confirmation = overlays.get("confirmation_level") or overlays.get("mss_level") or overlays.get("trigger_level") or {}
    if isinstance(confirmation, dict) and any(confirmation.get(key) is not None for key in ("price", "level", "close")):
        return True
    return bool((analysis.get("checklist_flags") or {}).get("mss") or (analysis.get("checklist_flags") or {}).get("ifvg"))


def confirmation_achieved(strategy: dict[str, object], analysis: dict[str, object]) -> bool:
    if strategy.get("confirmation_achieved") is not None:
        return bool(strategy.get("confirmation_achieved"))
    checklist = strategy.get("ict_checklist") or analysis.get("ict_checklist") or {}
    return checklist.get("choch") == "pass" or bool((analysis.get("checklist_flags") or {}).get("mss"))


def entry_zone(strategy: dict[str, object], analysis: dict[str, object]) -> dict[str, object]:
    levels = strategy.get("levels") or analysis.get("levels") or {}
    overlays = strategy.get("overlays") or analysis.get("overlays") or analysis.get("chart_overlays") or {}
    return levels.get("entry_zone") or overlays.get("entry_zone") or {}


def invalidation(strategy: dict[str, object], analysis: dict[str, object]) -> float | None:
    levels = strategy.get("levels") or analysis.get("levels") or {}
    overlays = strategy.get("overlays") or analysis.get("overlays") or analysis.get("chart_overlays") or {}
    return number(levels.get("stop_loss") or overlays.get("stop_loss") or overlays.get("invalidation_level") or analysis.get("invalidation_level"))


def target(strategy: dict[str, object], analysis: dict[str, object]) -> float | None:
    return number((strategy.get("levels") or analysis.get("levels") or {}).get("tp1"))


def risk_reward(strategy: dict[str, object], analysis: dict[str, object]) -> float | None:
    levels = strategy.get("levels") or analysis.get("levels") or {}
    primary = (strategy.get("objective_plan") or analysis.get("objective_plan") or {}).get("primary_objective") or {}
    return number(levels.get("rr1") if levels.get("rr1") is not None else primary.get("rr"))


def price_near_entry(strategy: dict[str, object], analysis: dict[str, object]) -> bool:
    if strategy.get("entry_proximity") is not None:
        return bool(strategy.get("entry_proximity"))
    zone = entry_zone(strategy, analysis)
    top = number(zone.get("top", zone.get("top_price")))
    bottom = number(zone.get("bottom", zone.get("bottom_price")))
    current = current_price(strategy, analysis)
    if top is None or bottom is None or current is None:
        return False
    low, high = sorted((bottom, top))
    buffer = max((high - low) * 0.2, abs(current) * 0.00002)
    return low - buffer <= current <= high + buffer


def current_price(strategy: dict[str, object], analysis: dict[str, object]) -> float | None:
    overlays = strategy.get("overlays") or analysis.get("overlays") or analysis.get("chart_overlays") or {}
    current = overlays.get("current_price")
    if isinstance(current, dict):
        current = current.get("price")
    return number(current if current is not None else ((analysis.get("shared_analysis") or {}).get("current") or {}).get("current_price"))


def target_closer_than_stop(strategy: dict[str, object], analysis: dict[str, object]) -> bool:
    zone = entry_zone(strategy, analysis)
    top = number(zone.get("top", zone.get("top_price")))
    bottom = number(zone.get("bottom", zone.get("bottom_price")))
    stop = invalidation(strategy, analysis)
    objective = target(strategy, analysis)
    if top is None or bottom is None or stop is None or objective is None:
        return False
    entry = (top + bottom) / 2
    return abs(objective - entry) < abs(entry - stop)


def trade_levels_visible(strategy: dict[str, object], analysis: dict[str, object]) -> bool:
    levels_mode = str(strategy.get("levels_mode") or analysis.get("levels_mode") or "hidden")
    levels = strategy.get("levels") or analysis.get("levels") or {}
    if levels_mode == "final":
        return True
    return any(levels.get(key) not in (None, {}, "") for key in ("entry_zone", "stop_loss", "tp1", "tp2"))


def number(value: object) -> float | None:
    if isinstance(value, dict):
        value = value.get("price", value.get("level"))
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
