from analysis.execution_state import normalize_execution_state


def _decision(direction="sell",current_state="too_late",confirmed=False,entry=None,rr=None,valid=False):
    stop=(entry-.0005 if direction=="buy" else entry+.0005) if entry else None; target=(entry+.001 if direction=="buy" else entry-.001) if entry else None
    return {"setup":{"setup_id":"new","direction":direction,"stage":current_state,"zone":{"low":1.40497,"high":1.40585},"confirmation":{"price":1.40511,"confirmed":confirmed},"invalidation":{"price":1.4040 if direction=="buy" else 1.4060}},"execution":{"state":current_state,"entry":entry,"entry_zone":{"low":entry-.0001,"high":entry+.0001,"type":"m5"} if entry else None,"m5_execution_zone":{"low":entry-.0001,"high":entry+.0001,"type":"m5"} if entry else None,"confirmed_entry":{"price":entry,"confirmed_at":"2026-01-01","trigger_price":1.40511,"trigger_close":entry} if confirmed else {},"stop":stop,"targets":[{"price":target}] if target else [],"risk_reward":rr,"forming_state":None,"confirmed_state":{"candle_time":"2026-01-01","completed":True,"candle_close":entry} if confirmed else None},"quality":{"trade_plan_valid":valid},"user_output":{},"requested_strategy":"ict_2022"}


def test_inside_sell_zone_cannot_be_too_late_before_confirmation():
    decision=_decision(); state=normalize_execution_state(decision,current_price=1.40502,minimum_rr=1.5,tolerance=.000005)
    assert state=="in_m15_area"
    assert decision["execution"]["price_location"]=="IN_M15_AREA"
    assert decision["user_output"]["status"]=="SELL SETUP FORMING"


def test_inside_buy_zone_and_boundary_equality_are_inside():
    decision=_decision("buy"); decision["setup"]["confirmation"]["price"]=1.4057
    assert normalize_execution_state(decision,current_price=1.40497)=="in_m15_area"
    assert decision["execution"]["price_location"]=="IN_M15_AREA"
    decision=_decision("buy"); normalize_execution_state(decision,current_price=1.40585000000001,tolerance=.000005)
    assert decision["execution"]["price_location"]=="IN_M15_AREA"


def test_price_below_sell_zone_before_confirmation_waits_for_zone():
    decision=_decision(); assert normalize_execution_state(decision,current_price=1.403)=="waiting_for_m15_area"


def test_completed_close_and_valid_plan_make_entry_available():
    decision=_decision(current_state="entry_available",confirmed=True,entry=1.4050,rr=1.8,valid=True)
    assert normalize_execution_state(decision,current_price=1.4049)=="entry_available"
    assert decision["execution"]["confirmation_requirements_passed"]


def test_poor_rr_is_too_late_after_confirmation():
    decision=_decision(confirmed=True,entry=1.4050,rr=1.2,valid=False)
    decision["execution"]["targets"]=[{"price":1.4048}]
    assert normalize_execution_state(decision,current_price=1.4048)=="too_late"


def test_confirmed_sell_can_become_extended_after_moving_away():
    decision=_decision(confirmed=True,entry=1.4055,rr=2.0,valid=False); decision["execution"]["targets"]=[{"price":1.403}]
    assert normalize_execution_state(decision,current_price=1.4045)=="entry_extended"
