import math,pandas as pd
from analysis.derived_market_profile import build_derived_market_profile

def candles(count=120):
    rows=[]
    for i in range(count):
        close=100+i*.08+((i%5)-2)*.03;rows.append({"time":pd.Timestamp("2025-01-01",tz="UTC")+pd.Timedelta(minutes=5*i),"open":close-.02,"high":close+.12,"low":close-.14,"close":close,"complete":True})
    return pd.DataFrame(rows)
def test_profile_is_finite_normalized_and_completed_only():
    profile=build_derived_market_profile(candles(),family="VOLATILITY",tick_size=.01,timeframe="M5",symbol="R_100")
    assert profile["profile_quality"]=="good" and profile["normalized_atr"]>0
    assert all(not isinstance(value,float) or math.isfinite(value) for value in profile.values())
def test_insufficient_profile_is_explicit():assert build_derived_market_profile(candles(10),family="STEP",tick_size=.01,timeframe="M5")["profile_quality"]=="insufficient"
