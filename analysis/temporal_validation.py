"""Temporal honesty checks for live and replay analysis."""

from __future__ import annotations

import pandas as pd

from analysis.time_context import TIMEFRAME_DURATIONS, as_utc_timestamp


def validate_temporal_analysis(
    *,
    analysis_timestamp: object,
    selected_timeframe: str,
    context: dict[str, pd.DataFrame],
    strategy_result: dict[str, object],
    session: dict[str, object],
    news: dict[str, object],
) -> dict[str, object]:
    """Return warnings when analysis references information from the future."""
    boundary = as_utc_timestamp(analysis_timestamp)
    warnings: list[str] = []
    selected = selected_timeframe.upper()

    for timeframe, candles in context.items():
        if candles is None or candles.empty:
            continue
        times = pd.to_datetime(candles["time"], errors="coerce", utc=True).dropna()
        if times.empty:
            continue
        latest = times.max()
        duration = TIMEFRAME_DURATIONS.get(timeframe.upper())
        available_at = latest if timeframe.upper() == selected or duration is None else latest + duration
        if available_at > boundary:
            warnings.append(f"{timeframe} context contains a candle unavailable at the analysis timestamp.")

    _validate_evaluation_time("Session", session.get("evaluated_at"), boundary, warnings)
    _validate_evaluation_time("News", news.get("evaluated_at"), boundary, warnings)

    setup = strategy_result.get("setup_state") or {}
    confirmation_time = setup.get("confirmation_time")
    if confirmation_time and as_utc_timestamp(confirmation_time) > boundary:
        warnings.append("Confirmation event occurs after the current analysis candle.")

    for target in (strategy_result.get("objective_plan") or {}).get("targets", []) or []:
        formed_at = target.get("formed_at")
        if formed_at and as_utc_timestamp(formed_at) > boundary:
            warnings.append(f"Target '{target.get('name', 'unknown')}' formed after the analysis timestamp.")
        if target.get("taken") and target.get("accepted"):
            warnings.append(f"Target '{target.get('name', 'unknown')}' is marked accepted after being swept.")

    state = str(strategy_result.get("state", ""))
    final_state = state in {"ENTRY_READY", "TRADE_ACTIVE"}
    if final_state and not confirmation_time:
        warnings.append("Entry Ready requires a stored confirmation event.")
    if final_state and not bool(strategy_result.get("entry_proximity")):
        warnings.append("Entry Ready exists while price is outside the entry zone.")

    completed_types = {str(event.get("type")) for event in setup.get("completed_events", []) if isinstance(event, dict)}
    if state in {"CONFIRMED_WAITING_FOR_ENTRY", "ENTRY_READY", "TRADE_ACTIVE"} and not (
        {"confirmation", "choch_confirmed", "breakout_confirmed"} & completed_types
    ):
        warnings.append("Strategy advanced beyond confirmation without a valid transition event.")
    if state in {"BREAKOUT_CONFIRMED", "WAITING_FOR_RETEST", "RETEST_ACTIVE", "WAITING_FOR_REJECTION"} and "breakout_confirmed" not in completed_types:
        warnings.append("Breakout state is missing its locked breakout event.")

    return {"valid": not warnings, "warnings": warnings}


def _validate_evaluation_time(
    label: str,
    evaluated_at: object,
    boundary: pd.Timestamp,
    warnings: list[str],
) -> None:
    if not evaluated_at:
        warnings.append(f"{label} evaluation timestamp is missing.")
        return
    evaluated = as_utc_timestamp(evaluated_at)
    if abs((evaluated - boundary).total_seconds()) > 1:
        warnings.append(f"{label} evaluation timestamp differs from the analysis timestamp.")
