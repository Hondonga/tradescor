from analysis.derived_retest_zone_engine import build_retest_zone,classify_retest_location
def test_retest_zone_is_narrow_and_anchors_to_broken_boundary():
    locked={"low":99,"high":101};bull=build_retest_zone(locked,{"accepted":True,"direction":"bullish","breakout_time":"t"},1,{"retest_zone_width_atr":.15});bear=build_retest_zone(locked,{"accepted":True,"direction":"bearish","breakout_time":"t"},1,{"retest_zone_width_atr":.15});assert bull["boundary"]==101 and bear["boundary"]==99 and bull["high"]-bull["low"]<2
    assert classify_retest_location(100.5,101,bull,locked,1)["completed_candle_state"]=="FAILED_BREAKOUT"
