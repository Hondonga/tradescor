import pandas as pd
from analysis.derived_engine import analyze_derived_index
from analysis.smc.smc_router import clear_smc_ownership
from replay.derived_replay_validator import parity_report

def test_smc_live_and_replay_use_identical_production_contract():
    rows=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:00:00Z")+pd.Timedelta(minutes=5*i),"open":100+(i%6),"high":101+(i%6),"low":99+(i%6),"close":100.5+(i%6),"complete":True} for i in range(60)]);frames={key:rows.copy() for key in ("D1","H4","H1","M15","M5")};kwargs=dict(symbol="R_100",metadata={"provider_symbol":"R_100","display_name":"Volatility 100 Index"},candles_by_timeframe=frames,tick_size=.01,analysis_time=rows.iloc[-1].time,requested_strategy="auto")
    clear_smc_ownership();live=analyze_derived_index(**kwargs);clear_smc_ownership();replay=analyze_derived_index(**kwargs);report=parity_report(live,replay,keys=("ownership","decision","setup","structure","liquidity","fvgs","order_blocks","trade_chart"));assert report["parity"],report
