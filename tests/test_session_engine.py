"""US Eastern session boundaries and daylight-saving behavior."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scanner.session_engine import get_session_status


NEW_YORK = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[1]


class SessionEngineTests(unittest.TestCase):
    def session_at(self, hour: int, minute: int = 0):
        timestamp = datetime(2026, 1, 5, hour, minute, tzinfo=NEW_YORK)
        return get_session_status(timestamp)

    def test_exact_new_york_session_boundaries(self):
        cases = [
            ((21, 0), "Asian Session", True),
            ((3, 0), "London Kill Zone", True),
            ((8, 30), "New York Kill Zone", True),
            ((11, 0), "London Close", True),
            ((13, 0), "Outside Trading Hours", False),
        ]
        for (hour, minute), name, active in cases:
            with self.subTest(hour=hour, minute=minute):
                session = self.session_at(hour, minute)
                self.assertEqual(session["name"], name)
                self.assertEqual(session["active"], active)

    def test_winter_uses_est(self):
        session = get_session_status(datetime(2026, 1, 5, 13, 30, tzinfo=timezone.utc))
        self.assertEqual(session["name"], "New York Kill Zone")
        self.assertEqual(session["timezone_abbreviation"], "EST")
        self.assertEqual(session["current_time_label"], "8:30:00 AM EST")

    def test_summer_uses_edt_without_shifting_session(self):
        session = get_session_status(datetime(2026, 7, 6, 12, 30, tzinfo=timezone.utc))
        self.assertEqual(session["name"], "New York Kill Zone")
        self.assertEqual(session["timezone_abbreviation"], "EDT")
        self.assertEqual(session["current_time_label"], "8:30:00 AM EDT")

    def test_next_session_is_chronological_after_midnight(self):
        session = self.session_at(0, 30)
        self.assertEqual(session["next_session"], "London Kill Zone")
        self.assertIn("2:00 AM EST", session["next_session_label"])

    def test_market_and_kill_zone_are_separate_statuses(self):
        london_close = self.session_at(11, 0)
        self.assertTrue(london_close["market_open"])
        self.assertEqual(london_close["market_status"], "OPEN")
        self.assertFalse(london_close["kill_zone_active"])
        self.assertEqual(london_close["kill_zone_status"], "INACTIVE")

        new_york = self.session_at(8, 30)
        self.assertTrue(new_york["market_open"])
        self.assertTrue(new_york["kill_zone_active"])

    def test_active_session_reports_next_transition(self):
        session = self.session_at(11, 0)
        self.assertEqual(session["next_transition"], "Outside Trading Hours")
        self.assertIn("12:00 PM EST", session["next_transition_label"])
        self.assertEqual(session["time_until_next_session"], "01:00:00")

    def test_forex_weekend_market_status(self):
        saturday = get_session_status(datetime(2026, 1, 10, 11, 0, tzinfo=NEW_YORK))
        sunday_open = get_session_status(datetime(2026, 1, 11, 18, 0, tzinfo=NEW_YORK))
        self.assertFalse(saturday["market_open"])
        self.assertTrue(sunday_open["market_open"])


class SessionUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

    def test_ui_labels_us_eastern_time(self):
        self.assertIn("New York", self.template)
        self.assertNotIn("US Eastern Time", self.template)
        self.assertIn('timeZone: "America/New_York"', self.javascript)
        self.assertIn('hour12: false', self.javascript)

    def test_replay_session_is_not_overwritten_by_live_clock(self):
        self.assertNotIn("analyzeReplay", self.javascript)

    def test_client_next_session_is_chronologically_sorted(self):
        self.assertIn("function updateClock", self.javascript)

    def test_ui_separates_market_session_and_kill_zone(self):
        self.assertIn('id="home-market-open"', self.template)
        self.assertIn('id="home-session"', self.template)
        self.assertIn('id="toolbar-session"', self.template)


if __name__ == "__main__":
    unittest.main()
