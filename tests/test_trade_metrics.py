"""Tests for Scanner risk and target distance metrics."""

from __future__ import annotations

import unittest

from analysis.trade_metrics import build_trade_metrics
from app import app
from tests.test_ict_strategy import candles


class TradeMetricsTests(unittest.TestCase):
    def test_jpy_pair_uses_point_zero_one_pip(self):
        metrics = build_trade_metrics(
            symbol="USD/JPY",
            asset_type="forex",
            direction="Bullish",
            levels_mode="final",
            levels={
                "entry_zone": {"top": 162.18, "bottom": 162.18},
                "stop_loss": 161.89,
                "tp1": 162.47,
                "tp2": 162.76,
            },
        )

        self.assertEqual(metrics["unit_size"], 0.01)
        self.assertEqual(metrics["risk"]["value"], 29.0)
        self.assertEqual(metrics["tp1"]["distance"]["value"], 29.0)
        self.assertEqual(metrics["tp1"]["risk_reward"], 1.0)
        self.assertEqual(metrics["tp2"]["distance"]["value"], 58.0)
        self.assertEqual(metrics["tp2"]["risk_reward"], 2.0)

    def test_non_jpy_forex_uses_point_zero_zero_zero_one_pip(self):
        metrics = build_trade_metrics(
            symbol="EUR/USD",
            asset_type="forex",
            direction="Bullish",
            levels_mode="final",
            levels={
                "entry_zone": {"top": 1.1000, "bottom": 1.1000},
                "stop_loss": 1.0970,
                "tp1": 1.1060,
                "tp2": None,
            },
        )

        self.assertEqual(metrics["unit_size"], 0.0001)
        self.assertEqual(metrics["risk"]["display"], "30 pips")
        self.assertEqual(metrics["tp1"]["distance"]["display"], "60 pips")
        self.assertEqual(metrics["tp1"]["risk_reward"], 2.0)
        self.assertIsNone(metrics["tp2"])

    def test_hidden_levels_do_not_publish_projected_metrics(self):
        metrics = build_trade_metrics(
            symbol="USD/JPY",
            asset_type="forex",
            direction="Bullish",
            levels_mode="hidden",
            levels={
                "entry_zone": {"top": 162.18, "bottom": 162.18},
                "stop_loss": 161.89,
                "tp1": 162.47,
            },
        )

        self.assertIsNone(metrics["risk"])
        self.assertIsNone(metrics["tp1"])
        self.assertIsNone(metrics["tp2"])

    def test_index_distance_uses_points(self):
        metrics = build_trade_metrics(
            symbol="NASDAQ 100",
            asset_type="index",
            direction="Bearish",
            levels_mode="final",
            levels={
                "entry_zone": {"top": 20000, "bottom": 20000},
                "stop_loss": 20030,
                "tp1": 19940,
            },
        )

        self.assertEqual(metrics["risk"]["display"], "30 points")
        self.assertEqual(metrics["tp1"]["distance"]["display"], "60 points")
        self.assertEqual(metrics["tp1"]["risk_reward"], 2.0)

    def test_visible_trigger_is_used_as_distance_reference(self):
        metrics = build_trade_metrics(
            symbol="USD/JPY",
            asset_type="forex",
            direction="Bullish",
            levels_mode="final",
            levels={
                "trigger_level": 162.18,
                "entry_zone": {"top": 162.12, "bottom": 162.10},
                "stop_loss": 161.89,
                "tp1": 162.47,
            },
        )

        self.assertEqual(metrics["entry_price"], 162.18)
        self.assertEqual(metrics["risk"]["value"], 29.0)
        self.assertEqual(metrics["tp1"]["distance"]["value"], 29.0)
        self.assertEqual(metrics["tp1"]["risk_reward"], 1.0)

    def test_existing_objectives_can_be_labeled_as_projected(self):
        metrics = build_trade_metrics(
            symbol="USD/JPY",
            asset_type="forex",
            direction="Bullish",
            levels_mode="hidden",
            levels={
                "trigger_level": 162.18,
                "invalidation": 161.89,
            },
            objective_plan={
                "decision": "ACCEPT",
                "primary_objective": {"price": 162.47},
                "secondary_objective": {"price": 162.76},
            },
        )

        self.assertEqual(metrics["plan_mode"], "projected")
        self.assertEqual(metrics["stop_loss"], 161.89)
        self.assertEqual(metrics["risk"]["display"], "29 pips")
        self.assertEqual(metrics["tp1"]["distance"]["display"], "29 pips")
        self.assertEqual(metrics["tp2"]["risk_reward"], 2.0)

    def test_rejected_objective_is_not_published_as_projected(self):
        metrics = build_trade_metrics(
            symbol="USD/JPY",
            asset_type="forex",
            direction="Bullish",
            levels_mode="hidden",
            levels={"trigger_level": 162.18, "invalidation": 161.89},
            objective_plan={
                "decision": "REJECT",
                "primary_objective": {"price": 162.47},
            },
        )

        self.assertEqual(metrics["plan_mode"], "unavailable")
        self.assertIsNone(metrics["risk"])
        self.assertIsNone(metrics["tp1"])

    def test_tp1_below_one_r_warns_when_tp2_is_first_acceptable_target(self):
        metrics = build_trade_metrics(
            symbol="EUR/USD",
            asset_type="forex",
            direction="Bearish",
            levels_mode="hidden",
            levels={"trigger_level": 1.14307, "invalidation": 1.14450},
            objective_plan={
                "decision": "ACCEPT",
                "primary_objective": {"price": 1.14215},
                "secondary_objective": {"price": 1.14020},
            },
        )

        self.assertLess(metrics["tp1"]["risk_reward"], 1.0)
        self.assertGreaterEqual(metrics["tp2"]["risk_reward"], 1.0)
        self.assertEqual(
            metrics["warnings"],
            ["TP1 has weak reward. TP2 is the first acceptable target."],
        )


class TradeMetricsApiTests(unittest.TestCase):
    def test_replay_analysis_includes_trade_metrics_without_live_api_call(self):
        response = app.test_client().post(
            "/api/analyze-replay",
            json={
                "symbol": "USD/JPY",
                "timeframe": "M5",
                "strategy": "universal_structure",
                "multi_timeframe": False,
                "candles": candles(),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("trade_metrics", payload["analysis"])
        self.assertIn("trade_metrics", payload["strategy_result"])
        self.assertEqual(payload["analysis"]["trade_metrics"]["unit"], "pips")


if __name__ == "__main__":
    unittest.main()
