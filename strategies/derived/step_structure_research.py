"""Step Index structure research orchestrator; paper-only, edge unvalidated."""
from __future__ import annotations
from strategies.derived.base_derived_strategy import load_strategy_thresholds
from strategies.derived.derived_range_reaction import evaluate_derived_range_reaction
from strategies.derived.range_break_retest import evaluate_derived_range_break_retest
from strategies.derived.volatility_structure_pullback import evaluate_volatility_structure_pullback
from analysis.step_market_profile import build_step_market_profile
from analysis.step_sequence_analyzer import analyze_step_sequence
from analysis.step_regime_classifier import classify_step_regime
from analysis.step_run_structure import analyze_step_run
from analysis.step_risk_adjuster import step_risk_adjustments
from analysis.step_decision_normalizer import normalize_step_decision
from analysis.derived_context import build_top_down_context
from analysis.derived_setup_lifecycle import archived_setups,cancel_active_setups_for_regime_change

_REGIMES={}

def evaluate_step_structure_research(*,symbol,family,profile,candles_by_timeframe,current_price,tick_size=None,data_quality=None,analysis_time=None):
    cfg=load_strategy_thresholds().get("step_structure_research",{});m15=candles_by_timeframe.get("M15");step_profile=build_step_market_profile(m15,tick_size);sequence=analyze_step_sequence(m15);regime=classify_step_regime(m15,step_profile,sequence);risk=step_risk_adjustments(cfg);reasons=[];previous_regime=_REGIMES.get(symbol)
    if previous_regime and previous_regime!=regime["regime"]:cancel_active_setups_for_regime_change(symbol,str(analysis_time or regime.get("formed_at")))
    _REGIMES[symbol]=regime["regime"]
    if family.get("family")!="STEP":reasons.append("Only the Step family is supported.")
    if float(family.get("classification_confidence",0))<.8:reasons.append("Family classification confidence is insufficient.")
    if tick_size is None or tick_size<=0:reasons.append("Valid symbol tick size is required.")
    minimum=int((cfg.get("profile") or {}).get("minimum_completed_candles",200))
    if step_profile["sample_size"]<minimum or step_profile["quality"]!="good":reasons.append("At least the configured completed-candle Step sample is required.")
    if data_quality and (not data_quality.get("analysis_allowed",True) or data_quality.get("status")!="good"):reasons.append("Synchronized current M15 and M5 data is required.")
    eligible=not reasons;selected=None;allowed=[];reason="";state=regime["regime"]
    if eligible and state=="STABLE_RANGE":selected="derived_range_reaction";allowed=["buy","sell"];reason="Stable Step range permits boundary reaction research."
    elif eligible and state in {"BULLISH_RUN","BULLISH_PULLBACK"}:selected="volatility_structure_pullback";allowed=["buy"];reason="Confirmed bullish Step structure permits buy pullback research."
    elif eligible and state in {"BEARISH_RUN","BEARISH_PULLBACK"}:selected="volatility_structure_pullback";allowed=["sell"];reason="Confirmed bearish Step structure permits sell pullback research."
    elif eligible and state in {"COMPRESSION","BREAKOUT_ATTEMPT","ACCEPTED_BREAKOUT"}:selected="derived_range_break_retest";allowed=["buy","sell"];reason="Step compression or accepted breakout permits retest research."
    else:reason="The current Step condition is not actionable."
    if sequence["extension_state"] in {"extended","extreme"} and selected=="volatility_structure_pullback":selected=None;reason="The current sequence is extended; do not chase it."
    routing={"eligible_sub_strategies":[selected] if selected else [],"delegated_sub_strategy":selected,"rejected_sub_strategies":[name for name in ("derived_range_reaction","volatility_structure_pullback","derived_range_break_retest") if name!=selected],"selection_reason":reason,"selection_confidence":min(regime.get("confidence",0),risk["confidence_ceiling"]),"allowed_directions":allowed};delegated=None
    adjustments={"minimum_tp1_rr_multiplier":risk["minimum_tp1_rr"]/1.5,"maximum_chase_atr_multiplier":risk["maximum_chase_atr"]/.35,"stop_buffer_atr_multiplier":risk["stop_buffer_multiplier"]}
    common=dict(symbol=symbol,family={**family,"family":"VOLATILITY"},regime={"regime":"RANGE" if selected=="derived_range_reaction" else "COMPRESSION" if selected=="derived_range_break_retest" else "TREND_BULLISH" if allowed==["buy"] else "TREND_BEARISH","direction":"bullish" if allowed==["buy"] else "bearish" if allowed==["sell"] else "neutral","formed_at":regime.get("formed_at")},profile=profile,candles_by_timeframe=candles_by_timeframe,current_price=current_price,tick_size=tick_size,data_quality=data_quality,analysis_time=analysis_time)
    if selected=="derived_range_reaction":delegated=evaluate_derived_range_reaction(**common,volatility={},risk_adjustments=adjustments)
    elif selected=="derived_range_break_retest":delegated=evaluate_derived_range_break_retest(**common,risk_adjustments=adjustments)
    elif selected=="volatility_structure_pullback":delegated=evaluate_volatility_structure_pullback(**common,top_down=build_top_down_context(candles_by_timeframe,"VOLATILITY",tick_size),risk_adjustments=adjustments)
    if delegated and (delegated.get("decision") or {}).get("developing_direction") not in allowed and (delegated.get("decision") or {}).get("developing_direction"):delegated=None;routing["delegated_sub_strategy"]=None;routing["selection_reason"]="Delegated direction contradicted the confirmed Step run."
    decision=normalize_step_decision(eligible=eligible,regime=regime,routing=routing,delegated=delegated,sequence=sequence,risk=risk);plan=(delegated or {}).get("active_trade_plan")
    if plan:plan={**plan,"paper_only":True,"research_mode":True}
    buy={"direction":"buy","eligible":bool(delegated and (delegated.get("buy_candidate") or delegated.get("bullish_candidate") or {}).get("eligible"))};sell={"direction":"sell","eligible":bool(delegated and (delegated.get("sell_candidate") or delegated.get("bearish_candidate") or {}).get("eligible"))}
    return {"strategy":{"name":"Step Index Structure Research","eligible":eligible,"eligibility_reason":"Eligible Step research context." if eligible else " ".join(reasons),"status":"research","validated_edge":False},"strategy_status":"research","validated_edge":False,"paper_analysis_only":True,"confidence_ceiling":risk["confidence_ceiling"],"step_profile":step_profile,"sequence":sequence,"regime":regime,"run_structure":analyze_step_run(m15,regime,step_profile,sequence,tick_size or 1),"routing":routing,"risk_adjustments":risk,"decision":decision,"m15_setup_zone":(delegated or {}).get("m15_setup_zone") or (delegated or {}).get("retest_zone"),"m5_execution_zone":(delegated or {}).get("m5_execution_zone") or (delegated or {}).get("retest_zone"),"confirmation":(delegated or {}).get("confirmation"),"active_trade_plan":plan,"delegated_result":delegated,"previous_setup":archived_setups()[-1] if archived_setups() else None,"warnings":[risk["research_warning"]],"rejected_candidates":reasons,"buy_candidate":buy,"sell_candidate":sell,"selected_candidate":buy if buy["eligible"] else sell if sell["eligible"] else None}
