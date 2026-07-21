"""Paper-only Derived Range Breakout and Retest strategy."""
from __future__ import annotations
import hashlib,json
import pandas as pd
from strategies.derived.base_derived_strategy import load_strategy_thresholds
from analysis.derived_range_detector import detect_derived_range
from analysis.derived_range_lock import lock_range,active_range,release_range
from analysis.derived_breakout_classifier import classify_breakout
from analysis.derived_retest_zone_engine import build_retest_zone,classify_retest_location
from analysis.derived_retest_confirmation import retest_interaction_time,confirm_retest,lock_range_entry
from analysis.derived_structural_stop import build_structural_stop
from analysis.derived_breakout_target_engine import build_breakout_targets
from analysis.derived_trade_plan_validator import validate_reward_risk,validate_chase
from analysis.derived_setup_lifecycle import advance_setup,archived_setups

ELIGIBLE_SECONDARY={"RANGE","COMPRESSION","BREAKOUT_ATTEMPT","ACCEPTED_BREAKOUT","EXPANSION"}
def evaluate_derived_range_break_retest(*,symbol,family,regime,profile,candles_by_timeframe,current_price,tick_size=.01,data_quality=None,analysis_time=None,risk_adjustments=None):
    cfg=load_strategy_thresholds().get("derived_range_break_retest",{});family_name=family.get("family","OTHER_DERIVED");relationship="primary" if family_name=="RANGE_BREAK" else "secondary" if family_name=="VOLATILITY" else "restricted";eligible_family=relationship=="primary" or relationship=="secondary" and regime.get("regime") in ELIGIBLE_SECONDARY;reasons=[]
    adjust=risk_adjustments or {};cfg["minimum_tp1_rr"]*=adjust.get("minimum_tp1_rr_multiplier",1);cfg["maximum_chase_atr"]*=adjust.get("maximum_chase_atr_multiplier",1);cfg["stop_buffer_atr"]*=adjust.get("stop_buffer_atr_multiplier",1)
    if not cfg.get("enabled",True):reasons.append("Strategy is disabled.")
    if not eligible_family:reasons.append("Family or regime is not eligible for range-break evaluation.")
    if regime.get("regime") in {"POST_SPIKE","UNSTABLE","INSUFFICIENT_DATA"}:reasons.append(f"Regime {regime.get('regime')} is restricted.")
    if data_quality and (not data_quality.get("analysis_allowed",True) or data_quality.get("status") not in {"good"}):reasons.append("Complete, current multi-timeframe data is required.")
    m15=_completed(candles_by_timeframe.get("M15"));m5=_completed(candles_by_timeframe.get("M5"));atr=float(profile.get("atr") or 0);locked=active_range(symbol);detected=None
    if not locked:
        detected=detect_derived_range(m15,atr,cfg)
        if detected.get("valid"):locked=lock_range(symbol,detected,_snapshot(m15))
    breakout=classify_breakout(m15,locked,atr,cfg) if locked else None
    if not locked:reasons.append("No measurable range is available to lock.")
    eligible=not reasons;retest=build_retest_zone(locked,breakout,atr,cfg) if breakout and breakout.get("accepted") else None;completed_close=float(m5.close.iloc[-1]) if len(m5) else None;location=classify_retest_location(completed_close,current_price,retest,locked,atr) if retest else {"completed_candle_state":"WAITING_FOR_RETEST","live_price_state":"WAITING_FOR_RETEST","distance_to_retest_points":None,"distance_to_retest_atr":None};interaction=retest_interaction_time(m5,retest,breakout.get("breakout_time")) if retest else None
    direction=breakout.get("direction") if breakout and breakout.get("accepted") else None;setup_id=_setup_id(symbol,locked,direction,breakout) if direction else None;confirmation=confirm_retest(m5,direction,retest,setup_id,locked["range_id"],interaction) if setup_id else None;entry_price=_confirmation_close(m5,confirmation);entry=lock_range_entry(confirmation,setup_id,locked["range_id"],entry_price) if confirmation else None;side="buy" if direction=="bullish" else "sell" if direction=="bearish" else None
    stop=build_structural_stop(direction=side,entry=entry.get("price") if entry else None,execution_zone=retest,reaction_extreme=None,atr=atr,tick_size=tick_size,config=cfg) if entry else None;targets=build_breakout_targets(candles_by_timeframe=candles_by_timeframe,direction=direction,entry=entry["price"],stop=stop.get("price"),locked_range=locked,atr=atr,minimum_rr=cfg.get("minimum_tp1_rr",1.5),current_price=current_price) if entry and stop and stop.get("valid") else None;rr=validate_reward_risk(direction=side,entry=entry["price"],stop=stop.get("price"),tp1=targets.get("tp1"),tp2=targets.get("tp2"),minimum_rr=cfg.get("minimum_tp1_rr",1.5)) if targets else None;chase=validate_chase(direction=side,current_price=current_price,entry=entry["price"],execution_zone=retest,tp1=targets.get("tp1"),stop=stop.get("price"),atr=atr,maximum_chase_atr=cfg.get("maximum_chase_atr",.35)) if rr and rr.get("valid") else None
    ready=all((eligible,direction,retest and retest.get("valid"),confirmation and confirmation.get("valid"),entry and entry.get("valid"),stop and stop.get("valid"),targets and targets.get("tp1"),rr and rr.get("valid"),chase and chase.get("valid")));status=_status(eligible,locked,breakout,retest,interaction,confirmation,ready,chase,location);market_bias="bullish" if direction=="bullish" else "bearish" if direction=="bearish" else "neutral";now=str(analysis_time or (_time(m5.iloc[-1]) if len(m5) else ""));lifecycle=None
    if setup_id:
        state="ENTRY_AVAILABLE" if ready else "TOO_LATE" if status=="TOO LATE" else "FAILED_BREAKOUT" if status=="FAILED BREAKOUT" else "CONFIRMED" if confirmation and confirmation.get("valid") else "IN_RETEST_AREA" if interaction else "WAITING_FOR_RETEST";lifecycle=advance_setup(symbol=symbol,direction=side,zone=retest or {"low":locked["low"],"high":locked["high"],"formed_at":locked["locked_at"]},state=state,at=now,setup_id=setup_id,strategy="derived_range_break_retest",family=family_name,range_id=locked["range_id"])
        if state in {"TOO_LATE","FAILED_BREAKOUT"}:release_range(symbol,locked["range_id"])
    plan={"direction":side,"entry":entry["price"],"stop":stop["price"],"tp1":targets["tp1"],"tp2":targets.get("tp2"),"tp1_rr":rr["tp1_rr"],"tp2_rr":rr.get("tp2_rr"),"timing_state":chase["state"]} if ready else None;decision={"status":status,"market_bias":market_bias,"developing_direction":side or "","trade_ready":ready,"setup_id":setup_id,"range_id":locked.get("range_id") if locked else None,"summary":status.title(),"next_action":_next(status,direction),"phase":status.replace(" ","_")}
    bull={"direction":"buy","eligible":bool(direction=="bullish" and eligible),"breakout":breakout if direction=="bullish" else None};bear={"direction":"sell","eligible":bool(direction=="bearish" and eligible),"breakout":breakout if direction=="bearish" else None}
    return {"strategy":{"name":"Derived Range Breakout and Retest","eligible":eligible,"eligibility_reason":"Eligible range-break context." if eligible else " ".join(reasons),"family_relationship":relationship},"decision":decision,"range":locked or detected,"breakout":breakout,"retest_zone":retest,"m5_execution_zone":retest,"price_location":location,"confirmation":confirmation,"confirmed_entry":entry,"structural_stop":stop,"targets":targets,"reward_risk":rr,"chase":chase,"active_trade_plan":plan,"previous_setup":archived_setups()[-1] if archived_setups() else None,"warnings":[],"rejection_reasons":reasons+(breakout.get("rejection_reasons",[]) if breakout else []),"bullish_candidate":bull,"bearish_candidate":bear,"selected_candidate":bull if bull["eligible"] else bear if bear["eligible"] else None,"lifecycle":lifecycle}

def evaluate_range_break(*,candles,profile,minimum_touches=3,minimum_duration=20):
    cfg={**load_strategy_thresholds().get("derived_range_break_retest",{}),"minimum_boundary_reactions":minimum_touches,"minimum_range_duration":minimum_duration,"minimum_range_quality":0};detected=detect_derived_range(candles.iloc[:-1],profile.get("atr"),cfg);locked={"low":detected.get("low"),"high":detected.get("high"),"locked_at":detected.get("ended_at")} if detected.get("valid") else None;breakout=classify_breakout(candles,locked,profile.get("atr"),cfg) if locked else None;return {"range":detected,"breakout":breakout,"retest_zone":build_retest_zone(locked,breakout,profile.get("atr"),cfg) if breakout else None,"state":"ACCEPTED_BREAKOUT" if breakout and breakout.get("accepted") else "RANGE_LOCKED" if locked else "RANGE_FORMING","bullish_candidate":{"eligible":bool(breakout and breakout.get("accepted") and breakout.get("direction")=="bullish")},"bearish_candidate":{"eligible":bool(breakout and breakout.get("accepted") and breakout.get("direction")=="bearish")},"selected_candidate":None}

def _status(eligible,locked,breakout,retest,interaction,confirmation,ready,chase,location):
    if not eligible:return "NO VALID SETUP"
    if chase and chase.get("state") in {"TOO_LATE","MISSED"}:return "TOO LATE"
    if ready:return "READY TO BUY" if breakout["direction"]=="bullish" else "READY TO SELL"
    if breakout and breakout.get("event_type")=="FAILED_BREAKOUT" or location.get("completed_candle_state")=="FAILED_BREAKOUT":return "FAILED BREAKOUT"
    if confirmation and confirmation.get("valid"):return "WAITING FOR M5 CONFIRMATION"
    if interaction:return "IN RETEST AREA"
    if retest:return "POTENTIAL BUY RETEST" if breakout["direction"]=="bullish" else "POTENTIAL SELL RETEST"
    if breakout and breakout.get("event_type")=="BREAKOUT_ATTEMPT":return "BREAKOUT ATTEMPT"
    return "RANGE LOCKED" if locked else "RANGE FORMING"
def _next(status,direction):
    if status=="RANGE LOCKED":return "Wait for price to close beyond a locked boundary with acceptance."
    if status.startswith("POTENTIAL"):return f"Wait for price to retest the broken range {'high' if direction=='bullish' else 'low'}. Confirmation is calculated only after interaction."
    if status=="FAILED BREAKOUT":return "Wait for a new range or an independently qualified setup."
    if status.startswith("READY"):return "Review the validated paper-analysis plan; no order is placed."
    return "Wait for the next required range-break condition."
def _setup_id(symbol,locked,direction,breakout):return "rbr-"+hashlib.sha256(json.dumps([symbol,locked["range_id"],direction,breakout.get("breakout_time")],default=str).encode()).hexdigest()[:20]
def _completed(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame();return rows[rows.complete.astype(bool)] if "complete" in rows else rows
def _snapshot(rows):return rows[[key for key in ("time","open","high","low","close") if key in rows]].to_dict("records")
def _confirmation_close(rows,confirmation):
    if not confirmation or not confirmation.get("valid"):return None
    matched=rows[rows.time==pd.Timestamp(confirmation["candle_time"])] if "time" in rows else rows.iloc[0:0];return float(matched.iloc[-1].close) if len(matched) else None
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
