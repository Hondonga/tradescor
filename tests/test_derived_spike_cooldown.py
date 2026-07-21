import pandas as pd
from analysis.derived_spike_cooldown import evaluate_spike_cooldown
def test_cooldown_uses_completed_candles_and_fresh_structure():
    rows=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:05:00Z")+pd.Timedelta(minutes=5*i),"complete":i<4} for i in range(5)]);spike={"completed_at":"2026-01-01T00:00:00Z"};structure={"formed_after_spike":True,"direction":"bullish"};released=evaluate_spike_cooldown(rows,spike,{"regime":"NORMAL"},structure,{"minimum_cooldown_candles":3});assert released["release_allowed"] and released["completed_candles_elapsed"]==4
    assert not evaluate_spike_cooldown(rows.iloc[:2],spike,{"regime":"NORMAL"},structure,{"minimum_cooldown_candles":3})["release_allowed"]
