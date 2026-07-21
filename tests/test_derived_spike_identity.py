from analysis.derived_spike_identity import lock_spike,clear_spikes
def test_spike_identity_is_immutable_and_new_event_gets_new_id():
    clear_spikes();event={"spike_detected":True,"classification":"expected_family_spike","direction":"up","formed_at":"t1","origin_price":100,"extreme_price":110,"magnitude_points":10,"magnitude_atr":3,"range_multiple":4,"family_expected":True};one=lock_spike("BOOM500","BOOM",event);same=lock_spike("BOOM500","BOOM",{**event,"extreme_price":999});assert one["spike_id"]!=same["spike_id"]
    again=lock_spike("BOOM500","BOOM",event);assert again==one
