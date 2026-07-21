"""Symmetry and status regression tests for trade direction handling."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from analysis.direction import (
    build_direction_debug,
    directional_geometry_warnings,
    format_user_status,
    normalize_direction,
)
from app import app
from scanner.dxy_correlation import _expected_symbol_bias
from strategies.supply_demand import _direction as supply_demand_direction


ROOT = Path(__file__).resolve().parents[1]


def trend_records(
    *,
    bullish: bool,
    count: int = 100,
    step: float = 0.08,
    minutes: int = 5,
    end: datetime | None = None,
) -> list[dict[str, float | int]]:
    end = end or datetime(2026, 7, 7, 13, 30, tzinfo=timezone.utc)
    start = end - timedelta(minutes=minutes * (count - 1))
    sign = 1 if bullish else -1
    rows = []
    for index in range(count):
        open_price = 100 + sign * step * index
        close = open_price + sign * step * 0.5
        rows.append(
            {
                "time": int((start + timedelta(minutes=minutes * index)).timestamp()),
                "open": open_price,
                "high": max(open_price, close) + step * 0.8,
                "low": min(open_price, close) - step * 0.8,
                "close": close,
            }
        )
    return rows


def supply_demand_records() -> list[dict[str, float | int]]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
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
        rows.append(
            {
                "time": int((start + timedelta(minutes=5 * index)).timestamp()),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
            }
        )
    return rows


def breakout_records() -> list[dict[str, float | int]]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(60):
        if index < 59:
            center = 99.0 + (index % 7) * 0.5
            open_price, close = center - 0.1, center + 0.1
            high, low = center + 0.25, center - 0.25
        else:
            open_price, close, high, low = 101.5, 102.7, 102.9, 101.4
        rows.append(
            {
                "time": int((start + timedelta(minutes=5 * index)).timestamp()),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
            }
        )
    return rows


def mirrored(records: list[dict[str, float | int]], pivot: float = 200.0) -> list[dict[str, float | int]]:
    return [
        {
            "time": candle["time"],
            "open": pivot - float(candle["open"]),
            "high": pivot - float(candle["low"]),
            "low": pivot - float(candle["high"]),
            "close": pivot - float(candle["close"]),
        }
        for candle in records
    ]


class DirectionHelperTests(unittest.TestCase):
    def test_aliases_are_symmetric_and_unknown_is_neutral(self):
        for value in ("buy", "bullish", "long", "BUY"):
            self.assertEqual(normalize_direction(value), "Buy")
        for value in ("sell", "bearish", "short", "SELL"):
            self.assertEqual(normalize_direction(value), "Sell")
        for value in (None, "", "unclear", "sideways"):
            self.assertEqual(normalize_direction(value), "Neutral")

    def test_user_status_mapping_covers_both_sides(self):
        self.assertEqual(format_user_status(status="WAITING", direction="Bullish", trade_ready=False), "BUY SETUP FORMING")
        self.assertEqual(format_user_status(status="WAITING", direction="Bearish", trade_ready=False), "SELL SETUP FORMING")
        self.assertEqual(format_user_status(status="ENTRY_READY", direction="Buy", trade_ready=True), "READY TO BUY")
        self.assertEqual(format_user_status(status="ENTRY_READY", direction="Sell", trade_ready=True), "READY TO SELL")
        self.assertEqual(format_user_status(status="WAITING", direction=None, trade_ready=False), "NO CLEAN ENTRY")

    def test_unavailable_timing_does_not_invalidate_forming_setup(self):
        self.assertEqual(
            format_user_status(
                status="WAITING_FOR_CONFIRMATION",
                direction="Bullish",
                trade_ready=False,
                timing_status="invalid",
                timing_available=False,
            ),
            "BUY SETUP FORMING",
        )
        self.assertEqual(
            format_user_status(
                status="WAITING_FOR_CONFIRMATION",
                direction="Bullish",
                trade_ready=False,
                timing_status="too_late",
                timing_available=True,
            ),
            "NO CLEAN ENTRY",
        )

    def test_invalid_level_geometry_never_flips_direction(self):
        buy_warnings = directional_geometry_warnings(
            "Bullish",
            {"entry_zone": {"top": 101, "bottom": 99}, "stop_loss": 102, "tp1": 98},
        )
        self.assertIn("Buy setup stop loss must be below the entry zone.", buy_warnings)
        self.assertIn("Buy setup TP1 must be above the entry zone.", buy_warnings)
        debug = build_direction_debug(
            {"bias": "Bullish", "state": "ENTRY_READY", "trade_decision": "ACCEPT", "levels_mode": "final", "levels": {"entry_zone": {"top": 101, "bottom": 99}, "stop_loss": 102, "tp1": 98}},
            {"trader_answers": {"trade_status": "Entry Ready"}},
        )
        self.assertEqual(debug["final_direction"], "Neutral")
        self.assertEqual(debug["user_status"], "NO CLEAN ENTRY")

    def test_neutral_htf_and_unclear_execution_do_not_show_buy_or_sell(self):
        debug = build_direction_debug(
            {"bias": "Bullish", "state": "WAITING_FOR_CONFIRMATION", "trade_decision": "PENDING", "levels_mode": "projected"},
            {
                "selected_timeframe": "M15",
                "top_down_context": {
                    "overall_alignment": "Neutral",
                    "selected_timeframe": "M15",
                    "timeframes": {
                        "D1": {"bias": "Neutral"},
                        "H4": {"bias": "Neutral"},
                        "H1": {"bias": "Neutral"},
                        "M15": {"bias": "Neutral"},
                    },
                },
                "trader_answers": {
                    "higher_timeframe_bias": "Neutral",
                    "execution_timeframe": "M15",
                    "execution_timeframe_trend": "Neutral",
                    "trend": "Unclear",
                    "trade_status": "Wait",
                },
            },
        )

        self.assertEqual(debug["final_direction"], "Neutral")
        self.assertEqual(debug["user_status"], "NO CLEAN ENTRY")
        self.assertTrue(debug["unclear_context"])
        self.assertFalse(debug["directional_setup_forming"])

    def test_bullish_rejection_context_can_form_buy_setup_before_entry_ready(self):
        debug = build_direction_debug(
            {
                "bias": "Bullish",
                "state": "WAITING_FOR_CONFIRMATION",
                "trade_decision": "REJECT",
                "levels_mode": "projected",
                "levels": {
                    "trigger_level": 162.18,
                    "invalidation": 161.89,
                    "tp1": 162.47,
                },
            },
            {
                "selected_timeframe": "M15",
                "top_down_context": {
                    "overall_alignment": "Neutral",
                    "selected_timeframe": "M15",
                    "timeframes": {
                        "D1": {"bias": "Neutral"},
                        "H4": {"bias": "Neutral"},
                        "H1": {"bias": "Neutral"},
                        "M15": {"bias": "Neutral"},
                    },
                },
                "trader_answers": {
                    "higher_timeframe_bias": "Neutral",
                    "execution_timeframe": "M15",
                    "execution_timeframe_trend": "Neutral",
                    "trend": "Unclear",
                    "trade_status": "Wait",
                },
                "entry_timing": {
                    "available": True,
                    "entry_timing_status": "near_entry",
                },
            },
        )

        self.assertEqual(debug["final_direction"], "Buy")
        self.assertEqual(debug["user_status"], "BUY SETUP FORMING")
        self.assertTrue(debug["directional_setup_forming"])
        self.assertNotEqual(debug["user_status"], "READY TO BUY")

    def test_near_entry_without_direction_stays_no_clean_entry(self):
        debug = build_direction_debug(
            {"bias": "Neutral", "state": "WAITING_FOR_CONFIRMATION", "trade_decision": "PENDING", "levels_mode": "projected"},
            {
                "trader_answers": {
                    "higher_timeframe_bias": "Neutral",
                    "execution_timeframe_trend": "Neutral",
                    "trend": "Unclear",
                    "trade_status": "Wait",
                },
                "entry_timing": {
                    "available": True,
                    "entry_timing_status": "near_entry",
                },
            },
        )

        self.assertEqual(debug["final_direction"], "Neutral")
        self.assertEqual(debug["user_status"], "NO CLEAN ENTRY")
        self.assertFalse(debug["directional_setup_forming"])

    def test_supply_demand_tie_and_missing_zones_are_neutral(self):
        self.assertEqual(supply_demand_direction({}, {}, {"demand": [], "supply": []}, 100), "Neutral")
        tied = {
            "demand": [{"price": 99, "status": "fresh"}],
            "supply": [{"price": 101, "status": "fresh"}],
        }
        self.assertEqual(supply_demand_direction({}, {}, tied, 100), "Neutral")

    def test_dxy_handles_any_usd_base_or_quote_pair(self):
        self.assertEqual(_expected_symbol_bias("USD/SGD", "Bullish"), "LONG")
        self.assertEqual(_expected_symbol_bias("SGD/USD", "Bullish"), "SHORT")
        self.assertEqual(_expected_symbol_bias("EUR/JPY", "Bullish"), "NEUTRAL")


class DirectionStrategyFixtureTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def analyze(self, strategy: str, candles, context=None):
        response = self.client.post(
            "/api/analyze-replay",
            json={
                "symbol": "S&P 500",
                "timeframe": "M5",
                "strategy": strategy,
                "multi_timeframe": bool(context),
                "candles": candles,
                "context_candles": context or {},
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_ict_bullish_and_bearish_contexts_are_both_forming(self):
        end = datetime(2026, 7, 7, 13, 30, tzinfo=timezone.utc)
        for bullish, expected_bias, expected_status in (
            (True, "Bullish", "BUY SETUP FORMING"),
            (False, "Bearish", "SELL SETUP FORMING"),
        ):
            selected = trend_records(bullish=bullish, end=end)
            context = {
                "D1": trend_records(bullish=bullish, count=60, step=0.30, minutes=1440, end=end),
                "H4": trend_records(bullish=bullish, count=60, step=0.20, minutes=240, end=end),
                "H1": trend_records(bullish=bullish, count=60, step=0.12, minutes=60, end=end),
                "M15": trend_records(bullish=bullish, count=80, step=0.09, minutes=15, end=end),
                "M5": selected,
            }
            payload = self.analyze("ict_2022", selected, context)
            self.assertEqual(payload["strategy_result"]["bias"], expected_bias)
            self.assertEqual(payload["user_status"], expected_status)

    def test_supply_and_demand_fixture_mirrors_buy_and_sell(self):
        bullish = supply_demand_records()
        buy = self.analyze("supply_demand", bullish)
        sell = self.analyze("supply_demand", mirrored(bullish))
        self.assertEqual(buy["strategy_result"]["bias"], "Bullish")
        self.assertEqual(buy["user_status"], "BUY SETUP FORMING")
        self.assertEqual(sell["strategy_result"]["bias"], "Bearish")
        self.assertEqual(sell["user_status"], "SELL SETUP FORMING")

    def test_breakout_fixture_mirrors_buy_and_sell(self):
        bullish = breakout_records()
        buy = self.analyze("breakout_retest", bullish)
        sell = self.analyze("breakout_retest", mirrored(bullish))
        self.assertEqual(buy["strategy_result"]["bias"], "Bullish")
        self.assertEqual(buy["user_status"], "BUY SETUP FORMING")
        self.assertEqual(sell["strategy_result"]["bias"], "Bearish")
        self.assertEqual(sell["user_status"], "SELL SETUP FORMING")


class DirectionFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javascript = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

    def test_frontend_prefers_backend_direction_and_status(self):
        self.assertIn("analysis.direction_debug?.user_status", self.javascript)
        self.assertIn("analysis.direction_debug?.final_direction", self.javascript)

    def test_frontend_never_defaults_missing_direction_to_sell(self):
        self.assertIn('return "Neutral"', self.javascript)
        self.assertIn('return "SELL SETUP FORMING"', self.javascript)
        self.assertIn('return "NO VALID SETUP"', self.javascript)


if __name__ == "__main__":
    unittest.main()
