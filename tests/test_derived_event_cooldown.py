import pandas as pd
from analysis.derived_event_cooldown import evaluate_event_cooldown
def test_cooldown_counts_only_completed_candles_and_requires_both_gates():
    event={"completed_at":"2026-01-01T00:00:00+00:00"};rows=pd.DataFrame({"time":pd.date_range("2026-01-01 00:05",periods=4,freq="5min",tz="UTC"),"complete":[True,True,False,True],"open":[1]*4,"high":[2]*4,"low":[0]*4,"close":[1]*4})
    blocked=evaluate_event_cooldown(rows,event,{"release_allowed":False},{"formed_after_event":True});assert blocked["completed_candles_elapsed"]==3 and not blocked["release_allowed"]
    assert evaluate_event_cooldown(rows,event,{"release_allowed":True},{"formed_after_event":True})["release_allowed"]
