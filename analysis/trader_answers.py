"""Plain-language market answers built from TradeScor's existing analysis.

This module does not predict prices or fetch data. It translates shared market
context and the selected strategy state into a short trader-facing narrative.
"""

from __future__ import annotations

from analysis.timeframe_alignment import describe_timeframe_alignment


def build_trader_answers(
    *,
    symbol: str,
    timeframe: str,
    shared_analysis: dict[str, object],
    strategy_result: dict[str, object],
    analysis: dict[str, object],
    top_down_context: dict[str, object],
) -> dict[str, object]:
    """Return the five answers that drive the default TradeScor interface."""
    execution_fallback = (shared_analysis.get("trend") or {}).get("direction", "Neutral")
    timeframe_view = describe_timeframe_alignment(top_down_context, timeframe, execution_fallback)
    trend = str(timeframe_view["execution_timeframe_trend"])
    if trend not in {"Bullish", "Bearish"}:
        trend = _trend(shared_analysis, strategy_result, top_down_context)
    price_location = _price_location(shared_analysis, strategy_result)
    market_intent = _market_intent(shared_analysis, strategy_result, trend, price_location)
    if timeframe_view["timeframe_alignment"] == "Counter-trend":
        market_intent = (
            f"{trend} pullback against "
            f"{timeframe_view['higher_timeframe_bias'].lower()} higher-timeframe bias"
        )
    trade_status = _trade_status(strategy_result, analysis)
    if timeframe_view["timeframe_alignment"] == "Counter-trend" and trade_status != "Trade Active":
        trade_status = "No Trade"
    top_down_summary = _top_down_summary(top_down_context, timeframe)
    next_action = _next_action(strategy_result, analysis, trade_status)
    if timeframe_view["timeframe_alignment"] == "Counter-trend":
        next_action = (
            f"Wait for {timeframe} to realign with the "
            f"{str(timeframe_view['higher_timeframe_bias']).lower()} higher-timeframe bias."
        )
    market_clarity = _market_clarity(shared_analysis, top_down_context, trend, price_location)
    trade_readiness = _trade_readiness(trade_status)
    why = _why(
        top_down_summary,
        trend,
        price_location,
        market_intent,
        trade_status,
        strategy_result,
        analysis,
        timeframe_view,
    )
    market_story = _market_story(
        symbol,
        trend,
        price_location,
        market_intent,
        trade_status,
        next_action,
        timeframe_view,
    )

    return {
        "trend": trend,
        **timeframe_view,
        "price_location": price_location,
        "market_intent": market_intent,
        "trade_status": trade_status,
        "why": why[:5],
        "top_down_summary": top_down_summary,
        "market_story": market_story,
        "next_action": next_action,
        "market_clarity": market_clarity,
        "trade_readiness": trade_readiness,
        "market_timeline": _market_timeline(trend, price_location, market_intent, trade_status),
    }


def actionable_wait_instruction(
    *,
    symbol: str,
    timeframe: str,
    direction: str,
    trigger_level: object,
    precision: int = 5,
) -> str | None:
    """Describe the exact price event required before a pending setup is usable."""
    trigger = _number(trigger_level)
    normalized_direction = str(direction or "").lower()
    if trigger is None or normalized_direction not in {"bullish", "bearish"}:
        return None

    side = "above" if normalized_direction == "bullish" else "below"
    continuation = "bullish" if normalized_direction == "bullish" else "bearish"
    safe_precision = max(0, min(int(precision), 8))
    formatted_trigger = f"{trigger:.{safe_precision}f}"
    return (
        f"Wait for {symbol} to break {side} {formatted_trigger} and hold. "
        f"Do not enter until {timeframe} confirms {continuation} continuation."
    )


def actionable_rejection_instruction(
    *,
    symbol: str,
    direction: str,
    trigger_level: object,
    precision: int = 5,
) -> str | None:
    """Name the rejected trigger without presenting it as a valid entry."""
    trigger = _number(trigger_level)
    normalized_direction = str(direction or "").lower()
    if trigger is None or normalized_direction not in {"bullish", "bearish"}:
        return None

    side = "above" if normalized_direction == "bullish" else "below"
    safe_precision = max(0, min(int(precision), 8))
    formatted_trigger = f"{trigger:.{safe_precision}f}"
    return (
        f"Do not trade the {symbol} break {side} {formatted_trigger}. "
        "The projected reward is insufficient. Wait for a new setup with at least 1.50R."
    )


def _trend(
    shared: dict[str, object],
    strategy: dict[str, object],
    top_down: dict[str, object],
) -> str:
    alignment = str(top_down.get("overall_alignment", "Neutral"))
    selected = str((shared.get("trend") or {}).get("direction", "Neutral"))
    strategy_bias = str(strategy.get("bias", "Neutral"))

    if alignment in {"Bullish", "Bearish"}:
        return alignment
    if alignment == "Mixed":
        return "Unclear"
    if selected in {"Bullish", "Bearish"}:
        return selected
    if strategy_bias in {"Bullish", "Bearish"}:
        return strategy_bias

    volatility = str((shared.get("volatility") or {}).get("health", "Unknown"))
    structure = shared.get("structure") or {}
    if volatility == "Quiet" or not (structure.get("bos") or structure.get("choch")):
        return "Range"
    return "Unclear"


def _price_location(shared: dict[str, object], strategy: dict[str, object]) -> str:
    strategy_location = str(strategy.get("price_location", "")).strip()
    if strategy_location:
        return strategy_location

    current = shared.get("current") or {}
    zones = shared.get("zones") or {}
    liquidity = shared.get("liquidity") or {}
    structure = shared.get("structure") or {}
    state = str(strategy.get("state", "")).upper()
    price = _number(current.get("current_price"))

    if price is None:
        return "No clear level"

    latest_sweep = liquidity.get("latest_sweep") or {}
    candle_count = int(shared.get("candles_count", 0) or 0)
    sweep_index = int(latest_sweep.get("index", -1000) or -1000)
    swept_level = _number(latest_sweep.get("swept_level"))
    atr = _number((shared.get("volatility") or {}).get("atr")) or abs(price) * 0.0005
    near_swept_level = swept_level is not None and abs(price - swept_level) <= atr * 1.5
    if latest_sweep and sweep_index >= candle_count - 3 and near_swept_level:
        return "At liquidity"

    support = zones.get("nearest_support") or {}
    resistance = zones.get("nearest_resistance") or {}
    at_support = _inside_zone(price, support)
    at_resistance = _inside_zone(price, resistance)

    if "PULLBACK" in state or "CONFIRMATION" in state:
        if at_support:
            return "Pullback into support"
        if at_resistance:
            return "Pullback into resistance"
        return "In pullback"
    if at_support:
        return "At support"
    if at_resistance:
        return "At resistance"
    if structure.get("bos"):
        return "In breakout"

    range_high = _number(current.get("range_high"))
    range_low = _number(current.get("range_low"))
    midpoint = _number(current.get("range_midpoint"))
    if range_high is not None and range_low is not None and midpoint is not None:
        range_size = range_high - range_low
        if range_size > 0 and abs(price - midpoint) <= range_size * 0.16:
            return "In range middle"

    return "No clear level"


def _market_intent(
    shared: dict[str, object],
    strategy: dict[str, object],
    trend: str,
    location: str,
) -> str:
    strategy_intent = str(strategy.get("market_intent", "")).strip()
    if strategy_intent:
        return strategy_intent

    state = str(strategy.get("state", "")).upper()
    structure = shared.get("structure") or {}
    volatility = str((shared.get("volatility") or {}).get("health", "Unknown"))

    if location == "At liquidity":
        return "Sweeping liquidity"
    if state in {"WAITING_FOR_ENTRY", "CONFIRMED_WAITING_FOR_ENTRY"}:
        return "Waiting for pullback"
    if location in {"Pullback into support", "At support"} and trend == "Bullish":
        return "Pulling back into support"
    if location in {"Pullback into resistance", "At resistance"} and trend == "Bearish":
        return "Pulling back into resistance"
    if "PULLBACK" in state or "CONFIRMATION" in state:
        return "Retesting before continuation"
    if location == "In breakout" or structure.get("bos"):
        return "Retesting breakout" if "WAITING" in state else "Continuing trend"
    if volatility == "Quiet":
        return "Compressing before breakout"
    if trend in {"Bullish", "Bearish"}:
        return "Continuing trend"
    return "Ranging / undecided"


def _trade_status(strategy: dict[str, object], analysis: dict[str, object]) -> str:
    state = str(strategy.get("state") or analysis.get("setup_status") or "").upper()
    levels_mode = str(strategy.get("levels_mode") or analysis.get("levels_mode") or "hidden")
    decision = str(strategy.get("trade_decision") or analysis.get("trade_decision") or "PENDING").upper()

    if "TRADE_ACTIVE" in state:
        return "Trade Active"
    if "INVALID" in state or "FAILED_BREAKOUT" in state:
        return "Invalidated"
    if levels_mode == "final" and decision == "ACCEPT":
        return "Entry Ready"
    if decision == "REJECT":
        return "No Trade"
    if any(label in state for label in ("WAITING_IFVG", "WAITING_FOR_CONFIRMATION", "WAITING_FOR_REJECTION", "ENTRY_READY")):
        return "Almost Ready"
    if any(
        label in state
        for label in (
            "PULLBACK",
            "AT_IMPORTANT_ZONE",
            "WAITING_FOR_ZONE",
            "WAITING_FOR_ENTRY",
            "CONFIRMED_WAITING_FOR_ENTRY",
            "WAITING_MSS",
            "LIQUIDITY",
            "TREND_DETECTED",
            "ZONE_IDENTIFIED",
            "WAITING_FOR_PRICE_TO_ENTER_ZONE",
            "PRICE_IN_ZONE",
            "WAITING_FOR_REACTION",
            "RANGE_IDENTIFIED",
            "WAITING_FOR_BREAKOUT",
            "BREAKOUT_CONFIRMED",
            "WAITING_FOR_RETEST",
            "RETEST_ACTIVE",
        )
    ):
        return "Wait"
    return "No Trade"


def _next_action(
    strategy: dict[str, object],
    analysis: dict[str, object],
    trade_status: str,
) -> str:
    objective = strategy.get("objective_plan") or analysis.get("objective_plan") or {}
    if trade_status == "Trade Active":
        return "Manage the active trade against the confirmed invalidation and objective."
    if trade_status == "Entry Ready":
        return "Price is inside the confirmed entry zone. Use only the validated trade plan."
    if str(objective.get("decision", "")).upper() == "REJECT":
        return "Stand aside and wait for a fresh setup with sufficient reward."

    trigger = str(
        strategy.get("next_trigger")
        or analysis.get("next_required_confirmation")
        or analysis.get("missing_confirmation")
        or ""
    ).strip()
    if trigger:
        return _plain_trigger(trigger)
    return "Wait for price to show clear confirmation before considering a trade."


def _plain_trigger(trigger: str) -> str:
    text = trigger.strip()
    replacements = {
        "IFVG": "entry-zone",
        "MSS": "structure shift",
        "HTF": "higher-timeframe",
    }
    for technical, plain in replacements.items():
        text = text.replace(technical, plain)
    if not text.endswith((".", "!", "?")):
        text += "."
    return text


def _market_clarity(
    shared: dict[str, object],
    top_down: dict[str, object],
    trend: str,
    location: str,
) -> str:
    points = 0
    if trend in {"Bullish", "Bearish"}:
        points += 2
    elif trend == "Range":
        points += 1
    if location != "No clear level":
        points += 1
    if str(top_down.get("overall_alignment", "Neutral")) in {"Bullish", "Bearish"}:
        points += 1
    if not (top_down.get("conflicts") or []):
        points += 1
    if str((shared.get("volatility") or {}).get("health", "Unknown")) != "Unknown":
        points += 1

    if points >= 5:
        return "High"
    if points >= 3:
        return "Medium"
    return "Low"


def _trade_readiness(trade_status: str) -> str:
    if trade_status in {"Entry Ready", "Trade Active"}:
        return "Ready"
    if trade_status in {"Wait", "Almost Ready"}:
        return "Building"
    return "Not Ready"


def _why(
    top_down_summary: str,
    trend: str,
    location: str,
    intent: str,
    trade_status: str,
    strategy: dict[str, object],
    analysis: dict[str, object],
    timeframe_view: dict[str, str],
) -> list[str]:
    reasons = [top_down_summary]

    if timeframe_view.get("timeframe_alignment") == "Counter-trend":
        reasons.append(
            f"{timeframe_view['execution_timeframe']} execution is "
            f"{timeframe_view['execution_timeframe_trend'].lower()} and not aligned with the "
            f"{timeframe_view['higher_timeframe_bias'].lower()} higher-timeframe bias."
        )
    elif timeframe_view.get("timeframe_alignment") == "Aligned":
        reasons.append(
            f"{timeframe_view['execution_timeframe']} execution is aligned with the "
            f"{timeframe_view['higher_timeframe_bias'].lower()} higher-timeframe bias."
        )

    if location == "No clear level":
        reasons.append("Price is not reacting from a clean support, resistance, or liquidity level.")
    else:
        reasons.append(f"Price is {location.lower()}.")

    if timeframe_view.get("timeframe_alignment") == "Counter-trend":
        reasons.append(
            f"{trend} pressure controls the execution timeframe during the pullback; "
            f"the higher-timeframe bias remains {timeframe_view['higher_timeframe_bias'].lower()}."
        )
    elif trend in {"Bullish", "Bearish"}:
        control = "Buyers" if trend == "Bullish" else "Sellers"
        reasons.append(f"{control} still control the broader structure while price is {intent.lower()}.")
    else:
        reasons.append("Directional structure is mixed, so continuation is not yet reliable.")

    objective = strategy.get("objective_plan") or analysis.get("objective_plan") or {}
    if str(objective.get("decision", "")).upper() == "REJECT":
        reasons.append(str(objective.get("reason", "The available reward does not justify the risk.")))
    elif trade_status == "Entry Ready":
        reasons.append("The setup and trade objective both meet the current confirmation rules.")
    elif trade_status == "Trade Active":
        reasons.append("Price has entered the confirmed trade area.")
    else:
        reasons.append("The final confirmation needed for an entry has not formed yet.")

    return _unique(reasons)


def _market_story(
    symbol: str,
    trend: str,
    location: str,
    intent: str,
    trade_status: str,
    next_action: str,
    timeframe_view: dict[str, str],
) -> str:
    higher_bias = timeframe_view.get("higher_timeframe_bias", "Neutral")
    execution_timeframe = timeframe_view.get("execution_timeframe", "Execution timeframe")
    alignment = timeframe_view.get("timeframe_alignment", "Unconfirmed")

    if alignment == "Counter-trend":
        return (
            f"{symbol} has a {higher_bias.lower()} higher-timeframe bias, while "
            f"{execution_timeframe} execution is {trend.lower()}. This is a counter-trend "
            f"pullback, so the timeframes are not aligned. Trade status is {trade_status}. "
            f"{next_action}"
        )

    if trend == "Bullish":
        opening = f"{symbol} is bullish across the clearest available timeframes."
        control = "Buyers remain in control"
    elif trend == "Bearish":
        opening = f"{symbol} is bearish across the clearest available timeframes."
        control = "Sellers remain in control"
    elif trend == "Range":
        opening = f"{symbol} is trading in a range without a clean directional trend."
        control = "Neither side has clear control"
    else:
        opening = f"{symbol} has mixed structure and no reliable directional trend."
        control = "Direction remains unclear"

    location_text = _location_sentence(location)
    intent_text = f"The market currently appears to be {intent.lower()}."

    if trade_status == "Entry Ready":
        trade_text = f"{control}, and a confirmed entry is available."
    elif trade_status == "Trade Active":
        trade_text = f"{control}, and the confirmed trade is active."
    elif trade_status == "Almost Ready":
        trade_text = f"{control}, but one final confirmation is still missing."
    elif trade_status == "Wait":
        trade_text = f"{control}, but there is no confirmed entry yet."
    else:
        trade_text = f"{control}; there is no trade right now."

    higher_text = (
        f"Higher-timeframe bias is {higher_bias.lower()}."
        if higher_bias in {"Bullish", "Bearish"}
        else "Higher-timeframe bias is not confirmed."
    )
    return " ".join([higher_text, opening, location_text, intent_text, trade_text, next_action])


def _location_sentence(location: str) -> str:
    phrases = {
        "At support": "Price is testing support.",
        "At resistance": "Price is testing resistance.",
        "Pullback into support": "Price is pulling back into support after the prior move.",
        "Pullback into resistance": "Price is pulling back into resistance after the prior move.",
        "In pullback": "Price is currently pulling back rather than expanding.",
        "In breakout": "Price is trading beyond recent structure.",
        "In range middle": "Price is near the middle of its recent range.",
        "At liquidity": "Price is interacting with a nearby liquidity pool.",
        "No clear level": "Price is not at a clean decision level.",
    }
    return phrases.get(location, f"Price is {location.lower()}.")


def _top_down_summary(top_down: dict[str, object], selected_timeframe: str) -> str:
    rows = top_down.get("timeframes") or {}
    if not rows:
        return "Higher-timeframe context is not loaded."

    major_order = ("D1", "H4", "H1")
    bullish = [timeframe for timeframe in major_order if (rows.get(timeframe) or {}).get("bias") == "Bullish"]
    bearish = [timeframe for timeframe in major_order if (rows.get(timeframe) or {}).get("bias") == "Bearish"]
    parts: list[str] = []
    if bullish:
        parts.append(f"{_join_words(bullish)} {'is' if len(bullish) == 1 else 'are'} bullish")
    if bearish:
        parts.append(f"{_join_words(bearish)} {'is' if len(bearish) == 1 else 'are'} bearish")

    timing_timeframe = _timing_timeframe(rows, selected_timeframe)
    timing = rows.get(timing_timeframe) or {}
    timing_status = str(timing.get("status", "Waiting")).lower()
    timing_phrase = ""
    if timing:
        if timing_status == "pullback":
            timing_phrase = f"{timing_timeframe} is pulling back"
        elif timing_status == "trend":
            timing_phrase = f"{timing_timeframe} remains in trend"
        else:
            timing_phrase = f"{timing_timeframe} is waiting"

    if len(parts) == 2:
        summary = f"{parts[0]} while {parts[1]}"
    elif parts:
        summary = parts[0]
    else:
        summary = "Higher timeframes are mixed"

    if timing_phrase:
        connector = " while " if len(parts) <= 1 else "; "
        summary += connector + timing_phrase
    return summary + "."


def _timing_timeframe(rows: dict[str, dict[str, object]], selected: str) -> str:
    if selected in rows and selected not in {"D1", "H4", "H1"}:
        return selected
    for timeframe in ("M15", "M5", "M1"):
        if timeframe in rows:
            return timeframe
    return selected if selected in rows else next(iter(rows))


def _market_timeline(trend: str, location: str, intent: str, trade_status: str) -> list[str]:
    timeline = [f"Market structure reads {trend.lower()}."]
    timeline.append(_location_sentence(location))
    timeline.append(f"Current behavior: {intent}.")
    if trade_status == "Entry Ready":
        timeline.append("Confirmation completed; entry is ready.")
    elif trade_status == "Trade Active":
        timeline.append("Price entered the confirmed trade area.")
    elif trade_status == "Almost Ready":
        timeline.append("Waiting for one final confirmation.")
    elif trade_status == "Wait":
        timeline.append("Waiting for confirmation before considering a trade.")
    else:
        timeline.append("No trade is available in the current conditions.")
    return _unique(timeline)[:4]


def _inside_zone(price: float, zone: dict[str, object]) -> bool:
    top = _number(zone.get("top_price", zone.get("top")))
    bottom = _number(zone.get("bottom_price", zone.get("bottom")))
    return top is not None and bottom is not None and min(top, bottom) <= price <= max(top, bottom)


def _join_words(values: list[str]) -> str:
    if len(values) <= 1:
        return values[0] if values else ""
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        clean = str(value).strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _number(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
