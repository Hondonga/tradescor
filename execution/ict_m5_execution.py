"""M5-only execution adapter for the frozen ICT 2022 v2 sequence."""

from __future__ import annotations

from copy import deepcopy

from analysis.m5_execution_engine import build_m5_execution_plan


STATE_MAP={"waiting_for_zone":"WAITING_FOR_ENTRY_ARRAY","in_zone":"IN_ENTRY_ARRAY","waiting_for_trigger":"REACTION_FORMING","trigger_forming":"WAITING_FOR_M5_CLOSE","trigger_confirmed":"M5_CONFIRMED","entry_valid":"ENTRY_AVAILABLE","entry_extended":"ENTRY_EXTENDED","too_late":"TOO_LATE","invalidated":"INVALIDATED","unavailable":"EXECUTION_DATA_UNAVAILABLE"}


def build_ict_m5_execution(*, top_down, entry_array, sweep, m5_candles, analysis_time, current_price, spread, asset_class, filters, session, minimum_rr, mode="conservative"):
    if not entry_array or not entry_array.get("valid"):
        return {"state":"WAITING_FOR_ENTRY_ARRAY","raw_state":"waiting_for_zone","trigger":None,"entry":None,"entry_zone":None,"stop":None,"targets":[],"risk_reward":None,"entry_distance":None,"confirmed_signal":None,"forming_signal":None,"rejection_reasons":["A valid displacement FVG is required."]}
    copied=deepcopy(top_down); direction=str((copied.get("alignment") or {}).get("primary_direction","neutral")); zone={"low":entry_array["low"],"high":entry_array["high"],"type":"fvg","label":"Displacement FVG","start_time":entry_array["formed_at"]}
    copied["m15_setup"]={**(copied.get("m15_setup") or {}),"enabled":True,"direction":direction,"setup_type":"ict_2022_v2","zone_low":zone["low"],"zone_high":zone["high"],"zone":zone,"status":"watching","target_context":(copied.get("m15_setup") or {}).get("target_context") or {}}
    raw=build_m5_execution_plan(top_down_analysis=copied,m5_candles=m5_candles,analysis_timestamp=analysis_time,current_price=current_price,spread=spread,asset_type=asset_class,news_filters=filters,session_context=session,minimum_rr=minimum_rr,mode=mode)
    stop=raw.get("stop"); extreme=(sweep or {}).get("sweep_extreme")
    if raw.get("entry") is not None and extreme is not None:
        if direction=="buy" and (stop is None or stop>=extreme): raw["stop"]=float(extreme)-abs(float(raw["entry"])-float(extreme))*.05
        if direction=="sell" and (stop is None or stop<=extreme): raw["stop"]=float(extreme)+abs(float(raw["entry"])-float(extreme))*.05
    raw["raw_state"]=raw.get("state","unavailable"); raw["state"]=STATE_MAP.get(raw["raw_state"],"EXPIRED"); raw["rejection_reasons"]=[] if raw["state"]=="ENTRY_AVAILABLE" else [str(raw.get("message") or "M5 execution sequence is incomplete.")]
    return raw
