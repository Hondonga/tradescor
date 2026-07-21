from __future__ import annotations

import unittest
from datetime import datetime, timezone

from scanner.session_engine import get_session_status


class SessionTimestampTests(unittest.TestCase):
    def test_replay_timestamp_controls_session(self):
        london_time = datetime(2026, 1, 5, 8, 30, tzinfo=timezone.utc)
        session = get_session_status(london_time)

        self.assertEqual(session["name"], "London Kill Zone")
        self.assertTrue(session["entry_allowed"])
        self.assertEqual(session["evaluated_at"], "2026-01-05T03:30:00-05:00")
