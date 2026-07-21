from analysis.derived_range_price_location import classify_range_location

def test_range_location_is_symmetric_and_midrange_is_explicit():
    locked={"low":100.,"high":110.}
    assert classify_range_location(101.,locked,1.)["location"]=="lower_boundary"
    assert classify_range_location(109.,locked,1.)["location"]=="upper_boundary"
    assert classify_range_location(105.,locked,1.)["location"]=="mid_range"
    assert classify_range_location(111.,locked,1.)["location"]=="outside"
