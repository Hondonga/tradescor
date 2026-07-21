from pathlib import Path
from analysis.derived_switch_decision_normalizer import normalize_switch_decision
def test_transition_has_no_plan_or_zero_distance():
    result=normalize_switch_decision(eligibility={"eligible":True,"family":"DRIFT_SWITCH","eligibility_reason":""},context={"transition_active":True},stability={"stable":False},transition={},routing={},risk_adjustments={},delegated_result={"active_trade_plan":{"entry":1}})
    assert result["active_trade_plan"] is None and result["decision"]["setup_id"] is None
def test_manual_option_and_backend_owned_projection():
    root=Path(__file__).parents[1]; assert 'value="derived_regime_switch"' in (root/"templates/index.html").read_text()
    plan={"entry":10,"stop":9,"tp1":{"price":12}};delegated={"decision":{"status":"READY TO BUY","trade_ready":True,"setup_id":"s","developing_direction":"buy"},"active_trade_plan":plan}
    result=normalize_switch_decision(eligibility={"eligible":True,"family":"DRIFT_SWITCH","eligibility_reason":""},context={"transition_active":False},stability={"stable":True,"change_pending":False},transition={},routing={},risk_adjustments={},delegated_result=delegated)
    assert result["active_trade_plan"] is plan
