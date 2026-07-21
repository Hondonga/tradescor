"""Regression tests for Strategy Lab result identity and stale-result safety."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module

from tests.test_backtesting import _make_candles


ROOT = Path(__file__).resolve().parents[1]


def _successful_engine_result(candle_count: int, mode: str) -> dict[str, object]:
    step = 1 if mode == "accurate" else 15
    return {
        "trades": {"universal_structure": []},
        "diagnostics": {},
        "warnings": [],
        "metadata": {
            "mode": mode,
            "strategy_step": step,
            "analysis_window": 150 if mode == "accurate" else 80,
            "evaluated_candles": 0,
            "total_candles": candle_count,
            "approximate": mode != "accurate",
            "timed_out": False,
        },
        "n_candles": candle_count,
    }


class BacktestApiIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_timeout_returns_no_result(self):
        timed_out = {
            "metadata": {"timed_out": True},
            "trades": {},
            "diagnostics": {},
            "warnings": [],
            "n_candles": 300,
        }
        with (
            patch.object(app_module, "get_candles", return_value=_make_candles(300)),
            patch.object(app_module, "run_backtest", return_value=timed_out),
        ):
            response = self.client.post(
                "/api/backtest",
                json={
                    "symbol": "EUR/USD",
                    "timeframe": "M15",
                    "bars": 1000,
                    "mode": "accurate",
                    "strategies": ["ict_2022"],
                },
            )

        self.assertEqual(response.status_code, 408)
        self.assertEqual(
            response.get_json(),
            {
                "ok": False,
                "error": "Backtest timed out before producing results.",
                "result": None,
            },
        )

    def test_success_returns_exact_result_identity_and_caps_accurate_bars(self):
        candles = _make_candles(300)
        engine_result = _successful_engine_result(300, "accurate")

        with (
            patch.object(app_module, "get_candles", return_value=candles) as get_candles,
            patch.object(app_module, "run_backtest", return_value=engine_result),
        ):
            response = self.client.post(
                "/api/backtest",
                json={
                    "symbol": "EUR/USD",
                    "timeframe": "M15",
                    "bars": 1000,
                    "mode": "accurate",
                    "strategies": ["universal_structure"],
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        identity = payload["result_identity"]
        self.assertEqual(identity["tested_symbol"], "EUR/USD")
        self.assertEqual(identity["tested_timeframe"], "M15")
        self.assertEqual(identity["tested_bars"], 300)
        self.assertEqual(identity["requested_bars"], 1000)
        self.assertEqual(identity["tested_mode"], "accurate")
        self.assertEqual(identity["tested_strategies"], ["universal_structure"])
        self.assertTrue(identity["generated_at"])
        self.assertEqual(get_candles.call_args.kwargs["bars"], 300)


class BacktestFrontendIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javascript = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
        cls.template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    def test_failed_run_clears_old_results(self):
        self.assertIn("function _markLabRunFailed", self.javascript)
        self.assertIn("clearStrategyLabResults();", self.javascript)
        self.assertIn("Previous results are hidden because they do not match", self.javascript)
        self.assertIn(".lab-results[hidden]", self.styles)

    def test_timeout_uses_failed_state_instead_of_old_result(self):
        self.assertIn('err.name === "AbortError"', self.javascript)
        self.assertIn("_markLabRunFailed", self.javascript)
        self.assertIn("No new results were produced", self.javascript)

    def test_config_mismatch_and_ict_selection_trigger_stale_warning(self):
        self.assertIn("_identityMatchesConfig", self.javascript)
        self.assertIn("identity.requested_bars", self.javascript)
        self.assertIn("_sameStrategies(identity.tested_strategies, config.strategies)", self.javascript)
        self.assertIn("Showing previous result. Run Backtest again to update.", self.javascript)

    def test_accurate_helper_is_candle_by_candle(self):
        self.assertIn(
            "Accurate Mode checks every candle and is capped at 300 bars to prevent timeout.",
            self.template,
        )
        self.assertNotIn("Accurate checks every 5 candles", self.template + self.javascript)

    def test_running_state_displays_exact_pending_config(self):
        self.assertIn("Pending config", self.javascript)
        self.assertIn("selected strategies:", self.javascript)
        self.assertIn("tested_symbol:", self.javascript)
        self.assertIn("tested_strategies:", self.javascript)


if __name__ == "__main__":
    unittest.main()
