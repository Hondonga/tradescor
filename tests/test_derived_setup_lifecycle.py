from analysis.derived_setup_lifecycle import setup_identity,advance_setup,archived_setups,clear_lifecycle
def test_terminal_setup_archives_and_new_opposite_setup_gets_new_id():
    clear_lifecycle();zone={"low":99,"high":100,"formed_at":"t"};sell=setup_identity("R_100","sell",zone);advance_setup(symbol="R_100",direction="sell",zone=zone,state="MISSED",at="t2",setup_id=sell);assert archived_setups()[-1]["setup_id"]==sell
    buy=setup_identity("R_100","buy",zone);assert buy!=sell;assert advance_setup(symbol="R_100",direction="buy",zone=zone,state="WAITING_FOR_PULLBACK",at="t3",setup_id=buy)["state"]=="WAITING_FOR_PULLBACK"

def test_out_of_order_stale_analysis_cannot_regress_a_newer_recorded_stage():
    # Simulates a slow/delayed request completing after a later poll already advanced
    # the same setup further - the stale write must be dropped, not applied on top.
    clear_lifecycle();zone={"low":99,"high":100,"formed_at":"t"};setup_id=setup_identity("R_100","buy",zone)
    advance_setup(symbol="R_100",direction="buy",zone=zone,state="IN_ZONE",at="2026-01-01T00:05:00Z",setup_id=setup_id)
    advance_setup(symbol="R_100",direction="buy",zone=zone,state="CONFIRMED",at="2026-01-01T00:10:00Z",setup_id=setup_id)
    stale=advance_setup(symbol="R_100",direction="buy",zone=zone,state="WAITING_FOR_CONFIRMATION",at="2026-01-01T00:07:00Z",setup_id=setup_id)
    assert stale["state"]=="CONFIRMED"
    fresh=advance_setup(symbol="R_100",direction="buy",zone=zone,state="ENTRY_AVAILABLE",at="2026-01-01T00:15:00Z",setup_id=setup_id)
    assert fresh["state"]=="ENTRY_AVAILABLE"
