import pandas as pd
from analysis.derived_event_cooldown import evaluate_event_cooldown
from analysis.derived_spike_cooldown import evaluate_spike_cooldown

def candles(count=6):return pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:00:00Z")+pd.Timedelta(minutes=5*i),"open":1,"high":2,"low":0,"close":1,"complete":True} for i in range(count)])

def test_event_cooldown_exposes_every_release_condition_and_releases():
    event={"completed_at":"2026-01-01T00:05:00Z"};blocked=evaluate_event_cooldown(candles(2),event,{"release_allowed":False},{"formed_after_event":False},{"minimum_completed_m5_candles":3})
    for key in ("minimum_candles_passed","volatility_stabilized","fresh_swings_available","fresh_structure_available","no_new_event","data_quality_passed","release_allowed"):assert key in blocked
    released=evaluate_event_cooldown(candles(),event,{"release_allowed":True},{"formed_after_event":True,"fresh_swings_available":True},{"minimum_completed_m5_candles":3});assert released["release_allowed"] and not released["active"]

def test_spike_cooldown_requires_more_than_elapsed_time_and_releases_with_structure():
    spike={"completed_at":"2026-01-01T00:05:00Z"};blocked=evaluate_spike_cooldown(candles(),spike,{"regime":"EXTREME"},{"formed_after_spike":True,"direction":"bearish"},{"minimum_cooldown_candles":3});assert not blocked["release_allowed"]
    released=evaluate_spike_cooldown(candles(),spike,{"regime":"NORMAL"},{"formed_after_spike":True,"fresh_swings_available":True,"direction":"bearish"},{"minimum_cooldown_candles":3});assert released["release_allowed"]

