from analysis.derived_switch_strategy_router import route_switch_strategy
def test_volatility_switch_routing_matrix():
    assert route_switch_strategy("VOLATILITY_SWITCH","LOW_STABLE",stable=True)["delegated_strategy"]=="derived_range_reaction"
    assert route_switch_strategy("VOLATILITY_SWITCH","COMPRESSION",stable=True)["delegated_strategy"]=="derived_range_break_retest"
    assert route_switch_strategy("VOLATILITY_SWITCH","RISING_VOLATILITY",stable=True,has_locked_range=True)["delegated_strategy"]=="derived_range_break_retest"
    assert route_switch_strategy("VOLATILITY_SWITCH","HIGH_STABLE",stable=True,directional_structure="bearish")["delegated_strategy"]=="volatility_structure_pullback"
    assert route_switch_strategy("VOLATILITY_SWITCH","EXTREME",stable=True)["delegated_strategy"] is None
def test_drift_routing_is_directionally_symmetric():
    bull=route_switch_strategy("DRIFT_SWITCH","BULLISH_DRIFT",stable=True);bear=route_switch_strategy("DRIFT_SWITCH","BEARISH_DRIFT",stable=True)
    assert bull["allowed_directions"]==["buy"] and bear["allowed_directions"]==["sell"]
    assert route_switch_strategy("DRIFT_SWITCH","SIDEWAYS_DRIFT",stable=True)["delegated_strategy"]=="derived_range_reaction"
    assert route_switch_strategy("DRIFT_SWITCH","DRIFT_TRANSITION",stable=True)["delegated_strategy"] is None
