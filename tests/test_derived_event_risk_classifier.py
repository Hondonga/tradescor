from analysis.derived_event_risk_classifier import classify_event_risk
def test_against_event_requires_more_rr_and_less_chase():
    aligned=classify_event_risk("up","buy");against=classify_event_risk("up","sell")
    assert against["minimum_required_rr"]>aligned["minimum_required_rr"] and against["maximum_chase_atr"]<aligned["maximum_chase_atr"]
