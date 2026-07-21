from analysis.derived_setup_lifecycle import advance_setup,cancel_active_setups_for_new_event,clear_lifecycle,active_setups,archived_setups
def test_new_event_cancels_and_archives_stale_setup():
    clear_lifecycle();advance_setup(symbol="J",direction="buy",zone={"low":1,"high":2,"formed_at":"x"},state="IN_ZONE",at="1",setup_id="old",strategy="jump_dex_post_event",family="JUMP")
    rows=cancel_active_setups_for_new_event("J","event-new","2");assert rows[0]["terminal_reason"]=="NEW_EVENT_CANCELLED" and not active_setups("J") and archived_setups()[-1]["setup_id"]=="old"
