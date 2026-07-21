"""Archive terminal setups and return the decision to current-market mode."""

from __future__ import annotations

import pandas as pd


TERMINAL_STATES={"too_late":"missed","entry_extended":"missed","entry_missed":"missed","setup_missed":"missed","expired":"expired","invalidated":"invalidated","completed":"completed","stopped":"stopped","target_hit":"target_hit"}


def apply_setup_recovery(decision:dict[str,object],*,current_price:object,analysis_time:object,asset_rules:dict[str,object],m5_atr:object=None)->dict[str,object]:
    setup=decision.get("setup") or {}; execution=decision.get("execution") or {}; state=str(execution.get("state") or setup.get("stage") or "")
    result=TERMINAL_STATES.get(state); active=_active_contract(setup,execution)
    if not result:
        decision["active_setup"]=active if active.get("setup_id") else None; decision["previous_setup"]=None; decision["previous_setup_status"]=None
        decision["current_market_decision"]={"status":(decision.get("user_output") or {}).get("status","NO CURRENT SETUP"),"direction":active.get("direction","neutral"),"strategy":active.get("strategy",""),"setup":active if active.get("setup_id") else None}
        return decision
    previous=_previous_contract(active,execution,result,current_price,analysis_time,asset_rules,m5_atr)
    decision["previous_setup"]=previous; decision["previous_setup_status"]=result; decision["setup_history"]=[previous]; decision["active_setup"]=None
    decision["setup"]=_empty_setup(); decision["execution"]=_empty_execution(); decision["overlays"]={"setup_zone":None,"confirmation":None,"invalidation":None,"entry":None,"stop":None,"targets":[],"conditional_arrow":None}
    decision["quality"]={**(decision.get("quality") or {}),"score":0,"confidence":"low","trade_plan_valid":False}
    output=decision.get("user_output") or {}; output.update({"status":"NO CURRENT SETUP","direction":"Neutral","execution_stage":"reassessing","next_action":"Wait for a new pullback or reversal confirmation.","summary":"Current market reassessed after archiving the terminal setup."}); decision["user_output"]=output
    decision["current_market_decision"]={"status":"NO CURRENT SETUP","direction":"neutral","strategy":"","setup":None,"scan":{"directions_evaluated":["buy","sell"],"strategies_evaluated":["ict_2022","supply_demand","breakout_retest"],"completed":True,"excluded_setup_id":previous["setup_id"]}}
    return decision


def _active_contract(setup,execution):
    confirmed=(execution.get("confirmed_entry") or {}).get("confirmed_at") or (setup.get("confirmation") or {}).get("confirmed_time")
    setup_zone=setup.get("zone") or {}; execution_zone=execution.get("m5_execution_zone") or execution.get("entry_zone") or {}; zone=setup_zone if _valid_zone(setup_zone) else execution_zone
    return {"setup_id":setup.get("setup_id"),"direction":setup.get("direction","neutral"),"strategy":setup.get("strategy",""),"entry_zone":{"low":_number(zone.get("low")),"high":_number(zone.get("high"))},"created_at":setup.get("created_time"),"confirmed_at":confirmed,"missed_at":None,"expired_at":setup.get("expires_time"),"state":execution.get("state") or setup.get("stage") or ""}


def _previous_contract(active,execution,result,current,when,rules,m5_atr=None):
    low,high=active["entry_zone"]["low"],active["entry_zone"]["high"]; price=_number(current); distance=_distance(price,low,high); unit,amount=_units(distance,rules); preferred=_number((execution.get("confirmed_entry") or {}).get("price")) or _number(execution.get("entry")); preferred_distance=abs(price-preferred) if price is not None and preferred is not None else None
    timestamp=_iso(when); direction=active.get("direction"); relation="below" if price is not None and low is not None and price<low else "above" if price is not None and high is not None and price>high else "inside"; atr=_number(m5_atr); distance_atr=round(distance/atr,2) if distance is not None and atr and atr>0 else None
    return {**active,"result":result,"state":result,"entry_low":low,"entry_high":high,"original_entry":{"low":low,"high":high},"missed_at":timestamp if result=="missed" else None,"expired_at":timestamp if result=="expired" else active.get("expired_at"),"reason":"Entry became extended before execution." if result=="missed" else f"Setup {result}.","distance_moved":amount,"distance_unit":unit,"distance_relation":relation,"distance_from_preferred":_units(preferred_distance,rules)[1],"distance_from_preferred_unit":unit,"distance_atr":distance_atr,"remaining_rr":_number(execution.get("remaining_rr_from_current")) or _number(execution.get("risk_reward")),"terminal_at":timestamp}


def _empty_setup(): return {"setup_id":None,"direction":"neutral","strategy":"","type":"","stage":"none","zone":{"low":None,"high":None,"type":"","origin_time":None},"confirmation":{"price":None,"type":"","confirmed":False,"confirmed_time":None},"invalidation":{"price":None,"type":""},"created_time":None,"updated_time":None,"expires_time":None}
def _empty_execution(): return {"state":"waiting_for_m15_area","direction":"neutral","entry":None,"m5_execution_zone":None,"entry_zone":None,"confirmed_entry":{"price":None,"confirmed_at":None,"trigger_price":None,"trigger_close":None},"stop":None,"targets":[],"risk_reward":None,"message":"Scanning synchronized candles for a fresh setup.","forming_state":None,"confirmed_state":None}
def _valid_zone(zone): return _number(zone.get("low")) is not None and _number(zone.get("high")) is not None
def _distance(current,low,high):
    if current is None or low is None or high is None:return None
    return low-current if current<low else current-high if current>high else 0.0
def _units(distance,rules):
    if distance is None:return ("pips" if rules.get("asset_class")=="forex" else "points"),None
    return ("pips",round(distance/float(rules["pip_size"]),1)) if rules.get("asset_class")=="forex" else ("points",round(distance,2))
def _iso(value):
    stamp=pd.Timestamp(value); stamp=stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC"); return stamp.isoformat()
def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
