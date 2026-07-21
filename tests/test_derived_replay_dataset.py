import pandas as pd
import pytest
from replay.derived_replay_dataset import build_replay_dataset

def rows(times):return pd.DataFrame([{"time":t,"open":10,"high":11,"low":9,"close":10} for t in times])

def test_dataset_checksum_is_deterministic_and_gaps_are_reported():
    a,_=build_replay_dataset(provider_symbol="R_100",display_name="R100",family="VOLATILITY",candles=rows([0,60,180]),base_timeframe="M1")
    b,_=build_replay_dataset(provider_symbol="R_100",display_name="R100",family="VOLATILITY",candles=rows([0,60,180]),base_timeframe="M1")
    assert a.dataset_id==b.dataset_id and a.checksum==b.checksum
    assert a.quality=="partial" and a.missing_intervals[0]["missing_count"]==1

def test_malformed_ohlc_prevents_replay():
    with pytest.raises(ValueError):build_replay_dataset(provider_symbol="R_100",display_name="R100",family="VOLATILITY",candles=pd.DataFrame([{"time":0,"open":10,"high":8,"low":9,"close":10}]),base_timeframe="M1")

