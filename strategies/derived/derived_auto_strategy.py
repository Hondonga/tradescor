"""Authoritative Derived Auto evaluator; delegates all price logic."""
from strategies.derived.boom_crash_spike_state import evaluate_boom_crash_spike_state
from strategies.derived.derived_range_reaction import evaluate_derived_range_reaction
from strategies.derived.range_break_retest import evaluate_derived_range_break_retest
from strategies.derived.volatility_structure_pullback import evaluate_volatility_structure_pullback
from strategies.derived.derived_switch_orchestrator import evaluate_derived_switch
from strategies.derived.jump_dex_post_event import evaluate_jump_dex_post_event
from strategies.derived.step_structure_research import evaluate_step_structure_research
from analysis.derived_strategy_registry import derived_strategy_registry
from analysis.derived_strategy_eligibility import derived_data_quality_gate,eligible_registry_entries
from analysis.derived_candidate_quality import measure_candidate_quality
from analysis.derived_candidate_comparator import compare_derived_candidates
from analysis.derived_auto_conflict_resolver import resolve_auto_conflict
from analysis.derived_historical_evidence import normalize_historical_evidence
from analysis.derived_evidence_weighting import weight_current_and_historical
from analysis.derived_auto_router import apply_auto_continuity
from analysis.derived_auto_decision_normalizer import normalize_derived_auto
from analysis.derived_context import build_top_down_context
from analysis.derived_setup_lifecycle import cancel_active_strategy_for_auto_replacement
from analysis.derived_strategy_gate_funnel import build_strategy_gate_funnel

def evaluate_derived_auto(*,symbol,family,regime,profile,volatility,spike,candles_by_timeframe,current_price,tick_size=.01,data_quality=None,analysis_time=None,historical_evidence=None,market_context=None,config=None):
    cfg=config or {};data_gate=derived_data_quality_gate(family,profile,data_quality or {},candles_by_timeframe);eligibility=eligible_registry_entries(family,regime,data_gate["passed"]);registry=derived_strategy_registry();results={};candidates=[];history_cfg=(cfg.get("historical_evidence") or {})
    if data_gate["passed"]:
        for entry in eligibility["eligible"]:
            strategy_id=entry["strategy_id"];result=_evaluate(strategy_id,symbol,family,regime,profile,volatility,spike,candles_by_timeframe,current_price,tick_size,data_quality,analysis_time);result["gate_funnel"]=build_strategy_gate_funnel(strategy_id,result,family=family,regime=regime,data_quality=data_quality,frames=candles_by_timeframe,current_price=current_price);results[strategy_id]=result;evidence=normalize_historical_evidence(strategy_id,symbol,family["family"],regime["regime"],(historical_evidence or {}).get(strategy_id,[]),history_cfg);quality=measure_candidate_quality(strategy_id,result,regime.get("confidence",0),data_gate["status"],entry["research_only"]);quality["gate_funnel"]=result["gate_funnel"];quality["quality_score"]=weight_current_and_historical(quality["quality_score"],evidence,entry["research_only"]);quality["historical_evidence"]=evidence;candidates.append(quality)
    compared=compare_derived_candidates(candidates,registry,float((cfg.get("candidate_quality") or {}).get("minimum_developing_score",.45)));resolved=resolve_auto_conflict(compared["selected_candidate"],compared["runner_up"],regime.get("regime"));selection={**compared,**resolved};proposed=(selection.get("selected_candidate") or {}).get("strategy_id");setup_id=(selection.get("selected_candidate") or {}).get("setup_id")
    continuity=apply_auto_continuity(symbol,proposed,regime.get("regime"),setup_id,float((cfg.get("selection") or {}).get("minimum_score_difference_to_replace",.08)),float((selection.get("selected_candidate") or {}).get("quality_score",0)))
    if continuity["selection_changed"] and continuity["previous_selected_strategy"]:cancel_active_strategy_for_auto_replacement(symbol,continuity["previous_selected_strategy"],str(analysis_time or regime.get("formed_at")),setup_id)
    if continuity["current_selected_strategy"]!=proposed:
        retained=next((row for row in candidates if row["strategy_id"]==continuity["current_selected_strategy"]),None);selection["selected_candidate"]=retained;proposed=continuity["current_selected_strategy"]
    selected_result=results.get(proposed);labels=[row["historical_evidence"]["evidence_label"] for row in candidates];historical_label="stronger" if "stronger" in labels else "moderate" if "moderate" in labels else "early" if "early" in labels else "insufficient"
    return normalize_derived_auto(family=family,regime=regime,data_gate=data_gate,eligibility=eligibility,candidates=candidates,selection=selection,selected_result=selected_result,historical_label=historical_label,continuity=continuity,market_context=market_context)

def _evaluate(strategy_id,symbol,family,regime,profile,volatility,spike,frames,current,tick_size,data_quality,analysis_time):
    common=dict(symbol=symbol,family=family,profile=profile,candles_by_timeframe=frames,current_price=current,tick_size=tick_size,data_quality=data_quality,analysis_time=analysis_time)
    if strategy_id=="volatility_structure_pullback":return evaluate_volatility_structure_pullback(**common,regime=regime,top_down=build_top_down_context(frames,family["family"],tick_size))
    if strategy_id=="derived_range_break_retest":return evaluate_derived_range_break_retest(**common,regime=regime)
    if strategy_id=="derived_range_reaction":return evaluate_derived_range_reaction(**common,regime=regime,volatility=volatility)
    if strategy_id=="boom_crash_spike_state":return evaluate_boom_crash_spike_state(**common,spike_detector=spike,volatility=volatility)
    if strategy_id=="derived_switch_orchestrator":return evaluate_derived_switch(**common,regime=regime,volatility=volatility)
    if strategy_id=="jump_dex_post_event":return evaluate_jump_dex_post_event(**common)
    if strategy_id=="step_structure_research":return evaluate_step_structure_research(**common)
    return {}
