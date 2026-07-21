from analysis.derived_spike_risk_classifier import classify_spike_risk
def test_boom_and_crash_alignment_is_mirrored():assert classify_spike_risk("BOOM","buy")["alignment"]==classify_spike_risk("CRASH","sell")["alignment"]=="aligned" and classify_spike_risk("BOOM","sell")["alignment"]==classify_spike_risk("CRASH","buy")["alignment"]=="opposed"
