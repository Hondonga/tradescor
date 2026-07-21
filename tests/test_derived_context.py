from analysis.derived_intelligence_normalizer import strategy_eligibility
def test_eligibility_is_non_actionable():
    result=strategy_eligibility({"family":"VOLATILITY"},{"regime":"TREND_BEARISH"})
    assert result["eligible_strategies"]==["Structure Pullback"] and not any(key in result for key in ("entry","stop","targets"))
