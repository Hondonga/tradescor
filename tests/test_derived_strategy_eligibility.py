from analysis.derived_strategy_eligibility import eligible_registry_entries
def _ids(family,regime):return [row["strategy_id"] for row in eligible_registry_entries({"family":family},{"regime":regime},True)["eligible"]]
def test_family_and_regime_gate_precedes_scoring():
    assert _ids("VOLATILITY","TREND_BEARISH")==["volatility_structure_pullback"]
    assert _ids("VOLATILITY","RANGE")==["derived_range_break_retest","derived_range_reaction"]
    assert _ids("BOOM","RANGE")==["boom_crash_spike_state"]
    assert _ids("JUMP","RANGE")==["jump_dex_post_event"]
    assert _ids("STEP","RANGE")==["step_structure_research"]
    assert _ids("OTHER_DERIVED","RANGE")==[]
def test_data_failure_makes_all_entries_ineligible():assert not eligible_registry_entries({"family":"VOLATILITY"},{"regime":"RANGE"},False)["eligible"]
