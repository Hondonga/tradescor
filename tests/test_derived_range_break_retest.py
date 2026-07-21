from strategies.derived.range_break_retest import evaluate_derived_range_break_retest
def test_data_error_cannot_create_setup():
    result=evaluate_derived_range_break_retest(symbol="RB100",family={"family":"RANGE_BREAK"},regime={"regime":"RANGE"},profile={"atr":1},candles_by_timeframe={},current_price=None,data_quality={"analysis_allowed":False,"status":"invalid"})
    assert not result["strategy"]["eligible"] and result["decision"]["status"]=="NO VALID SETUP" and result["active_trade_plan"] is None
