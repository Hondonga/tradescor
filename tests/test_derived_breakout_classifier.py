import pandas as pd
from analysis.derived_breakout_classifier import classify_breakout
LOCK={"low":99,"high":101,"locked_at":"2026-01-01T00:00:00+00:00"};CFG={"breakout_buffer_atr":.1,"minimum_breakout_body_ratio":.45}
def rows(open_,high,low,close,complete=True):return pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:15:00Z"),"open":open_,"high":high,"low":low,"close":close,"complete":complete}])
def test_completed_directional_breakouts_and_wick_reclaim_are_distinct():
    assert classify_breakout(rows(100.5,102,100.4,101.8),LOCK,1,CFG)["accepted"]
    assert classify_breakout(rows(99.5,99.6,98,98.2),LOCK,1,CFG)["direction"]=="bearish"
    wick=classify_breakout(rows(100.5,102,100,100.8),LOCK,1,CFG);assert wick["event_type"]=="SWEEP_RECLAIM" and not wick["accepted"]
    assert classify_breakout(rows(100.5,102,100.4,101.8,False),LOCK,1,CFG)["event_type"]=="NO_BREAKOUT"
