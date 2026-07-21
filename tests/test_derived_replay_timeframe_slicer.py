import pandas as pd
from replay.derived_replay_timeframe_slicer import slice_timeframes

def base(count=240):
    return pd.DataFrame([{"time":i*60,"open":100+i,"high":101+i,"low":99+i,"close":100.5+i,"complete":True} for i in range(count)])

def test_incomplete_higher_timeframes_are_excluded():
    frames,audit=slice_timeframes(base(),"1970-01-01T03:59:00+00:00","M1")
    assert len(frames["H1"])==3 and frames["H4"].empty and frames["D1"].empty
    assert audit["incomplete_candles_excluded"] is True

def test_no_future_base_or_aggregated_candles_are_visible():
    frames,_=slice_timeframes(base(),"1970-01-01T01:00:00+00:00","M1")
    assert len(frames["M5"])==12 and len(frames["M15"])==4 and len(frames["H1"])==1
    assert frames["M5"].iloc[-1].time.isoformat().startswith("1970-01-01T00:55:00")

