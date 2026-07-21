"""Automatic strategy selection tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from strategies import auto_strategy, normalize_strategy_key
from strategies.base import make_strategy_result


def candidate(name: str, **updates):
    result = make_strategy_result(
        strategy_name=name,
        bias="Bullish",
        state="WAITING_FOR_CONFIRMATION",
        score=60,
        market_story="A model is developing.",
        next_trigger="Wait for confirmation.",
    )
    result.update(updates)
    return result


class AutoStrategyTests(unittest.TestCase):
    def setUp(self):
        self.candles = pd.DataFrame(
            [{"time": 1, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0}]
        )
        self.kwargs = {
            "symbol": "EUR/USD",
            "timeframe": "M5",
            "macro_context": {},
            "top_down_context": {},
        }

    def test_auto_is_normalized_and_is_default(self):
        self.assertEqual(normalize_strategy_key("auto"), "auto")
        self.assertEqual(normalize_strategy_key(None), "auto")

    def test_derived_manual_models_preserve_request_identity(self):
        self.assertEqual(normalize_strategy_key("volatility_smc"), "volatility_smc")
        self.assertEqual(
            normalize_strategy_key("volatility_structure_pullback"),
            "volatility_structure_pullback",
        )
        self.assertEqual(normalize_strategy_key("jump_smc"), "jump_smc")
        self.assertEqual(normalize_strategy_key("step_smc"), "step_smc")

    @patch("strategies.auto_strategy.breakout_retest.analyze")
    @patch("strategies.auto_strategy.supply_demand.analyze")
    @patch("strategies.auto_strategy.ict_2022.analyze")
    def test_ict_precision_wins_when_context_aligns(self, ict, supply, breakout):
        ict.return_value = (
            candidate(
                "ICT 2022 Model",
                ict_checklist={"kill_zone": "pass", "liquidity_swept": "pass", "fvg": "pass"},
            ),
            {"legacy": True},
        )

        result, legacy = auto_strategy.analyze(self.candles, {}, **self.kwargs)

        self.assertEqual(result["selected_strategy"], "ICT Precision")
        self.assertEqual(result["selected_strategy_key"], "ict_2022")
        self.assertIn("Liquidity sweep", result["strategy_reason"])
        self.assertEqual(legacy, {"legacy": True})
        supply.assert_not_called()
        breakout.assert_not_called()

    @patch("strategies.auto_strategy.breakout_retest.analyze")
    @patch("strategies.auto_strategy.supply_demand.analyze")
    @patch("strategies.auto_strategy.ict_2022.analyze")
    def test_supply_and_demand_is_selected_for_valid_zone(self, ict, supply, breakout):
        ict.return_value = (candidate("ICT", ict_checklist={}), None)
        supply.return_value = (
            candidate(
                "Supply & Demand",
                state="PRICE_IN_ZONE",
                supply_demand_details={"zone_quality": {"valid": True}},
            ),
            None,
        )

        result, _legacy = auto_strategy.analyze(self.candles, {}, **self.kwargs)

        self.assertEqual(result["selected_strategy_key"], "supply_demand")
        self.assertIn("supply or demand zone", result["strategy_reason"])
        breakout.assert_not_called()

    @patch("strategies.auto_strategy.breakout_retest.analyze")
    @patch("strategies.auto_strategy.supply_demand.analyze")
    @patch("strategies.auto_strategy.ict_2022.analyze")
    def test_breakout_requires_break_and_retest(self, ict, supply, breakout):
        ict.return_value = (candidate("ICT", ict_checklist={}), None)
        supply.return_value = (candidate("Supply", state="NO_TRADE"), None)
        breakout.return_value = (
            candidate(
                "Breakout & Retest",
                state="RETEST_ACTIVE",
                breakout_retest_details={
                    "breakout": {"level": 1.1},
                    "retest": {"time": 2},
                    "failed_breakout": False,
                },
            ),
            None,
        )

        result, _legacy = auto_strategy.analyze(self.candles, {}, **self.kwargs)

        self.assertEqual(result["selected_strategy_key"], "breakout_retest")
        self.assertIn("broken a defined range", result["strategy_reason"])

    @patch("strategies.auto_strategy.universal_structure.analyze")
    @patch("strategies.auto_strategy.breakout_retest.analyze")
    @patch("strategies.auto_strategy.supply_demand.analyze")
    @patch("strategies.auto_strategy.ict_2022.analyze")
    def test_fallback_is_structure_context_without_trade_plan(self, ict, supply, breakout, structure):
        ict.return_value = (candidate("ICT", ict_checklist={}), None)
        supply.return_value = (candidate("Supply", state="NO_TRADE"), None)
        breakout.return_value = (
            candidate("Breakout", state="WAITING_FOR_BREAKOUT", breakout_retest_details={}),
            None,
        )
        structure.return_value = (
            candidate(
                "Universal Structure",
                state="ENTRY_READY",
                levels_mode="final",
                levels={"entry_zone": {"top": 1.0, "bottom": 0.9}, "stop_loss": 0.8, "tp1": 1.2},
                trade_decision="ACCEPT",
            ),
            None,
        )

        result, _legacy = auto_strategy.analyze(self.candles, {}, **self.kwargs)

        self.assertEqual(result["selected_strategy"], "Structure Context")
        self.assertEqual(result["selected_strategy_key"], "universal_structure")
        self.assertEqual(result["levels_mode"], "hidden")
        self.assertEqual(result["trade_decision"], "PENDING")
        self.assertIsNone(result["levels"]["entry_zone"])
        self.assertIn("No clean specialist strategy", result["strategy_reason"])


if __name__ == "__main__":
    unittest.main()
