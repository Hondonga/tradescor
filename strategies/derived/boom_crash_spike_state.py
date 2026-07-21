"""Boom/Crash post-spike structure strategy; paper analysis only."""
from __future__ import annotations
import hashlib,json
import pandas as pd
from strategies.derived.base_derived_strategy import load_strategy_thresholds,candidate,directional_result
from analysis.boom_crash_family_context import build_boom_crash_family_context
from analysis.derived_spike_identity import qualify_spike,lock_spike
from analysis.derived_post_spike_structure import analyze_post_spike_structure
from analysis.derived_spike_cooldown import evaluate_spike_cooldown
from analysis.derived_spike_hold_classifier import classify_spike_hold
from analysis.derived_spike_rejection_classifier import classify_spike_rejection
from analysis.derived_post_spike_zone_engine import build_post_spike_zone,narrow_post_spike_execution_zone
from analysis.derived_spike_risk_classifier import classify_spike_risk
from analysis.derived_post_spike_confirmation import post_spike_zone_interaction,confirm_post_spike,lock_post_spike_entry
from analysis.derived_structural_stop import build_structural_stop
from analysis.derived_spike_target_engine import build_spike_targets
from analysis.derived_trade_plan_validator import validate_reward_risk,validate_chase
from analysis.derived_setup_lifecycle import advance_setup,archived_setups

def evaluate_boom_crash_spike_state(*,symbol,family,spike_detector,volatility,profile,candles_by_timeframe,current_price,tick_size=.01,data_quality=None,analysis_time=None):
    cfg=load_strategy_thresholds().get("boom_crash_spike_state",{});name=family.get("family","OTHER_DERIVED");m15=_completed(candles_by_timeframe.get("M15"));m5=_completed(candles_by_timeframe.get("M5"));context=build_boom_crash_family_context(name,m15);qualification=qualify_spike(spike_detector,name);reasons=[]
    if name not in {"BOOM","CRASH"}:reasons.append("Only Boom and Crash families are supported.")
    if float(family.get("classification_confidence",family.get("confidence",0)))<.6:reasons.append("Family classification confidence is insufficient.")
    if profile.get("profile_quality") not in {"good","partial"}:reasons.append("Market profile is insufficient.")
    if data_quality and (not data_quality.get("analysis_allowed",True) or data_quality.get("status") not in {"good"}):reasons.append("Synchronized completed-candle data is unavailable.")
    eligible=not reasons;spike=lock_spike(symbol,name,spike_detector) if qualification["qualified"] else None;structure=analyze_post_spike_structure(m15,spike) if spike else analyze_post_spike_structure(m15,None);cooldown=evaluate_spike_cooldown(m5,spike,volatility,structure,cfg) if spike else None;hold=classify_spike_hold(m15,spike,profile.get("atr"),cfg) if spike else None;rejection=classify_spike_rejection(spike,hold,structure) if spike else None
    continuation_direction="buy" if spike and spike["direction"]=="up" else "sell" if spike else None;normalization_direction="sell" if continuation_direction=="buy" else "buy" if continuation_direction else None;continuation_valid=bool(spike and cooldown and cooldown["release_allowed"] and structure.get("direction")== _word(continuation_direction) and hold.get("classification") in {"HOLDING_ABOVE_ORIGIN","HOLDING_BELOW_ORIGIN","PARTIAL_RETRACE"});normalization_valid=bool(spike and cooldown and cooldown["release_allowed"] and rejection and rejection.get("rejected"));continuation={"scenario":"spike_continuation","direction":continuation_direction,"eligible":continuation_valid,"reasons":[] if continuation_valid else ["Continuation requires cooldown release, a maintained hold, and fresh aligned structure."]};normalization={"scenario":"normalization","direction":normalization_direction,"eligible":normalization_valid,"reasons":[] if normalization_valid else ["Normalization requires cooldown release, origin failure, and fresh opposite structure."]};selected=continuation if continuation_valid else normalization if normalization_valid else None
    direction=selected.get("direction") if selected else None;scenario=selected.get("scenario") if selected else "";risk=classify_spike_risk(name,direction,cfg) if direction else None;zone=build_post_spike_zone(m15,direction,spike,structure,profile.get("atr"),current_price,cfg,"M15") if selected else None;execution=narrow_post_spike_execution_zone(zone,profile.get("atr"));setup_id=_setup_id(symbol,spike,scenario,direction,zone) if execution else None;interaction=post_spike_zone_interaction(m5,execution,spike["completed_at"]) if setup_id else None;confirmation=confirm_post_spike(m5,direction,execution,setup_id,spike["spike_id"],interaction,cooldown) if setup_id else None;entry_price=_confirmation_close(m5,confirmation);entry=lock_post_spike_entry(confirmation,setup_id,spike["spike_id"],entry_price) if confirmation else None;atr=float(profile.get("atr") or 0)
    stop=build_structural_stop(direction=direction,entry=entry.get("price") if entry else None,execution_zone=execution,reaction_extreme=None,atr=atr,tick_size=tick_size,config=cfg) if entry else None
    if stop:stop["spike_risk_adjusted"]=bool(risk and risk["alignment"]=="opposed")
    targets=build_spike_targets(candles_by_timeframe=candles_by_timeframe,direction=direction,entry=entry["price"],stop=stop.get("price"),spike=spike,atr=atr,minimum_rr=risk["minimum_required_rr"],current_price=current_price) if entry and stop and stop.get("valid") else None;rr=validate_reward_risk(direction=direction,entry=entry["price"],stop=stop.get("price"),tp1=targets.get("tp1"),tp2=targets.get("tp2"),minimum_rr=risk["minimum_required_rr"]) if targets else None;max_chase=cfg.get("aligned_maximum_chase_atr",.35) if risk and risk["alignment"]=="aligned" else cfg.get("opposed_maximum_chase_atr",.25);chase=validate_chase(direction=direction,current_price=current_price,entry=entry["price"],execution_zone=execution,tp1=targets.get("tp1"),stop=stop.get("price"),atr=atr,maximum_chase_atr=max_chase) if rr and rr.get("valid") else None;ready=all((eligible,selected,zone and zone.get("valid"),execution and execution.get("valid"),confirmation and confirmation.get("valid"),entry and entry.get("valid"),stop and stop.get("valid"),targets and targets.get("tp1"),rr and rr.get("valid"),chase and chase.get("valid")));status=_status(eligible,spike,cooldown,selected,execution,confirmation,ready,chase,name,risk);now=str(analysis_time or (_time(m5.iloc[-1]) if len(m5) else ""));lifecycle=None
    if setup_id:
        state="ENTRY_AVAILABLE" if ready else "TOO_LATE" if status=="TOO LATE" else "CONFIRMED" if confirmation and confirmation.get("valid") else "IN_ZONE" if interaction else "WAITING_FOR_PULLBACK";lifecycle=advance_setup(symbol=symbol,direction=direction,zone=zone,state=state,at=now,setup_id=setup_id,strategy="boom_crash_spike_state",family=name);lifecycle["spike_id"]=spike["spike_id"]
    plan={"direction":direction,"entry":entry["price"],"stop":stop["price"],"tp1":targets["tp1"],"tp2":targets.get("tp2"),"tp1_rr":rr["tp1_rr"],"tp2_rr":rr.get("tp2_rr"),"timing_state":chase["state"],"spike_risk_alignment":risk["alignment"]} if ready else None;decision={"status":status,"market_bias":_word(direction),"developing_direction":direction or "","trade_ready":ready,"scenario":scenario,"risk_alignment":risk.get("alignment") if risk else "","spike_id":spike.get("spike_id") if spike else None,"setup_id":setup_id,"summary":status.title(),"next_action":_next(status,name,direction),"phase":status.replace(" ","_")}
    return {"strategy":{"name":"Boom/Crash Spike-State","eligible":eligible,"eligibility_reason":"Eligible family and synchronized data." if eligible else " ".join(reasons)},"family_context":context,"decision":decision,"spike":spike,"qualification":qualification,"cooldown":cooldown,"spike_hold":hold,"spike_rejection":rejection,"post_spike_structure":structure,"m15_setup_zone":zone,"m5_execution_zone":execution,"confirmation":confirmation,"confirmed_entry":entry,"structural_stop":stop,"targets":targets,"reward_risk":rr,"chase":chase,"active_trade_plan":plan,"rejected_candidates":reasons+continuation["reasons"]+normalization["reasons"],"previous_setup":archived_setups()[-1] if archived_setups() else None,"warnings":risk.get("warnings",[]) if risk else [],"bullish_continuation_candidate":continuation if name=="BOOM" else None,"bearish_normalization_candidate":normalization if name=="BOOM" else None,"bearish_continuation_candidate":continuation if name=="CRASH" else None,"bullish_normalization_candidate":normalization if name=="CRASH" else None,"selected_candidate":selected,"lifecycle":lifecycle}

def evaluate_spike_state(*,family,spike,regime):
    family=family.upper();cooldown=bool(spike.get("cooldown_active"));expected="up" if family=="BOOM" else "down"
    def side(name):
        alignment="aligned" if (family=="BOOM" and name=="buy") or (family=="CRASH" and name=="sell") else "opposed";eligible=bool(spike.get("spike_detected") and not cooldown and regime.get("direction")==_word(name));return candidate("boom_crash_spike_state",name,eligible=eligible,state="WAITING_FOR_PULLBACK" if eligible else "POST_SPIKE_COOLDOWN" if cooldown else "NO_SETUP",quality=75 if eligible else 0)|{"spike_direction_alignment":alignment,"required_minimum_rr":1.5 if alignment=="aligned" else 2.0,"required_confirmation_strength":"standard" if alignment=="aligned" else "strong","position_risk_multiplier":1.0 if alignment=="aligned" else .5,"gap_risk":"moderate" if alignment=="aligned" else "high","slippage_risk":"high"}
    result=directional_result("boom_crash_spike_state",side("buy"),side("sell"));result["state"]="COOLDOWN" if cooldown else "POST_SPIKE_EVALUATION" if spike.get("spike_detected") else "NORMAL_DRIFT";result["expected_spike_direction"]=expected;return result
def _status(eligible,spike,cooldown,selected,execution,confirmation,ready,chase,family,risk):
    if not eligible:return "DATA UNAVAILABLE"
    if not spike:return "NORMAL DRIFT"
    if cooldown and cooldown.get("active"):return "POST-SPIKE COOLDOWN"
    if not selected:return "RECALIBRATING STRUCTURE"
    if chase and chase.get("state") in {"TOO_LATE","MISSED"}:return "TOO LATE"
    if ready:
        base="READY TO BUY" if selected["direction"]=="buy" else "READY TO SELL";return base+(" — AGAINST SPIKE RISK" if risk["alignment"]=="opposed" else "")
    if execution:return "WAITING FOR M5 CONFIRMATION"
    return f"{family} {'BUY CONTINUATION' if selected['scenario']=='spike_continuation' and selected['direction']=='buy' else 'SELL CONTINUATION' if selected['scenario']=='spike_continuation' else 'BUY NORMALIZATION' if selected['direction']=='buy' else 'SELL NORMALIZATION'} FORMING"
def _next(status,family,direction):
    if status=="NORMAL DRIFT":return "No qualified spike is active. Do not infer that a spike is due."
    if status=="POST-SPIKE COOLDOWN":return "Wait for completed candles, stabilized volatility, and fresh post-spike structure."
    if status.startswith("READY"):return "Review the validated paper-analysis plan; no order is placed."
    return "Wait for a fresh post-spike area and completed M5 confirmation."
def _setup_id(symbol,spike,scenario,direction,zone):return "bcs-"+hashlib.sha256(json.dumps([symbol,spike["spike_id"],scenario,direction,zone.get("low"),zone.get("high")],default=str).encode()).hexdigest()[:20]
def _word(direction):return "bullish" if direction=="buy" else "bearish" if direction=="sell" else direction
def _completed(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame();return rows[rows.complete.astype(bool)] if "complete" in rows else rows
def _confirmation_close(rows,confirmation):
    if not confirmation or not confirmation.get("valid"):return None
    matched=rows[rows.time==pd.Timestamp(confirmation["candle_time"])] if "time" in rows else rows.iloc[0:0];return float(matched.iloc[-1].close) if len(matched) else None
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
