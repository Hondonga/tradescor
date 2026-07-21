from analysis.derived_regime_stability import evaluate_regime_stability,clear_regime_stability
def test_candidate_requires_distinct_completed_candles():
    clear_regime_stability(); assert not evaluate_regime_stability("x","LOW_STABLE",.9,"1",3)["stable"]
    assert not evaluate_regime_stability("x","LOW_STABLE",.9,"1",3)["stable"]
    evaluate_regime_stability("x","LOW_STABLE",.9,"2",3); assert evaluate_regime_stability("x","LOW_STABLE",.9,"3",3)["stable"]
