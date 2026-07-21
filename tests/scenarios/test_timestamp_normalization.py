from __future__ import annotations

import unittest

from providers.twelvedata import normalize_time_series_payload


class TimestampNormalizationTests(unittest.TestCase):
    def test_exchange_local_index_time_is_converted_to_utc(self):
        payload = {
            "meta": {"exchange_timezone": "America/New_York"},
            "values": [
                {"datetime": "2026-01-05 09:30:00", "open": "100", "high": "101", "low": "99", "close": "100.5"}
            ],
        }

        candles, metadata = normalize_time_series_payload(
            payload,
            interval="1day",
            requested_timezone=None,
        )

        self.assertEqual(candles.iloc[0]["time"].isoformat(), "2026-01-05T14:30:00+00:00")
        self.assertEqual(metadata["source_timezone"], "America/New_York")
        self.assertEqual(metadata["normalized_timezone"], "UTC")
