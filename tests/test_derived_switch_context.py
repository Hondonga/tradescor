from analysis.derived_switch_context import build_switch_context
PROFILE={"profile_quality":"good","atr_percentile":20,"volatility_percentile":20,"compression_ratio":1,"expansion_ratio":1,"abnormal_candle_frequency":0,"directional_efficiency":.1,"trend_persistence":.5}
QUALITY={"analysis_allowed":True,"status":"good"}
def test_volatility_switch_low_stable_context():
    row=build_switch_context(family={"family":"VOLATILITY_SWITCH","classification_confidence":.98},profile=PROFILE,regime={"regime":"RANGE","direction":"neutral"},data_quality=QUALITY)
    assert row["eligibility"]["eligible"] and row["context"]["current_regime"]=="LOW_STABLE"
def test_data_errors_are_not_trade_rejections():
    row=build_switch_context(family={"family":"VOLATILITY_SWITCH","classification_confidence":.98},profile={**PROFILE,"profile_quality":"insufficient"},regime={},data_quality={"analysis_allowed":False,"status":"reconnecting"})
    assert row["eligibility"]["data_state"]=="DATA RECONNECTING"
