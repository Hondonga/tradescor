from analysis.derived_event_identity import lock_event,clear_events
def test_event_identity_is_immutable_and_distinct():
    clear_events();base={"qualified":True,"direction":"up","origin_price":1,"extreme_price":2,"completed_at":"2026-01-01","magnitude_points":1}
    first=lock_event("J","JUMP",base);again=lock_event("J","JUMP",{**base,"extreme_price":2});second=lock_event("J","JUMP",{**base,"completed_at":"2026-01-02","extreme_price":3})
    assert first==again and first["event_id"]!=second["event_id"] and first["extreme_price"]==2
