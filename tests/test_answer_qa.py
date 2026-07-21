"""Validation checks for trader-facing market answers."""

from __future__ import annotations

import unittest

from analysis.answer_qa import validate_answers


def answers(**overrides):
    value = {
        "trend": "Bullish",
        "price_location": "At support",
        "market_intent": "Pulling back into support",
        "trade_status": "Wait",
        "next_action": "Wait for a close above the recent swing high.",
        "why": ["Higher timeframes are bullish.", "Price is at support.", "Confirmation is missing."],
    }
    value.update(overrides)
    return value


class AnswerValidationTests(unittest.TestCase):
    def test_valid_waiting_answer(self):
        result = validate_answers(
            trader_answers=answers(),
            strategy_result={"bias": "Bullish", "levels_mode": "hidden", "levels": {}},
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["warnings"], [])

    def test_entry_ready_requires_confirmation(self):
        result = validate_answers(
            trader_answers=answers(trade_status="Entry Ready"),
            strategy_result={
                "bias": "Bullish",
                "levels_mode": "final",
                "levels": {"entry_zone": {"top": 101, "bottom": 100}},
                "overlays": {},
            },
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertFalse(result["valid"])
        self.assertIn("Entry Ready requires a visible confirmation trigger.", result["warnings"])

    def test_no_trade_cannot_expose_levels(self):
        result = validate_answers(
            trader_answers=answers(trade_status="No Trade"),
            strategy_result={
                "bias": "Bullish",
                "levels_mode": "final",
                "levels": {"entry_zone": {"top": 101, "bottom": 100}, "stop_loss": 99},
            },
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertFalse(result["valid"])
        self.assertIn("No Trade must not expose entry, stop-loss, or target levels.", result["warnings"])

    def test_wait_requires_next_action(self):
        result = validate_answers(
            trader_answers=answers(next_action=""),
            strategy_result={"bias": "Bullish", "levels_mode": "hidden", "levels": {}},
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertFalse(result["valid"])
        self.assertIn("Wait requires a next action.", result["warnings"])

    def test_invalidated_is_a_supported_status(self):
        result = validate_answers(
            trader_answers=answers(
                trade_status="Invalidated",
                next_action="Wait for a fresh sequence.",
            ),
            strategy_result={"bias": "Bullish", "levels_mode": "hidden", "levels": {}},
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertTrue(result["valid"])

    def test_complete_entry_ready_answer_is_valid(self):
        result = validate_answers(
            trader_answers=answers(
                trade_status="Entry Ready",
                market_story="EUR/USD remains bullish and price is inside the confirmed entry zone.",
            ),
            strategy_result={
                "bias": "Bullish",
                "state": "ENTRY_READY",
                "trade_decision": "ACCEPT",
                "levels_mode": "final",
                "confirmation_achieved": True,
                "entry_proximity": True,
                "levels": {
                    "entry_zone": {"top": 1.1010, "bottom": 1.1000},
                    "stop_loss": 1.0980,
                    "tp1": 1.1060,
                    "rr1": 2.2,
                },
                "overlays": {
                    "current_price": {"price": 1.1005},
                    "confirmation_level": {"price": 1.1020},
                },
            },
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertTrue(result["valid"])

    def test_entry_ready_rejects_unclear_trend_and_story(self):
        result = validate_answers(
            trader_answers=answers(
                trend="Unclear",
                trade_status="Entry Ready",
                market_story="Structure is mixed with no reliable trend.",
            ),
            strategy_result=_ready_strategy(),
            analysis={},
            top_down_context={"overall_alignment": "Mixed"},
        )

        self.assertFalse(result["valid"])
        self.assertIn("Entry Ready requires a clear bullish or bearish trend.", result["warnings"])
        self.assertIn("Entry Ready conflicts with an unclear or mixed market story.", result["warnings"])

    def test_entry_ready_rejects_poor_reward_and_far_price(self):
        strategy = _ready_strategy()
        strategy["entry_proximity"] = False
        strategy["levels"]["rr1"] = 0.8
        result = validate_answers(
            trader_answers=answers(
                trade_status="Entry Ready",
                market_story="EUR/USD remains bullish with clear structure.",
            ),
            strategy_result=strategy,
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertFalse(result["valid"])
        self.assertTrue(any("at least 1.50R" in warning for warning in result["warnings"]))
        self.assertTrue(any("inside or near" in warning for warning in result["warnings"]))

    def test_wait_cannot_expose_final_levels(self):
        result = validate_answers(
            trader_answers=answers(trade_status="Wait"),
            strategy_result=_ready_strategy(),
            analysis={},
            top_down_context={"overall_alignment": "Bullish"},
        )

        self.assertFalse(result["valid"])
        self.assertIn("Wait must not expose entry, stop-loss, or target levels.", result["warnings"])


def _ready_strategy():
    return {
        "bias": "Bullish",
        "state": "ENTRY_READY",
        "trade_decision": "ACCEPT",
        "levels_mode": "final",
        "confirmation_achieved": True,
        "entry_proximity": True,
        "levels": {
            "entry_zone": {"top": 1.1010, "bottom": 1.1000},
            "stop_loss": 1.0980,
            "tp1": 1.1060,
            "rr1": 2.2,
        },
        "overlays": {
            "current_price": {"price": 1.1005},
            "confirmation_level": {"price": 1.1020},
        },
    }


if __name__ == "__main__":
    unittest.main()
