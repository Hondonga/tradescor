"""Authoritative V1 downgrade behavior for contradictory entry responses."""

from __future__ import annotations

import unittest

from app import _downgrade_invalid_entry_ready


class ReadinessGateTests(unittest.TestCase):
    def test_far_entry_is_downgraded_and_levels_are_removed(self):
        strategy = {
            "state": "ENTRY_READY",
            "trade_decision": "ACCEPT",
            "levels_mode": "final",
            "levels": {
                "entry_zone": {"top": 1.101, "bottom": 1.100},
                "stop_loss": 1.098,
                "tp1": 1.106,
                "rr1": 2.2,
            },
            "overlays": {
                "entry_zone": {"top": 1.101, "bottom": 1.100},
                "stop_loss": 1.098,
                "tp1": 1.106,
            },
        }
        analysis = {
            "trader_answers": {
                "trend": "Bullish",
                "trade_status": "Entry Ready",
                "trade_readiness": "Ready",
                "why": [
                    "Higher timeframes are bullish.",
                    "Price reacted from support.",
                    "The setup and trade objective both meet the current confirmation rules.",
                ],
            },
            "levels": strategy["levels"].copy(),
            "overlays": strategy["overlays"].copy(),
        }

        _downgrade_invalid_entry_ready(
            analysis,
            strategy,
            "EUR/USD",
            ["Entry Ready requires price to be inside or near the valid entry zone."],
        )

        self.assertEqual(analysis["trader_answers"]["trade_status"], "Wait")
        self.assertEqual(strategy["state"], "CONFIRMED_WAITING_FOR_ENTRY")
        self.assertEqual(strategy["levels_mode"], "hidden")
        self.assertIsNone(strategy["levels"]["entry_zone"])
        self.assertIsNone(strategy["overlays"]["tp1"])
        self.assertIn("pull back", analysis["trader_answers"]["next_action"].lower())

    def test_poor_reward_is_rejected(self):
        strategy = {"levels_mode": "final", "levels": {}, "overlays": {}}
        analysis = {
            "trader_answers": {
                "trend": "Bullish",
                "trade_status": "Entry Ready",
                "why": ["Bias is bullish.", "Price is at support.", "Confirmation completed."],
            }
        }

        _downgrade_invalid_entry_ready(
            analysis,
            strategy,
            "EUR/USD",
            ["Entry Ready requires at least 1.50R; current reward is 0.80R."],
        )

        self.assertEqual(analysis["trader_answers"]["trade_status"], "No Trade")
        self.assertEqual(strategy["trade_decision"], "REJECT")


if __name__ == "__main__":
    unittest.main()
