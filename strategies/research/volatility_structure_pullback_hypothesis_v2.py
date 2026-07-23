"""Phase 7 research variant -- exactly one preregistered eligibility change
over the frozen, rejected parent strategy.

parent_strategy_id: volatility_structure_pullback
parent_engine: analysis.volatility_structure_pullback_engine.evaluate_volatility_structure_pullback (UNMODIFIED)
parent_verdict: REJECTED_NO_EDGE_AFTER_COSTS (data/stabilization/phase5/frozen/phase5-r75-vsp-walkforward-v1)
single_change: reject a setup if stop_distance_atr > MAX_STOP_DISTANCE_ATR

This module NEVER duplicates the parent engine's structure/entry/stop/target
logic -- it calls the frozen parent engine as-is and applies exactly one
additional read-only eligibility check on top of its output. It carries no
Auto/paper/live/ML authority and must never be imported by app.py, the
Workspace request path, or the Markets Scanner: it exists only for the
Phase 7 preregistered research evaluation and any isolated test that
exercises it directly.
"""
from __future__ import annotations

import pandas as pd

from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback

STRATEGY_ID = "volatility_structure_pullback_hypothesis_v2"
PARENT_STRATEGY_ID = "volatility_structure_pullback"
PARENT_VERDICT = "REJECTED_NO_EDGE_AFTER_COSTS"
PARENT_EXPERIMENT_ID = "phase5-r75-vsp-walkforward-v1"

# Frozen at preregistration time (data/stabilization/phase7/preregistration/
# hypothesis_experiment_spec.json) -- the Q4/Q5 quartile cutpoint of
# stop_distance_atr on the full Phase 5 consumed distribution. Never adjusted
# after this module is written.
MAX_STOP_DISTANCE_ATR = 3.975

RESEARCH_ONLY = True
AUTO_ELIGIBLE = False
PAPER_SIGNAL_ALLOWED = False
LIVE_EXECUTION_ALLOWED = False
ML_FILTER_ALLOWED = False
EXACTLY_ONE_DECLARED_CHANGE = True


def _stop_distance_atr(candles_by_timeframe: dict, analysis_time, entry: float | None, stop: float | None) -> float | None:
    """Recomputes the same 14-period M5 high-low ATR the parent engine uses
    internally (analysis/volatility_structure_pullback_engine.py::_execution),
    over the same completed-candle-up-to-analysis_time window. Read-only --
    never mutates candles_by_timeframe or calls back into the parent engine's
    internals."""
    if entry is None or stop is None:
        return None
    m5 = candles_by_timeframe.get("M5")
    if m5 is None or not len(m5):
        return None
    frame = m5.copy()
    if "complete" in frame:
        frame = frame[frame.complete.astype(bool)]
    if analysis_time is not None and "time" in frame:
        frame = frame[pd.to_datetime(frame.time, utc=True) <= pd.Timestamp(analysis_time)]
    frame = frame.sort_values("time").tail(14)
    if len(frame) < 14:
        return None
    atr = float((frame.high - frame.low).mean())
    if atr <= 0:
        return None
    return abs(entry - stop) / atr


def evaluate_research_variant(*, symbol, candles_by_timeframe, tick_size: float = .01, analysis_time=None, **kwargs) -> dict:
    """Calls the frozen parent engine unmodified, then applies exactly the
    one preregistered eligibility filter on top of its output. The parent's
    own setup/decision/overlays are never altered -- this only adds a
    `research_variant` diagnostic block describing whether the single new
    condition passed."""
    parent_result = evaluate_volatility_structure_pullback(
        symbol=symbol, candles_by_timeframe=candles_by_timeframe, tick_size=tick_size,
        analysis_time=analysis_time, **kwargs,
    )
    result = dict(parent_result)
    setup = result.get("setup") or {}
    entry, stop = setup.get("entry"), setup.get("stop")
    stop_distance_atr = _stop_distance_atr(candles_by_timeframe, analysis_time, entry, stop)
    parent_trade_ready = bool((result.get("decision") or {}).get("trade_ready"))
    variant_eligible = bool(parent_trade_ready and stop_distance_atr is not None and stop_distance_atr <= MAX_STOP_DISTANCE_ATR)

    result["research_variant"] = {
        "strategy_id": STRATEGY_ID,
        "parent_strategy_id": PARENT_STRATEGY_ID,
        "parent_verdict": PARENT_VERDICT,
        "parent_experiment_id": PARENT_EXPERIMENT_ID,
        "single_change": f"stop_distance_atr <= {MAX_STOP_DISTANCE_ATR}",
        "stop_distance_atr": stop_distance_atr,
        "parent_trade_ready": parent_trade_ready,
        "variant_eligible": variant_eligible,
        "research_only": RESEARCH_ONLY,
        "auto_eligible": AUTO_ELIGIBLE,
        "paper_signal_allowed": PAPER_SIGNAL_ALLOWED,
        "live_execution_allowed": LIVE_EXECUTION_ALLOWED,
        "ml_filter_allowed": ML_FILTER_ALLOWED,
    }
    return result
