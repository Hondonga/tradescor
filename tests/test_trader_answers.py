"""Checks for the plain-language Trader Answers contract."""

from __future__ import annotations

import unittest

from analysis.trader_answers import (
    actionable_rejection_instruction,
    actionable_wait_instruction,
    build_trader_answers,
)


class TraderAnswersTests(unittest.TestCase):
    def setUp(self):
        self.shared = {
            "candles_count": 100,
            "trend": {"direction": "Bullish"},
            "current": {
                "current_price": 100.0,
                "range_high": 106.0,
                "range_low": 96.0,
                "range_midpoint": 101.0,
            },
            "zones": {
                "nearest_support": {"bottom_price": 99.5, "top_price": 100.5},
                "nearest_resistance": {"bottom_price": 105.0, "top_price": 106.0},
            },
            "structure": {},
            "liquidity": {"latest_sweep": {}},
            "volatility": {"health": "Healthy"},
        }
        self.top_down = {
            "overall_alignment": "Bullish",
            "conflicts": [],
            "timeframes": {
                "D1": {"bias": "Bullish", "status": "Trend"},
                "H4": {"bias": "Bullish", "status": "Trend"},
                "M15": {"bias": "Bearish", "status": "Pullback"},
            },
        }

    def test_separates_bullish_htf_bias_from_bearish_execution_pullback(self):
        answers = build_trader_answers(
            symbol="EUR/USD",
            timeframe="M15",
            shared_analysis=self.shared,
            strategy_result={
                "bias": "Bullish",
                "state": "WAITING_FOR_CONFIRMATION",
                "trade_decision": "PENDING",
                "levels_mode": "hidden",
                "next_trigger": "Wait for a close above the recent swing high",
            },
            analysis={},
            top_down_context=self.top_down,
        )

        self.assertEqual(answers["higher_timeframe_bias"], "Bullish")
        self.assertEqual(answers["trend"], "Bearish")
        self.assertEqual(answers["execution_timeframe_trend"], "Bearish")
        self.assertEqual(answers["execution_description"], "Bearish pullback")
        self.assertEqual(answers["timeframe_alignment"], "Counter-trend")
        self.assertEqual(answers["price_location"], "Pullback into support")
        self.assertIn("pullback against bullish", answers["market_intent"].lower())
        self.assertEqual(answers["trade_status"], "No Trade")
        self.assertEqual(answers["trade_readiness"], "Not Ready")
        self.assertIn("D1 and H4 are bullish", answers["top_down_summary"])
        self.assertIn("bullish higher-timeframe bias", answers["market_story"])
        self.assertIn("M15 execution is bearish", answers["market_story"])
        self.assertNotIn("higher-timeframe direction is not confirmed", " ".join(answers["why"]).lower())
        self.assertGreaterEqual(len(answers["why"]), 3)
        self.assertLessEqual(len(answers["why"]), 5)

    def test_aligned_timeframes_preserve_directional_status(self):
        self.top_down["timeframes"]["M15"] = {"bias": "Bullish", "status": "Trend"}
        answers = build_trader_answers(
            symbol="EUR/USD",
            timeframe="M15",
            shared_analysis=self.shared,
            strategy_result={
                "bias": "Bullish",
                "state": "WAITING_FOR_CONFIRMATION",
                "trade_decision": "PENDING",
                "levels_mode": "hidden",
            },
            analysis={},
            top_down_context=self.top_down,
        )

        self.assertEqual(answers["higher_timeframe_bias"], "Bullish")
        self.assertEqual(answers["trend"], "Bullish")
        self.assertEqual(answers["timeframe_alignment"], "Aligned")
        self.assertEqual(answers["trade_status"], "Almost Ready")

    def test_rejected_trade_is_explained_as_no_trade(self):
        answers = build_trader_answers(
            symbol="EUR/USD",
            timeframe="M15",
            shared_analysis=self.shared,
            strategy_result={
                "bias": "Bullish",
                "state": "ENTRY_READY",
                "trade_decision": "REJECT",
                "levels_mode": "hidden",
                "objective_plan": {
                    "decision": "REJECT",
                    "reason": "Best objective offers only 0.70R.",
                },
            },
            analysis={},
            top_down_context=self.top_down,
        )

        self.assertEqual(answers["trade_status"], "No Trade")
        self.assertEqual(answers["trade_readiness"], "Not Ready")
        self.assertIn("trade status is no trade", answers["market_story"].lower())
        self.assertIn("Best objective offers only 0.70R.", answers["why"])

    def test_wait_sell_action_names_trigger_and_break_direction(self):
        action = actionable_wait_instruction(
            symbol="EUR/USD",
            timeframe="M15",
            direction="Bearish",
            trigger_level=1.14307,
            precision=5,
        )

        self.assertEqual(
            action,
            "Wait for EUR/USD to break below 1.14307 and hold. "
            "Do not enter until M15 confirms bearish continuation.",
        )

    def test_wait_buy_action_names_trigger_and_break_direction(self):
        action = actionable_wait_instruction(
            symbol="USD/JPY",
            timeframe="M5",
            direction="Bullish",
            trigger_level=162.18,
            precision=3,
        )

        self.assertIn("break above 162.180 and hold", action)
        self.assertIn("M5 confirms bullish continuation", action)

    def test_rejected_setup_names_level_without_presenting_entry(self):
        action = actionable_rejection_instruction(
            symbol="EUR/USD",
            direction="Bearish",
            trigger_level=1.14307,
            precision=5,
        )

        self.assertIn("Do not trade the EUR/USD break below 1.14307", action)
        self.assertIn("projected reward is insufficient", action)
        self.assertIn("at least 1.50R", action)


if __name__ == "__main__":
    unittest.main()
