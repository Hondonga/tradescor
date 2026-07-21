from analysis.derived_auto_decision_normalizer import normalize_derived_auto
def test_selected_strategy_plan_is_same_object_and_no_selection_has_no_levels():
    plan={"entry":10,"stop":9,"tp1":{"price":12}};selected={"decision":{"status":"READY TO BUY","trade_ready":True,"setup_id":"id","developing_direction":"buy"},"active_trade_plan":plan};candidate={"strategy_id":"s","quality_score":.8,"trade_ready":True}
    result=normalize_derived_auto(family={"family":"V"},regime={"regime":"R"},data_gate={"passed":True,"status":"good","warnings":[]},eligibility={"eligible":[],"ineligible":[]},candidates=[candidate],selection={"selected_candidate":candidate,"runner_up":None},selected_result=selected)
    assert result["active_trade_plan"] is plan and result["decision"]["strategy"]=="s"
    none=normalize_derived_auto(family={"family":"V"},regime={"regime":"UNSTABLE"},data_gate={"passed":True,"status":"good","warnings":[]},eligibility={"eligible":[],"ineligible":[]},candidates=[],selection={"selected_candidate":None,"runner_up":None})
    assert none["active_trade_plan"] is None and none["decision"]["setup_id"] is None and none["decision"]["status"]=="STRATEGY INELIGIBLE"
