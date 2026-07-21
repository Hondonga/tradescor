"""Regime-aware delegation to existing Derived strategies; paper analysis only."""
from analysis.derived_switch_context import build_switch_context
from analysis.derived_regime_stability import evaluate_regime_stability
from analysis.derived_regime_hysteresis import apply_regime_hysteresis
from analysis.derived_switch_transition import manage_switch_transition
from analysis.derived_switch_strategy_router import route_switch_strategy
from analysis.derived_switch_risk_adjuster import switch_risk_adjustments
from analysis.derived_switch_decision_normalizer import normalize_switch_decision
from analysis.derived_range_lock import active_range
from analysis.derived_context import build_top_down_context
from analysis.derived_setup_lifecycle import archived_setups
from strategies.derived.base_derived_strategy import load_strategy_thresholds
from strategies.derived.derived_range_reaction import evaluate_derived_range_reaction
from strategies.derived.range_break_retest import evaluate_derived_range_break_retest
from strategies.derived.volatility_structure_pullback import evaluate_volatility_structure_pullback

def evaluate_derived_switch(*,symbol,family,regime,profile,volatility,candles_by_timeframe,current_price,tick_size=.01,data_quality=None,analysis_time=None,config=None):
    cfg=config or load_strategy_thresholds().get("derived_switch_orchestrator",{}); completed=_last_completed(candles_by_timeframe.get("M15")); previous=(cfg.get("previous_regime") or "")
    built=build_switch_context(family=family,profile=profile,regime=regime,data_quality=data_quality,last_completed_at=completed,previous_regime=previous); context=built["context"]; eligibility=built["eligibility"]
    stability=evaluate_regime_stability(symbol,context["candidate_regime"],context["regime_confidence"],completed,int((cfg.get("stability") or {}).get("minimum_confirmed_candles",3)))
    decisive=bool(regime.get("structure",{}).get("bullish_break") or regime.get("structure",{}).get("bearish_break")); hysteresis=apply_regime_hysteresis(symbol,context["candidate_regime"],context["regime_confidence"],stability["completed_candles_in_candidate"],cfg.get("hysteresis"),decisive)
    stability={**stability,**hysteresis,"stable":bool(stability["stable"] and not hysteresis["change_pending"])}; context["previous_regime"]=previous or hysteresis.get("previous_confirmed_regime") or hysteresis["confirmed_regime"]; context["stable_completed_candles"]=stability["completed_candles_in_candidate"]
    transition=manage_switch_transition(symbol=symbol,from_regime=context["previous_regime"],to_candidate_regime=context["candidate_regime"],started_at=completed,change_pending=hysteresis["change_pending"],change_confirmed=hysteresis["change_confirmed"])
    routing=route_switch_strategy(context["family"],hysteresis["confirmed_regime"] or context["current_regime"],has_locked_range=bool(active_range(symbol)),directional_structure=context["structure_direction"],stable=stability["stable"],transition_active=context["transition_active"] or hysteresis["change_pending"])
    risk=switch_risk_adjustments(context["current_regime"]); delegated=None
    if eligibility["eligible"] and routing["delegated_strategy"] and stability["stable"] and not context["transition_active"] and not hysteresis["change_pending"]:
        adapted_family={**family,"family":"VOLATILITY"}; adapted_regime={**regime,"regime":_delegate_regime(routing["delegated_strategy"],context),"direction":context["structure_direction"]}
        common=dict(symbol=symbol,family=adapted_family,regime=adapted_regime,profile=profile,candles_by_timeframe=candles_by_timeframe,current_price=current_price,tick_size=tick_size,data_quality=data_quality,analysis_time=analysis_time)
        if routing["delegated_strategy"]=="derived_range_reaction": delegated=evaluate_derived_range_reaction(**common,volatility=volatility,risk_adjustments=risk)
        elif routing["delegated_strategy"]=="derived_range_break_retest": delegated=evaluate_derived_range_break_retest(**common,risk_adjustments=risk)
        else: delegated=evaluate_volatility_structure_pullback(**common,top_down=build_top_down_context(candles_by_timeframe,"VOLATILITY",tick_size),risk_adjustments=risk)
        selected=(delegated.get("decision") or {}).get("developing_direction"); allowed=routing["allowed_directions"]
        if selected and selected not in allowed: delegated=None; routing["selection_reason"]="Delegated candidate contradicts the confirmed drift direction."; routing["delegated_strategy"]=None
    result=normalize_switch_decision(eligibility=eligibility,context=context,stability=stability,transition=transition,routing=routing,risk_adjustments=risk,delegated_result=delegated); result["previous_setup"]=archived_setups()[-1] if archived_setups() else None; return result

def _delegate_regime(strategy,context):
    if strategy=="derived_range_reaction": return "RANGE" if context["family"]=="VOLATILITY_SWITCH" else "DRIFT_SIDEWAYS"
    if strategy=="derived_range_break_retest": return "COMPRESSION" if context["current_regime"]=="COMPRESSION" else "BREAKOUT_ATTEMPT"
    return "TREND_BULLISH" if context["structure_direction"]=="bullish" else "TREND_BEARISH"
def _last_completed(rows):
    if rows is None or rows.empty:return None
    done=rows[rows.complete.astype(bool)] if "complete" in rows else rows
    if done.empty:return None
    value=done.iloc[-1].time;return value.isoformat() if hasattr(value,"isoformat") else str(value)
