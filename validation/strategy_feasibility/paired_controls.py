"""Mandatory matched controls.

For every Event, the same entry / timing / risk / cost is evaluated under each
direction assignment. Only direction differs, so a difference between arms is
attributable to direction, not to a different event set or geometry.

Controls:
  same_direction            -> the strategy's native call
  paired_opposite_direction -> native flipped
  random_direction          -> seeded deterministic random sign
  geometry_only             -> direction thesis removed; averages both signs,
                               isolating whatever the selection + R:R alone yield
"""
from __future__ import annotations

import numpy as np

from .event_matcher import Event
from .symmetric_geometry import build_symmetric_geometry
from .forward_simulator import simulate_outcome


def evaluate_controls(candles_by_symbol: dict, events: list[Event], spec, seed: int = 7) -> list[dict]:
    rng = np.random.default_rng(seed)
    risk_atr = float(spec.parameters.get("risk_atr", 1.0))
    rr = float(spec.parameters.get("rr", 1.5))
    window = int(spec.parameters.get("outcome_window", 120))
    rows = []
    for ev in events:
        candles = candles_by_symbol[ev.symbol]
        record = {"symbol": ev.symbol, "event_id": ev.event_id, "day": ev.day,
                  "period": ev.period, "structural_episode": ev.structural_episode,
                  "native_direction": ev.native_direction}

        def run(direction):
            geo = build_symmetric_geometry(ev.entry_price, ev.atr, direction, risk_atr, rr)
            return simulate_outcome(candles, ev.entry_index, geo, window, spec.cost_model, ev.atr)

        same = run(ev.native_direction)
        opp = run(-ev.native_direction)
        rnd = run(int(rng.choice([-1, 1])))
        if same is None or opp is None or rnd is None:
            continue
        record["same_direction"] = same["net_r"]
        record["paired_opposite_direction"] = opp["net_r"]
        record["random_direction"] = rnd["net_r"]
        # geometry_only: mean of both directions removes the directional thesis
        record["geometry_only"] = 0.5 * (same["net_r"] + opp["net_r"])
        record["resolution"] = same["resolution"]
        rows.append(record)
    return rows
