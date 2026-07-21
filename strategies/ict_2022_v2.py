"""Frozen, temporally ordered TradeScor ICT 2022 research model v2."""

from __future__ import annotations

from copy import deepcopy
import pandas as pd

from analysis.asset_rules import asset_rules
from analysis.ict_displacement import detect_displacement
from analysis.ict_entry_array import select_entry_array
from analysis.ict_fvg import identify_displacement_fvg
from analysis.ict_liquidity import identify_liquidity
from analysis.ict_narrative import build_narrative
from analysis.ict_state import evidence_result, load_config, stable_id
from analysis.ict_structure_shift import detect_mss
from analysis.ict_sweep import classify_sweep
from analysis.ict_state import evidence_result
from analysis.liquidity_target_engine import build_liquidity_targets
from execution.ict_m5_execution import build_ict_m5_execution


STRATEGY_ID="ict_2022"; STRATEGY_VERSION="ict_2022_v2"


def analyze_ict_2022_v2(*, symbol, asset_class, bundle, top_down, analysis_time, spread=0, filters=None, session=None, minimum_rr=None, execution_mode="conservative", amd=None):
    config,config_hash=load_config(); minimum_rr=float(minimum_rr or config["minimum_rr"]); filters=filters or {}; session=session or {}; rules=asset_rules(symbol,asset_class)
    frames=bundle["timeframes"]; m15=frames["M15"]["candles"]; m5_available=frames["M5"]["available_candles"]; m5=frames["M5"]["candles"]
    narrative_event=build_narrative(bundle=bundle,top_down=top_down); narrative=narrative_event.get("result") or _empty_narrative(); htf_direction=narrative["direction"]; live_m15=_forming(frames["M15"])
    bullish=_observe_direction("buy",m15,live_m15,m5,analysis_time,config,rules,spread); bearish=_observe_direction("sell",m15,live_m15,m5,analysis_time,config,rules,spread)
    selected=_select_observation(bullish,bearish,htf_direction); direction=selected["direction"]; relationship=_relationship(direction,htf_direction,selected,top_down)
    liquidity_event,liquidity=selected["liquidity_event"],selected["liquidity"]; sweep_event,sweep=selected["sweep_event"],selected["sweep"]; displacement_event,displacement=selected["displacement_event"],selected["displacement"]; mss_event,mss=selected["mss_event"],selected["mss"]; fvg_event=selected["fvg_event"]; entry_event,entry_array=selected["entry_event"],selected["entry_array"]; interaction=selected["interaction"]
    current=float(m5_available.iloc[-1].close) if not m5_available.empty else None
    effective_minimum_rr=max(minimum_rr,2.0) if relationship=="countertrend_reversal_candidate" else minimum_rr
    execution_top_down=_execution_top_down(top_down,direction)
    execution=build_ict_m5_execution(top_down=execution_top_down,entry_array=entry_array,sweep=sweep,m5_candles=m5_available,analysis_time=analysis_time,current_price=current,spread=spread,asset_class=asset_class,filters=filters,session=session,minimum_rr=effective_minimum_rr,mode=execution_mode)
    reference_entry=_number(execution.get("entry")) or _number((entry_array or {}).get("preferred_price")) or ((_number((entry_array or {}).get("low"))+_number((entry_array or {}).get("high")))/2 if _number((entry_array or {}).get("low")) is not None and _number((entry_array or {}).get("high")) is not None else None); reference_stop=_number(execution.get("stop")) or _number((sweep or {}).get("sweep_extreme")); directional=(liquidity or {}).get("directional_target")
    target_engine=build_liquidity_targets(symbol=symbol,asset_class=asset_class,direction=direction,entry_price=reference_entry,stop_price=reference_stop,candles_by_timeframe={key:value["candles"] for key,value in frames.items()},decision_timestamp=analysis_time,higher_timeframe_draw=htf_direction,strategy=STRATEGY_ID,spread=spread,minimum_tp1_rr=1.0,preferred_rr=effective_minimum_rr,candidate_levels=[directional] if directional else [])
    targets=[row for row in (target_engine["selected_targets"].get(key) for key in ("tp1","tp2","tp3")) if row]; remaining_rr=(targets[0].get("risk_reward") if targets else None); target_valid=bool(execution.get("entry") is not None and execution.get("stop") is not None and target_engine["quality_gate"]["passed"] and targets)
    target_event=evidence_result(result={"targets":targets,"remaining_rr":remaining_rr,"valid":target_valid,"rating":"strong" if target_valid else "projected" if targets else "reject","engine":target_engine},timestamp=None,timeframe=targets[0].get("source_timeframe","") if targets else "",valid=target_valid,evidence=[targets[0]["reason"]] if target_valid else [],rejection_reason=None if target_valid else target_engine["quality_gate"]["reason"])
    execution_confirmed=bool((execution.get("confirmed_signal") or {}).get("completed") and (execution.get("confirmed_signal") or {}).get("candle_time") and execution.get("entry") is not None); narrative_allows_trade=narrative_event["valid"] or relationship in {"countertrend_reversal_candidate","full_regime_reversal"}; core_valid=narrative_allows_trade and all(event["valid"] for event in (sweep_event,displacement_event,mss_event,fvg_event,entry_event)); plan_valid=core_valid and not interaction["expired"] and execution.get("state")=="ENTRY_AVAILABLE" and target_event["valid"]
    execution.update({"targets":targets if execution_confirmed else [],"risk_reward":remaining_rr if execution_confirmed else None})
    reentry_valid=bool(interaction["entry_array_touched"] and not interaction["expired"] and interaction["freshness"] in {"fresh","partially_mitigated"})
    sequence={"htf_narrative":_state(narrative_event) if direction==htf_direction else "waiting","directional_draw":"pass" if liquidity.get("directional_target") or (direction==htf_direction and narrative.get("draw_on_liquidity") is not None) else "waiting","opposing_liquidity":"pass" if liquidity.get("opposing_pool") else "waiting","liquidity_sweep":_state(sweep_event),"displacement":_state(displacement_event),"mss":_state(mss_event),"fvg":_state(fvg_event),"entry_array_touched":"pass" if interaction["entry_array_touched"] else "waiting","price_in_entry_array":"pass" if interaction["currently_inside_entry_array"] else "waiting","m5_confirmation":"pass" if execution_confirmed else "forming" if execution.get("forming_signal") and interaction["currently_inside_entry_array"] else "unavailable" if m5.empty else "waiting","stop_valid":"pass" if plan_valid and execution.get("stop") is not None else "waiting","target_valid":_state(target_event) if execution_confirmed else "waiting","risk_reward":"pass" if plan_valid and remaining_rr is not None else "fail" if execution_confirmed and remaining_rr is not None and remaining_rr<1 else "waiting"}
    state=_lifecycle(sequence,sweep_event,execution,plan_valid); setup_id=_setup_id(symbol,direction,liquidity,sweep,mss,entry_array) if entry_array and sweep and mss else None
    score=_score(sequence,plan_valid,bundle["data_quality"],interaction,reentry_valid); setup_score=_setup_score(sequence,bundle["data_quality"],narrative); setup_quality="high" if setup_score>=70 else "medium" if setup_score>=45 else "low"; entry_timing=_entry_timing(state)
    confidence="high" if plan_valid and bundle["data_quality"]=="valid" and narrative["alignment"]=="aligned" else "medium" if sequence["liquidity_sweep"]=="pass" and sequence["fvg"]=="pass" else "low"
    status=_status(direction,state,m5,plan_valid); first_missing=next((key for key in sequence if key!="entry_array_touched" and sequence[key]!="pass"),None); next_action="The move displaced without leaving an active retracement FVG. Do not chase." if state=="EXPIRED" else _next(first_missing,direction,execution,remaining_rr)
    if interaction["expired"]:status="SETUP EXPIRED"; next_action="The entry array is no longer valid. Wait for a new setup."
    elif interaction["entry_array_touched"] and not reentry_valid:status="NO VALID RE-ENTRY"; next_action="The entry array has been excessively mitigated. Wait for a fresh setup."
    elif reentry_valid and not interaction["currently_inside_entry_array"]:status=f"POTENTIAL {'BUY' if direction=='buy' else 'SELL'} RE-ENTRY"; next_action=f"Set an alert at {entry_array['high'] if direction=='buy' else entry_array['low']:.5f}. Do not {'buy' if direction=='buy' else 'sell'} at the current price."
    core_sequence=all(sequence.get(key)=="pass" for key in ("liquidity_sweep","displacement","mss","fvg"))
    if relationship=="countertrend_reversal_candidate":
        status=("READY TO BUY — COUNTERTREND" if direction=="buy" else "READY TO SELL — COUNTERTREND") if plan_valid else ("BUY ICT SETUP FORMING" if direction=="buy" else "SELL ICT SETUP FORMING") if core_sequence else ("POTENTIAL BUY REVERSAL" if direction=="buy" else "POTENTIAL SELL REVERSAL")
    rejection=[event["rejection_reason"] for event in (narrative_event,liquidity_event,sweep_event,displacement_event,mss_event,fvg_event,entry_event,target_event) if event.get("rejection_reason")]
    setup={"setup_id":setup_id if not interaction["expired"] else None,"candidate_id":selected["candidate_id"],"direction":direction,"relationship":relationship,"state":"EXPIRED" if interaction["expired"] else state,"sweep":sweep,"displacement":displacement,"mss":mss,"entry_array":entry_array,"entry_array_state":interaction,"freshness":interaction["freshness"],"liquidity_targets":target_engine,"confirmed_execution":{"entry":execution.get("entry"),"entry_zone":execution.get("entry_zone"),"stop":execution.get("stop"),"targets":execution.get("targets",[]),"risk_reward":execution.get("risk_reward"),"signal":execution.get("confirmed_signal"),"state":execution.get("state"),"entry_distance":execution.get("entry_distance")} if execution_confirmed else None,"invalidation":sweep.get("sweep_extreme") if sweep else None,"created_at":sweep.get("sweep_time") if sweep else None,"updated_at":bundle["analysis_time_utc"] if setup_id else None,"expires_at":bundle["analysis_time_utc"] if interaction["expired"] else None,"expiration_reason":interaction["expiration_reason"]}
    overlays=_overlays(narrative,liquidity,sweep,mss,entry_array,execution,plan_valid)
    diagnostics={"data":_data_diagnostics(bundle),"htf_narrative":narrative_event.get("diagnostics",{}),"liquidity":liquidity_event.get("diagnostics",{}),"liquidity_sweep":sweep_event.get("diagnostics",{}),"displacement":displacement_event.get("diagnostics",{}),"mss":mss_event.get("diagnostics",{}),"fvg":fvg_event.get("diagnostics",{}),"entry_array":entry_event.get("diagnostics",{}),"target":target_event.get("diagnostics",{})}
    bullish_contract=_candidate_contract(bullish,_relationship("buy",htf_direction,bullish,top_down),target_event if direction=="buy" else None); bearish_contract=_candidate_contract(bearish,_relationship("sell",htf_direction,bearish,top_down),target_event if direction=="sell" else None)
    trigger_visible=interaction["currently_inside_entry_array"] or interaction["approaching_entry_array"] or execution_confirmed
    return {"strategy_id":STRATEGY_ID,"strategy_version":STRATEGY_VERSION,"configuration_hash":config_hash,"research_profile":config["profile"],"symbol":symbol,"asset_class":asset_class,"analysis_time_utc":bundle["analysis_time_utc"],"execution_timeframe":"M5","narrative":narrative,"direction_resolution":{"higher_timeframe_bias":htf_direction,"local_setup_direction":direction,"relationship":relationship,"primary_actionable_direction":direction if plan_valid else "neutral"},"bullish_candidate":bullish_contract,"bearish_candidate":bearish_contract,"liquidity":liquidity,"sequence":sequence,"sequence_events":_events(narrative_event,liquidity_event,sweep_event,displacement_event,mss_event,fvg_event,interaction,execution,target_event),"diagnostics":{**diagnostics,"bullish_candidate":bullish_contract,"bearish_candidate":bearish_contract,"selection":{"selected_candidate":selected["candidate_id"],"reason":f"{direction.title()} candidate has the strongest temporally valid local sequence; relationship is {relationship}."}},"setup":setup,"execution":{"state":execution["state"],"entry_timing":entry_timing,"minimum_rr_required":effective_minimum_rr,"trigger":execution.get("trigger") if trigger_visible else None,"entry":execution.get("entry") if plan_valid else None,"entry_zone":entry_array if plan_valid else None,"stop":execution.get("stop") if plan_valid else None,"targets":targets if plan_valid else [],"remaining_rr":remaining_rr if plan_valid else None,"entry_distance":execution.get("entry_distance"),"confirmed_at":(execution.get("confirmed_signal") or {}).get("candle_time"),"rejection_reasons":rejection},"quality":{"sequence_score":score,"setup_score":setup_score,"setup_quality":setup_quality,"entry_timing_score":_entry_timing_score(state),"confidence":confidence,"trade_plan_valid":plan_valid,"data_quality":bundle["data_quality"]},"user_output":{"status":status,"direction":"Long bias" if direction=="buy" else "Short bias" if direction=="sell" else "Neutral","strategy_eligibility":"Eligible" if setup_id and not interaction["expired"] else "Not yet eligible","trade_readiness":"Ready" if plan_valid else "Not confirmed","execution_stage":state,"entry_timing":entry_timing,"next_action":next_action,"m5_confirmation":"Confirmed" if execution_confirmed else "Waiting for bearish trigger" if direction=="sell" and interaction["currently_inside_entry_array"] else "Waiting for bullish trigger" if direction=="buy" and interaction["currently_inside_entry_array"] else "Pending zone interaction","target_status":"Available" if plan_valid else "Pending confirmation","summary":f"Strict ICT 2022 v2 · {state.replace('_',' ').title()}.","why":[item for item in [narrative_event.get("rejection_reason"),sweep_event.get("rejection_reason"),fvg_event.get("rejection_reason"),target_event.get("rejection_reason")] if item][:3]},"overlays":overlays,"optional_context":{"amd":{"available":bool((amd or {}).get("available")),"phase":((amd or {}).get("phase") or {}).get("current"),"can_replace_core_sequence":False},"ote":{"enabled":False,"can_replace_core_sequence":False},"order_block":{"enabled":False,"can_replace_core_sequence":False}}}


def _observe_direction(direction,m15,live_m15,m5,analysis_time,config,rules,spread):
    liquidity_event=identify_liquidity(m15,timeframe="M15",direction=direction,minimum_age=int(config["liquidity_min_age_bars"]),prominence_atr=float(config["liquidity_prominence_atr"]),tolerance_atr=float(config["equal_level_tolerance_atr"]),tick_size=float(rules["tick_size"])); liquidity=liquidity_event.get("result") or {"directional_target":None,"opposing_pool":None,"candidate_pools":[]}
    sweep_event=classify_sweep(m15,liquidity.get("opposing_pool"),direction=direction,reclaim_window=int(config["reclaim_window_bars"]),accepted_closes=int(config["accepted_breakout_closes"]),forming_candle=live_m15,tick_size=float(rules["tick_size"]),spread=_number(spread) or 0); sweep=sweep_event.get("result")
    displacement_event=detect_displacement(m15,sweep,direction=direction,body_atr_threshold=float(config["displacement_body_atr"]),range_atr_threshold=float(config["displacement_range_atr"]),close_location_threshold=float(config["displacement_close_location"]),impulse_score_threshold=float(config["displacement_impulse_score"]),maximum_candles=int(config["displacement_max_candles"]),forming_candle=live_m15) if sweep_event["valid"] else _waiting("Confirmed sweep is required."); displacement=displacement_event.get("result")
    mss_event=detect_mss(m15,sweep,displacement,direction=direction,forming_candle=live_m15) if displacement_event["valid"] else _waiting("Confirmed displacement is required."); mss=mss_event.get("result")
    fvg_event=identify_displacement_fvg(m15,displacement,direction=direction,tick_size=float(rules["tick_size"]),minimum_ticks=int(config["fvg_minimum_ticks"]),max_age=int(config["fvg_max_age_bars"]),spread=_number(spread) or 0) if mss_event["valid"] else _waiting("Confirmed MSS is required.")
    entry_event=select_entry_array(fvg_event,profile="fvg"); entry_array=entry_event.get("result"); interaction=_interaction(entry_array,m5,analysis_time,direction,sweep,liquidity.get("directional_target"))
    score=sum((bool(liquidity.get("opposing_pool")),sweep_event["valid"],displacement_event["valid"],mss_event["valid"],fvg_event["valid"],interaction["state"]=="pass"))
    candidate_id=stable_id("ict-candidate",{"version":STRATEGY_VERSION,"direction":direction,"pool":(liquidity.get("opposing_pool") or {}).get("liquidity_id"),"sweep":(sweep or {}).get("sweep_time"),"mss":(mss or {}).get("break_time"),"fvg":(entry_array or {}).get("fvg_id")})
    return {"candidate_id":candidate_id,"direction":direction,"score":score,"liquidity_event":liquidity_event,"liquidity":liquidity,"sweep_event":sweep_event,"sweep":sweep,"displacement_event":displacement_event,"displacement":displacement,"mss_event":mss_event,"mss":mss,"fvg_event":fvg_event,"entry_event":entry_event,"entry_array":entry_array,"interaction":interaction}
def _select_observation(bullish,bearish,htf_direction):
    rows=[bullish,bearish]; aligned=next((row for row in rows if row["direction"]==htf_direction),None); rows.sort(key=lambda row:(row["score"],row["direction"]==htf_direction),reverse=True)
    if aligned and rows[0]["direction"]!=htf_direction and rows[0]["score"]<3:return aligned
    return {**rows[0],"direction":"neutral"} if rows[0]["score"]==0 and htf_direction=="neutral" else rows[0]
def _relationship(direction,htf_direction,candidate,top_down):
    if direction==htf_direction:return "aligned_continuation"
    core=all(candidate[key]["valid"] for key in ("sweep_event","displacement_event","mss_event","fvg_event"))
    if not core:return "invalid"
    frames=top_down.get("timeframes") or {}; h1=str((frames.get("H1") or {}).get("bias","neutral")); h4=str((frames.get("H4") or {}).get("bias","neutral")); expected="bullish" if direction=="buy" else "bearish"
    return "full_regime_reversal" if h1==expected and h4 in {expected,"neutral"} else "countertrend_reversal_candidate"
def _execution_top_down(top_down,direction):
    copied=deepcopy(top_down); copied["alignment"]={**(copied.get("alignment") or {}),"primary_direction":direction}; return copied
def _candidate_contract(candidate,relationship,target_event):
    events={key:candidate[key] for key in ("liquidity_event","sweep_event","displacement_event","mss_event","fvg_event","entry_event")}; rejection=[event.get("rejection_reason") for event in events.values() if event.get("rejection_reason")]
    invalidation_reason=candidate["sweep_event"].get("rejection_reason") if candidate["sweep_event"].get("rejection_reason")=="Accepted breakout is not an ICT sweep." else None
    return {"candidate_id":candidate["candidate_id"],"direction":candidate["direction"],"relationship":relationship,"score":candidate["score"],"liquidity":candidate["liquidity"],"sweep":candidate["sweep"],"displacement":candidate["displacement"],"mss":candidate["mss"],"fvg":candidate["fvg_event"].get("result"),"entry":candidate["entry_array"],"target":(target_event or {}).get("result"),"rejection_reasons":rejection,"state":"invalidated" if invalidation_reason else "forming" if candidate["score"]>=2 else "invalid","invalidation_time":candidate["sweep_event"].get("timestamp") if invalidation_reason else None,"invalidation_reason":invalidation_reason}


def _forming(frame):
    available,confirmed=frame["available_candles"],frame["candles"]
    if available.empty:return None
    confirmed_times=set(pd.to_datetime(confirmed.time,utc=True)) if not confirmed.empty else set(); rows=available.loc[~pd.to_datetime(available.time,utc=True).isin(confirmed_times)]
    return rows.tail(1) if not rows.empty else None
def _waiting(reason):return evidence_result(timeframe="M15",rejection_reason=reason,state="waiting")
def _empty_narrative():return {"direction":"neutral","alignment":"mixed","draw_on_liquidity":None,"draw_type":"","confidence":"low","evidence":[],"contradictions":[]}
def _state(event):return event.get("state","pass" if event.get("valid") else "waiting")
def _interaction(array,m5,time,direction="neutral",sweep=None,target=None):
    empty={"state":"waiting","timestamp":None,"evidence":[],"entry_array_touched":False,"currently_inside_entry_array":False,"current_location":"unavailable","reentry_required":False,"first_touch_time":None,"touch_count":0,"maximum_mitigation_depth":0.0,"time_since_departure":None,"original_target_reached":False,"approaching_entry_array":False,"freshness":"fresh","expired":False,"expiration_reason":None}
    if not array or m5 is None or m5.empty:return empty
    low,high=sorted((float(array["low"]),float(array["high"]))); width=max(high-low,1e-12); formed=pd.Timestamp(array["formed_at"]); formed=formed.tz_localize("UTC") if formed.tzinfo is None else formed.tz_convert("UTC"); times=pd.to_datetime(m5.time,utc=True); rows=m5.loc[times>formed].copy()
    if rows.empty:return empty
    overlap=(rows.low.astype(float)<=high)&(rows.high.astype(float)>=low); touched=rows.loc[overlap]; current=float(rows.iloc[-1].close); inside=low<=current<=high; location="inside_entry_array" if inside else "below_entry_array" if current<low else "above_entry_array"
    episodes=int((overlap & ~overlap.shift(fill_value=False)).sum()); depth=0.0
    if not touched.empty:
        depth=float(((touched.high.astype(float).clip(upper=high)-low)/width).max()) if direction=="sell" else float(((high-touched.low.astype(float).clip(lower=low))/width).max())
    last_touch_index=touched.index[-1] if not touched.empty else None; departed=rows.loc[rows.index>last_touch_index] if last_touch_index is not None else rows.iloc[0:0]; departure_time=pd.Timestamp(departed.iloc[0].time) if not departed.empty else None; now=pd.Timestamp(time); now=now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    target_price=_number((target or {}).get("price")); target_reached=bool(target_price is not None and ((rows.low.astype(float)<=target_price).any() if direction=="sell" else (rows.high.astype(float)>=target_price).any()))
    invalidation=_number((sweep or {}).get("sweep_extreme")); invalidated=bool(invalidation is not None and ((rows.high.astype(float)>=invalidation).any() if direction=="sell" else (rows.low.astype(float)<=invalidation).any()))
    freshness="fresh" if episodes==0 else "partially_mitigated" if episodes==1 and depth<.65 else "weakened" if episodes<=2 and depth<.85 else "expired"
    expired=invalidated or target_reached or freshness=="expired"; reason="Zone invalidated by price." if invalidated else "The original target was already reached." if target_reached else "Zone was excessively mitigated." if freshness=="expired" else None
    if expired:freshness="expired"
    distance=0 if inside else low-current if current<low else current-high
    return {"state":"pass" if inside else "waiting","timestamp":touched.iloc[0].time.isoformat() if not touched.empty else None,"evidence":["Entry array was previously touched."] if not touched.empty else [],"entry_array_touched":not touched.empty,"currently_inside_entry_array":inside,"current_location":location,"reentry_required":bool(not touched.empty and not inside and not expired),"first_touch_time":touched.iloc[0].time.isoformat() if not touched.empty else None,"touch_count":episodes,"maximum_mitigation_depth":round(min(max(depth,0),1),4),"time_since_departure":str(now-departure_time) if departure_time is not None else None,"original_target_reached":target_reached,"approaching_entry_array":bool(not inside and distance<=width*.25),"freshness":freshness,"expired":expired,"expiration_reason":reason}
def _setup_id(symbol,direction,liquidity,sweep,mss,array):return stable_id("ict-setup",{"symbol":symbol,"version":STRATEGY_VERSION,"direction":direction,"liquidity_id":(liquidity.get("opposing_pool") or {}).get("liquidity_id"),"sweep":sweep.get("sweep_time"),"mss":mss.get("break_time"),"fvg":array.get("fvg_id"),"low":array.get("low"),"high":array.get("high")})
def _lifecycle(s,e,x,valid):
    if e.get("rejection_reason")=="Accepted breakout is not an ICT sweep.":return "INVALIDATED"
    if valid:return "ENTRY_AVAILABLE"
    if s.get("liquidity_sweep")==s.get("displacement")==s.get("mss")=="pass" and s.get("fvg")=="fail":return "EXPIRED"
    mapping=[("htf_narrative","NO_ICT_CONTEXT"),("directional_draw","HTF_NARRATIVE_IDENTIFIED"),("opposing_liquidity","WAITING_FOR_OPPOSING_LIQUIDITY"),("liquidity_sweep","WAITING_FOR_SWEEP"),("displacement","WAITING_FOR_DISPLACEMENT"),("mss","WAITING_FOR_MSS"),("fvg","WAITING_FOR_FVG"),("price_in_entry_array","WAITING_FOR_RETURN"),("m5_confirmation","WAITING_FOR_M5_CLOSE")]
    for key,state in mapping:
        if s[key]!="pass":return "SWEEP_FORMING" if key=="liquidity_sweep" and s[key]=="forming" else "DISPLACEMENT_FORMING" if key=="displacement" and s[key]=="forming" else state
    return x.get("state","M5_CONFIRMED")
def _score(s,valid,data,interaction=None,reentry_valid=False):
    points={"htf_narrative":10,"directional_draw":5,"opposing_liquidity":10,"liquidity_sweep":10,"displacement":10,"mss":10,"fvg":10,"price_in_entry_array":5,"m5_confirmation":15,"stop_valid":5,"target_valid":5,"risk_reward":5}; raw=sum(value for key,value in points.items() if s[key]=="pass")+(5 if data=="valid" else 0)
    touched=bool((interaction or {}).get("entry_array_touched")); cap=100 if valid else 90 if s["m5_confirmation"]=="pass" else 80 if reentry_valid else 75 if touched else 70 if s["fvg"]=="pass" else 60 if s["displacement"]=="pass" else 50 if s["liquidity_sweep"]=="pass" else 35 if s["opposing_liquidity"]=="pass" else 25
    return min(raw,cap)
def _setup_score(sequence,data,narrative):
    weights={"directional_draw":10,"opposing_liquidity":10,"liquidity_sweep":15,"displacement":15,"mss":15,"fvg":15}
    narrative_points=15 if narrative.get("direction") in {"buy","sell"} else 0
    return min(100,narrative_points+sum(points for key,points in weights.items() if sequence.get(key)=="pass")+(5 if data=="valid" else 2 if data=="partial" else 0))
def _entry_timing(state):
    if state=="WAITING_FOR_RETURN":return "waiting"
    if state=="IN_ENTRY_ARRAY":return "in_zone"
    if state in {"M5_CONFIRMED","ENTRY_AVAILABLE"}:return "confirmed"
    if state=="ENTRY_EXTENDED":return "extended"
    if state in {"TOO_LATE","EXPIRED"}:return "too_late"
    return "waiting"
def _entry_timing_score(state):return {"WAITING_FOR_RETURN":35,"IN_ENTRY_ARRAY":60,"M5_TRIGGER_FORMING":70,"WAITING_FOR_M5_CLOSE":75,"M5_CONFIRMED":90,"ENTRY_AVAILABLE":100,"ENTRY_EXTENDED":20,"TOO_LATE":0}.get(state,10)
def _data_diagnostics(bundle):
    rows={}
    for timeframe in ("D1","H4","H1","M15","M5"):
        frame=(bundle.get("timeframes") or {}).get(timeframe) or {}; candles=frame.get("candles"); count=len(candles) if candles is not None else 0
        rows[timeframe]={"candle_count":count,"first_timestamp":candles.iloc[0].time.isoformat() if count else None,"last_timestamp":candles.iloc[-1].time.isoformat() if count else None,"last_completed_candle":frame.get("last_completed_time"),"timezone":frame.get("timezone","UTC"),"validation_status":"valid" if frame.get("valid") else "unavailable" if count==0 else "partial","failure_reason":None if frame.get("valid") else "No completed candles." if count==0 else "Fewer than 20 completed candles."}
    return rows
def _status(direction,state,m5,valid):
    if valid:return "READY TO BUY" if direction=="buy" else "READY TO SELL"
    if (m5 is None or m5.empty) and state in {"WAITING_FOR_RETURN","IN_ENTRY_ARRAY","WAITING_FOR_M5_CLOSE","M5_CONFIRMED"}:return "EXECUTION DATA UNAVAILABLE"
    if state in {"INVALIDATED"}:return "ICT SETUP INVALIDATED"
    if state in {"TOO_LATE","ENTRY_EXTENDED","EXPIRED"}:return "ICT SETUP MISSED"
    if state in {"SWEEP_FORMING","WAITING_FOR_DISPLACEMENT","DISPLACEMENT_FORMING","WAITING_FOR_MSS","WAITING_FOR_FVG","WAITING_FOR_RETURN","IN_ENTRY_ARRAY","WAITING_FOR_M5_CLOSE","M5_CONFIRMED"}:return "BUY ICT SETUP FORMING" if direction=="buy" else "SELL ICT SETUP FORMING"
    if direction in {"buy","sell"}:return "POTENTIAL BUY CONTEXT" if direction=="buy" else "POTENTIAL SELL CONTEXT"
    return "NO VALID ICT CONTEXT"
def _next(key,direction,execution,rr):
    side="sell-side" if direction=="buy" else "buy-side"; move="bullish" if direction=="buy" else "bearish"
    return {"htf_narrative":"Waiting for a clear higher-timeframe draw on liquidity.","directional_draw":"Waiting for a clear higher-timeframe draw on liquidity.","opposing_liquidity":"Waiting for a meaningful liquidity pool.","liquidity_sweep":f"Wait for {side} liquidity to be swept and reclaimed.","displacement":f"Wait for {move} displacement away from the sweep.","mss":f"Wait for a completed {move} market-structure shift.","fvg":"Wait for a valid displacement FVG.","price_in_entry_array":"Wait for price to return to the active FVG.","m5_confirmation":f"Wait for the M5 {move} confirmation candle to close.","stop_valid":"Wait for a structurally valid M5 stop.","target_valid":"Wait for a valid unswept opposing-liquidity target.","risk_reward":"The confirmation is too late for a clean entry."}.get(key,"Review the completed M5 plan.")
def _events(n,l,s,d,m,f,i,x,t):
    names=("htf_narrative","opposing_liquidity","liquidity_sweep","displacement","mss","fvg"); events={key:{"timestamp":event.get("timestamp"),"source_timeframe":event.get("source_timeframe"),"evidence":event.get("evidence",[]),"valid":event.get("valid",False)} for key,event in zip(names,(n,l,s,d,m,f))}; events["entry_array_touched"]={"timestamp":i.get("first_touch_time"),"source_timeframe":"M5","evidence":i.get("evidence",[]),"valid":i.get("entry_array_touched",False)}; events["price_in_entry_array"]={"timestamp":i.get("timestamp") if i.get("currently_inside_entry_array") else None,"source_timeframe":"M5","evidence":[],"valid":i.get("currently_inside_entry_array",False)}; events["m5_confirmation"]={"timestamp":(x.get("confirmed_signal") or {}).get("candle_time"),"source_timeframe":"M5","evidence":[]}; events["target_valid"]={"timestamp":t.get("timestamp"),"source_timeframe":t.get("source_timeframe"),"evidence":t.get("evidence",[])}; return events
def _overlays(n,l,s,m,a,x,valid):
    return {"directional_liquidity":l.get("directional_target"),"opposing_liquidity":l.get("opposing_pool"),"liquidity_sweep":{"price":s.get("sweep_extreme"),"time":s.get("sweep_time")} if s else None,"mss":{"price":m.get("level"),"time":m.get("break_time")} if m else None,"entry_array":a,"entry":{"price":x.get("entry")} if valid else None,"stop":{"price":x.get("stop")} if valid else None,"targets":x.get("targets",[]) if valid else [],"conditional_arrow":None}
def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
