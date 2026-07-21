import pandas as pd
from validation.smc_dataset_matrix import select_neutral_period,build_matrix_dataset,SELECTION_POLICY

def candles(duplicate=False,gap=False):
    times=[pd.Timestamp("2026-07-01T00:00:00Z")+pd.Timedelta(minutes=i) for i in range(20) if not gap or i!=10]
    if duplicate:times.append(times[-1])
    return pd.DataFrame([{"time":t,"open":1.,"high":2.,"low":0.,"close":1.,"performance":999} for t in times])
def test_period_selection_is_fixed_before_and_independent_of_performance():
    a,policy=select_neutral_period(candles());changed=candles();changed["performance"]=-999;b,_=select_neutral_period(changed);assert a.time.tolist()==b.time.tolist() and policy["performance_fields_used"]==[]
def test_matrix_checksum_is_stable_and_gaps_duplicates_are_reported():
    spec={"symbol":"R_100","display_name":"Volatility 100 Index","family":"VOLATILITY","variant":"VOLATILITY_100"};first,_=build_matrix_dataset(spec,candles(duplicate=True,gap=True),downloaded_at="x");second,_=build_matrix_dataset(spec,candles(duplicate=True,gap=True),downloaded_at="x");assert first["checksum"]==second["checksum"] and first["missing_intervals"] and first["duplicate_intervals"]

