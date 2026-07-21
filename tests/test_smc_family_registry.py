from analysis.derived_family_classifier import classify_derived_family

def test_jump_event_direction_is_always_unknown_before_event():
    row=classify_derived_family({"provider_symbol":"JD10","display_name":"Jump 10 Index","expected_spike_direction":"down"})
    assert row["family"]=="JUMP" and row["expected_event_direction"] is None and row["expected_spike_direction"] is None
    assert row["direction_probability_model"]=="symmetric"

def test_step_variants_are_registry_first_and_do_not_imply_trade_direction():
    assert classify_derived_family({"provider_symbol":"x","display_name":"Multi Step Index"})["family"]=="STEP_MULTI"
    skew=classify_derived_family({"provider_symbol":"x","display_name":"Skew Step Up Index"});assert skew["family"]=="STEP_SKEW_UP" and skew["expected_event_direction"] is None

