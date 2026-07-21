"""Symbol-aware display precision rules."""

from __future__ import annotations

import unittest

from analysis.price_precision import display_precision


class PricePrecisionTests(unittest.TestCase):
    def test_standard_forex_uses_five_decimals(self):
        for symbol in ("EUR/USD", "GBP/USD", "AUD/USD", "USD/CAD"):
            with self.subTest(symbol=symbol):
                self.assertEqual(display_precision(symbol, "forex", 1.42312), 5)

    def test_jpy_pairs_use_three_decimals(self):
        self.assertEqual(display_precision("USD/JPY", "forex", 157.245), 3)
        self.assertEqual(display_precision("GBP/JPY", "forex", 201.125), 3)

    def test_indices_and_major_crypto_use_two_decimals(self):
        self.assertEqual(display_precision("NASDAQ 100", "index", 19542.25), 2)
        self.assertEqual(display_precision("BTC/USD", "crypto", 67245.10), 2)

    def test_sub_unit_crypto_uses_dynamic_precision(self):
        self.assertEqual(display_precision("TOKEN/USD", "crypto", 0.012345), 6)


if __name__ == "__main__":
    unittest.main()
