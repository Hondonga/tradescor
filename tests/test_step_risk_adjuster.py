from analysis.step_risk_adjuster import step_risk_adjustments
def test_research_risk_is_capped_and_conservative():
    row=step_risk_adjustments();assert row["confidence_ceiling"]<=.65 and row["maximum_chase_atr"]<.35 and "research" in row["research_warning"].lower()
