"""Actionable, paper-analysis-only Volatility Structure Pullback strategy."""
from __future__ import annotations
import pandas as pd
from strategies.derived.base_derived_strategy import strategy_eligibility,load_strategy_thresholds,candidate,directional_result
from analysis.derived_pullback_zone_engine import detect_pullback,select_m15_pullback_zone
from analysis.derived_execution_confirmation import build_m5_execution_zone,confirm_m5_execution,lock_confirmed_entry
from analysis.derived_structural_stop import build_structural_stop
from analysis.derived_target_engine import structural_target_candidates,build_derived_targets
from analysis.derived_trade_plan_validator import validate_reward_risk,validate_chase,validate_range_position
from analysis.derived_setup_lifecycle import setup_identity,advance_setup,archived_setups
from analysis.derived_strategy_decision import normalize_strategy_decision

def evaluate_volatility_structure_pullback(*,symbol,family,regime,top_down,profile,candles_by_timeframe,current_price,tick_size=.01,data_quality=None,analysis_time=None,existing_entry=None,risk_adjustments=None):
    cfg=dict(load_strategy_thresholds()["volatility_structure_pullback"]);adjust=risk_adjustments or {};cfg["minimum_tp1_rr"]*=adjust.get("minimum_tp1_rr_multiplier",1);cfg["maximum_chase_atr"]*=adjust.get("maximum_chase_atr_multiplier",1);cfg["stop_buffer_atr"]*=adjust.get("stop_buffer_atr_multiplier",1);gate=strategy_eligibility(family=family,regime=regime,profile_quality=profile.get("profile_quality","insufficient"),data_quality=data_quality);direction_info=_higher_direction(top_down,regime);direction=direction_info["direction"] if gate["eligible"] else None;m15=candles_by_timeframe.get("M15",pd.DataFrame());m5=candles_by_timeframe.get("M5",pd.DataFrame());atr=float(profile.get("atr") or 0);now=str(analysis_time or (_time(m5.iloc[-1]) if len(m5) else ""))
    pullback=detect_pullback(m15,direction,atr,cfg) if direction else detect_pullback(m15,None,atr,cfg);zone=select_m15_pullback_zone(m15,direction,pullback,atr,current_price,cfg) if direction else None
    setup_id=setup_identity(symbol,direction,zone,regime.get("formed_at")) if zone and zone.get("valid") else None;zone_reached_at=_zone_reached_at(m5,zone);location=_location(current_price,zone,atr)
    execution_zone=build_m5_execution_zone(m5,direction,zone,zone_reached_at) if setup_id else None;confirmation=confirm_m5_execution(m5,direction,zone,execution_zone,setup_id,zone_reached_at) if execution_zone else None;confirmed_close=_confirmed_close(m5,confirmation);entry=lock_confirmed_entry(confirmation,setup_id,existing_entry,confirmed_close) if setup_id else None
    stop=build_structural_stop(direction=direction,entry=entry.get("price") if entry else None,execution_zone=execution_zone,reaction_extreme=None,atr=atr,tick_size=tick_size,config=cfg) if entry else None;raw_targets=structural_target_candidates(candles_by_timeframe,direction,entry["price"]) if entry and entry.get("valid") else [];targets=build_derived_targets(direction=direction,entry=entry["price"],stop=stop.get("price") if stop else None,candidates=raw_targets,current_price=current_price,minimum_rr=cfg["minimum_tp1_rr"],atr=atr) if entry and stop else None;rr=validate_reward_risk(direction=direction,entry=entry["price"],stop=stop.get("price"),tp1=targets.get("tp1"),tp2=targets.get("tp2"),minimum_rr=cfg["minimum_tp1_rr"]) if targets else None;chase=validate_chase(direction=direction,current_price=current_price,entry=entry["price"],execution_zone=execution_zone,tp1=targets.get("tp1"),stop=stop.get("price"),atr=atr,maximum_chase_atr=cfg["maximum_chase_atr"]) if rr and rr.get("valid") else None;range_position=validate_range_position(direction=direction,current_price=current_price,m15_candles=m15,maximum_hostile_position=cfg.get("maximum_range_position",.75)) if rr and rr.get("valid") else None
    decision=normalize_strategy_decision(eligible=gate["eligible"] and direction is not None,direction=direction,pullback=pullback,zone=zone,execution_zone=execution_zone,confirmation=confirmation,entry=entry,stop=stop,targets=targets,rr=rr,chase=chase,setup_id=setup_id,range_position=range_position)
    lifecycle=None
    if setup_id:
        lifecycle_state="ENTRY_AVAILABLE" if decision["trade_ready"] else "TOO_LATE" if decision["status"]=="TOO LATE" else "CONFIRMED" if confirmation and confirmation.get("valid") else "WAITING_FOR_CONFIRMATION" if execution_zone and execution_zone.get("valid") else "IN_ZONE" if zone_reached_at else "WAITING_FOR_PULLBACK";lifecycle=advance_setup(symbol=symbol,direction=direction,zone=zone,state=lifecycle_state,at=now,setup_id=setup_id)
    plan={"direction":direction,"entry":entry["price"],"stop":stop["price"],"tp1":targets["tp1"],"tp2":targets.get("tp2"),"tp1_rr":rr["tp1_rr"],"tp2_rr":rr.get("tp2_rr"),"timing_state":chase["state"]} if decision["trade_ready"] else None
    return {"strategy":{"name":"Volatility Structure Pullback","eligible":gate["eligible"],"eligibility_reason":gate["eligibility_reason"]},"decision":decision,"direction_context":direction_info,"pullback":pullback,"price_location":location,"m15_setup_zone":zone,"m5_execution_zone":execution_zone,"confirmation":confirmation,"confirmed_entry":entry,"structural_stop":stop,"targets":targets,"reward_risk":rr,"chase":chase,"range_position":range_position,"active_trade_plan":plan,"key_levels":{"support":zone.get("low") if zone and direction=="buy" else None,"resistance":zone.get("high") if zone and direction=="sell" else None,"liquidity_above":targets.get("tp1") if targets and direction=="buy" else None,"liquidity_below":targets.get("tp1") if targets and direction=="sell" else None},"rejected_candidates":gate["rejection_reasons"]+pullback.get("rejection_reasons",[])+(zone.get("rejection_reasons",[]) if zone else []),"previous_setup":archived_setups()[-1] if archived_setups() else None,"lifecycle":lifecycle,"warnings":[],"buy_candidate":{"eligible":direction=="buy","direction":"buy"},"sell_candidate":{"eligible":direction=="sell","direction":"sell"},"selected_candidate":{"direction":direction} if direction else None}

def evaluate_structure_pullback(*,regime,zone,current_price,profile):
    direction={"TREND_BULLISH":"buy","PULLBACK_IN_BULLISH_TREND":"buy","TREND_BEARISH":"sell","PULLBACK_IN_BEARISH_TREND":"sell"}.get(regime.get("regime"));inside=bool(zone and current_price is not None and zone.get("low")<=current_price<=zone.get("high"))
    def side(name):return candidate("volatility_structure_pullback",name,eligible=direction==name,state="IN_PULLBACK_ZONE" if direction==name and inside else "WAITING_FOR_PULLBACK" if direction==name else "NO_SETUP",zone=zone,quality=72 if inside else 60 if direction==name else 0,reasons=[] if direction==name else ["Directional structure is not aligned."])
    return directional_result("volatility_structure_pullback",side("buy"),side("sell"))

def _higher_direction(top_down,regime):
    h1=(top_down.get("h1") or {}).get("direction");h4=(top_down.get("h4") or {}).get("direction");local=regime.get("direction");evidence=[];contradictions=[]
    if h1 in {"bullish","bearish"} and h4 in {h1,"neutral"} and local in {h1,"neutral"}:direction="buy" if h1=="bullish" else "sell";relationship="aligned";evidence=["H1 direction is confirmed and H4 does not conflict."]
    else:direction=None;relationship="mixed";contradictions=["H1, H4, and M15 structure are not aligned."]
    return {"direction":direction,"relationship":relationship,"confidence":.85 if direction else .25,"evidence":evidence,"contradictions":contradictions}
def _zone_reached_at(rows,zone):
    if not zone or rows is None or rows.empty:return None
    completed=rows[rows.complete.astype(bool)] if "complete" in rows else rows;touch=completed[(completed.low<=zone["high"])&(completed.high>=zone["low"])]
    return touch.iloc[-1].time if len(touch) else None
def _location(price,zone,atr):
    if price is None or not zone:return "NO_SETUP"
    if zone["low"]<=price<=zone["high"]:return "IN_SETUP_ZONE"
    distance=min(abs(price-zone["low"]),abs(price-zone["high"]));return "APPROACHING_SETUP_ZONE" if atr and distance<=atr*.35 else "WAITING_FOR_PULLBACK"
def _confirmed_close(rows,confirmation):
    if not confirmation or not confirmation.get("valid"):return None
    matched=rows[rows.time==pd.Timestamp(confirmation["candle_time"])] if "time" in rows else rows.iloc[0:0];return float(matched.iloc[-1].close) if len(matched) else None
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
