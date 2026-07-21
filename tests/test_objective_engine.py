"""Deterministic checks for objective selection and trade rejection."""

from __future__ import annotations

import unittest

from analysis.objectives import analyze_objectives
from scanner.objective_engine import build_objective_plan


class ObjectiveEngineTests(unittest.TestCase):
    def test_rejects_trade_below_minimum_reward(self):
        plan = build_objective_plan(
            direction="bullish",
            entry_price=100,
            stop_loss=98,
            swings={"highs": [{"price": 101.2}], "lows": []},
        )

        self.assertEqual(plan["decision"], "REJECT")
        self.assertFalse(plan["trade_accepted"])
        self.assertEqual(plan["best_rejected_objective"]["rr"], 0.6)

    def test_prefers_strong_liquidity_objective(self):
        plan = build_objective_plan(
            direction="bullish",
            entry_price=100,
            stop_loss=98,
            swings={"highs": [{"price": 101.2}, {"price": 105}], "lows": []},
            equal_levels={"equal_highs": [{"price": 104.6}], "equal_lows": []},
        )

        self.assertEqual(plan["decision"], "ACCEPT")
        self.assertEqual(plan["primary_objective"]["name"], "Equal Highs")
        self.assertEqual(plan["primary_objective"]["rr"], 2.3)

    def test_supports_bearish_objectives(self):
        plan = build_objective_plan(
            direction="bearish",
            entry_price=100,
            stop_loss=102,
            swings={"highs": [], "lows": [{"price": 96.5}]},
        )

        self.assertEqual(plan["decision"], "ACCEPT")
        self.assertEqual(plan["primary_objective"]["rr"], 1.75)

    def test_shared_objectives_include_strategy_candidates(self):
        plan = analyze_objectives(
            direction="Bullish",
            entry_price=100,
            stop_loss=98,
            shared_analysis={"swings": {}, "liquidity": {}, "zones": {}},
            extra_candidates=[
                {
                    "name": "Measured Move",
                    "price": 105,
                    "source": "measured_move",
                    "probability": 78,
                    "reason": "Range projection.",
                }
            ],
        )

        self.assertEqual(plan["selected_tp1"]["name"], "Measured Move")
        self.assertEqual(plan["selected_tp1"]["rr"], 2.5)

    def test_shared_objectives_require_two_r_for_tp2(self):
        plan = analyze_objectives(
            direction="Bullish",
            entry_price=100,
            stop_loss=98,
            shared_analysis={
                "swings": {"highs": [{"price": 103.2}, {"price": 103.8}], "lows": []},
                "liquidity": {},
                "zones": {},
            },
        )

        self.assertGreaterEqual(plan["selected_tp1"]["rr"], 1.5)
        self.assertEqual(plan["selected_tp2"], {})


if __name__ == "__main__":
    unittest.main()
