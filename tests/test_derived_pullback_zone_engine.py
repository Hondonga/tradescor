import pandas as pd
from analysis.derived_pullback_zone_engine import detect_pullback,select_m15_pullback_zone
def frame(values):return pd.DataFrame([{"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=15*i),"open":v-.1,"high":v+.25,"low":v-.25,"close":v,"complete":True} for i,v in enumerate(values)])
def test_pullback_differs_from_invalidation_and_zone_has_measured_origin():
    rows=frame(list(range(100,125))+[124,123.5,123,122.5,122]);pull=detect_pullback(rows,"buy",1,{"minimum_pullback_atr":.25,"maximum_pullback_atr":3,"minimum_pullback_percentage":.01,"maximum_pullback_percentage":.9});assert pull["valid"]
    zone=select_m15_pullback_zone(rows,"buy",pull,1,122,{"minimum_zone_quality":0,"maximum_zone_touches":20});assert zone["formed_at"] and zone["low"]<zone["high"]
    deep=detect_pullback(frame(list(range(100,125))+[120,115,105,95]),"buy",1,{"minimum_pullback_atr":.25,"maximum_pullback_atr":2,"minimum_pullback_percentage":.01,"maximum_pullback_percentage":.8});assert deep["state"] in {"TOO_DEEP","STRUCTURE_INVALIDATED"}
