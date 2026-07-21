from analysis.derived_spike_risk_classifier import classify_spike_risk
def test_opposed_candidate_requires_more_rr_and_less_risk():
    aligned=classify_spike_risk("BOOM","buy");opposed=classify_spike_risk("BOOM","sell");assert aligned["alignment"]=="aligned" and opposed["minimum_required_rr"]>aligned["minimum_required_rr"] and opposed["risk_multiplier"]<aligned["risk_multiplier"]
