from analysis.derived_setup_lifecycle import advance_setup,archived_setups,clear_lifecycle
def test_new_spike_cancellation_is_archived():
    clear_lifecycle();zone={"low":1,"high":2,"formed_at":"t"};advance_setup(symbol="BOOM500",direction="buy",zone=zone,state="POST_SPIKE_CANCELLED",at="x",setup_id="old",strategy="boom_crash_spike_state",family="BOOM");
    assert archived_setups()[-1]["state"]=="POST_SPIKE_CANCELLED" and archived_setups()[-1]["cancelled_by_new_spike_at"]=="x"
