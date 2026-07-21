from __future__ import annotations

import unittest

from scanner.objective_engine import build_objective_plan
from tests.scenarios.fixtures import candle_frame


class TargetValidityTests(unittest.TestCase):
    def test_swept_swing_cannot_be_selected(self):
        candles = candle_frame(20)
        candles.loc[10, "high"] = 106.0
        swing = {"price": 105.0, "index": 5, "time": candles.iloc[5]["time"]}

        plan = build_objective_plan(
            direction="bullish",
            entry_price=100,
            stop_loss=98,
            swings={"highs": [swing], "lows": []},
            analysis_candles=candles,
        )

        self.assertFalse(plan["trade_accepted"])
        self.assertTrue(plan["candidates"][0]["taken"])
        self.assertIsNotNone(plan["candidates"][0]["taken_at"])
