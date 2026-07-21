"""V1 entry-location rules for the Universal Structure strategy."""

from __future__ import annotations

import unittest

from strategies.universal_structure import _state


class UniversalStateTests(unittest.TestCase):
    def test_confirmation_away_from_zone_waits_for_entry(self):
        self.assertEqual(
            _state("Bullish", {"top_price": 1.101, "bottom_price": 1.100}, True, False, True),
            "CONFIRMED_WAITING_FOR_ENTRY",
        )

    def test_confirmation_inside_zone_is_entry_ready(self):
        self.assertEqual(
            _state("Bullish", {"top_price": 1.101, "bottom_price": 1.100}, True, True, True),
            "ENTRY_READY",
        )


if __name__ == "__main__":
    unittest.main()
