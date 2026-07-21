"""Quality checks and provenance for TradeScor's trader-facing answers."""

from __future__ import annotations

from analysis.strategy_validation import confirmation_exists, validate_strategy


def build_answer_qa(
    *,
    trader_answers: dict[str, object],
    shared_analysis: dict[str, object],
    strategy_result: dict[str, object],
    analysis: dict[str, object],
    top_down_context: dict[str, object],
) -> dict[str, object]:
    """Explain answer inputs and validate that the visible story is coherent."""
    validation = validate_answers(
        trader_answers=trader_answers,
        strategy_result=strategy_result,
        analysis=analysis,
        top_down_context=top_down_context,
    )
    warnings = _missing_data_warnings(shared_analysis, strategy_result, top_down_context)

    return {
        "current_trader_answers": trader_answers,
        "source_strategy": _source_strategy(strategy_result),
        "answer_conditions": _answer_conditions(
            trader_answers,
            shared_analysis,
            strategy_result,
            top_down_context,
        ),
        "missing_data_warnings": warnings,
        "clarity_explanation": _clarity_explanation(
            trader_answers,
            shared_analysis,
            top_down_context,
            warnings,
        ),
        "validation": validation,
    }


def validate_answers(
    *,
    trader_answers: dict[str, object],
    strategy_result: dict[str, object],
    analysis: dict[str, object],
    top_down_context: dict[str, object],
) -> dict[str, object]:
    return validate_strategy(
        trader_answers=trader_answers,
        strategy_result=strategy_result,
        analysis=analysis,
        top_down_context=top_down_context,
    )


def _source_strategy(strategy: dict[str, object]) -> dict[str, object]:
    return {
        "strategy_name": strategy.get("strategy_name", "Unknown"),
        "state": strategy.get("state", "NO_SETUP"),
        "bias": strategy.get("bias", "Neutral"),
        "levels_mode": strategy.get("levels_mode", "hidden"),
        "trade_decision": strategy.get("trade_decision", "PENDING"),
        "setup_quality": strategy.get("setup_quality", strategy.get("score", 0)),
        "trade_quality": strategy.get("trade_quality", 0),
        "next_trigger": strategy.get("next_trigger", ""),
    }


def _answer_conditions(
    answers: dict[str, object],
    shared: dict[str, object],
    strategy: dict[str, object],
    top_down: dict[str, object],
) -> dict[str, list[str]]:
    trend = shared.get("trend") or {}
    current = shared.get("current") or {}
    structure = shared.get("structure") or {}
    liquidity = shared.get("liquidity") or {}
    zones = shared.get("zones") or {}
    volatility = shared.get("volatility") or {}

    return {
        "trend": [
            f"Higher-timeframe alignment: {top_down.get('overall_alignment', 'Neutral')}.",
            f"Selected-chart trend: {trend.get('direction', 'Neutral')} ({trend.get('strength', 'unknown')} strength).",
            f"Strategy bias: {strategy.get('bias', 'Neutral')}.",
        ],
        "price_location": [
            f"Current range location: {current.get('range_location', 'unknown')}.",
            f"Support zone available: {'yes' if zones.get('nearest_support') else 'no'}.",
            f"Resistance zone available: {'yes' if zones.get('nearest_resistance') else 'no'}.",
            f"Recent liquidity sweep: {'yes' if liquidity.get('latest_sweep') else 'no'}.",
        ],
        "market_intent": [
            f"Price location answer: {answers.get('price_location', 'No clear level')}.",
            f"Strategy state: {strategy.get('state', 'NO_SETUP')}.",
            f"Structure break: {'yes' if structure.get('bos') or structure.get('choch') else 'no'}.",
            f"Volatility: {volatility.get('health', 'Unknown')}.",
        ],
        "trade_status": [
            f"Strategy state: {strategy.get('state', 'NO_SETUP')}.",
            f"Trade decision: {strategy.get('trade_decision', 'PENDING')}.",
            f"Levels mode: {strategy.get('levels_mode', 'hidden')}.",
            f"Confirmation present: {'yes' if confirmation_exists(strategy, {}) else 'no'}.",
        ],
        "why": [
            "Reasons combine top-down direction, current price location, market behavior, and entry readiness.",
            f"Market clarity: {answers.get('market_clarity', 'Low')}.",
        ],
    }


def _missing_data_warnings(
    shared: dict[str, object],
    strategy: dict[str, object],
    top_down: dict[str, object],
) -> list[str]:
    warnings: list[str] = []
    current = shared.get("current") or {}
    swings = shared.get("swings") or {}
    zones = shared.get("zones") or {}

    timeframe_rows = top_down.get("timeframes") or {}
    if len(timeframe_rows) <= 1:
        warnings.append("Multi-timeframe context is limited; trend relies mainly on the selected chart.")
    if current.get("current_price") is None:
        warnings.append("Current candle context is missing.")
    if not (swings.get("highs") or swings.get("lows")):
        warnings.append("Confirmed swing structure is not available.")
    if not (zones.get("nearest_support") or zones.get("nearest_resistance")):
        warnings.append("No active support or resistance zone is available.")
    if str(strategy.get("state", "")).upper() in {
        "WAITING_FOR_CONFIRMATION",
        "WAITING_MSS",
        "WAITING_FOR_CHOCH",
    } and not confirmation_exists(strategy, {}):
        warnings.append("The strategy is waiting, but no numeric confirmation level is available yet.")
    return warnings


def _clarity_explanation(
    answers: dict[str, object],
    shared: dict[str, object],
    top_down: dict[str, object],
    warnings: list[str],
) -> str:
    clarity = str(answers.get("market_clarity", "Low"))
    trend = str(answers.get("trend", "Unclear"))
    location = str(answers.get("price_location", "No clear level"))
    alignment = str(top_down.get("overall_alignment", "Neutral"))
    volatility = str((shared.get("volatility") or {}).get("health", "Unknown"))

    strengths = []
    if trend in {"Bullish", "Bearish", "Range"}:
        strengths.append(f"the market has a readable {trend.lower()} structure")
    if location != "No clear level":
        strengths.append(f"price has a defined location ({location.lower()})")
    if alignment in {"Bullish", "Bearish"}:
        strengths.append(f"higher timeframes align {alignment.lower()}")
    if volatility != "Unknown":
        strengths.append(f"volatility is {volatility.lower()}")

    evidence = ", ".join(strengths) if strengths else "direction and location are still unclear"
    limitation = f" {len(warnings)} data warning(s) reduce confidence." if warnings else " No material data warnings are present."
    return f"Clarity is {clarity.lower()} because {evidence}.{limitation}"
