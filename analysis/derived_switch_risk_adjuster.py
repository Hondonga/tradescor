def switch_risk_adjustments(regime):
    result={"minimum_tp1_rr_multiplier":1.0,"maximum_chase_atr_multiplier":1.0,"stop_buffer_atr_multiplier":1.0,"setup_lifetime_multiplier":1.0,"confidence_ceiling":1.0,"warnings":[]}
    if regime=="RISING_VOLATILITY": result.update(maximum_chase_atr_multiplier=.8,stop_buffer_atr_multiplier=1.15)
    elif regime=="HIGH_STABLE": result.update(stop_buffer_atr_multiplier=1.15,minimum_tp1_rr_multiplier=1.05)
    elif regime=="FALLING_VOLATILITY": result.update(setup_lifetime_multiplier=.75,confidence_ceiling=.75)
    elif "TRANSITION" in regime: result.update(confidence_ceiling=.5,warnings=["Transitions cannot release a setup."])
    return result
