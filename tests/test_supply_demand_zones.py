"""Supply/demand origin and displacement detection tests."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from scanner.supply_demand_zones import detect_supply_demand_zones


class SupplyDemandZoneTests(unittest.TestCase):
    def test_detects_fresh_demand_from_bullish_displacement(self):
        zones = detect_supply_demand_zones(_displacement_candles("demand"), atr=0.3)
        zone = zones["demand"][-1]

        self.assertEqual(zone["type"], "demand")
        self.assertGreater(zone["proximal_price"], zone["distal_price"])
        self.assertGreaterEqual(zone["impulse_atr"], 1.25)
        self.assertEqual(zone["status"], "fresh")

    def test_detects_fresh_supply_from_bearish_displacement(self):
        zones = detect_supply_demand_zones(_displacement_candles("supply"), atr=0.3)
        zone = zones["supply"][-1]

        self.assertEqual(zone["type"], "supply")
        self.assertGreater(zone["distal_price"], zone["proximal_price"])
        self.assertGreaterEqual(zone["impulse_atr"], 1.25)
        self.assertEqual(zone["status"], "fresh")


def _displacement_candles(zone_type: str) -> pd.DataFrame:
    rows = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(60):
        if index < 30:
            base = 99 + index * 0.03 if zone_type == "demand" else 101 - index * 0.03
            open_price = base
            close = base + 0.05 if zone_type == "demand" else base - 0.05
        elif index == 30:
            open_price, close = (100.0, 99.9) if zone_type == "demand" else (100.1, 100.2)
        elif index == 31:
            open_price, close = (100.0, 102.0) if zone_type == "demand" else (100.1, 98.1)
        else:
            base = 102.0 + (index - 32) * 0.02 if zone_type == "demand" else 98.1 - (index - 32) * 0.02
            open_price = base
            close = base + 0.08 if zone_type == "demand" else base - 0.08
        rows.append(
            {
                "time": start + timedelta(minutes=5 * index),
                "open": open_price,
                "high": max(open_price, close) + 0.1,
                "low": min(open_price, close) - 0.1,
                "close": close,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
