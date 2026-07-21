"""Orchestrator: run the full feasibility sequence for one strategy hypothesis.

    strategy hypothesis
    -> causal setup generation      (setup_generator)
    -> matched directional controls  (paired_controls)
    -> symmetric geometry            (symmetric_geometry)
    -> realistic costs               (cost_model)
    -> grouped uncertainty           (grouped_resampling)
    -> symbol stability              (stability_analysis)
    -> period stability              (stability_analysis)
    -> freeze the result             (experiment_freezer)
    -> promote or reject             (feasibility_report)

The caller supplies:
  candle_loader(symbol)          -> DataFrame[time, open, high, low, close]
  setup_generator(symbol, df)    -> list[Event]
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from .experiment_spec import ExperimentSpec
from .event_matcher import Event, normalize_events
from .paired_controls import evaluate_controls
from .statistical_tests import control_comparison
from .stability_analysis import direction_consistency, profit_concentration, per_group_expectancy
from .feasibility_report import build_report
from .experiment_freezer import freeze_experiment


def run_feasibility(spec: ExperimentSpec,
                    candle_loader: Callable[[str], pd.DataFrame],
                    setup_generator: Callable[[str, pd.DataFrame], list],
                    freeze: bool = True) -> dict:
    problems = spec.validate()
    if problems:
        raise ValueError("Invalid ExperimentSpec: " + "; ".join(problems))

    candles_by_symbol: dict[str, pd.DataFrame] = {}
    all_events: list[Event] = []
    for symbol in spec.symbols:
        df = candle_loader(symbol).reset_index(drop=True)
        candles_by_symbol[symbol] = df
        all_events.extend(setup_generator(symbol, df))

    events = normalize_events(all_events)
    rows = evaluate_controls(candles_by_symbol, events, spec)
    if not rows:
        return {"outcome": "REJECTED_INSUFFICIENT_SAMPLE",
                "reasons": ["No resolvable setups were generated."], "n": 0}

    comparison = control_comparison(rows, spec.grouping_unit)
    n_periods = len({r["period"] for r in rows})
    stability = {
        "symbol_consistency": direction_consistency(rows, "same_direction"),
        "symbol_concentration": profit_concentration(rows, "same_direction", "symbol"),
        "period_concentration": profit_concentration(rows, "same_direction", "period"),
        "per_symbol": per_group_expectancy(rows, "same_direction", "symbol"),
        "per_period": per_group_expectancy(rows, "same_direction", "period"),
    }
    report = build_report(spec, comparison, stability, n_periods)

    if freeze:
        frozen = freeze_experiment(spec, report)
        report["frozen_record"] = {"promotion": frozen["promotion"],
                                   "data_previously_consumed": frozen["data_previously_consumed"]}
    return report
