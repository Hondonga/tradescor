from collections import Counter,defaultdict

SETUP_TYPES={"VOLATILITY":("volatility_structure_pullback","volatility_liquidity_reversal","volatility_range_reaction"),"JUMP":("jump_post_event_continuation","jump_post_event_reversal"),"STEP_CLASSIC":("step_range_reaction","step_structure_pullback","step_breakout_and_retest"),"STEP_MULTI":("step_range_reaction","step_structure_pullback","step_breakout_and_retest"),"STEP_SKEW_UP":("step_range_reaction","step_structure_pullback","step_breakout_and_retest"),"STEP_SKEW_DOWN":("step_range_reaction","step_structure_pullback","step_breakout_and_retest")}

def build_reachability(decisions,setups=None,outcomes=None):
    setups=setups or [];outcomes=outcomes or [];filled_ids={x.get("paper_setup_id") for x in outcomes if x.get("entry_filled")};resolved_ids={x.get("paper_setup_id") for x in outcomes if x.get("outcome") not in {None,"OPEN"}};rows={}
    for item in decisions:
        payload=item.get("payload") or item;smc=payload.get("smc_contract") or {};family=payload.get("family");contract_setup=smc.get("setup") or {};funnel=smc.get("gate_funnel") or {};candidates=smc.get("evaluated_candidates") or []
        trace=smc.get("target_trace") or contract_setup.get("target_trace") or {}
        for setup_type in SETUP_TYPES.get(family,()):
            row=rows.setdefault(setup_type,_empty(setup_type));row["evaluations"]+=1;detected=_source_behavior(setup_type,smc,candidates);row["source_behavior_count"]+=int(detected);row["context_count"]+=int(bool(contract_setup.get("direction") or (smc.get("structure") or {}).get("external_structure") in {"bullish","bearish"}));row["location_count"]+=int(bool(contract_setup.get("entry_array")));row["target_candidate_count"]+=len(trace.get("candidates_found") or []);row["target_selected_count"]+=int(bool(trace.get("selected_target")));ready=contract_setup.get("state")=="TRADE_READY" and detected;row["confirmation_count"]+=int(bool((contract_setup.get("entry") is not None or ready) and detected));row["trade_ready_count"]+=int(ready);block=trace.get("first_blocker") or funnel.get("first_blocking_gate") or _blocker(contract_setup);row["first_blockers"][block]+=1 if block else 0
    setup_by_type=Counter(_normalize_setup_type(x) for x in setups)
    for setup_type,row in rows.items():
        row["filled_count"]=sum(1 for x in setups if _normalize_setup_type(x)==setup_type and x.get("paper_setup_id") in filled_ids);row["resolved_count"]=sum(1 for x in setups if _normalize_setup_type(x)==setup_type and x.get("paper_setup_id") in resolved_ids);row["first_blockers"]=dict(row["first_blockers"]);row["reachable"]=row["trade_ready_count"]>0;row["zero_trade_classification"]=_classify(row)
    return list(rows.values())
def aggregate_blockers(reachability):
    counts=Counter();evaluations=sum(x["evaluations"] for x in reachability)
    for row in reachability:counts.update(row["first_blockers"])
    return {"evaluations":evaluations,"first_blockers":dict(counts),"percentages":{key:round(value*100/max(1,sum(counts.values())),2) for key,value in counts.items()}}
def _empty(name):return {"setup_type":name,"evaluations":0,"source_behavior_count":0,"context_count":0,"location_count":0,"target_candidate_count":0,"target_selected_count":0,"confirmation_count":0,"trade_ready_count":0,"filled_count":0,"resolved_count":0,"first_blockers":Counter(),"reachable":False}
def _source_behavior(name,smc,candidates):
    setup=smc.get("setup") or {};event=smc.get("event") or {};structure=smc.get("structure") or {};sweep=setup.get("sweep") or {}
    if name.startswith("jump_"):return bool(event.get("qualified"))
    if "liquidity_reversal" in name or "range_reaction" in name:return sweep.get("type")=="sweep"
    if "breakout" in name:return bool(structure.get("last_bos") or sweep.get("type")=="accepted_breakout")
    return bool(structure.get("last_bos"))
def _blocker(setup):return {"NO_CONTEXT":"external_structure","WAITING_FOR_SWEEP":"sweep_event","WAITING_FOR_DISPLACEMENT":"displacement","MSS_CONFIRMED":"entry_array","WAITING_FOR_RETRACE":"setup_location","WAITING_FOR_ENTRY_CONFIRMATION":"reward_to_risk","TOO_LATE":"chase"}.get(setup.get("state"),setup.get("state","unknown").lower())
def _classify(row):
    if row["evaluations"]==0:return "INSUFFICIENT_DATA"
    if row["source_behavior_count"]==0:return "SOURCE_BEHAVIOR_ABSENT"
    if row["context_count"]==0:return "STRUCTURE_DETECTED"
    if row["target_candidate_count"]==0:return "TARGET_UNAVAILABLE"
    if row["target_selected_count"]==0:return "TARGET_REJECTED"
    if row["trade_ready_count"]==0 and row["confirmation_count"]:return "PLAN_REJECTED"
    if row["trade_ready_count"]==0 and row["location_count"]:return "SETUP_NEAR_MISS"
    if row["trade_ready_count"]==0:return "UNREACHABLE_LIFECYCLE"
    return "REACHABLE"
def _normalize_setup_type(row):return str(row.get("setup_type") or row.get("strategy") or "").lower()
