"""ICT-only state and API contract regression tests."""

from __future__ import annotations

import math
import unittest
from datetime import datetime, timedelta, timezone

from app import app
from scanner.ict_checklist import build_ict_checklist, classify_ict_state
from strategies.ict_2022 import _ict_trader_answers


def checklist(**overrides):
    values = {
        "htf_bias_confirmed": True,
        "kill_zone_active": True,
        "liquidity_pool_identified": True,
        "liquidity_swept": True,
        "choch_confirmed": True,
        "fvg_present": True,
        "order_block_present": True,
        "order_block_valid": True,
        "ote_available": True,
        "ote_aligned": True,
        "dxy_status": "Waiting",
        "news_enabled": False,
        "news_restricted": False,
        "risk_reward": 2.0,
    }
    values.update(overrides)
    return build_ict_checklist(**values)


def candles(count=140):
    start = datetime(2026, 6, 20, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        base = 1.15 + index * 0.00004 + math.sin(index / 7) * 0.0012
        close = base + math.sin(index / 3) * 0.00025
        rows.append(
            {
                "time": int((start + timedelta(minutes=5 * index)).timestamp()),
                "open": round(base, 6),
                "high": round(max(base, close) + 0.00035, 6),
                "low": round(min(base, close) - 0.00035, 6),
                "close": round(close, 6),
            }
        )
    return rows


class IctStateTests(unittest.TestCase):
    def test_state_follows_required_sequence(self):
        self.assertEqual(
            classify_ict_state(checklist(kill_zone_active=False)),
            "WAITING_FOR_KILL_ZONE",
        )
        self.assertEqual(
            classify_ict_state(checklist(liquidity_swept=False)),
            "WAITING_FOR_LIQUIDITY_SWEEP",
        )
        self.assertEqual(
            classify_ict_state(checklist(choch_confirmed=False)),
            "WAITING_FOR_CHOCH",
        )
        self.assertEqual(
            classify_ict_state(checklist(fvg_present=False, order_block_valid=False)),
            "WAITING_FOR_FVG_OR_OB",
        )
        self.assertEqual(
            classify_ict_state(checklist(ote_aligned=False)),
            "WAITING_FOR_OTE",
        )
        self.assertEqual(classify_ict_state(checklist()), "ENTRY_READY")

    def test_rejected_reward_is_no_trade(self):
        self.assertEqual(
            classify_ict_state(checklist(risk_reward=0.8)),
            "NO_TRADE",
        )


class StrategyIsolationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.candles = candles()

    def analyze(self, strategy):
        return self.client.post(
            "/api/analyze-replay",
            json={
                "symbol": "EUR/USD",
                "timeframe": "M5",
                "strategy": strategy,
                "multi_timeframe": False,
                "candles": self.candles,
            },
        )

    def test_universal_response_has_no_ict_details(self):
        response = self.analyze("universal_structure")
        self.assertEqual(response.status_code, 200)
        result = response.get_json()["strategy_result"]
        self.assertNotIn("ict_checklist", result)
        self.assertNotIn("ict_details", result)

    def test_ict_response_is_strategy_specific_and_gates_levels(self):
        response = self.analyze("ict_2022")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        result = payload["strategy_result"]

        self.assertEqual(result["strategy_name"], "ICT 2022 Model")
        self.assertIn("ict_checklist", result)
        self.assertIn("ict_details", result)
        self.assertTrue(payload["answer_validation"]["valid"])

        if result["state"] not in {"ENTRY_READY", "TRADE_ACTIVE"}:
            self.assertEqual(result["levels_mode"], "hidden")
            for key in ("entry_zone", "stop_loss", "tp1", "tp2"):
                self.assertIsNone(result["levels"][key])


class IctNarrativeAlignmentTests(unittest.TestCase):
    def test_counter_trend_story_explains_htf_and_execution_separately(self):
        timeframe_view = {
            "higher_timeframe_bias": "Bullish",
            "execution_timeframe": "M5",
            "execution_timeframe_trend": "Bearish",
            "execution_description": "Bearish pullback",
            "timeframe_alignment": "Counter-trend",
            "alignment_summary": "Higher-timeframe bias is bullish, but M5 execution is bearish and not aligned yet.",
        }
        ict_checks = {
            "htf_bias": "pass",
            "kill_zone": "fail",
            "liquidity_pool": "pass",
            "liquidity_swept": "waiting",
            "choch": "waiting",
            "fvg": "pass",
            "ob_valid": "waiting",
            "ote": "waiting",
            "dxy": "unknown",
            "news": "unknown",
            "risk_reward": "waiting",
            "execution_alignment": "fail",
        }
        answers = _ict_trader_answers(
            "USD/JPY",
            "Bullish",
            "NO_TRADE",
            ict_checks,
            {},
            "Wait for M5 to realign with the bullish higher-timeframe bias.",
            {"summary": "D1/H4/H1 bullish while M5 is bearish."},
            timeframe_view,
        )

        self.assertEqual(answers["higher_timeframe_bias"], "Bullish")
        self.assertEqual(answers["trend"], "Bearish")
        self.assertEqual(answers["trade_status"], "No Trade")
        self.assertIn("bullish higher-timeframe ICT bias", answers["market_story"])
        self.assertIn("M5 execution is bearish", answers["market_story"])
        self.assertNotIn("higher-timeframe direction is not confirmed", " ".join(answers["why"]).lower())


if __name__ == "__main__":
    unittest.main()
