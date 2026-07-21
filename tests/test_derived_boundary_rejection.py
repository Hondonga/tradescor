import pandas as pd
from analysis.derived_boundary_rejection import detect_boundary_rejection

def _rows(values):
    return pd.DataFrame([{"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=5*i),"open":o,"high":h,"low":l,"close":c,"complete":complete} for i,(o,h,l,c,complete) in enumerate(values)])

def test_wick_only_is_not_confirmation_and_forming_candle_is_ignored():
    locked={"low":100.,"high":110.}
    wick=_rows([(101,102,99,100.5,True)])
    assert detect_boundary_rejection(wick,locked,"lower",atr=1)["event_type"]=="WICK_ONLY"
    forming=_rows([(101,102,99,100.5,True),(100.5,103,100.4,102.5,False)])
    assert not detect_boundary_rejection(forming,locked,"lower",atr=1)["valid"]
    completed=_rows([(101,102,99,100.5,True),(100.5,103,100.4,102.5,True)])
    assert detect_boundary_rejection(completed,locked,"lower",atr=1)["valid"]
