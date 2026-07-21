import pandas as pd
from analysis.derived_range_detector import detect_derived_range
def range_rows(count=24):
    values=[100+((i%4)-1.5)*.15 for i in range(count)];return pd.DataFrame([{"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=15*i),"open":v-.03,"high":v+.22,"low":v-.22,"close":v,"complete":True} for i,v in enumerate(values)])
def test_range_requires_duration_and_measured_boundaries():
    cfg={"minimum_range_duration":18,"minimum_boundary_reactions":2,"minimum_reactions_per_side":1,"minimum_range_quality":0,"minimum_width_atr":.1,"maximum_width_atr":10}
    result=detect_derived_range(range_rows(),.3,cfg);assert result["valid"] and result["high"]>result["low"] and result["duration_candles"]>=18
    assert not detect_derived_range(range_rows(8),.3,cfg)["valid"]
