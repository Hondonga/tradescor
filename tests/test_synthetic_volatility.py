from analysis.synthetic_volatility import detect_synthetic_volatility
def test_compression_and_expansion_volatility_are_distinct():
    base={"profile_quality":"good","atr_percentile":70,"volatility_percentile":65,"abnormal_candle_frequency":0}
    assert detect_synthetic_volatility({**base,"expansion_ratio":1.6,"compression_ratio":1})["regime"]=="RISING"
    assert detect_synthetic_volatility({**base,"atr_percentile":20,"volatility_percentile":20,"expansion_ratio":.5,"compression_ratio":.6})["regime"]=="FALLING"
