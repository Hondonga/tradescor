from __future__ import annotations

import unittest

from analysis.temporal_validation import validate_temporal_analysis
from scanner.economic_calendar import get_news_status
from scanner.session_engine import get_session_status
from tests.scenarios.fixtures import candle_frame


class TemporalValidationTests(unittest.TestCase):
    def test_entry_ready_without_stored_confirmation_is_rejected(self):
        candles = candle_frame(40)
        timestamp = candles.iloc[-1]["time"]
        validation = validate_temporal_analysis(
            analysis_timestamp=timestamp,
            selected_timeframe="M5",
            context={"M5": candles},
            strategy_result={
                "state": "ENTRY_READY",
                "entry_proximity": True,
                "setup_state": {"completed_events": [], "confirmation_time": None},
                "objective_plan": {"targets": []},
            },
            session=get_session_status(timestamp),
            news=get_news_status(timestamp, "EUR/USD"),
        )

        self.assertFalse(validation["valid"])
        self.assertIn("Entry Ready requires a stored confirmation event.", validation["warnings"])
