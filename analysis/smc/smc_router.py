from analysis.smc.adapters import evaluate_volatility_smc,evaluate_jump_smc,evaluate_step_smc
from analysis.derived_model_compatibility import resolve_family_model
from analysis.strategy_reachability_gate import gate_auto_result

_OWNERS={}
def route_smc(*,symbol,family,candles_by_timeframe,tick_size,requested_strategy,analysis_time=None):
    name=family.get("family");previous=_OWNERS.get(symbol);resolution=resolve_family_model(name,requested_strategy);requested=str(requested_strategy).lower();resolved=resolution["resolved_model"] or requested;owner=resolved if resolved not in {"auto","smc_auto","smc"} else "smc_auto";archived=None
    if previous and (previous["owner"]!=owner or previous["family"]!=name):archived={"owner_id":previous["owner"],"setup_id":previous.get("setup_id"),"state":"ARCHIVED_ON_CONTEXT_CHANGE","archived_at":str(analysis_time),"reason":"Authoritative model or market family changed."}
    common=dict(symbol=symbol,family=family,candles_by_timeframe=candles_by_timeframe,tick_size=tick_size,requested_strategy=resolved,analysis_time=analysis_time)
    if name=="VOLATILITY":result=evaluate_volatility_smc(**common)
    elif name=="JUMP":result=evaluate_jump_smc(**common)
    elif name in {"STEP","STEP_CLASSIC","STEP_MULTI","STEP_SKEW_UP","STEP_SKEW_DOWN"}:result=evaluate_step_smc(**common)
    else:raise ValueError(f"SMC adapter is unavailable for {name}.")
    result["ownership"].update({"requested_strategy_id":requested,"selected_strategy_id":owner,"decision_owner_id":owner,"overlay_owner_id":owner,"requested_model":requested,"resolved_model":resolved,"corrected":resolution["corrected"],"correction_reason":resolution["reason"],"selection_mode":"auto" if requested in {"auto","smc","smc_auto"} else "manual","selection_reason":resolution["reason"]})
    result=gate_auto_result(result,name,requested)
    _OWNERS[symbol]={"owner":owner,"family":name,"setup_id":(result.get("setup") or {}).get("setup_id")}
    result["previous_setup"]=archived;return result
def clear_smc_ownership():
    _OWNERS.clear()
    from analysis.smc.adapters.jump_smc_adapter import clear_jump_event_state
    clear_jump_event_state()
