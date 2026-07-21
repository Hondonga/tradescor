from analysis.derived_family_classifier import classify_derived_family
from analysis.derived_index_rules import derived_index_rules

def test_registry_metadata_unknown_and_override_priority():
    assert classify_derived_family({"provider_symbol":"R_100"})["family"]=="VOLATILITY"
    assert classify_derived_family({"provider_symbol":"B_1","underlying_symbol_type":"boom"})["expected_spike_direction"]=="up"
    assert classify_derived_family({"provider_symbol":"C_1","submarket":"crash indices"})["family"]=="CRASH"
    assert classify_derived_family({"provider_symbol":"UNKNOWN_X"})["family"]=="OTHER_DERIVED"
    assert classify_derived_family({"provider_symbol":"R_100","subgroup":"boom"},{"R_100":{"family":"STEP"}})["family"]=="STEP"

def test_classifier_has_no_second_precision_source():
    # Deriv precision must come only from provider pip-size metadata
    # (analysis.derived_index_rules / precision_registry), never from a
    # hardcoded registry field the classifier would otherwise surface.
    row=classify_derived_family({"provider_symbol":"R_75"})
    assert "symbol_precision" not in row
    assert derived_index_rules("R_75",{"pip_size":.0001})["precision"]==4
