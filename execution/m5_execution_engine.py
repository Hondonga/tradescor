"""Candidate-oriented facade over TradeScor's common M5 executor."""

from __future__ import annotations

from analysis.m5_execution_engine import build_m5_execution_plan


def execute_candidate(*, candidate: dict[str, object], top_down: dict[str, object], m5_candles, analysis_timestamp: object, current_price: object = None, spread: object = 0, asset_type: str = "forex", filters: dict[str, object] | None = None, session: dict[str, object] | None = None, minimum_rr: float = 1.5, mode: str = "conservative") -> dict[str, object]:
    plan = build_m5_execution_plan(top_down_analysis=top_down, m5_candles=m5_candles, analysis_timestamp=analysis_timestamp, current_price=current_price, spread=spread, asset_type=asset_type, news_filters=filters or {}, session_context=session or {}, minimum_rr=minimum_rr, mode=mode)
    return {"execution_timeframe": "M5", "candidate_id": candidate.get("candidate_id") or f"{candidate.get('strategy_id')}:{candidate.get('zone', {}).get('origin_time')}", "state": plan.get("state", "unavailable"), "trigger": plan.get("trigger"), "entry": plan.get("entry"), "entry_zone": plan.get("entry_zone"), "stop": plan.get("stop"), "targets": plan.get("targets", []), "remaining_rr": plan.get("risk_reward"), "chase_distance": plan.get("entry_distance"), "confirmed_candle_time": (plan.get("confirmed_signal") or {}).get("candle_time"), "forming_signal": plan.get("forming_signal"), "confirmed_signal": plan.get("confirmed_signal"), "rejection_reasons": [] if plan.get("state") == "entry_valid" else [plan.get("message", "Execution requirements are incomplete.")], "message": plan.get("message", "")}
