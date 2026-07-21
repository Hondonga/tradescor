import pandas as pd
from analysis.derived_model_compatibility import compatibility_for,resolve_family_model
from analysis.smc.smc_data_readiness import evaluate_data_readiness
from analysis.smc.smc_product_contract import build_smc_product_contract
from analysis.smc.smc_blockers import target_blocker_detail
from providers.market_registry import derived_registry

def _frame(count=80):
    return pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:00:00Z")+pd.Timedelta(minutes=5*i),"open":100,"high":101,"low":99,"close":100,"complete":True} for i in range(count)])
def _frames(stale=False):
    rows={key:_frame() for key in ("M5","M15","H1","H4")}
    if stale:
        for frame in rows.values():frame.attrs.update(stale_data=True,last_successful_update=1760000000)
    return rows
class Provider:
    def list_symbols(self):return [{"provider_symbol":"CRASH50","display_name":"Crash 50 Index","family":"CRASH","analysis_supported":True},{"provider_symbol":"JD10","display_name":"Jump 10 Index","family":"JUMP","analysis_supported":True}]

def test_family_matrix_never_exposes_step_for_other_families():
    for family in ("CRASH","BOOM","JUMP","VOLATILITY"):assert "step_smc" not in compatibility_for(family)["allowed_models"]
    crash=next(row for row in derived_registry(Provider()) if row["family"]=="CRASH")
    assert crash["default_model"]=="boom_crash_spike_state" and {x["id"] for x in crash["available_models"]}=={"boom_crash_spike_state"}
    assert crash["production_supported"] is False and crash["research_supported"] is True
    correction=resolve_family_model("CRASH","step_smc");assert correction=={**correction,"resolved_model":"boom_crash_spike_state","corrected":True}

def test_cached_completed_history_is_stale_not_provider_error():
    state=evaluate_data_readiness(_frames(True),pd.Timestamp("2026-01-01T08:00:00Z"));assert state["state"]=="stale" and state["analysis_paused"] and state["last_successful_update"]==1760000000
    empty=evaluate_data_readiness({},pd.Timestamp("2026-01-01T08:00:00Z"));assert empty["state"]=="insufficient"

def test_no_context_contract_has_no_setup_or_quality():
    result={"ownership":{"selected_strategy_id":"smc_auto","decision_owner_id":"smc_auto","overlay_owner_id":"smc_auto","adapter_id":"volatility_smc_adapter"},"setup":{"state":"NO_CONTEXT","setup_id":"x","direction":"","entry_array":{},"targets":[]},"structure":{"external_structure":"range","internal_structure":"range"},"scoring":{"quality_score":64,"quality_grade":"C","valid":False},"trade_chart":{"current_price":100}}
    contract=build_smc_product_contract(symbol="R_50",display_symbol="Volatility 50 Index",timeframe="M5",analysis_time=pd.Timestamp("2026-01-01T08:00:00Z"),family={"family":"VOLATILITY"},candles_by_timeframe=_frames(),result=result)
    assert contract["decision"]["stage"]=="NO_CONTEXT" and contract["setup"]["setup_type"] is None and contract["setup"]["direction"] is None and contract["setup"]["setup_quality_score"] is None

def test_range_candidate_cannot_remain_no_context():
    result={"ownership":{"selected_strategy_id":"smc_auto","decision_owner_id":"smc_auto","overlay_owner_id":"smc_auto","adapter_id":"volatility_smc_adapter"},"setup":{"state":"NO_CONTEXT","setup_id":"x","setup_type":"range_reaction","direction":"","entry_array":{},"targets":[],"next_required_condition":"Reach boundary"},"dealing_range":{"valid":True,"low":90,"high":110},"structure":{"external_structure":"range","internal_structure":"range"},"scoring":{"quality_score":64,"quality_grade":"C","valid":False},"trade_chart":{"current_price":100}}
    contract=build_smc_product_contract(symbol="R_50",display_symbol="Volatility 50 Index",timeframe="M5",analysis_time=pd.Timestamp("2026-01-01T08:00:00Z"),family={"family":"VOLATILITY"},candles_by_timeframe=_frames(),result=result)
    assert contract["decision"]["stage"]=="WAITING_FOR_BOUNDARY" and contract["decision"]["status"]=="WAITING FOR BOUNDARY"

def test_target_blocker_has_code_and_separate_label():
    detail=target_blocker_detail({"first_blocker":"TARGET_EXISTS_RR_REJECTED","candidates_rejected":[{"rejection_code":"RR_BELOW_MINIMUM","projected_rr":1.18}]})
    assert detail=={"code":"TARGET_RR_BELOW_MINIMUM","label":"Target does not provide enough reward","current_value":"1.18R","required_value":"1.50R"}
