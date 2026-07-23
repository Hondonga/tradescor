"""Prevent unproved strategy behaviors from emitting Auto trade plans."""
from __future__ import annotations
import json
from pathlib import Path

_REPORT=Path(__file__).resolve().parents[1]/"data"/"strategy_setup_proof"/"latest.json"
_HISTORY_REPORT=Path(__file__).resolve().parents[1]/"data"/"volatility75_acceptance"/"latest_audit.json"


def reachability_status(strategy_id,report_path=None):
    try:rows=json.loads(Path(report_path or _REPORT).read_text(encoding="utf-8")).get("strategies",[])
    except (OSError,ValueError):return "UNPROVED"
    return next((row.get("status","UNPROVED") for row in rows if row.get("strategy_id")==strategy_id),"UNPROVED")


def production_strategy_status(strategy_id="volatility_structure_pullback"):
    try:proof=json.loads(_REPORT.read_text(encoding="utf-8"));row=next((item for item in proof.get("strategies",[]) if item.get("strategy_id")==strategy_id),{})
    except (OSError,ValueError):row={}
    try:history=json.loads(_HISTORY_REPORT.read_text(encoding="utf-8"));historical=bool((history.get("acceptance") or {}).get("passed") and (history.get("counts") or {}).get("trade_ready",0)>0)
    except (OSError,ValueError):historical=False
    reachable=row.get("status")=="REACHABLE";supported=bool(row.get("production_supported",strategy_id=="volatility_structure_pullback"))
    directions=set(row.get("directions_reached") or [])
    return {"strategy_id":strategy_id,"production_supported":supported,"fixture_buy_reachable":"buy" in directions,"fixture_sell_reachable":"sell" in directions,"historically_observed":historical,"live_observed":False,"auto_eligible":bool(supported and reachable)}


def strategy_id_for_setup(family,setup_type):
    family=str(family or "").upper();kind=str(setup_type or "").lower()
    if family=="VOLATILITY":return {"structure_pullback":"volatility_structure_pullback","liquidity_reversal":"volatility_liquidity_reversal","range_reaction":"volatility_range_reaction","breakout_and_retest":"volatility_breakout_and_retest"}.get(kind)
    if family.startswith("STEP") or family=="STEP":return {"range_reaction":"step_range_reaction","range_boundary_reaction":"step_range_reaction","structure_pullback":"step_structure_pullback","breakout_and_retest":"step_breakout_and_retest"}.get(kind)
    if family=="JUMP":return {"jump_post_event_continuation":"jump_post_event_continuation","jump_post_event_reversal":"jump_post_event_reversal","jump_post_event_smc":"jump_post_event_continuation"}.get(kind)
    if family in {"BOOM","CRASH","BOOM_CRASH"}:return "boom_crash_spike_state"
    return None


# Phase 6: no strategy for this market has passed the required historical
# validation, so a reachable-but-unvalidated Auto candidate must be blocked
# with its own distinct outcome rather than reported as "PLAN REJECTED"
# (which means "not even technically reachable"). Deferred import avoids a
# circular import -- strategy_quarantine_registry imports this module.
NO_VALIDATED_STRATEGY_MESSAGE = "No strategy for this market has passed the required historical validation."


def _validation_blocked(strategy_id):
    from analysis.strategy_quarantine_registry import is_auto_eligible
    return not is_auto_eligible(strategy_id)


def gate_auto_result(result,family,requested_strategy):
    if str(requested_strategy or "auto").lower() not in {"auto","smc","smc_auto"}:return result
    setup=result.get("setup") or {};strategy_id=strategy_id_for_setup(family,setup.get("setup_type") or setup.get("type"))
    if not strategy_id:return result
    if reachability_status(strategy_id)!="REACHABLE":
        reason=f"{strategy_id} is excluded from production Auto routing until chronological setup proof reaches REACHABLE."
        setup.update(state="PLAN REJECTED",entry=None,stop=None,targets=[],rr=None,research_only=True,next_required_condition=reason,reachability_status=reachability_status(strategy_id))
        decision=result.get("decision") or {};decision.update(status="PLAN REJECTED",trade_ready=False,next_action=reason,first_blocking_gate="strategy_reachability")
        result.update(setup=setup,decision=decision,active_trade_plan=None,m15_setup_zone=None,m5_execution_zone=None)
        chart=result.get("trade_chart") or {};chart.update(state="none",confirmed_entry=None,stop=None,targets=[]);result["trade_chart"]=chart
        result["reachability_gate"]={"strategy_id":strategy_id,"status":reachability_status(strategy_id),"auto_eligible":False,"reason":reason}
        return result
    if _validation_blocked(strategy_id):
        reason=NO_VALIDATED_STRATEGY_MESSAGE
        setup.update(state="NO_VALIDATED_STRATEGY_AVAILABLE",entry=None,stop=None,targets=[],rr=None,research_only=True,next_required_condition=reason)
        decision=result.get("decision") or {};decision.update(status="NO_VALIDATED_STRATEGY_AVAILABLE",trade_ready=False,next_action=reason,first_blocking_gate="historical_validation")
        result.update(setup=setup,decision=decision,active_trade_plan=None,m15_setup_zone=None,m5_execution_zone=None)
        chart=result.get("trade_chart") or {};chart.update(state="none",confirmed_entry=None,stop=None,targets=[]);result["trade_chart"]=chart
        result["reachability_gate"]={"strategy_id":strategy_id,"status":reachability_status(strategy_id),"auto_eligible":False,"reason":reason,"blocking_gate":"historical_validation"}
        return result
    return result


def gate_normalized_auto_result(result,family,requested_strategy):
    if str(requested_strategy or "auto").lower() not in {"auto","smc","smc_auto"}:return result
    decision=result.get("decision") or {};strategy_id=strategy_id_for_setup(family,(result.get("setup") or {}).get("setup_type"))
    if not strategy_id and str(family).upper() in {"BOOM","CRASH"}:strategy_id="boom_crash_spike_state"
    if not strategy_id:return result
    if reachability_status(strategy_id)!="REACHABLE":
        reason=f"{strategy_id} is excluded from production Auto routing until chronological setup proof reaches REACHABLE."
        decision.update(status="PLAN REJECTED",trade_ready=False,next_action=reason,first_blocking_gate="strategy_reachability")
        result.update(decision=decision,active_trade_plan=None,m15_setup_zone=None,m5_execution_zone=None,reachability_gate={"strategy_id":strategy_id,"status":reachability_status(strategy_id),"auto_eligible":False,"reason":reason})
        chart=result.get("trade_chart") or {};chart.update(state="none",confirmed_entry=None,stop=None,targets=[]);result["trade_chart"]=chart
        return result
    if _validation_blocked(strategy_id):
        reason=NO_VALIDATED_STRATEGY_MESSAGE
        decision.update(status="NO_VALIDATED_STRATEGY_AVAILABLE",trade_ready=False,next_action=reason,first_blocking_gate="historical_validation")
        result.update(decision=decision,active_trade_plan=None,m15_setup_zone=None,m5_execution_zone=None,reachability_gate={"strategy_id":strategy_id,"status":reachability_status(strategy_id),"auto_eligible":False,"reason":reason,"blocking_gate":"historical_validation"})
        chart=result.get("trade_chart") or {};chart.update(state="none",confirmed_entry=None,stop=None,targets=[]);result["trade_chart"]=chart
        return result
    return result
