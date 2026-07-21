from __future__ import annotations

import unittest
from datetime import timedelta

from analysis.time_context import build_temporal_context
from app import app
from tests.scenarios.fixtures import candle_frame


class ReplayNoLookAheadTests(unittest.TestCase):
    def test_future_higher_timeframe_candles_are_removed(self):
        selected = candle_frame(20)
        replay_time = selected.iloc[-1]["time"]
        h1 = candle_frame(5, minutes=60, start=selected.iloc[0]["time"] - timedelta(hours=2))
        future = h1.iloc[-1].copy()
        future["time"] = replay_time + timedelta(hours=1)
        h1.loc[len(h1)] = future

        temporal = build_temporal_context(
            selected_candles=selected,
            context={"M5": selected, "H1": h1},
            selected_timeframe="M5",
            replay=True,
        )

        sliced_h1 = temporal["context"]["H1"]
        self.assertTrue(((sliced_h1["time"] + timedelta(hours=1)) <= replay_time).all())
        self.assertLess(len(sliced_h1), len(h1))

    def test_replay_api_returns_only_temporally_available_context(self):
        selected = candle_frame(40)
        h1 = candle_frame(8, minutes=60, start=selected.iloc[0]["time"] - timedelta(hours=3))

        def records(frame):
            rows = frame.copy()
            rows["time"] = rows["time"].map(lambda value: int(value.timestamp()))
            return rows.to_dict(orient="records")

        response = app.test_client().post(
            "/api/analyze-replay",
            json={
                "symbol": "EUR/USD",
                "timeframe": "M5",
                "strategy": "universal_structure",
                "multi_timeframe": True,
                "candles": records(selected),
                "context_candles": {"H1": records(h1)},
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        boundary = payload["analysis_timestamp_epoch"]
        returned_h1 = payload["multi_timeframe"]["context"]["H1"]
        self.assertTrue(all(candle["time"] + 3600 <= boundary for candle in returned_h1))
        self.assertTrue(payload["temporal_validation"]["valid"])
