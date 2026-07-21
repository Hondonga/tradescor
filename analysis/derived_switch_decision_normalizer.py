"""Projection of orchestration/delegation without recalculating trade prices."""
def normalize_switch_decision(*,eligibility,context,stability,transition,routing,risk_adjustments,delegated_result=None):
    if not eligibility["eligible"]: status=eligibility.get("data_state","DATA UNAVAILABLE"); delegated_result=None
    elif context.get("transition_active") or stability.get("change_pending") or not stability.get("stable"): status="WAITING FOR REGIME CONFIRMATION"; delegated_result=None
    elif delegated_result: status=(delegated_result.get("decision") or {}).get("status","STRATEGY DELEGATED")
    else: status="NO VALID SETUP"
    source=(delegated_result or {}).get("decision") or {}; plan=(delegated_result or {}).get("active_trade_plan")
    decision={"status":status,"market_bias":source.get("market_bias","neutral"),"developing_direction":source.get("developing_direction","") if delegated_result else "","trade_ready":bool(source.get("trade_ready") and delegated_result),"setup_id":source.get("setup_id") if delegated_result else None,"summary":status.title(),"phase":context.get("current_regime",""),"next_action":source.get("next_action") if delegated_result else "Wait for completed-candle regime confirmation." if status=="WAITING FOR REGIME CONFIRMATION" else "Wait for a stable eligible regime."}
    return {"orchestrator":{"name":"Derived Regime-Switch Orchestrator","eligible":eligibility["eligible"],"family":eligibility["family"],"eligibility_reason":eligibility["eligibility_reason"]},"switch_context":context,"regime_stability":stability,"transition":transition,"routing":routing,"risk_adjustments":risk_adjustments,"decision":decision,"delegated_result":delegated_result,"active_trade_plan":plan,"previous_setup":None,"warnings":[]}
