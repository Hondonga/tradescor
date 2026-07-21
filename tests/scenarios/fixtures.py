from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd


def candle_frame(count: int = 40, *, minutes: int = 5, start: datetime | None = None) -> pd.DataFrame:
    start = start or datetime(2026, 1, 5, 7, 0, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        close = 100 + index * 0.05
        rows.append(
            {
                "time": start + timedelta(minutes=minutes * index),
                "open": close - 0.1,
                "high": close + 0.25,
                "low": close - 0.25,
                "close": close,
            }
        )
    return pd.DataFrame(rows)


def locked_breakout_frame(extra_retest: bool = False) -> pd.DataFrame:
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    rows = []
    for index in range(40):
        center = 100 + (index % 5) * 0.25
        rows.append(
            {
                "time": start + timedelta(minutes=5 * index),
                "open": center - 0.1,
                "high": center + 0.2,
                "low": center - 0.2,
                "close": center + 0.1,
            }
        )
    rows.append(
        {
            "time": start + timedelta(minutes=200),
            "open": 100.8,
            "high": 101.8,
            "low": 100.7,
            "close": 101.7,
        }
    )
    if extra_retest:
        rows.extend(
            [
                {
                    "time": start + timedelta(minutes=205),
                    "open": 101.6,
                    "high": 101.65,
                    "low": 101.15,
                    "close": 101.3,
                },
                {
                    "time": start + timedelta(minutes=210),
                    "open": 101.3,
                    "high": 101.7,
                    "low": 101.2,
                    "close": 101.6,
                },
            ]
        )
    return pd.DataFrame(rows)
