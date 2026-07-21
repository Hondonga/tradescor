from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from analysis.setup_state import find_confirmation_event
from strategies.universal_structure import _state


class ConfirmationPersistenceTests(unittest.TestCase):
    def test_confirmation_remains_true_during_pullback(self):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        closes = [99.5, 100.2, 101.2, 100.7, 99.9]
        candles = pd.DataFrame(
            [
                {
                    "time": start + timedelta(minutes=5 * index),
                    "open": close - 0.1,
                    "high": close + 0.2,
                    "low": close - 0.2,
                    "close": close,
                }
                for index, close in enumerate(closes)
            ]
        )
        trigger = {"price": 101.0, "index": 1, "time": candles.iloc[1]["time"]}

        event = find_confirmation_event(candles, "Bullish", trigger, after_index=2)

        self.assertEqual(event["index"], 2)
        self.assertEqual(
            _state("Bullish", {"top_price": 100.1, "bottom_price": 99.7}, True, True, bool(event)),
            "ENTRY_READY",
        )
