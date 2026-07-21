from analysis.asset_rules import asset_rules
from analysis.execution_state import normalize_execution_state
from analysis.trade_chart import build_trade_chart


def _decision(*,entry=162.34,stop=162.16,targets=None,state="m5_confirmed",timestamp="2026-07-17T10:00:00Z",valid=False):
    targets=targets if targets is not None else [{"name":"TP1","price":162.67},{"name":"TP2","price":162.85}]
    signal={"completed":True,"candle_time":timestamp,"candle_close":162.35} if timestamp else {}
    return {"setup":{"setup_id":"usd-jpy-buy","direction":"buy","stage":state,"zone":{"low":162.17,"high":162.39,"type":"demand"},"confirmation":{"price":162.33,"confirmed":bool(timestamp)},"invalidation":{"price":162.16}},"execution":{"state":state,"entry":entry,"entry_zone":{"low":162.31,"high":162.35,"type":"m5_confirmation_retest"},"m5_execution_zone":{"low":162.31,"high":162.35,"type":"m5_confirmation_retest"},"confirmed_entry":{"price":entry,"confirmed_at":timestamp,"trigger_price":162.33,"trigger_close":162.35},"stop":stop,"targets":targets,"risk_reward":None,"confirmed_state":signal},"quality":{"trade_plan_valid":valid},"user_output":{}}


def test_m15_context_zone_is_distinct_from_narrow_m5_execution_zone():
    decision=_decision(); assert decision["setup"]["zone"]!={k:decision["execution"]["m5_execution_zone"].get(k) for k in decision["setup"]["zone"]}
    assert decision["execution"]["m5_execution_zone"]["low"]>decision["setup"]["zone"]["low"]


def test_m5_confirmed_requires_timestamp_and_confirmed_entry():
    missing_time=_decision(timestamp=None); assert normalize_execution_state(missing_time,current_price=162.34)=="m5_setup_forming"
    missing_entry=_decision(entry=None); assert normalize_execution_state(missing_entry,current_price=162.34)=="m5_setup_forming"
    assert missing_entry["user_output"]["trade_plan_checks_passed"] is False


def test_rr_is_recalculated_from_confirmed_entry_for_every_target():
    decision=_decision(); normalize_execution_state(decision,current_price=162.34,minimum_rr=1.5)
    expected_tp1=(162.67-162.34)/(162.34-162.16); expected_tp2=(162.85-162.34)/(162.34-162.16)
    assert decision["execution"]["targets"][0]["risk_reward"]==round(expected_tp1,3)
    assert decision["execution"]["targets"][1]["risk_reward"]==round(expected_tp2,3)


def test_tp2_cannot_rescue_poor_tp1_geometry():
    decision=_decision(targets=[{"name":"TP1","price":162.47},{"name":"TP2","price":163.0}]); state=normalize_execution_state(decision,current_price=162.40,minimum_rr=1.5)
    assert decision["execution"]["targets"][0]["risk_reward"]<1
    assert state=="too_late" and decision["quality"]["trade_plan_valid"] is False


def test_current_price_near_broad_m15_zone_is_not_near_confirmed_entry():
    decision=_decision(entry=None,timestamp=None,state="waiting_for_m15_area"); state=normalize_execution_state(decision,current_price=162.401)
    assert state=="waiting_for_m15_area" and "near" not in state


def test_entry_extended_uses_confirmed_entry_not_m15_edge():
    decision=_decision(targets=[{"name":"TP1","price":163.0}]); state=normalize_execution_state(decision,current_price=162.50,minimum_rr=1.5)
    assert state=="entry_extended"
    assert decision["execution"]["entry_distance"]==162.50-162.34


def test_chart_and_panel_share_state_and_keep_zones_separate():
    decision=_decision(valid=True); state=normalize_execution_state(decision,current_price=162.34,minimum_rr=1.5); chart=build_trade_chart(decision,current_price=162.34,asset_rules=asset_rules("USD/JPY","forex"))
    assert chart["state"]==state==decision["user_output"]["execution_stage"]
    assert chart["m15_setup_zone"]["low"]==162.17 and chart["m5_execution_zone"]["low"]==162.31
    assert chart["confirmed_entry"]==162.34

