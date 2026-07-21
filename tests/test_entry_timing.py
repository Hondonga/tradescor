"""Entry timing engine and UI contract tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from analysis.entry_timing import evaluate_entry_timing
from app import _apply_entry_timing_gate


ROOT = Path(__file__).resolve().parents[1]


def timing(**overrides):
    values = {
        "symbol": "EUR/USD",
        "asset_type": "forex",
        "direction": "Bullish",
        "current_price": 1.1000,
        "entry_zone": {"bottom": 1.0998, "top": 1.1002},
        "trigger_level": 1.1000,
        "stop_loss": 1.0980,
        "tp1": 1.1040,
        "tp2": 1.1060,
        "atr": 0.0010,
    }
    values.update(overrides)
    return evaluate_entry_timing(**values)


class EntryTimingEngineTests(unittest.TestCase):
    def test_buy_setup_at_entry(self):
        result = timing()
        self.assertEqual(result["entry_timing_status"], "at_entry")
        self.assertTrue(result["can_enter_now"])
        self.assertEqual(result["message"], "Price is inside the entry zone. Confirm risk before entering.")

    def test_near_entry_uses_standard_wording(self):
        result = timing(current_price=1.10025)
        self.assertEqual(result["entry_timing_status"], "near_entry")
        self.assertEqual(
            result["message"],
            "Price is near the entry zone. Entry may still be valid if risk/reward holds.",
        )

    def test_extended_uses_standard_wording(self):
        result = timing(current_price=1.1008)
        self.assertEqual(result["entry_timing_status"], "extended")
        self.assertEqual(
            result["message"],
            "Price has moved away from entry. Do not chase. Look for a pullback.",
        )

    def test_buy_setup_far_above_entry(self):
        result = timing(current_price=1.1025)
        self.assertIn(result["entry_timing_status"], {"extended", "too_late"})
        self.assertFalse(result["can_enter_now"])
        self.assertIn("pullback", result["next_action"].lower())

    def test_buy_setup_past_tp1_is_missed(self):
        result = timing(current_price=1.1041)
        self.assertEqual(result["entry_timing_status"], "missed")
        self.assertFalse(result["can_enter_now"])
        self.assertEqual(result["message"], "Setup already moved to target area. Look for the next setup.")

    def test_invalid_setup_uses_standard_wording(self):
        result = timing(current_price=1.0979)
        self.assertEqual(result["entry_timing_status"], "invalid")
        self.assertEqual(result["message"], "Setup is invalidated. Do not enter.")

    def test_sell_setup_at_entry(self):
        result = timing(
            direction="Bearish",
            current_price=1.1000,
            stop_loss=1.1020,
            tp1=1.0960,
            tp2=1.0940,
        )
        self.assertEqual(result["entry_timing_status"], "at_entry")
        self.assertTrue(result["can_enter_now"])

    def test_sell_setup_far_below_entry(self):
        result = timing(
            direction="Bearish",
            current_price=1.0975,
            stop_loss=1.1020,
            tp1=1.0960,
            tp2=1.0940,
        )
        self.assertIn(result["entry_timing_status"], {"extended", "too_late"})
        self.assertFalse(result["can_enter_now"])

    def test_current_rr_below_one_blocks_entry(self):
        result = timing(current_price=1.1030)
        self.assertLess(result["remaining_rr_to_tp1"], 1.0)
        self.assertEqual(result["entry_timing_status"], "too_late")
        self.assertFalse(result["can_enter_now"])

    def test_usd_jpy_screenshot_scenario_is_not_chaseable(self):
        result = timing(
            symbol="USD/JPY",
            direction="buy",
            current_price=162.323,
            entry_zone={"bottom": 161.970, "top": 161.990},
            trigger_level=161.980,
            stop_loss=161.940,
            tp1=162.673,
            tp2=163.000,
            atr=None,
        )
        self.assertIn(result["entry_timing_status"], {"extended", "too_late"})
        self.assertFalse(result["can_enter_now"])
        self.assertEqual(
            result["message"],
            "Price already moved away from the entry area.",
        )
        self.assertEqual(
            result["next_action"],
            "Do not chase. Look for a fresh entry or a clean pullback.",
        )
        self.assertEqual(result["distance_from_entry_pips"], 34.3)

    def test_too_late_downgrades_entry_ready_and_marks_avoid(self):
        timing_result = timing(current_price=1.1030)
        analysis = {
            "entry_timing": timing_result,
            "trader_answers": {
                "trade_status": "Entry Ready",
                "trade_readiness": "Ready",
                "market_story": "A bullish setup is technically confirmed.",
                "next_action": "Enter now.",
                "why": [],
            },
            "levels": {"entry_zone": {}, "stop_loss": 1.098, "tp1": 1.104, "tp2": 1.106},
            "overlays": {"levels_mode": "final"},
            "trade_metrics": {"plan_mode": "final", "warnings": []},
        }
        strategy = {
            "state": "ENTRY_READY",
            "trade_decision": "ACCEPT",
            "levels_mode": "final",
            "overlays": {"levels_mode": "final"},
            "market_story": analysis["trader_answers"]["market_story"],
        }

        changed = _apply_entry_timing_gate(analysis, strategy)

        self.assertTrue(changed)
        self.assertEqual(analysis["trader_answers"]["trade_status"], "Wait")
        self.assertEqual(strategy["levels_mode"], "projected")
        self.assertEqual(strategy["entry_timing_action"], "AVOID")
        self.assertIn("pullback", analysis["trader_answers"]["next_action"].lower())


class EntryTimingUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "static" / "style.css").read_text(encoding="utf-8")

    def test_decision_panel_has_one_entry_timing_section(self):
        self.assertEqual(self.template.count('id="decision-timing"'), 1)
        self.assertIn("function formatTiming", self.javascript)

    def test_chart_uses_banner_without_duplicate_too_late_badge(self):
        self.assertIn('raw.includes("late")', self.javascript)
        self.assertNotIn("function drawEntryTimingOverlay", self.javascript)
        self.assertIn('return "Too late"', self.javascript)

    def test_extended_is_forming_and_too_late_has_no_clean_entry(self):
        self.assertIn('return "NO VALID SETUP"', self.javascript)
        self.assertIn('return "BUY SETUP FORMING"', self.javascript)
        self.assertIn('return "SELL SETUP FORMING"', self.javascript)

    def test_too_late_uses_requested_action_language(self):
        self.assertIn('raw.includes("chase")', self.javascript)
        self.assertIn('return "Too late"', self.javascript)


if __name__ == "__main__":
    unittest.main()
