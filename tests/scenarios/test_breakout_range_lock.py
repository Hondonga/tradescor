from __future__ import annotations

import unittest

from strategies.breakout_retest import _locked_breakout_sequence
from tests.scenarios.fixtures import locked_breakout_frame


class BreakoutRangeLockTests(unittest.TestCase):
    def test_range_and_breakout_do_not_shift_during_retest(self):
        breakout_only = locked_breakout_frame(False)
        with_retest = locked_breakout_frame(True)

        first = _locked_breakout_sequence(breakout_only, 0.5)
        later = _locked_breakout_sequence(with_retest, 0.5)

        self.assertTrue(first)
        self.assertEqual(first["range"]["high"], later["range"]["high"])
        self.assertEqual(first["range"]["low"], later["range"]["low"])
        self.assertEqual(first["breakout"]["index"], later["breakout"]["index"])
