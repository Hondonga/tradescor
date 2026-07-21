import pandas as pd
from analysis.step_market_profile import build_step_market_profile
def _rows(n=220,mirror=1):
    close=[100+mirror*((i%10)-5)*.01 for i in range(n)];return pd.DataFrame({"time":pd.date_range("2026-01-01",periods=n,freq="15min",tz="UTC"),"open":close,"high":[x+.02 for x in close],"low":[x-.02 for x in close],"close":close,"complete":[True]*n})
def test_profile_is_tick_normalized():
    row=build_step_market_profile(_rows(),.01);assert row["quality"]=="good" and abs(row["median_range_ticks"]-4)<1e-9
def test_unknown_tick_size_is_insufficient():assert build_step_market_profile(_rows(),None)["quality"]=="insufficient"
