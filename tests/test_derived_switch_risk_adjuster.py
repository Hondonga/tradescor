from analysis.derived_switch_risk_adjuster import switch_risk_adjustments
def test_rising_and_transition_risk_are_conservative():
    assert switch_risk_adjustments("RISING_VOLATILITY")["maximum_chase_atr_multiplier"]<1
    assert switch_risk_adjustments("DRIFT_TRANSITION")["confidence_ceiling"]<1
