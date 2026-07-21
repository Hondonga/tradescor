from analysis.derived_setup_lifecycle import advance_setup,archived_setups,clear_lifecycle
def test_failed_breakout_archives_and_new_setup_id_is_independent():
    clear_lifecycle();zone={"low":99,"high":100,"formed_at":"t"};old=advance_setup(symbol="RB100",direction="buy",zone=zone,state="FAILED_BREAKOUT",at="x",setup_id="old",strategy="derived_range_break_retest",family="RANGE_BREAK",range_id="r1");assert archived_setups()[-1]["setup_id"]=="old"
    new=advance_setup(symbol="RB100",direction="sell",zone=zone,state="WAITING_FOR_RETEST",at="y",setup_id="new",strategy="derived_range_break_retest",family="RANGE_BREAK",range_id="r2");assert new["setup_id"]!=old["setup_id"]
