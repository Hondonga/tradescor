import pandas as pd
from replay.derived_replay_timeframe_slicer import available_after
from paper_testing.derived_fill_engine import evaluate_paper_fill
from paper_testing.derived_outcome_resolver import resolve_paper_outcome

def test_zone_and_pivot_are_unavailable_before_confirmation():
    assert not available_after({"formed_at":"2026-01-01T00:00:00Z","first_available_at":"2026-01-01T00:10:00Z"},"2026-01-01T00:05:00Z")
    assert available_after({"pivot_time":"2026-01-01T00:00:00Z","confirmed_at":"2026-01-01T00:10:00Z"},"2026-01-01T00:10:00Z")

def test_new_setup_cannot_use_decision_candle_range_or_prefill_outcome():
    setup={"created_at":"2026-01-01T00:05:00Z","entry":100,"direction":"buy","stop":98,"tp1":102,"tp2":None,"risk_points":2}
    data=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:05:00Z"),"open":100,"high":103,"low":97,"close":100,"complete":True}])
    assert not evaluate_paper_fill(setup,data,"limit")["filled"]
    assert resolve_paper_outcome(setup,data,"2026-01-01T00:05:00Z")["outcome"]=="OPEN"

def test_confirmation_close_next_open_does_not_use_confirmation_extremes():
    setup={"created_at":"2026-01-01T00:05:00Z","entry":100,"direction":"buy"};data=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:10:00Z"),"open":101,"high":999,"low":1,"close":102,"complete":True}])
    fill=evaluate_paper_fill(setup,data,"next_base_candle_open");assert fill["filled_entry"]==101

