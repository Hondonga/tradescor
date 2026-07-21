"""Regression tests for the shared four-strategy contract."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app import app
from tests.test_ict_strategy import candles


STRATEGIES = (
    "universal_structure",
    "ict_2022",
    "supply_demand",
    "breakout_retest",
)

REQUIRED_FIELDS = {
    "strategy_name",
    "bias",
    "state",
    "trade_status",
    "market_clarity",
    "trade_readiness",
    "market_story",
    "next_action",
    "why",
    "levels",
    "levels_mode",
    "overlays",
    "timeline",
    "validation",
}

REQUIRED_LEVELS = {
    "important_zone",
    "trigger_level",
    "invalidation",
    "entry_zone",
    "stop_loss",
    "tp1",
    "tp2",
    "rr1",
    "rr2",
}


class StrategyContractTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def analyze(self, strategy: str, records=None, symbol="EUR/USD"):
        return self.client.post(
            "/api/analyze-replay",
            json={
                "symbol": symbol,
                "timeframe": "M5",
                "strategy": strategy,
                "multi_timeframe": False,
                "candles": records or candles(),
            },
        )

    def test_every_strategy_returns_the_standard_contract(self):
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                response = self.analyze(strategy)
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                result = payload["strategy_result"]
                self.assertFalse(REQUIRED_FIELDS - set(result))
                self.assertFalse(REQUIRED_LEVELS - set(result["levels"]))
                self.assertNotIn("COMING_SOON", result["state"])
                self.assertTrue(payload["answer_validation"]["valid"])

    def test_only_ict_returns_the_ict_checklist(self):
        for strategy in STRATEGIES:
            result = self.analyze(strategy).get_json()["strategy_result"]
            if strategy == "ict_2022":
                self.assertIn("ict_checklist", result)
                self.assertTrue(
                    set(result["ict_checklist"].values())
                    <= {"pass", "fail", "waiting", "unknown"}
                )
            else:
                self.assertNotIn("ict_checklist", result)

    def test_non_ready_strategies_hide_trade_levels(self):
        for strategy in STRATEGIES:
            result = self.analyze(strategy).get_json()["strategy_result"]
            if result["trade_status"] not in {"Entry Ready", "Trade Active"}:
                self.assertEqual(result["levels_mode"], "hidden")
                for key in ("entry_zone", "stop_loss", "tp1", "tp2"):
                    self.assertIsNone(result["levels"][key])

    def test_supply_and_demand_returns_an_active_zone(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        records = []
        for index in range(80):
            if index == 50:
                open_price, close, high, low = 100.0, 99.9, 100.1, 99.7
            elif index == 51:
                open_price, close, high, low = 100.0, 102.0, 102.2, 99.9
            elif index > 51:
                open_price = 102.0 + (index - 52) * 0.035
                close, high, low = open_price + 0.12, open_price + 0.22, open_price - 0.12
            else:
                open_price = 98.0 + index * 0.04
                close, high, low = open_price + 0.08, open_price + 0.18, open_price - 0.12
            records.append(
                {
                    "time": int((start + timedelta(minutes=5 * index)).timestamp()),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                }
            )

        result = self.analyze("supply_demand", records).get_json()["strategy_result"]
        details = result.get("supply_demand_details") or {}
        self.assertTrue(details.get("zone"))
        zone = details["zone"]
        overlay = (result.get("overlays") or {}).get("supply_demand_zone")
        self.assertEqual(zone["type"], "demand")
        self.assertGreaterEqual(zone["impulse_atr"], 1.25)
        self.assertEqual(overlay["tag"], "Demand")
        self.assertEqual(overlay["visual_variant"], "supply-demand")

    def test_breakout_waits_for_retest_after_breakout(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        records = []
        for index in range(60):
            if index < 59:
                center = 99.0 + (index % 7) * 0.5
                open_price = center - 0.1
                close = center + 0.1
                high = center + 0.25
                low = center - 0.25
            else:
                open_price, close, high, low = 101.5, 102.7, 102.9, 101.4
            records.append(
                {
                    "time": int((start + timedelta(minutes=5 * index)).timestamp()),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                }
            )

        result = self.analyze("breakout_retest", records, "S&P 500").get_json()["strategy_result"]
        self.assertEqual(result["state"], "BREAKOUT_CONFIRMED")
        self.assertEqual(result["trade_status"], "Wait")
        self.assertEqual(result["levels_mode"], "hidden")
        self.assertFalse(result["breakout_retest_details"]["retest"])


if __name__ == "__main__":
    unittest.main()
