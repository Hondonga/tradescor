from analysis.derived_spike_rejection_classifier import classify_spike_rejection
def test_rejection_requires_origin_failure_and_fresh_opposite_structure():
    spike={"direction":"up"};hold={"classification":"FAILED_HOLD","confidence":.8};assert classify_spike_rejection(spike,hold,{"direction":"bearish","formed_after_spike":True})["rejected"]
    assert not classify_spike_rejection(spike,hold,{"direction":"bullish","formed_after_spike":True})["rejected"]
