"""Shared strategy objective selection and V1 target contract."""

from __future__ import annotations

import pandas as pd

from scanner.objective_engine import build_objective_plan


def analyze_objectives(
    *,
    direction: str | None,
    entry_price: float | None,
    stop_loss: float | None,
    shared_analysis: dict[str, object],
    context_candles: dict[str, pd.DataFrame] | None = None,
    liquidity_map: dict[str, object] | None = None,
    extra_candidates: list[dict[str, object]] | None = None,
    analysis_candles: pd.DataFrame | None = None,
    minimum_tp1_rr: float = 1.5,
    minimum_tp2_rr: float = 2.0,
) -> dict[str, object]:
    """Rank common and strategy-specific objectives without fetching data."""
    liquidity = shared_analysis.get("liquidity") or {}
    zones = shared_analysis.get("zones") or {}
    plan = build_objective_plan(
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        swings=shared_analysis.get("swings") or {},
        equal_levels={
            "equal_highs": liquidity.get("equal_highs", []),
            "equal_lows": liquidity.get("equal_lows", []),
        },
        zones=zones,
        fvgs=zones.get("fvg", []),
        context_candles=context_candles or {},
        liquidity_map=liquidity_map or {},
        extra_candidates=extra_candidates or [],
        analysis_candles=analysis_candles,
        min_risk_reward=minimum_tp1_rr,
    )

    primary = plan.get("primary_objective")
    secondary = plan.get("secondary_objective")
    if secondary and float(secondary.get("rr", 0) or 0) < minimum_tp2_rr:
        secondary = None

    return {
        **plan,
        "targets": plan.get("candidates", []),
        "selected_tp1": primary or {},
        "selected_tp2": secondary or {},
        "rejected_reason": None if primary else plan.get("reason"),
        "primary_objective": primary,
        "secondary_objective": secondary,
        "minimum_tp1_rr": minimum_tp1_rr,
        "minimum_tp2_rr": minimum_tp2_rr,
    }
