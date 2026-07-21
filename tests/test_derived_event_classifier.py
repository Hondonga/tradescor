import pandas as pd
from analysis.derived_event_classifier import classify_derived_event
def _rows(direction=1,forming=False):
    rows=[]
    for i in range(24):
        o=100.;move=6*direction if i==20 else .2*((i%2)*2-1);c=o+move;rows.append({"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=5*i),"open":o,"high":max(o,c)+.2,"low":min(o,c)-.2,"close":c,"complete":not(forming and i==20)})
    return pd.DataFrame(rows)
def test_up_and_down_events_are_directionally_symmetric():
    profile={"atr":1,"median_range":.5};up=classify_derived_event(_rows(1),profile);down=classify_derived_event(_rows(-1),profile)
    assert up["qualified"] and up["direction"]=="up";assert down["qualified"] and down["direction"]=="down"
def test_incomplete_event_candle_cannot_qualify():assert not classify_derived_event(_rows(1,True),{"atr":1,"median_range":.5})["qualified"]
