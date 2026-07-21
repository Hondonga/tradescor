from __future__ import annotations

import pandas as pd

from strategies.breakout_retest import _failure_event, _failure_recovered, _invalidation


def _frame(*closes: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time": pd.Timestamp("2026-07-09T12:00:00Z") + pd.Timedelta(minutes=15 * index),
                "open": close,
                "high": close + 0.02,
                "low": close - 0.02,
                "close": close,
            }
            for index, close in enumerate(closes)
        ]
    )


def test_bearish_retest_probe_does_not_immediately_fail_breakout():
    candles = _frame(162.20, 162.358)
    breakout = {"direction": "Bearish", "index": 0, "level": 162.325}

    assert _failure_event(candles, breakout, atr=0.04) == {}


def test_decisive_move_back_inside_range_fails_breakout():
    candles = _frame(162.20, 162.386)
    breakout = {"direction": "Bearish", "index": 0, "level": 162.325}

    failure = _failure_event(candles, breakout, atr=0.04)

    assert failure["type"] == "failed_breakout"
    assert failure["close"] == 162.386


def test_failed_breakout_can_recover_when_price_returns_to_broken_level():
    candles = _frame(162.20, 162.386, 162.367)
    breakout = {"direction": "Bearish", "index": 0, "level": 162.325}
    failure = _failure_event(candles, breakout, atr=0.04)

    assert failure["type"] == "failed_breakout"
    assert _failure_recovered(candles, breakout, atr=0.04, failure=failure) is True


def test_breakout_retest_invalidation_has_breathing_room():
    assert _invalidation(162.325, 0.04, "Bearish") == 162.385
    assert _invalidation(162.325, 0.04, "Bullish") == 162.265
