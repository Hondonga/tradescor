import pandas as pd
from analysis.derived_strategy_gate_funnel import build_strategy_gate_funnel
from analysis.strategy_gate_diagnostics_store import StrategyGateDiagnosticsStore
from paper_testing.derived_signal_snapshot import build_derived_signal_snapshot
from paper_testing.derived_setup_tracker import build_paper_setup

def frames(count=25):
    row=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:00:00Z")+pd.Timedelta(minutes=i*5),"open":100,"high":101,"low":99,"close":100,"complete":True} for i in range(count)])
    return {key:row.copy() for key in ("D1","H4","H1","M15","M5")}

def base_result(**changes):
    row={"strategy":{"eligible":True,"eligibility_reason":"Eligible context."},"decision":{"status":"WAITING","developing_direction":"sell","trade_ready":False},"m15_setup_zone":{"low":101,"high":102,"valid":True},"m5_execution_zone":None,"confirmation":None,"active_trade_plan":None}
    row.update(changes);return row

def test_missing_h4_h1_is_insufficient_history():
    history=frames();history["H4"]=history["H4"].iloc[0:0];history["H1"]=history["H1"].iloc[0:0]
    funnel=build_strategy_gate_funnel("test",base_result(),data_quality={"status":"good","analysis_allowed":True},frames=history,current_price=100)
    assert funnel["status"]=="INSUFFICIENT HISTORY" and not funnel["history_depth"]["passed"]

def test_developing_setup_has_direction_and_specific_waiting_status():
    funnel=build_strategy_gate_funnel("test",base_result(),data_quality={"status":"good","analysis_allowed":True},frames=frames(),current_price=100)
    assert funnel["directional_context"]["passed"] and funnel["status"]=="WAITING FOR LOCATION" and funnel["first_blocking_gate"]=="zone_interaction"

def test_stable_range_unstable_structure_is_contradiction_and_stale_range_detects():
    result=base_result(decision={"status":"STABLE RANGE","phase":"STABLE RANGE","developing_direction":"sell"},structure={"state":"UNSTABLE"},range={"valid":True,"low":99,"high":101,"range_id":"r1"})
    funnel=build_strategy_gate_funnel("range",result,data_quality={"status":"good","analysis_allowed":True},frames=frames(),current_price=102)
    assert funnel["status"]=="STATE CONTRADICTION" and funnel["stale_setup_state"] and funnel["state_contradictions"]

def test_confirmation_with_failed_rr_is_plan_rejected_with_values():
    result=base_result(m5_execution_zone={"low":101,"high":102},confirmation={"valid":True},structural_stop={"valid":True},targets={"valid":True,"tp1":99},reward_risk={"valid":False,"tp1_rr":1.28,"minimum_required_rr":1.5},chase={"valid":True})
    funnel=build_strategy_gate_funnel("test",result,data_quality={"status":"good","analysis_allowed":True},frames=frames(),current_price=101.5)
    assert funnel["status"]=="PLAN REJECTED" and funnel["first_blocking_gate"]=="reward_to_risk"
    assert funnel["shadow_candidate"]["current_values"]["tp1_rr"]==1.28 and funnel["shadow_candidate"]["required_values"]["minimum_tp1_rr"]==1.5

def test_failed_chase_is_too_late():
    result=base_result(m5_execution_zone={"low":101,"high":102},confirmation={"valid":True},structural_stop={"valid":True},targets={"valid":True,"tp1":99},reward_risk={"valid":True,"tp1_rr":2},chase={"valid":False})
    funnel=build_strategy_gate_funnel("test",result,data_quality={"status":"good","analysis_allowed":True},frames=frames(),current_price=101.5);assert funnel["status"]=="TOO LATE"

def test_shadow_candidate_has_no_actionable_levels_or_paper_setup():
    result=base_result();funnel=build_strategy_gate_funnel("test",result,data_quality={"status":"good","analysis_allowed":True},frames=frames(),current_price=100);shadow=funnel["shadow_candidate"]
    assert shadow["actionable_levels"] is None and shadow["research_only"]
    contract={"decision":{"setup_id":"s1","developing_direction":"sell","status":"WAITING"},"active_trade_plan":None,"shadow_candidate":shadow};snap=build_derived_signal_snapshot(provider_symbol="R_100",display_name="R100",family="VOLATILITY",subfamily="",requested_strategy="Auto",analysis_candle_time="2026-01-01T00:00:00Z",decision_contract=contract);assert build_paper_setup(snap) is None

def test_gate_failure_counts_persist(tmp_path):
    store=StrategyGateDiagnosticsStore(tmp_path/"gates.db");funnel=build_strategy_gate_funnel("test",base_result(),data_quality={"status":"good","analysis_allowed":True},frames=frames(),current_price=100)
    store.record(symbol="R_100",family="VOLATILITY",strategy="test",regime="TREND",funnel=funnel,day="2026-01-01");store.record(symbol="R_100",family="VOLATILITY",strategy="test",regime="TREND",funnel=funnel,day="2026-01-01");report=store.report(symbol="R_100")
    assert report["evaluations"]==2 and report["most_common_blocker"]=="zone_interaction"
