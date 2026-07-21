"""Family eligibility + regime suitability router for Derived Indices."""
from __future__ import annotations
from analysis.derived_candidate_ranker import rank_derived_candidates
from strategies.derived.volatility_structure_pullback import evaluate_structure_pullback
from strategies.derived.volatility_breakout_retest import evaluate_breakout_retest
from strategies.derived.boom_crash_spike_state import evaluate_spike_state
from strategies.derived.range_break_retest import evaluate_range_break
from strategies.derived.regime_switch_strategy import evaluate_regime_switch
from strategies.derived.post_event_structure import evaluate_post_event
from strategies.derived.step_structure import evaluate_step
from strategies.derived.derived_range_reaction import evaluate_range_reaction

def route_derived_strategies(*,family,candles,profile,regime,spike,zone=None,current_price=None,price_location="mid_range",historical_evidence=None,data_quality=None):
    name=family.get("family","OTHER_DERIVED");results=[];rejected=[]
    if data_quality and not data_quality.get("analysis_allowed",True):return _result([],[],"Data quality blocks analysis.")
    if name=="RANGE_BREAK":results=[evaluate_range_break(candles=candles,profile=profile)]
    elif name in {"BOOM","CRASH"}:results=[evaluate_spike_state(family=name,spike=spike,regime=regime)]
    elif name in {"JUMP","DEX"}:results=[evaluate_post_event(spike=spike,regime=regime)]
    elif name in {"VOLATILITY_SWITCH","DRIFT_SWITCH"}:results=[evaluate_regime_switch(profile=profile,regime=regime)]
    elif name=="STEP":results=[evaluate_step(regime=regime,price_location=price_location)]
    else:
        if regime.get("regime") in {"TREND_BULLISH","TREND_BEARISH","PULLBACK_BULLISH","PULLBACK_BEARISH"}:results=[evaluate_structure_pullback(regime=regime,zone=zone,current_price=current_price,profile=profile)]
        elif regime.get("regime")=="COMPRESSION":results=[evaluate_breakout_retest(candles=candles,profile=profile,locked_range=_range(candles))]
        elif regime.get("regime")=="RANGE":results=[evaluate_range_reaction(profile=profile,price_location=price_location)]
    candidates=[]
    for result in results:candidates.extend([result.get("bullish_candidate"),result.get("bearish_candidate")])
    candidates=[row for row in candidates if row]
    for row in candidates:
        if not row.get("eligible"):rejected.append({"strategy":row.get("strategy"),"direction":row.get("direction"),"reason":"; ".join(row.get("reasons") or ["Current regime requirements are incomplete."])})
    ranked=rank_derived_candidates(candidates,historical_evidence);selected=ranked[0] if ranked else None
    return {"requested_strategy":"Auto","eligible_strategies":sorted(set(row["strategy"] for row in ranked)),"rejected_strategies":rejected,"selected_strategy":selected.get("strategy") if selected else None,"selection_reason":f"{selected['strategy']} has the strongest currently eligible {selected['direction']} candidate." if selected else "No strategy is currently suitable.","selection_confidence":min(.95,float(selected.get("quality",0))/100) if selected else 0.0,"bullish_candidate":max((row for row in candidates if row.get("direction")=="buy"),key=lambda row:row.get("quality",0),default={}),"bearish_candidate":max((row for row in candidates if row.get("direction")=="sell"),key=lambda row:row.get("quality",0),default={}),"selected_candidate":selected,"strategy_results":results}

def _range(candles):
    rows=candles.iloc[-21:-1] if len(candles)>20 else candles.iloc[:-1];return {"low":float(rows.low.min()),"high":float(rows.high.max())} if len(rows) else {"low":None,"high":None}
def _result(candidates,rejected,reason):return {"requested_strategy":"Auto","eligible_strategies":[],"rejected_strategies":rejected,"selected_strategy":None,"selection_reason":reason,"selection_confidence":0.0,"bullish_candidate":{},"bearish_candidate":{},"selected_candidate":None,"strategy_results":[]}
