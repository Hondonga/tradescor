"""Paper-only boundary reaction strategy for stable Derived ranges."""
from __future__ import annotations
import hashlib,json
import pandas as pd
from strategies.derived.base_derived_strategy import load_strategy_thresholds,candidate,directional_result
from analysis.derived_range_reaction_context import build_range_reaction_context
from analysis.derived_range_detector import detect_derived_range
from analysis.derived_range_lock import active_range,lock_range,release_range
from analysis.derived_range_boundary_quality import evaluate_boundary_quality
from analysis.derived_boundary_pressure import detect_boundary_pressure
from analysis.derived_range_price_location import classify_range_location
from analysis.derived_boundary_rejection import detect_boundary_rejection
from analysis.derived_range_execution_zone import build_range_boundary_zone,build_range_m5_execution_zone
from analysis.derived_range_confirmation import confirm_range_reaction,lock_range_reaction_entry
from analysis.derived_structural_stop import build_structural_stop
from analysis.derived_range_target_engine import build_range_reaction_targets
from analysis.derived_trade_plan_validator import validate_reward_risk,validate_chase
from analysis.derived_setup_lifecycle import advance_setup,archived_setups

def evaluate_derived_range_reaction(*,symbol,family,regime,profile,volatility,candles_by_timeframe,current_price,tick_size=.01,data_quality=None,analysis_time=None,risk_adjustments=None):
    cfg=load_strategy_thresholds().get("derived_range_reaction",{});adjust=risk_adjustments or {};cfg["minimum_tp1_rr"]*=adjust.get("minimum_tp1_rr_multiplier",1);cfg["maximum_chase_atr"]*=adjust.get("maximum_chase_atr_multiplier",1);cfg["stop_buffer_atr"]*=adjust.get("stop_buffer_atr_multiplier",1); context=build_range_reaction_context(family,regime,profile,volatility,data_quality,cfg)
    m15=_completed(candles_by_timeframe.get("M15")); m5=_completed(candles_by_timeframe.get("M5")); atr=float(profile.get("atr") or 0); locked=active_range(symbol); detected=None
    detector_cfg={"minimum_range_duration":18,"minimum_boundary_reactions":3,"minimum_reactions_per_side":1,"minimum_width_atr":.75,"maximum_width_atr":5,"minimum_range_quality":cfg.get("minimum_range_quality",.68)}
    if not locked:
        detected=detect_derived_range(m15,atr,detector_cfg)
        if detected.get("valid"): locked=lock_range(symbol,detected,_snapshot(m15))
    reasons=list(context["rejection_reasons"])
    if not locked: reasons.append("No qualified range is available to lock.")
    location=classify_range_location(current_price,locked,atr,cfg) if locked else classify_range_location(None,None,atr,cfg)
    lower=evaluate_boundary_quality(m15,locked,"lower",atr,cfg) if locked else None; upper=evaluate_boundary_quality(m15,locked,"upper",atr,cfg) if locked else None
    pressure=detect_boundary_pressure(m15,locked,atr,profile,cfg) if locked else None
    direction="buy" if location["location"] in {"lower_boundary","lower_quartile"} else "sell" if location["location"] in {"upper_boundary","upper_quartile"} else None
    side="lower" if direction=="buy" else "upper" if direction=="sell" else None; quality=lower if side=="lower" else upper if side else None
    if direction and quality and not quality.get("valid"): reasons.extend(quality["rejection_reasons"])
    pressured=bool(direction and pressure and pressure.get("breakout_risk") and pressure.get("dominant_side")==side)
    if pressured: reasons.append("Breakout pressure vetoes fading this boundary.")
    zone=build_range_boundary_zone(locked,direction,atr,cfg) if locked else None
    rejection=detect_boundary_rejection(m5,locked,side,atr=atr) if side and locked else None
    if rejection and rejection.get("event_type")=="ACCEPTED_BREAKOUT": reasons.append("Accepted breakout invalidates the boundary fade.")
    eligible=bool(context["eligible"] and locked and direction and quality and quality.get("valid") and not pressured and not (rejection and rejection.get("event_type")=="ACCEPTED_BREAKOUT"))
    setup_id=_setup_id(symbol,locked,direction) if eligible else None; execution=build_range_m5_execution_zone(zone,rejection,atr) if eligible else None
    confirmation=confirm_range_reaction(m5,direction,zone,execution,setup_id,locked["range_id"],rejection) if setup_id else None
    entry_price=_confirmation_close(m5,confirmation); entry=lock_range_reaction_entry(confirmation,setup_id,locked["range_id"],entry_price) if confirmation else None
    stop=build_structural_stop(direction=direction,entry=entry.get("price") if entry else None,execution_zone=zone,reaction_extreme=(rejection or {}).get("rejection_extreme"),atr=atr,tick_size=tick_size,config=cfg) if entry else None
    targets=build_range_reaction_targets(direction=direction,entry=entry["price"],stop=stop["price"],locked_range=locked,current_price=current_price,minimum_rr=cfg.get("minimum_tp1_rr",1.3),atr=atr) if entry and stop and stop.get("valid") else None
    rr=validate_reward_risk(direction=direction,entry=entry["price"],stop=stop["price"],tp1=targets.get("tp1"),tp2=targets.get("tp2"),minimum_rr=cfg.get("minimum_tp1_rr",1.3)) if targets else None
    chase=validate_chase(direction=direction,current_price=current_price,entry=entry["price"],execution_zone=execution,tp1=targets.get("tp1"),stop=stop["price"],atr=atr,maximum_chase_atr=cfg.get("maximum_chase_atr",.25)) if rr and rr.get("valid") else None
    ready=bool(eligible and rejection and rejection.get("valid") and confirmation and confirmation.get("valid") and entry and entry.get("valid") and stop and stop.get("valid") and targets and targets.get("valid") and rr and rr.get("valid") and chase and chase.get("valid"))
    status=_status(context,locked,location,direction,pressure,rejection,confirmation,ready,chase,reasons); now=str(analysis_time or (_time(m5.iloc[-1]) if len(m5) else "")); lifecycle=None
    if setup_id:
        state="ENTRY_AVAILABLE" if ready else "TOO_LATE" if status=="TOO LATE" else "INVALIDATED" if status=="RANGE INVALIDATED" else "CONFIRMED" if confirmation and confirmation.get("valid") else "WAITING_FOR_CONFIRMATION" if rejection and rejection.get("valid") else "IN_ZONE"
        lifecycle=advance_setup(symbol=symbol,direction=direction,zone=zone,state=state,at=now,setup_id=setup_id,strategy="derived_range_reaction",family=family.get("family"),range_id=locked["range_id"])
        if state=="INVALIDATED": release_range(symbol,locked["range_id"])
    plan={"direction":direction,"entry":entry["price"],"stop":stop["price"],"tp1":targets["tp1"],"tp2":targets.get("tp2"),"tp1_rr":rr["tp1_rr"],"tp2_rr":rr.get("tp2_rr"),"timing_state":chase["state"]} if ready else None
    decision={"status":status,"market_bias":"bullish" if direction=="buy" else "bearish" if direction=="sell" else "neutral","developing_direction":direction or "","trade_ready":ready,"setup_id":setup_id,"range_id":locked.get("range_id") if locked else None,"summary":status.title(),"next_action":_next(status,direction),"phase":status.replace(" ","_"),"strategy_status":context["strategy_status"]}
    buy={"direction":"buy","eligible":bool(eligible and direction=="buy"),"boundary_quality":lower}; sell={"direction":"sell","eligible":bool(eligible and direction=="sell"),"boundary_quality":upper}
    return {"strategy":{"name":"Derived Range Reaction","eligible":eligible,"eligibility_reason":"Eligible boundary reaction context." if eligible else " ".join(dict.fromkeys(reasons)),"family_relationship":context["family_relationship"],"status":context["strategy_status"]},"decision":decision,"range":locked or detected,"boundary_quality":{"lower":lower,"upper":upper},"boundary_pressure":pressure,"price_location":location,"boundary_rejection":rejection,"m15_setup_zone":zone,"m5_execution_zone":execution,"confirmation":confirmation,"confirmed_entry":entry,"structural_stop":stop,"targets":targets,"reward_risk":rr,"chase":chase,"active_trade_plan":plan,"previous_setup":archived_setups()[-1] if archived_setups() else None,"warnings":[],"rejection_reasons":list(dict.fromkeys(reasons)),"bullish_candidate":buy,"bearish_candidate":sell,"selected_candidate":buy if buy["eligible"] else sell if sell["eligible"] else None,"lifecycle":lifecycle}

def evaluate_range_reaction(*,profile,price_location):
    stable=profile.get("regime") in {"range","stable_range","RANGE"}; buy=candidate("derived_range_reaction","buy",eligible=stable and price_location in {"near_low","lower_boundary"},state="WAITING_FOR_CONFIRMATION",quality=60); sell=candidate("derived_range_reaction","sell",eligible=stable and price_location in {"near_high","upper_boundary"},state="WAITING_FOR_CONFIRMATION",quality=60); return directional_result("derived_range_reaction",buy,sell)

def _status(context,locked,location,direction,pressure,rejection,confirmation,ready,chase,reasons):
    if not context["eligible"]: return "NO VALID SETUP"
    if not locked: return "RANGE FORMING"
    if location["location"]=="outside" or rejection and rejection.get("event_type")=="ACCEPTED_BREAKOUT": return "RANGE INVALIDATED"
    if location["location"]=="mid_range": return "MID-RANGE — NO TRADE"
    if pressure and pressure.get("breakout_risk") and pressure.get("dominant_side")==('lower' if direction=='buy' else 'upper'): return "BREAKOUT PRESSURE"
    if chase and chase.get("state") in {"TOO_LATE","MISSED"}: return "TOO LATE"
    if ready: return "READY TO BUY" if direction=="buy" else "READY TO SELL"
    if confirmation and confirmation.get("valid"): return "WAITING FOR M5 CONFIRMATION"
    if rejection and rejection.get("valid"): return "WAITING FOR M5 BUY CONFIRMATION" if direction=="buy" else "WAITING FOR M5 SELL CONFIRMATION"
    if rejection and rejection.get("event_type")=="WICK_ONLY": return "BUY REACTION FORMING" if direction=="buy" else "SELL REACTION FORMING"
    if location["location"] in {"lower_boundary","upper_boundary"}: return "IN BUY REACTION AREA" if direction=="buy" else "IN SELL REACTION AREA"
    return "APPROACHING LOWER BOUNDARY" if direction=="buy" else "APPROACHING UPPER BOUNDARY" if direction=="sell" else "RANGE LOCKED"
def _next(status,direction):
    if status=="MID-RANGE — NO TRADE": return "Do not enter in the middle of the range. Wait for a qualified boundary interaction."
    if status=="BREAKOUT PRESSURE": return "Do not fade sustained boundary pressure; wait for resolution."
    if status.startswith("READY"): return "Review the validated paper-analysis plan; no order is placed."
    if direction: return f"Wait for a completed M5 {'bullish' if direction=='buy' else 'bearish'} boundary rejection and confirmation."
    return "Wait for price to approach a qualified range boundary."
def _setup_id(symbol,locked,direction): return "drr-"+hashlib.sha256(json.dumps([symbol,locked["range_id"],direction],default=str).encode()).hexdigest()[:20]
def _completed(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame(); return rows[rows.complete.astype(bool)] if "complete" in rows else rows
def _snapshot(rows): return rows[[key for key in ("time","open","high","low","close") if key in rows]].to_dict("records")
def _confirmation_close(rows,confirmation):
    if not confirmation or not confirmation.get("valid"): return None
    matched=rows[rows.time==pd.Timestamp(confirmation["candle_time"])] if "time" in rows else rows.iloc[0:0]; return float(matched.iloc[-1].close) if len(matched) else None
def _time(row):
    value=row.get("time"); return value.isoformat() if hasattr(value,"isoformat") else str(value)
