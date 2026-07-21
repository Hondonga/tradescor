import pytest
from replay.derived_replay_clock import DerivedReplayClock

def test_replay_clock_advances_only_by_completed_candles():
    clock=DerivedReplayClock([0,300,600],300);ticks=list(clock)
    assert [x["current_index"] for x in ticks]==[0,1,2]
    assert ticks[0]["current_time"].startswith("1970-01-01T00:05:00")
    assert ticks[-1]["progress_percent"]==100

def test_replay_clock_has_no_wall_clock_dependency():
    assert list(DerivedReplayClock([0],60))[0]["current_time"].startswith("1970-01-01T00:01:00")

