"""Chronological, no-lookahead strategy setup-proof harness."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from analysis.smc.smc_invariants import validate_trade_ready_invariants
from validation.strategy_reachability_registry import strategy_reachability_registry


ZERO_SETUP_CLASSES={
    "UNREACHABLE_CODE_PATH","SOURCE_BEHAVIOR_ABSENT","DIRECTIONAL_CONTEXT_ABSENT",
    "LOCATION_NEVER_REACHED","CONFIRMATION_NEVER_REACHED","TARGET_CREATION_FAILURE",
    "RISK_VALIDATION_DOMINANT","INSUFFICIENT_HISTORY",
}


@dataclass(frozen=True)
class ChronologicalFixture:
    fixture_id:str
    strategy_id:str
    direction:str
    symbol:str
    family:dict
    candles_by_timeframe:dict[str,pd.DataFrame]
    decision_times:tuple
    outcome_candles:pd.DataFrame|None=None


def completed_slice(rows,decision_time):
    source=rows.copy() if rows is not None else pd.DataFrame()
    if "complete" in source:source=source[source.complete.astype(bool)]
    if "time" in source:source=source[pd.to_datetime(source.time,utc=True)<=pd.Timestamp(decision_time)]
    return source.sort_values("time").reset_index(drop=True) if "time" in source else source.reset_index(drop=True)


def run_strategy_fixture(fixture:ChronologicalFixture,evaluator:Callable,*,paper_service=None):
    registry=strategy_reachability_registry();spec=registry[fixture.strategy_id]
    if fixture.fixture_id not in spec["fixture_ids"]:raise ValueError("Fixture is not registered for this strategy.")
    transitions=[];ready_contract=None;seen_times=[]
    for decision_time in sorted(pd.Timestamp(x) for x in fixture.decision_times):
        frames={key:completed_slice(rows,decision_time) for key,rows in fixture.candles_by_timeframe.items()}
        for rows in frames.values():
            if len(rows) and "time" in rows:
                latest=pd.Timestamp(rows.iloc[-1].time);assert latest<=decision_time,"Future candle access detected."
        contract=evaluator(symbol=fixture.symbol,family=fixture.family,candles_by_timeframe=frames,analysis_time=decision_time)
        contract=_product_contract(contract);setup=contract.get("setup") or {};decision=contract.get("decision") or {};diagnostics=contract.get("diagnostics") or {};stage=setup.get("stage") or setup.get("state") or decision.get("stage") or "NO_CONTEXT";asserted=bool(setup.get("trade_ready") or decision.get("trade_ready") or str(stage).upper()=="TRADE_READY");observed=_observed_strategy(contract,fixture.family.get("family"))
        invariants=validate_trade_ready_invariants(_invariant_contract(contract))
        entities=_entities(contract)
        target_trace=diagnostics.get("target_trace") or setup.get("target_trace") or {};entry_trace=diagnostics.get("entry_trace") or setup.get("entry_trace") or {};stop_trace=diagnostics.get("stop_trace") or setup.get("stop_trace") or {}
        transition={"decision_time":decision_time.isoformat(),"stage":stage,"lifecycle_reached":list(diagnostics.get("lifecycle_reached") or []),"first_blocker":decision.get("first_blocking_code") or decision.get("first_blocking_gate") or setup.get("first_blocking_gate") or _first_blocker(diagnostics),"entities_available":entities,"entry":setup.get("entry"),"stop":setup.get("stop"),"target":((setup.get("targets") or [{}])[0]).get("price"),"rr":setup.get("rr"),"entry_trace":entry_trace,"stop_trace":stop_trace,"target_trace":target_trace,"geometry_funnel":target_trace.get("counts") or {},"asserted_trade_ready":asserted,"invariants_valid":invariants["valid"],"invariant_violations":invariants["violations"],"observed_strategy_id":observed,"strategy_identity_matches":observed==fixture.strategy_id}
        transitions.append(transition);seen_times.append(decision_time)
        if asserted and invariants["valid"] and observed==fixture.strategy_id:ready_contract=contract
    paper_registered=False;entry_filled=False;outcome_resolved=False;paper_result=None
    if ready_contract is not None and paper_service is not None:
        paper_result=paper_service(fixture,ready_contract)
        paper_registered=bool(paper_result.get("paper_registered"));entry_filled=bool(paper_result.get("entry_filled"));outcome_resolved=bool(paper_result.get("outcome_resolved"))
    reached={row["stage"] for row in transitions};reached.update(stage for row in transitions for stage in row.get("lifecycle_reached",[]));missing=[stage for stage in spec["required_stages"] if stage not in reached];proved=ready_contract is not None and not missing
    return {"strategy_id":fixture.strategy_id,"direction":fixture.direction,"fixture_id":fixture.fixture_id,"transitions":transitions,"trade_ready_reached":proved,"paper_registered":paper_registered if proved else False,"entry_filled":entry_filled if proved else False,"outcome_resolved":outcome_resolved if proved else False,"paper_result":paper_result,"required_stages_missing":missing,"future_candle_access":False,"classification":_fixture_classification(transitions,ready_contract if proved else None),"production_pipeline":getattr(evaluator,"production_pipeline",False)}


def build_strategy_reachability_report(results):
    registry=strategy_reachability_registry();grouped={key:[] for key in registry}
    for result in results:grouped.setdefault(result["strategy_id"],[]).append(result)
    rows=[]
    for strategy_id,spec in registry.items():
        fixtures=grouped.get(strategy_id,[]);directions=sorted({x["direction"] for x in fixtures if x["trade_ready_reached"]});ready=sum(x["trade_ready_reached"] for x in fixtures);registered=sum(x["paper_registered"] for x in fixtures);filled=sum(x.get("entry_filled",False) for x in fixtures);resolved=sum(x["outcome_resolved"] for x in fixtures)
        if not spec["production_supported"]:status="NOT_PRODUCTION_SUPPORTED"
        elif set(directions)>=set(spec["supported_directions"]) and ready and registered==ready and filled==ready and resolved==ready:status="REACHABLE"
        elif ready:status="PARTIALLY_REACHABLE"
        else:status="UNREACHABLE"
        failed=next((x["classification"] for x in fixtures if not x["trade_ready_reached"]),None)
        rows.append({"strategy_id":strategy_id,"family":spec["family"],"directions_required":spec["supported_directions"],"directions_reached":directions,"fixtures_run":len(fixtures),"trade_ready_count":ready,"paper_registered_count":registered,"entry_filled_count":filled,"resolved_count":resolved,"failed_stage":failed,"reachable":status=="REACHABLE","status":status,"production_supported":bool(spec["production_supported"]),"fixture_buy_reachable":"buy" in directions,"fixture_sell_reachable":"sell" in directions,"historically_observed":False,"live_observed":False,"auto_eligible":bool(spec["production_supported"] and status=="REACHABLE")})
    return {"strategies":rows}


def validate_registry_fixture_coverage(fixtures):
    ids={x.fixture_id for x in fixtures};missing={key:[name for name in spec["fixture_ids"] if name not in ids] for key,spec in strategy_reachability_registry().items() if spec["production_supported"]};return {key:value for key,value in missing.items() if value}


def classify_historical_funnel(row):
    if not row.get("evaluations"):return "INSUFFICIENT_HISTORY"
    if not row.get("code_path_entered",True):return "UNREACHABLE_CODE_PATH"
    if not row.get("sweeps_or_events"):return "SOURCE_BEHAVIOR_ABSENT"
    if not row.get("directional_contexts"):return "DIRECTIONAL_CONTEXT_ABSENT"
    if not row.get("valid_locations"):return "LOCATION_NEVER_REACHED"
    if not row.get("structure_confirmations"):return "CONFIRMATION_NEVER_REACHED"
    if not row.get("target_candidates"):return "TARGET_CREATION_FAILURE"
    if not row.get("rr_passes"):return "RISK_VALIDATION_DOMINANT"
    return None


def _product_contract(value):return value.get("product_contract") or value.get("decision_contract") or value
def _invariant_contract(contract):
    setup=dict(contract.get("setup") or {});decision=contract.get("decision") or {};ownership=contract.get("ownership") or {}
    if "stage" in setup and "state" not in setup:setup["state"]=setup["stage"]
    if setup.get("trade_ready") and setup.get("state")!="TRADE_READY":setup["state"]="TRADE_READY"
    return {**contract,"setup":setup,"decision":decision,"ownership":ownership}
def _entities(contract):
    setup=contract.get("setup") or {};smc=contract.get("smc") or {};ownership=contract.get("ownership") or {};values={"setup_id":setup.get("setup_id"),"direction":setup.get("direction"),"completed_confirmation":setup.get("completed_confirmation") or setup.get("mss") or setup.get("bos"),"entry":setup.get("entry"),"stop":setup.get("stop"),"tp1":(setup.get("targets") or [None])[0],"reward_to_risk":setup.get("rr"),"decision_owner":ownership.get("decision_owner_id"),"overlay_owner":ownership.get("overlay_owner_id"),"sweep":setup.get("sweep") or (smc.get("sweeps") or [None])[0],"bos":setup.get("bos") or (smc.get("structure_events") or [None])[0],"mss":setup.get("mss"),"dealing_range":smc.get("dealing_range"),"fvg":(smc.get("fvgs") or [None])[0],"order_block":(smc.get("order_blocks") or [None])[0]};return sorted(key for key,value in values.items() if value is not None and value!="" and value is not False)
def _first_blocker(diagnostics):return ((diagnostics.get("gate_funnel") or {}).get("first_blocking_gate") or (diagnostics.get("target_trace") or {}).get("first_blocker"))
def _fixture_classification(transitions,ready):
    if ready:return "REACHABLE"
    if not transitions:return "INSUFFICIENT_HISTORY"
    blockers=" ".join(str(x.get("first_blocker") or "").upper() for x in transitions)
    if "HISTORY" in blockers or "INSUFFICIENT" in blockers:return "INSUFFICIENT_HISTORY"
    if "TARGET" in blockers:return "TARGET_CREATION_FAILURE"
    if "REWARD" in blockers or "RISK" in blockers or "RR" in blockers:return "RISK_VALIDATION_DOMINANT"
    if transitions and not any(x.get("strategy_identity_matches") for x in transitions):return "UNREACHABLE_CODE_PATH"
    entities=set().union(*(set(x["entities_available"]) for x in transitions))
    if "direction" not in entities:return "DIRECTIONAL_CONTEXT_ABSENT"
    if not ({"sweep","bos","mss"}&entities):return "SOURCE_BEHAVIOR_ABSENT"
    if "entry" not in entities:return "LOCATION_NEVER_REACHED"
    if "completed_confirmation" not in entities:return "CONFIRMATION_NEVER_REACHED"
    if "tp1" not in entities:return "TARGET_CREATION_FAILURE"
    return "RISK_VALIDATION_DOMINANT"


def _observed_strategy(contract,family):
    setup=contract.get("setup") or {};ownership=contract.get("ownership") or {};raw=str(setup.get("setup_type") or "").lower();family=str(family or "").upper()
    if family=="VOLATILITY":return {"structure_pullback":"volatility_structure_pullback","liquidity_reversal":"volatility_liquidity_reversal","range_reaction":"volatility_range_reaction","breakout_and_retest":"volatility_breakout_and_retest"}.get(raw,ownership.get("selected_model_id") or "")
    if family.startswith("STEP") or family=="STEP":return {"structure_pullback":"step_structure_pullback","range_reaction":"step_range_reaction","range_boundary_reaction":"step_range_reaction","breakout_and_retest":"step_breakout_and_retest"}.get(raw,ownership.get("selected_model_id") or "")
    if family=="JUMP":return {"jump_post_event_continuation":"jump_post_event_continuation","jump_post_event_reversal":"jump_post_event_reversal"}.get(raw,raw)
    if family in {"BOOM","CRASH","BOOM_CRASH"}:return "boom_crash_spike_state"
    return ownership.get("selected_model_id") or raw
