from analysis.derived_setup_lifecycle import advance_setup,clear_lifecycle,active_setups,archived_setups
from analysis.derived_switch_transition import manage_switch_transition
def test_confirmed_switch_archives_and_removes_old_setup():
    clear_lifecycle();zone={"low":1,"high":2,"formed_at":"t"};advance_setup(symbol="DS",direction="buy",zone=zone,state="WAITING_FOR_CONFIRMATION",at="1",setup_id="old")
    row=manage_switch_transition(symbol="DS",from_regime="BULLISH_DRIFT",to_candidate_regime="BEARISH_DRIFT",started_at="2",change_confirmed=True)
    assert row["cancelled_setup_id"]=="old" and not active_setups("DS")
    assert archived_setups()[-1]["terminal_reason"]=="REGIME_SWITCH_CANCELLED"
