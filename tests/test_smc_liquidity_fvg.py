import pandas as pd
from analysis.smc.smc_liquidity_engine import structural_liquidity,classify_reference_event
from analysis.smc.smc_fvg_engine import detect_fvgs

def test_equal_level_clusters_are_deterministic():
    swings=[{"swing_id":"a","type":"high","price":10,"confirmation_time":"1","candle_time":"0"},{"swing_id":"b","type":"high","price":10.02,"confirmation_time":"2","candle_time":"1"}];a=structural_liquidity(swings,atr=1,tick_size=.01);b=structural_liquidity(swings,atr=1,tick_size=.01);assert a==b and a[0]["source"]=="equal_levels"

def test_sweep_and_accepted_breakout_are_distinct_completed_close_events():
    ref={"reference_id":"x","type":"buy_side","price":10};sweep=pd.DataFrame([{"time":1,"open":9.8,"high":10.5,"low":9.5,"close":9.9,"complete":True}]);accepted=sweep.assign(close=10.3)
    assert classify_reference_event(sweep,ref,.1)["type"]=="sweep";assert classify_reference_event(accepted,ref,.1)["type"]=="accepted_breakout"

def test_fvg_uses_three_completed_candles_and_jump_spanning_fvg_is_rejected():
    rows=pd.DataFrame([{"time":pd.Timestamp(f"2026-01-01T00:{i*5:02d}:00Z"),"open":1.0+i,"high":2.0+i,"low":float(i),"close":1.5+i,"complete":True} for i in range(3)]);rows.loc[2,"low"]=2.5;rows.loc[2,"high"]=3.5
    found=detect_fvgs(rows,atr=2,tick_size=.1,minimum_gap_ticks=1,minimum_gap_atr=0);assert found and found[0]["direction"]=="bullish"
    assert detect_fvgs(rows,atr=2,tick_size=.1,minimum_gap_ticks=1,minimum_gap_atr=0,excluded_times=[rows.iloc[1].time.isoformat()])==[]
