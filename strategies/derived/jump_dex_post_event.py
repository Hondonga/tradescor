"""Jump/DEX post-event structure; measurable completed-candle paper analysis only."""
from __future__ import annotations
import hashlib,json
import pandas as pd
from strategies.derived.base_derived_strategy import load_strategy_thresholds
from analysis.derived_event_classifier import classify_derived_event
from analysis.derived_event_identity import active_event,lock_event,event_identity
from analysis.derived_post_event_volatility import recalibrate_post_event_volatility
from analysis.derived_post_event_structure import analyze_post_event_structure
from analysis.derived_event_hold_classifier import classify_event_hold
from analysis.derived_event_cooldown import evaluate_event_cooldown
from analysis.derived_post_event_zone_engine import build_post_event_zone,narrow_post_event_execution_zone
from analysis.derived_post_event_confirmation import post_event_zone_interaction,confirm_post_event,lock_post_event_entry
from analysis.derived_event_risk_classifier import classify_event_risk
from analysis.derived_post_event_target_engine import build_post_event_targets
from analysis.derived_event_decision_normalizer import normalize_event_decision
from analysis.derived_structural_stop import build_structural_stop
from analysis.derived_trade_plan_validator import validate_reward_risk,validate_chase
from analysis.derived_setup_lifecycle import advance_setup,archived_setups,cancel_active_setups_for_new_event

def evaluate_jump_dex_post_event(*,symbol,family,profile,candles_by_timeframe,current_price,tick_size=.01,data_quality=None,analysis_time=None):
    cfg=load_strategy_thresholds().get("jump_dex_post_event",{});name=family.get("family","");m15=_completed(candles_by_timeframe.get("M15"));m5=_completed(candles_by_timeframe.get("M5"));reasons=[]
    configured=bool(family.get("event_driven") and family.get("expected_event_direction")=="both");
    if name not in {"JUMP","DEX"} and not (name=="OTHER_DERIVED" and configured):reasons.append("Family is not configured for bidirectional event analysis.")
    if float(family.get("classification_confidence",0))<.8:reasons.append("Family classification confidence is insufficient.")
    if profile.get("profile_quality") not in {"good","partial"}:reasons.append("Completed-candle market profile is insufficient.")
    if data_quality and (not data_quality.get("analysis_allowed",True) or data_quality.get("status") not in {"good"}):reasons.append("Synchronized current M15 and M5 data is unavailable.")
    classified=classify_derived_event(m5,profile,cfg);old=active_event(symbol);new_id=event_identity(symbol,name,classified) if classified.get("qualified") else None;cancellation=None
    if new_id and old and old["event_id"]!=new_id:
        cancelled=cancel_active_setups_for_new_event(symbol,new_id,str(analysis_time or classified["completed_at"]));cancellation={"cancelled_setup_id":cancelled[-1]["setup_id"] if cancelled else None,"cancelled_by_event_id":new_id,"cancelled_at":str(analysis_time or classified["completed_at"]),"terminal_reason":"NEW_EVENT_CANCELLED"}
    event=lock_event(symbol,name,classified) if classified.get("qualified") else old;eligible=not reasons;vol=recalibrate_post_event_volatility(m5,event,cfg) if event else None;structure=analyze_post_event_structure(m15,event) if event else analyze_post_event_structure(m15,None);hold=classify_event_hold(m15,event,profile.get("atr"),cfg) if event else None;cooldown=evaluate_event_cooldown(m5,event,vol or {},structure,cfg) if event else None
    scenarios=_scenarios(event,cooldown,structure,hold);selected=next((row for row in scenarios.values() if row["eligible"]),None);direction=selected.get("direction") if selected else None;risk=classify_event_risk(event["direction"],direction,cfg) if direction else None;zone=build_post_event_zone(m15,direction,event,structure,profile.get("atr"),current_price,cfg) if selected else None;execution=narrow_post_event_execution_zone(zone,profile.get("atr")) if zone else None;setup_id=_setup_id(symbol,event,selected,zone) if execution else None
    if selected:selected["setup_id"]=setup_id;selected["event_relationship"]=risk["relationship"] if risk else ""
    interaction=post_event_zone_interaction(m5,execution,event["completed_at"]) if setup_id else None;confirmation=confirm_post_event(m5,direction,execution,setup_id,event["event_id"],interaction,cooldown) if setup_id else None;entry_price=_confirmation_close(m5,confirmation);entry=lock_post_event_entry(confirmation,setup_id,event["event_id"],entry_price) if confirmation else None;atr=float(profile.get("atr") or 0);stop_cfg={"stop_buffer_atr":(cfg.get("stop") or {}).get("buffer_atr",.12),"maximum_stop_atr":3}
    stop=build_structural_stop(direction=direction,entry=entry.get("price") if entry else None,execution_zone=execution,reaction_extreme=None,atr=atr,tick_size=tick_size,config=stop_cfg) if entry else None
    if stop:stop.update(event_adjusted=True,structural_level=execution.get("low" if direction=="buy" else "high"))
    targets=build_post_event_targets(candles_by_timeframe=candles_by_timeframe,direction=direction,entry=entry["price"],stop=stop["price"],event=event,atr=atr,minimum_rr=risk["minimum_required_rr"],current_price=current_price) if entry and stop and stop.get("valid") else None;rr=validate_reward_risk(direction=direction,entry=entry["price"],stop=stop["price"],tp1=targets.get("tp1"),tp2=targets.get("tp2"),minimum_rr=risk["minimum_required_rr"]) if targets else None;chase=validate_chase(direction=direction,current_price=current_price,entry=entry["price"],execution_zone=execution,tp1=targets.get("tp1"),stop=stop["price"],atr=atr,maximum_chase_atr=risk["maximum_chase_atr"]) if rr and rr.get("valid") else None;ready=all((eligible,selected,confirmation and confirmation.get("valid"),entry and entry.get("valid"),stop and stop.get("valid"),targets and targets.get("valid"),rr and rr.get("valid"),chase and chase.get("valid")))
    decision=normalize_event_decision(eligible=eligible,event=event,cooldown=cooldown,volatility=vol,structure=structure,selected=selected,confirmation=confirmation,ready=ready,chase=chase);now=str(analysis_time or (_time(m5.iloc[-1]) if len(m5) else ""));lifecycle=None
    if setup_id:lifecycle=advance_setup(symbol=symbol,direction=direction,zone=zone,state="ENTRY_AVAILABLE" if ready else "TOO_LATE" if decision["status"]=="TOO LATE" else "CONFIRMED" if confirmation and confirmation.get("valid") else "IN_ZONE" if interaction else "WAITING_FOR_PULLBACK",at=now,setup_id=setup_id,strategy="jump_dex_post_event",family=name);lifecycle["event_id"]=event["event_id"]
    plan={"direction":direction,"entry":entry["price"],"stop":stop["price"],"tp1":targets["tp1"],"tp2":targets.get("tp2"),"tp1_rr":rr["tp1_rr"],"tp2_rr":rr.get("tp2_rr"),"timing_state":chase["state"],"event_id":event["event_id"]} if ready else None
    return {"strategy":{"name":"Jump/DEX Post-Event Structure","eligible":eligible,"eligibility_reason":"Eligible bidirectional event family and synchronized data." if eligible else " ".join(reasons)},"decision":decision,"event":event,"event_classification":classified,"cooldown":cooldown,"post_event_volatility":vol,"post_event_structure":structure,"event_hold":hold,"scenarios":scenarios,"m15_setup_zone":zone,"m5_execution_zone":execution,"confirmation":confirmation,"confirmed_entry":entry,"structural_stop":stop,"targets":targets,"reward_risk":rr,"chase":chase,"active_trade_plan":plan,"new_event_cancellation":cancellation,"rejected_candidates":reasons+[reason for row in scenarios.values() for reason in row["reasons"]],"previous_setup":archived_setups()[-1] if archived_setups() else None,"warnings":risk.get("warnings",[]) if risk else [],"selected_candidate":selected,"lifecycle":lifecycle}

def _scenarios(event,cooldown,structure,hold):
    specs=[("up_event_bullish_continuation","up","buy","bullish",{"HOLDING_ABOVE_EVENT_ORIGIN","PARTIAL_RETRACE"}),("up_event_bearish_rejection","up","sell","bearish",{"EVENT_REJECTED","FULL_RETRACE","ORIGIN_RECLAIMED"}),("down_event_bearish_continuation","down","sell","bearish",{"HOLDING_BELOW_EVENT_ORIGIN","PARTIAL_RETRACE"}),("down_event_bullish_recovery","down","buy","bullish",{"EVENT_REJECTED","FULL_RETRACE","ORIGIN_RECLAIMED"})];rows={}
    for scenario,event_dir,direction,structure_dir,holds in specs:
        valid=bool(event and event["direction"]==event_dir and cooldown and cooldown.get("release_allowed") and structure.get("direction")==structure_dir and hold.get("classification") in holds);rows[scenario]={"scenario":scenario,"direction":direction,"eligible":valid,"reasons":[] if valid else ["Scenario requires matching event, cooldown release, fresh structure, and measured hold/rejection."]}
    return rows
def _setup_id(symbol,event,selected,zone):return "jde-"+hashlib.sha256(json.dumps([symbol,event["event_id"],selected["scenario"],selected["direction"],zone.get("low"),zone.get("high")],default=str).encode()).hexdigest()[:20]
def _completed(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame();return rows[rows.complete.astype(bool)] if "complete" in rows else rows
def _confirmation_close(rows,confirmation):
    if not confirmation or not confirmation.get("valid"):return None
    matched=rows[rows.time==pd.Timestamp(confirmation["candle_time"])] if "time" in rows else rows.iloc[0:0];return float(matched.iloc[-1].close) if len(matched) else None
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
