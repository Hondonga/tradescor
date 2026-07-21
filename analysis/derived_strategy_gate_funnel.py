"""Ordered, diagnostic-only gates for every Derived strategy evaluation."""
from __future__ import annotations
import pandas as pd

GATES=("family_supported","data_quality","history_depth","regime_eligibility","directional_context","setup_location","zone_interaction","confirmation","stop_geometry","target_geometry","reward_to_risk","chase_validation")
DEFAULT_REQUIRED={"D1":1,"H4":1,"H1":1,"M15":20,"M5":20}

def build_strategy_gate_funnel(strategy,result,*,family=None,regime=None,data_quality=None,frames=None,current_price=None,required_history=None):
    family=family or {};regime=regime or {};quality=data_quality or {};frames=frames or {};required={**DEFAULT_REQUIRED,**(required_history or {})};available={key:len(frames.get(key,[])) if frames.get(key) is not None else 0 for key in required};strategy_contract=result.get("strategy") or {};decision=result.get("decision") or {};zone=result.get("m15_setup_zone") or result.get("retest_zone");execution=result.get("m5_execution_zone") or result.get("retest_zone");confirmation=result.get("confirmation") or {};plan=result.get("active_trade_plan") or {};stop=result.get("structural_stop") or {};targets=result.get("targets") or {};rr=result.get("reward_risk") or {};chase=result.get("chase") or {};eligibility_reason=strategy_contract.get("eligibility_reason","")
    history_ok=all(available[key]>=needed for key,needed in required.items());family_ok=bool(strategy_contract.get("eligible",True)) or not any(word in eligibility_reason.lower() for word in ("family","unsupported"));regime_ok=not any(word in eligibility_reason.lower() for word in ("regime","restricted"));direction=decision.get("developing_direction") or (result.get("selected_candidate") or {}).get("direction");zone_interacted=bool(execution or confirmation.get("zone_interacted") or confirmation.get("valid"));stop_ok=bool(plan.get("stop") is not None or stop.get("valid"));target_ok=bool(plan.get("tp1") is not None or targets.get("tp1") is not None or targets.get("valid"));rr_value=plan.get("tp1_rr",rr.get("tp1_rr",rr.get("rr")));rr_ok=bool(rr.get("valid") or plan and rr_value is not None);chase_ok=bool(chase.get("valid") or plan and plan.get("timing_state") not in {"TOO_LATE","MISSED","EXTENDED"});stale=_stale_range(result,current_price);contradictions=_contradictions(result)
    rows={
      "family_supported":_gate(family_ok,eligibility_reason or ("Family supported." if family_ok else "Family is unsupported.")),
      "data_quality":_gate(quality.get("status","good")=="good" and quality.get("analysis_allowed",True),"Completed-candle data passed quality checks." if quality.get("status","good")=="good" else "Candle data is partial, invalid, or still loading."),
      "history_depth":{**_gate(history_ok,"Required completed higher-timeframe history is available." if history_ok else "Required completed higher-timeframe context is not loaded."),"available":available,"required":required},
      "regime_eligibility":_gate(regime_ok,eligibility_reason or ("Current regime is eligible." if regime_ok else "Current regime is not supported.")),
      "directional_context":_gate(direction in {"buy","sell"},f"{str(direction).title()} context identified." if direction else "No measurable directional context yet."),
      "setup_location":_gate(bool(zone) and not stale,"A current setup location is locked." if zone and not stale else "No current valid setup location exists." if not zone else "The locked setup location is stale."),
      "zone_interaction":_gate(zone_interacted,"Price has interacted with the execution area." if zone_interacted else "Price has not reached the selected setup area."),
      "confirmation":_gate(bool(confirmation.get("valid")),"Completed M5 confirmation passed." if confirmation.get("valid") else "A completed M5 trigger is not available."),
      "stop_geometry":_gate(stop_ok,"Structural stop geometry passed." if stop_ok else "Unavailable until confirmation produces valid execution structure."),
      "target_geometry":_gate(target_ok,"A valid unswept target is available." if target_ok else "No validated target geometry is available."),
      "reward_to_risk":_gate(rr_ok,"Projected reward-to-risk passed." if rr_ok else "Reward-to-risk is unavailable or below the configured minimum."),
      "chase_validation":_gate(chase_ok,"Entry distance passed chase validation." if chase_ok else "Entry is too extended under the configured chase limit.")}
    first=next((key for key in GATES if not rows[key]["passed"]),"");passed=sum(rows[key]["passed"] for key in GATES);status=_status(first,rows,contradictions,stale,decision);stage=_stage(first,result)
    funnel={"strategy":strategy,**rows,"first_blocking_gate":first,"passed_gate_count":passed,"total_gate_count":len(GATES),"status":status,"setup_stage":stage,"state_contradictions":contradictions,"stale_setup_state":stale,"next_price_condition":_next_condition(first,direction),"confirmation_required":"Completed M5 confirmation is required before any plan becomes actionable.","why_no_trade_plan":rows[first]["reason"] if first else "All setup gates passed."}
    funnel["shadow_candidate"]=_shadow(funnel,result,direction,rr_value)
    return funnel

def _gate(passed,reason):return {"passed":bool(passed),"reason":reason}
def _status(first,rows,contradictions,stale,decision):
    if contradictions:return "STATE CONTRADICTION"
    if stale:return "STALE SETUP STATE"
    if first in {"data_quality","history_depth"}:return "INSUFFICIENT HISTORY"
    if first in {"family_supported","regime_eligibility"}:return "STRATEGY INELIGIBLE"
    if first in {"directional_context","setup_location"}:return "NO MARKET OPPORTUNITY" if first=="directional_context" else "WAITING FOR LOCATION"
    if first in {"zone_interaction","confirmation"}:return "WAITING FOR CONFIRMATION" if rows["zone_interaction"]["passed"] else "WAITING FOR LOCATION"
    if first=="chase_validation":return "TOO LATE"
    if first:return "PLAN REJECTED"
    return decision.get("status","TRADE PLAN READY")
def _stage(first,result):
    if first in {"family_supported","data_quality","history_depth","regime_eligibility","directional_context"}:return "context evaluation"
    if first=="setup_location":return "waiting for setup location"
    if first=="zone_interaction":return "waiting for price interaction"
    if first=="confirmation":return "waiting for M5 confirmation"
    if first:return "trade plan validation"
    return "trade ready"
def _next_condition(first,direction):
    if first=="setup_location":return "Wait for a qualified completed-candle setup area."
    if first=="zone_interaction":return f"Wait for price to reach the selected {direction or 'setup'} area."
    if first=="confirmation":return "Wait for a completed M5 trigger."
    if first in {"stop_geometry","target_geometry","reward_to_risk"}:return "Wait for structurally valid risk and objective geometry."
    return "Wait for the first blocking requirement to pass."
def _stale_range(result,current):
    locked=result.get("range") or {};low=locked.get("low");high=locked.get("high")
    return bool(locked.get("valid") and current is not None and low is not None and high is not None and not float(low)<=float(current)<=float(high) and (result.get("decision") or {}).get("status") in {"STABLE RANGE","STEP RANGE","RANGE LOCKED","WAITING FOR BOUNDARY"})
def _contradictions(result):
    decision=result.get("decision") or {};phase=str(decision.get("phase") or decision.get("status") or "").upper().replace("_"," ");structure=str((result.get("structure") or result.get("run_structure") or {}).get("state") or (result.get("run_structure") or {}).get("classification") or decision.get("structure") or "").upper().replace("_"," ");rows=[]
    if "STABLE RANGE" in phase and "UNSTABLE" in structure:rows.append("Stable Range cannot coexist with Unstable Structure without a temporary-instability classification.")
    if decision.get("trade_ready") and not result.get("active_trade_plan"):rows.append("Trade-ready state has no complete active trade plan.")
    return rows
def _shadow(funnel,result,direction,rr_value):
    if not direction and funnel["passed_gate_count"]<4:return None
    first=funnel["first_blocking_gate"]
    return {"strategy":funnel["strategy"],"direction":direction or "","setup_stage":funnel["setup_stage"],"passed_gate_count":funnel["passed_gate_count"],"total_gate_count":funnel["total_gate_count"],"first_blocking_gate":first,"current_values":{"tp1_rr":rr_value},"required_values":{"minimum_tp1_rr":(result.get("reward_risk") or {}).get("minimum_required_rr")},"would_be_trade_ready_if":[funnel[first]["reason"]] if first else [],"research_only":True,"actionable_levels":None}

def archive_stale_range(symbol,result,at):
    from analysis.derived_range_lock import release_range
    from analysis.derived_setup_lifecycle import active_setups,advance_setup
    locked=result.get("range") or {};range_id=locked.get("range_id")
    if not range_id:return []
    release_range(symbol,range_id);archived=[]
    for row in active_setups(symbol):
        if row.get("range_id")==range_id:archived.append(advance_setup(symbol=symbol,direction=row["direction"],zone=result.get("m15_setup_zone") or {"low":locked.get("low"),"high":locked.get("high")},state="INVALIDATED",at=str(at),setup_id=row["setup_id"],strategy=row.get("strategy",""),family=row.get("family",""),range_id=range_id))
    return archived
