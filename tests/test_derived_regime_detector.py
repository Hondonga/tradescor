import pandas as pd
from analysis.derived_regime_detector import detect_derived_structure,detect_derived_regime
def waves(values):return pd.DataFrame([{"time":i,"open":v-.1,"high":v+.2,"low":v-.2,"close":v,"complete":True} for i,v in enumerate(values)])
def test_structure_and_regime_are_directionally_symmetric():
    bull=waves([1,2,3,2,1.5,2.5,4,3,2.5,3.5,5,4,3.5,4.5,6,5,4.5,5.5,7,6,6.5,7.5])
    bear=waves([10-v for v in bull.close])
    assert detect_derived_structure(bull)["direction"]=="bullish"
    assert detect_derived_structure(bear)["direction"]=="bearish"
    profile={"directional_efficiency":.6,"trend_persistence":.7,"compression_ratio":1,"expansion_ratio":1}
    assert detect_derived_regime(bull,profile)["regime"]=="TREND_BULLISH"
    assert detect_derived_regime(bear,profile)["regime"]=="TREND_BEARISH"
def test_low_efficiency_stable_market_is_range():
    market=waves([100+(i%2)*.1 for i in range(30)]);profile={"directional_efficiency":.05,"trend_persistence":.5,"compression_ratio":1,"expansion_ratio":1}
    assert detect_derived_regime(market,profile)["regime"]=="RANGE"
