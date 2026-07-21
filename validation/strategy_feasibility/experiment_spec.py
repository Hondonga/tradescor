"""Experiment specification — frozen contract for one feasibility run.

Parameters MUST be frozen before the run. The spec records the exact strategy
version, engine version, symbols, window, hypothesis, grouping unit, controls
and cost model, so a result can never be silently re-tuned and re-reported as
independent evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


VALID_GROUPING_UNITS = {"event_id", "structural_episode", "day", "symbol_period"}
VALID_CONTROLS = {
    "same_direction",            # the actual strategy direction
    "paired_opposite_direction", # same event/timing/geometry, direction flipped
    "random_direction",          # seeded random assignment
    "geometry_only",             # same selection + R:R, direction thesis removed
}


@dataclass
class ExperimentSpec:
    experiment_id: str
    strategy_id: str
    strategy_version: str
    engine_version: str
    symbols: list[str]
    start_time: str
    end_time: str
    hypothesis: str
    primary_metric: str = "expectancy_R"
    grouping_unit: str = "event_id"
    control_methods: list[str] = field(
        default_factory=lambda: ["paired_opposite_direction", "random_direction", "geometry_only"]
    )
    cost_model: dict = field(default_factory=lambda: {"type": "per_trade_R", "cost_R": 0.0002})
    parameters_frozen_before_run: bool = True
    parameters: dict = field(default_factory=dict)
    # acceptance thresholds (screening, not law)
    min_resolved_trades: int = 200
    min_independent_periods: int = 8
    max_single_symbol_profit_share: float = 0.60
    max_single_period_profit_share: float = 0.60
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> list[str]:
        problems = []
        if not self.parameters_frozen_before_run:
            problems.append("parameters_frozen_before_run must be True before a run.")
        if self.grouping_unit not in VALID_GROUPING_UNITS:
            problems.append(f"grouping_unit must be one of {sorted(VALID_GROUPING_UNITS)}.")
        unknown = set(self.control_methods) - VALID_CONTROLS
        if unknown:
            problems.append(f"unknown control_methods: {sorted(unknown)}.")
        if "paired_opposite_direction" not in self.control_methods:
            problems.append("paired_opposite_direction control is mandatory for a directional test.")
        if "random_direction" not in self.control_methods:
            problems.append("random_direction control is mandatory.")
        if not self.symbols:
            problems.append("at least one symbol is required.")
        if not self.engine_version:
            problems.append("engine_version must be recorded (results are engine-bound).")
        return problems

    def parameter_hash(self) -> str:
        payload = json.dumps({"parameters": self.parameters, "cost_model": self.cost_model,
                              "strategy_version": self.strategy_version,
                              "engine_version": self.engine_version}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)
