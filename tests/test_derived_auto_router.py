from analysis.derived_strategy_eligibility import eligible_registry_entries
def _selected(family,regime):
    rows=eligible_registry_entries({"family":family},{"regime":regime},True)["eligible"];return [row["strategy_id"] for row in rows]
def test_primary_family_routes():
    assert _selected("RANGE_BREAK","COMPRESSION")==["derived_range_break_retest"]
    assert _selected("CRASH","RANGE")==["boom_crash_spike_state"]
    assert _selected("DEX","RANGE")==["jump_dex_post_event"]
    assert _selected("VOLATILITY_SWITCH","UNSTABLE")==["derived_switch_orchestrator"]
    assert _selected("DRIFT_SWITCH","RANGE")==["derived_switch_orchestrator"]
