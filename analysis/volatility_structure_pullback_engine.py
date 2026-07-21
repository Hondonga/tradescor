"""Focused H1/M15/M5 Volatility 75 Structure Pullback production engine."""
from __future__ import annotations
import hashlib,json
import pandas as pd

from analysis.smc.smc_swing_engine import confirmed_swings
from analysis.smc.smc_target_engine import evaluate_structural_targets
from analysis.smc.smc_invariants import validate_trade_ready_invariants
from analysis.global_overlay_contract import normalize_global_decision
from analysis.blocker_translations import translate_blocker,translate_next_requirement


DEFAULTS={"mode":"balanced","swing_prominence_atr":.15,"displacement_body_atr":.55,"displacement_range_atr":.75,"structure_break_buffer_atr":.02,"pullback_minimum":.18,"pullback_maximum":.78,"entry_chase_risk":1.0,"minimum_rr":1.5,"maximum_range_position":.75,"range_position_window":40,"pullback_zone_max_width_atr":8.0}


def evaluate_volatility_structure_pullback(*,symbol,candles_by_timeframe,tick_size=.01,analysis_time=None,profile=None,display_symbol=None,requested_model="smc_auto",source_timeframe="provided",overlay_mode="LIVE"):
    cfg={**DEFAULTS,**(profile or {})};frames={key:_completed(value,analysis_time) for key,value in candles_by_timeframe.items()};h1=frames.get("H1",pd.DataFrame());m15=frames.get("M15",pd.DataFrame());m5=frames.get("M5",pd.DataFrame());current=float(m5.iloc[-1].close) if len(m5) else None
    readiness=_readiness(h1,m15,m5);h1_model=_persistent_structure(h1,tick_size,cfg,scope="external");direction=h1_model.get("direction");m15_model=_pullback_location(m15,direction,h1_model,cfg);m5_model=_execution(m5,direction,m15_model,tick_size,cfg);entry_trace,stop_trace=_geometry_traces(direction,m5_model,current);setup_id=_setup_id(symbol,direction,h1_model,m5_model) if direction else None
    entry=m5_model.get("entry");stop=m5_model.get("stop");target_result={"tp1":None,"tp2":None,"target_trace":{"candidates_found":[],"candidates_rejected":[],"selected_target":None,"first_blocker":"TARGET_NOT_EVALUATED_BEFORE_ENTRY_STOP"},"target_source_audit":{},"history_depth_audit":{}}
    # Target evaluation is intentionally last.  No target engine call occurs
    # until completed confirmation has produced both executable entry and stop.
    if entry is not None and stop is not None:
        atr=float((m15.high-m15.low).tail(14).mean()) if len(m15) else tick_size;prominence=cfg["swing_prominence_atr"];swings=confirmed_swings(m5,atr=atr,tick_size=tick_size,scope="execution",minimum_prominence_atr=prominence)+confirmed_swings(m15,atr=atr,tick_size=tick_size,scope="internal",minimum_prominence_atr=prominence)+confirmed_swings(h1,atr=atr,tick_size=tick_size,left_strength=3,right_strength=3,scope="external",minimum_prominence_atr=prominence)
        target_result=evaluate_structural_targets(symbol=symbol,direction=direction,entry=entry,stop=stop,swings=swings,liquidity=[],candles_by_timeframe=frames,minimum_rr=cfg["minimum_rr"],setup_type="structure_pullback",tick_size=tick_size,owning_setup_id=setup_id,structural_leg_id=(m5_model.get("confirmation") or {}).get("structure_event_id"))
    tp1=target_result.get("tp1");tp2=target_result.get("tp2");rr=tp1.get("projected_rr") if tp1 else None;range_position=_range_position(m15,direction,current,cfg);ready=bool(readiness["ready"] and direction and m15_model.get("valid_location") and m5_model.get("confirmation") and entry is not None and stop is not None and tp1 and rr is not None and rr>=cfg["minimum_rr"] and m5_model.get("chase_valid") and range_position["valid"])
    stage=_stage(readiness,direction,m15_model,m5_model,entry,stop,tp1,rr,cfg)
    if stage in {"READY_TO_BUY","READY_TO_SELL"} and not range_position["valid"]:stage="AT_RANGE_EXTREME"
    targets=[]
    if ready:
        targets=[{"name":"TP1","price":tp1["price"],"risk_reward":rr,"target_id":tp1.get("target_id"),"source":tp1.get("source_type"),"timeframe":tp1.get("timeframe"),"scope":tp1.get("scope"),"confirmed_at":tp1.get("confirmed_at")}]
        if tp2:targets.append({"name":"TP2","price":tp2["price"],"risk_reward":tp2.get("projected_rr"),"target_id":tp2.get("target_id"),"source":tp2.get("source_type"),"timeframe":tp2.get("timeframe"),"scope":tp2.get("scope"),"confirmed_at":tp2.get("confirmed_at")})
    owner="volatility_structure_pullback";m5_status=_m5_status(m5_model,ready);setup={"setup_id":setup_id,"setup_type":"structure_pullback","strategy_id":owner,"family_adapter":"volatility_structure_pullback_engine","direction":"buy" if direction=="bullish" else "sell" if direction=="bearish" else None,"state":"TRADE_READY" if ready else stage,"stage":"TRADE_READY" if ready else stage,"status":"TRADE_READY" if ready else stage,"context_summary":f"H1 {(direction or 'insufficient').title()} · M15 {m15_model.get('condition','insufficient').title()}","trade_ready":ready,"htf_structure":direction,"recent_condition":h1_model.get("recent_condition"),"pullback":m15_model,"m5_confirmation_status":m5_status,"completed_confirmation":m5_model.get("confirmation"),"bos":m5_model.get("confirmation"),"entry_array":m5_model.get("entry_zone") or {},"entry":entry if ready else None,"stop":stop if ready else None,"targets":targets,"rr":rr if ready else None,"target_source":(tp1 or {}).get("source_type"),"target_timeframe":(tp1 or {}).get("timeframe"),"invalidation":{"price":stop,"condition":("Below the protected M5 structural low" if direction=="bullish" else "Above the protected M5 structural high") if stop is not None else "Pending M5 structure"},"projected_entry":entry,"projected_stop":stop,"projected_target":tp1,"projected_rr":rr,"structural_target":tp1 or {},"entry_trace":entry_trace,"stop_trace":stop_trace,"chase_valid":m5_model.get("chase_valid",True),"range_position":range_position,"research_only":False,"event_risk":None,"stale":False,"next_required_condition":_next(stage,direction,m5_model,target_result),"target_trace":target_result["target_trace"],"target_source_audit":target_result.get("target_source_audit",{}),"history_depth_audit":target_result.get("history_depth_audit",{})}
    public_status=("READY TO BUY" if direction=="bullish" else "READY TO SELL") if ready else _status(stage,direction);ownership={"selection_mode":"auto" if str(requested_model).lower() in {"auto","smc","smc_auto"} else "manual","requested_model":requested_model,"selected_model":owner,"requested_model_id":requested_model,"selected_model_id":owner,"selected_strategy_id":owner,"decision_owner_id":owner,"overlay_owner_id":owner,"family_adapter_id":"volatility_structure_pullback_engine","production_reachable":True,"selection_reason":"Only proven production strategy enabled during focused validation."}
    invariant_source={"setup":setup,"decision":{"status":public_status,"trade_ready":ready,"direction":setup["direction"]},"ownership":ownership,"readiness":{"state":"ready" if readiness["ready"] else "insufficient"}};invariants=validate_trade_ready_invariants(invariant_source);ready=ready and invariants["valid"]
    setup["entry_area"]=m5_model.get("entry_zone")
    if not ready and setup["state"]=="TRADE_READY":setup.update(state="PLAN_VALIDATION",stage="PLAN_VALIDATION",trade_ready=False,entry=None,stop=None,targets=[],rr=None);public_status="PLAN VALIDATION"
    decision_id="vsp-"+hashlib.sha256(json.dumps([symbol,str(analysis_time),setup_id,stage,entry,stop,(tp1 or {}).get("price")],default=str).encode()).hexdigest()[:24]
    overlays=_overlays(owner,setup,current,m5_model,h1_model,m15_model,tp1,tp2,ready,analysis_time)
    lifecycle=[]
    if direction:lifecycle.append("H1_DIRECTIONAL")
    if m15_model.get("pullback"):lifecycle.append("M15_PULLBACK")
    if m15_model.get("valid_location"):lifecycle.append("VALID_LOCATION")
    if m5_model.get("confirmation"):lifecycle.extend(["M5_DISPLACEMENT","M5_STRUCTURE_BREAK"])
    if entry is not None:lifecycle.append("ENTRY_SELECTED")
    if stop is not None:lifecycle.append("STOP_SELECTED")
    if tp1:lifecycle.append("TARGET_SELECTED")
    if rr is not None and rr>=cfg["minimum_rr"]:lifecycle.append("RR_VALIDATED")
    if ready:lifecycle.append("TRADE_READY")
    external_display=direction or ("range" if readiness["timeframes"]["H1"]["passed"] else "insufficient");trade_plan={"available":ready,"status":public_status if ready else "UNAVAILABLE","entry":setup.get("entry"),"stop":setup.get("stop"),"targets":setup.get("targets") or [],"reason":None if ready else "Unavailable until all production geometry passes."}
    product={"decision_id":decision_id,"meta":{"symbol":symbol,"display_symbol":display_symbol or symbol,"timeframe":"M5","source_timeframe":source_timeframe,"analysis_time":str(analysis_time),"emitted_time":str(analysis_time),"market_source":"deriv","market_type":"derived","family":"VOLATILITY","live":readiness["ready"],"market_schedule":"24_7","analysis_clock":"UTC","analysis_profile":cfg["mode"]},"ownership":ownership,"production_status":{"strategy_id":owner,"production_supported":True,"fixture_buy_reachable":True,"fixture_sell_reachable":True,"historically_observed":False,"live_observed":False,"auto_eligible":True},"readiness":{"state":"ready" if readiness["ready"] else "insufficient","timeframes":readiness["timeframes"]},"market":{"external_structure":external_display,"internal_structure":m15_model.get("condition","insufficient"),"recent_condition":h1_model.get("recent_condition"),"current_price":current},"decision":{"status":public_status,"direction":setup["direction"],"market_bias":direction or "neutral","setup_type":"structure_pullback","stage":setup["stage"],"headline":public_status,"summary":f"H1 {external_display.title()} · M15 {m15_model.get('condition','insufficient').title()}","next_action":setup["next_required_condition"],"first_blocking_gate":translate_blocker(_blocker(stage)),"trade_ready":ready},"trade_plan":trade_plan,"setup":setup,"diagnostics":{"invariants":invariants,"entry_trace":entry_trace,"stop_trace":stop_trace,"target_trace":target_result["target_trace"],"blocker_code":_blocker(stage),"lifecycle_order":["DATA_LOADING","NO_DIRECTIONAL_CONTEXT","WAITING_FOR_PULLBACK","WAITING_FOR_LOCATION","WAITING_FOR_DISPLACEMENT","WAITING_FOR_M5_BREAK","WAITING_FOR_ENTRY","PLAN_VALIDATION","READY_TO_BUY","READY_TO_SELL","TOO_LATE","INVALIDATED"],"lifecycle_reached":lifecycle,"target_evaluated_after_entry_stop":entry is not None and stop is not None if target_result["target_trace"].get("first_blocker")!="TARGET_NOT_EVALUATED_BEFORE_ENTRY_STOP" else False,"h1":h1_model,"m15":m15_model,"m5":m5_model,"profile":cfg},"overlays":overlays,"previous_setup":None,"paper_analysis_only":True,"focused_production":True}
    return normalize_global_decision(product,instrument_metadata={"tick_size":tick_size},mode=overlay_mode)


def _persistent_structure(rows,tick,cfg,scope):
    if len(rows)<12:return {"direction":None,"recent_condition":"insufficient"}
    atr=float((rows.high-rows.low).tail(14).mean());swings=sorted(confirmed_swings(rows,atr=atr,tick_size=tick,left_strength=2,right_strength=2,scope=scope,minimum_prominence_atr=cfg["swing_prominence_atr"]),key=lambda x:pd.Timestamp(x["confirmation_time"]));events=[];cursor=0;highs=[];lows=[]
    for index,row in rows.iterrows():
        time=pd.Timestamp(row.time)
        while cursor<len(swings) and pd.Timestamp(swings[cursor]["confirmation_time"])<time:
            (highs if swings[cursor]["type"]=="high" else lows).append(swings[cursor]);cursor+=1
        body=abs(float(row.close-row.open));span=max(float(row.high-row.low),1e-12);passed=body/max(atr,1e-12)>=cfg["displacement_body_atr"] and span/max(atr,1e-12)>=cfg["displacement_range_atr"]
        if not passed:continue
        if highs and float(row.close)>float(highs[-1]["price"])+atr*cfg["structure_break_buffer_atr"]:events.append({"direction":"bullish","confirmed_at":str(row.time),"broken_swing":highs[-1],"protected":lows[-1] if lows else None})
        if lows and float(row.close)<float(lows[-1]["price"])-atr*cfg["structure_break_buffer_atr"]:events.append({"direction":"bearish","confirmed_at":str(row.time),"broken_swing":lows[-1],"protected":highs[-1] if highs else None})
    event=events[-1] if events else None;direction=event.get("direction") if event else None;recent=rows.tail(6);change=float(recent.iloc[-1].close-recent.iloc[0].close);span=float(recent.high.max()-recent.low.min());condition="consolidating" if abs(change)<span*.2 else "pulling_back" if direction=="bullish" and change<0 or direction=="bearish" and change>0 else "impulsing"
    protected=(event or {}).get("protected");invalid=bool(protected and (float(rows.iloc[-1].close)<protected["price"] if direction=="bullish" else float(rows.iloc[-1].close)>protected["price"]));return {"direction":None if invalid else direction,"recent_condition":"invalidating" if invalid else condition,"last_break":event,"protected_structure":protected,"events":events}


def _pullback_location(rows,direction,h1,cfg):
    if not direction or len(rows)<12:return {"condition":"insufficient","pullback":False,"valid_location":False}
    recent=rows.tail(32);low=float(recent.low.min());high=float(recent.high.max());current=float(rows.iloc[-1].close);depth=(high-current)/max(high-low,1e-12) if direction=="bullish" else (current-low)/max(high-low,1e-12);pullback=depth>=cfg["pullback_minimum"];valid=bool(pullback and depth<=cfg["pullback_maximum"])
    # Display-only geometry gate: the drawn M15 pullback area must stay within
    # an ATR-relative width. This never affects `pullback`/`valid_location`
    # (the setup-progression gate above), only whether the zone is drawable.
    atr=float((rows.high-rows.low).tail(14).mean()) if len(rows) else 0.0;zone_width_atr=(high-low)/atr if atr>0 else None;zone_valid=bool(zone_width_atr is not None and zone_width_atr<=cfg["pullback_zone_max_width_atr"])
    return {"condition":"pullback" if pullback else "impulsing","pullback":pullback,"valid_location":valid,"depth":depth,"range_low":low,"range_high":high,"current":current,"zone_width_atr":zone_width_atr,"zone_valid":zone_valid,"zone_max_width_atr":cfg["pullback_zone_max_width_atr"]}


def _execution(rows,direction,location,tick,cfg):
    if not direction or not location.get("valid_location") or len(rows)<20:return {"confirmation":None,"entry":None,"stop":None,"entry_zone":None,"chase_valid":True,"confirmation_level":None}
    atr=float((rows.high-rows.low).tail(14).mean());swings=sorted(confirmed_swings(rows,atr=atr,tick_size=tick,scope="execution",minimum_prominence_atr=cfg["swing_prominence_atr"]),key=lambda x:pd.Timestamp(x["confirmation_time"]));events=[];cursor=0;wanted=[];protected=[];displacement_seen=False
    for position,(_,row) in enumerate(rows.iterrows()):
        time=pd.Timestamp(row.time)
        while cursor<len(swings) and pd.Timestamp(swings[cursor]["confirmation_time"])<time:
            item=swings[cursor];(wanted if item["type"]==("high" if direction=="bullish" else "low") else protected).append(item);cursor+=1
        if not wanted or not protected:continue
        body=float(row.close-row.open);span=max(float(row.high-row.low),1e-12);disp=(body>0 if direction=="bullish" else body<0) and abs(body)/max(atr,1e-12)>=cfg["displacement_body_atr"] and span/max(atr,1e-12)>=cfg["displacement_range_atr"];broken=float(row.close)>wanted[-1]["price"]+atr*cfg["structure_break_buffer_atr"] if direction=="bullish" else float(row.close)<wanted[-1]["price"]-atr*cfg["structure_break_buffer_atr"]
        displacement_seen=displacement_seen or disp
        if disp and broken:events.append({"structure_event_id":"m5-break-"+hashlib.sha256(str([row.time,direction,wanted[-1]["swing_id"]]).encode()).hexdigest()[:16],"direction":direction,"confirmed_at":str(row.time),"completed":True,"broken_price":wanted[-1]["price"],"protected":protected[-1],"candle":{"time":str(row.time),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close)},"index":position})
    event=events[-1] if events else None;level=(next((x for x in reversed(swings) if x["type"]==("high" if direction=="bullish" else "low")),None) or {}).get("price")
    if not event:return {"confirmation":None,"entry":None,"stop":None,"entry_zone":None,"chase_valid":True,"confirmation_level":level,"displacement_seen":displacement_seen}
    candle=event["candle"];zone_low=min(candle["open"],candle["close"]);zone_high=max(candle["open"],candle["close"]);after=rows.iloc[event["index"]+1:];retrace=next((row for _,row in after.iterrows() if float(row.low)<=zone_high and float(row.high)>=zone_low),None)
    if retrace is None:return {"confirmation":event,"entry":None,"stop":None,"entry_zone":{"low":zone_low,"high":zone_high},"chase_valid":True,"confirmation_level":event["broken_price"]}
    entry=(zone_low+zone_high)/2;protected=float(event["protected"]["price"]);buffer=max(tick*2,atr*.05);stop=protected-buffer if direction=="bullish" else protected+buffer;post_confirmation=rows.iloc[event["index"]+1:];invalidated=bool((post_confirmation.low.astype(float)<=stop).any()) if direction=="bullish" else bool((post_confirmation.high.astype(float)>=stop).any())
    if invalidated:return {"confirmation":event,"entry":None,"stop":None,"entry_zone":{"low":zone_low,"high":zone_high,"type":"m5_displacement_retrace"},"chase_valid":False,"confirmation_level":event["broken_price"],"retrace_time":str(retrace.time),"entry_event_invalidated":True}
    risk=abs(entry-stop);current=float(rows.iloc[-1].close);chase=abs(current-entry)<=risk*cfg["entry_chase_risk"]
    return {"confirmation":event,"entry":entry,"stop":stop,"entry_zone":{"low":zone_low,"high":zone_high,"type":"m5_displacement_retrace"},"chase_valid":chase,"confirmation_level":event["broken_price"],"retrace_time":str(retrace.time)}


def _readiness(h1,m15,m5):
    counts={"H1":len(h1),"M15":len(m15),"M5":len(m5)};required={"H1":20,"M15":40,"M5":60};return {"ready":all(counts[x]>=required[x] for x in required),"timeframes":{x:{"available":counts[x],"required":required[x],"passed":counts[x]>=required[x]} for x in required}}

def _m5_status(execution,ready):
    if ready:return "Passed"
    if execution.get("confirmation") and execution.get("entry") is None:return "Waiting for retracement"
    if execution.get("displacement_seen"):return "Waiting for structure break"
    return "Waiting for displacement"

def _geometry_traces(direction,execution,current):
    side="buy" if direction=="bullish" else "sell" if direction=="bearish" else None;event=execution.get("confirmation");zone=execution.get("entry_zone");entry=execution.get("entry");stop=execution.get("stop")
    entry_trace={"direction":side,"confirmation_time":(event or {}).get("confirmed_at"),"candidate_sources":[],"selected_entry":entry,"rejections":[],"first_blocker":None}
    if not event:entry_trace["first_blocker"]="NO_CONFIRMATION"
    elif execution.get("entry_event_invalidated"):entry_trace["first_blocker"]="ENTRY_EVENT_INVALIDATED"
    elif not zone:entry_trace["first_blocker"]="NO_RETRACE_AREA"
    else:
        candidate={"price":(float(zone["low"])+float(zone["high"]))/2,"source":"m5_displacement_retrace","timeframe":"M5","creation_time":event.get("confirmed_at"),"confirmation_time":event.get("confirmed_at"),"selected_time":execution.get("retrace_time"),"current_price_when_emitted":current,"distance_from_current_price":abs(float(current)-float(entry)) if current is not None and entry is not None else None,"already_passed":not execution.get("chase_valid",True),"chase_distance":abs(float(current)-float(entry)) if current is not None and entry is not None else None,"rejection_code":None}
        if entry is None:candidate["rejection_code"]="NO_RETRACE_AREA";entry_trace["rejections"].append(candidate);entry_trace["first_blocker"]="NO_RETRACE_AREA"
        elif candidate["already_passed"]:candidate["rejection_code"]="ENTRY_ALREADY_PASSED";entry_trace["rejections"].append(candidate);entry_trace["first_blocker"]="ENTRY_ALREADY_PASSED"
        entry_trace["candidate_sources"].append(candidate)
    stop_trace={"candidate_sources":[],"selected_stop":stop,"rejections":[],"first_blocker":None}
    if entry is None:stop_trace["first_blocker"]="ENTRY_OR_STOP_MISSING"
    elif not event or not event.get("protected"):stop_trace["first_blocker"]="STRUCTURAL_INVALIDATION_UNAVAILABLE"
    else:
        protected=event["protected"];candidate={"price":stop,"source":"protected_m5_swing","timeframe":"M5","creation_time":protected.get("candle_time"),"confirmation_time":protected.get("confirmation_time"),"intended_invalidation":protected.get("price"),"rejection_code":None}
        valid=stop is not None and (float(stop)<float(entry) if direction=="bullish" else float(stop)>float(entry))
        if not valid:candidate["rejection_code"]="STOP_WRONG_SIDE";stop_trace["rejections"].append(candidate);stop_trace["first_blocker"]="STOP_WRONG_SIDE"
        stop_trace["candidate_sources"].append(candidate)
    return entry_trace,stop_trace
def _range_position(m15,direction,current,cfg):
    """Position of price inside the recent M15 dealing range (0 = low, 1 = high).

    Blocks trade-ready when a buy sits above ``maximum_range_position`` or a
    sell sits below its mirror. Evidence (R_75, 90-day dataset): hostile-extreme
    entries lost in both directions (buys at top quartile, sells at bottom).
    """
    base={"position":None,"range_low":None,"range_high":None,"maximum_hostile_position":cfg.get("maximum_range_position",.75),"valid":True,"state":"NOT_EVALUATED"}
    if direction not in {"bullish","bearish"} or current is None or m15 is None or not len(m15):return base
    rows=m15.tail(int(cfg.get("range_position_window",40)))
    if len(rows)<10:return base
    range_low=float(rows.low.min());range_high=float(rows.high.max());width=range_high-range_low
    if width<=0:return base
    position=max(0.0,min(1.0,(float(current)-range_low)/width));maximum=float(cfg.get("maximum_range_position",.75))
    hostile=(direction=="bullish" and position>maximum) or (direction=="bearish" and position<1-maximum)
    return {**base,"position":position,"range_low":range_low,"range_high":range_high,"valid":not hostile,"state":"AT_HOSTILE_EXTREME" if hostile else "ACCEPTABLE_LOCATION"}

def _stage(r,d,m15,m5,entry,stop,tp1,rr,cfg):
    if not r["ready"]:return "DATA_LOADING"
    if not d:return "NO_DIRECTIONAL_CONTEXT"
    if not m15.get("pullback"):return "WAITING_FOR_PULLBACK"
    if not m15.get("valid_location"):return "WAITING_FOR_LOCATION"
    if not m5.get("confirmation"):return "WAITING_FOR_DISPLACEMENT"
    if entry is None:return "WAITING_FOR_ENTRY"
    if not m5.get("chase_valid"):return "TOO_LATE"
    if stop is None or tp1 is None or rr is None or rr<cfg["minimum_rr"]:return "PLAN_VALIDATION"
    return "READY_TO_BUY" if d=="bullish" else "READY_TO_SELL"
def _status(stage,d):return {"DATA_LOADING":"LOADING MARKET CONTEXT","NO_DIRECTIONAL_CONTEXT":"NO DIRECTIONAL CONTEXT","WAITING_FOR_PULLBACK":"WAITING FOR PULLBACK","WAITING_FOR_LOCATION":"WAITING FOR LOCATION","WAITING_FOR_DISPLACEMENT":"WAITING FOR BULLISH M5 DISPLACEMENT" if d=="bullish" else "WAITING FOR BEARISH M5 DISPLACEMENT","WAITING_FOR_ENTRY":"WAITING FOR ENTRY RETRACEMENT","PLAN_VALIDATION":"PLAN VALIDATION","TOO_LATE":"TOO LATE","AT_RANGE_EXTREME":"AT RANGE EXTREME"}.get(stage,stage.replace("_"," "))
def _blocker(stage):return {"DATA_LOADING":"history","NO_DIRECTIONAL_CONTEXT":"h1_structure","WAITING_FOR_PULLBACK":"m15_pullback","WAITING_FOR_LOCATION":"m15_location","WAITING_FOR_DISPLACEMENT":"m5_displacement_break","WAITING_FOR_ENTRY":"m5_retrace","PLAN_VALIDATION":"plan_geometry","TOO_LATE":"chase","AT_RANGE_EXTREME":"m15_range_position"}.get(stage)
def _next(stage,d,m5,target):
    side="bullish" if d=="bullish" else "bearish";trade_side="buy" if d=="bullish" else "sell";return {"DATA_LOADING":"Wait for completed M1-derived H1, M15 and M5 history.","NO_DIRECTIONAL_CONTEXT":"Wait for a completed H1 directional structure break.","WAITING_FOR_PULLBACK":f"Wait for an M15 pullback against {side} H1 structure before evaluating a {trade_side} location.","WAITING_FOR_LOCATION":f"Wait for the M15 pullback to enter the valid {trade_side} location.","WAITING_FOR_DISPLACEMENT":f"Wait for a completed {side} displacement and close {'above' if d=='bullish' else 'below'} the latest M5 internal swing {'high' if d=='bullish' else 'low'}.","WAITING_FOR_ENTRY":"Wait for the M5 retracement after the completed structure break.","AT_RANGE_EXTREME":f"Price is at the hostile extreme of the M15 dealing range for a {trade_side}. Wait for a healthier location instead of chasing.","PLAN_VALIDATION":translate_next_requirement((target.get("target_trace") or {}).get("first_blocker"),direction=d),"READY_TO_BUY":"Paper-analysis buy plan is complete.","READY_TO_SELL":"Paper-analysis sell plan is complete."}.get(stage,"Wait for the next completed structural condition.")
def _setup_id(symbol,d,h1,m5):return "vsp-setup-"+hashlib.sha256(json.dumps([symbol,d,((h1.get("last_break") or {}).get("confirmed_at")),((m5.get("confirmation") or {}).get("confirmed_at"))],default=str).encode()).hexdigest()[:20]
def _overlays(owner,setup,current,m5,h1,m15,tp1,tp2,ready,analysis_time):
    rows=[];setup_id=setup.get("setup_id");event=m5.get("confirmation") or {};created=event.get("confirmed_at") or str(analysis_time)
    def add(key,kind,price,name,state="conditional",category="trade_plan",created_at=None,setup_owner=None,priority=None):
        if price is not None:
            row={"overlay_id":f"{owner}-{setup_owner or 'context'}-{key}","owner_id":owner,"setup_id":setup_owner,"visibility_category":category,"type":kind,"state":state,"price":price,"name":name,"created_at":created_at or created,"actionable_at_decision_time":True}
            if priority is not None:row["priority"]=priority
            rows.append(row)
    # current_price is emitted once, mode-aware, by global_overlay_contract's
    # _required_rows() — a strategy-level row here would shadow it in dedup
    # and always show a static (often wrong-for-mode) label.
    broken=((h1.get("last_break") or {}).get("broken_swing") or {});add("h1-context","h1_context",broken.get("price"),f"H1 {str(h1.get('direction') or '').title()} Context","active","market_structure",(h1.get("last_break") or {}).get("confirmed_at"))
    if m15.get("valid_location") and m15.get("zone_valid",True):rows.append({"overlay_id":f"{owner}-{setup_id}-m15-pullback","owner_id":owner,"setup_id":setup_id,"visibility_category":"context_levels","type":"m15_pullback_area","state":"active","low":m15.get("range_low"),"high":m15.get("range_high"),"name":"M15 Pullback Area","created_at":created,"actionable_at_decision_time":True})
    zone=m5.get("entry_zone")
    if zone:rows.append({"overlay_id":f"{owner}-{setup_id}-entry-zone","owner_id":owner,"setup_id":setup_id,"visibility_category":"trade_plan","type":"entry_area","state":"active","low":zone["low"],"high":zone["high"],"name":"M5 Retracement Entry","created_at":created,"actionable_at_decision_time":True})
    # Completed M5 Displacement stays default-visible only while it is the
    # freshly-completed gate (WAITING_FOR_ENTRY); afterward it recedes to its
    # normal Advanced SMC priority tier so the chart doesn't stay cluttered.
    candle=event.get("candle") or {};add("displacement","m5_displacement",candle.get("close"),"Completed M5 Displacement","active","market_structure",event.get("confirmed_at"),priority=80 if setup.get("stage")=="WAITING_FOR_ENTRY" else None);add("confirmation","confirmation",m5.get("confirmation_level"),"M5 Structure Break","active" if event else "conditional",setup_owner=setup_id)
    if ready:add("entry","entry",setup.get("entry"),"Entry","active",setup_owner=setup_id)
    # A single "stop" row carries both the trade-ready stop and the developing
    # idea-invalidation price (they are the same value pre-ready); a second
    # "invalidation" row at the identical price only produced a meaningless
    # clustered duplicate.
    add("stop","stop",setup.get("stop") if ready else setup.get("projected_stop"),"Stop Loss" if ready else "Invalidation","active" if ready else "conditional",setup_owner=setup_id)
    add("tp1","target",(tp1 or {}).get("price"),"TP1" if ready else "Potential TP1","active" if ready else "conditional",created_at=(tp1 or {}).get("confirmed_at"),setup_owner=setup_id)
    add("tp2","target",(tp2 or {}).get("price"),"TP2" if ready else "Potential TP2","active" if ready else "conditional",created_at=(tp2 or {}).get("confirmed_at"),setup_owner=setup_id)
    return rows
def _completed(rows,at):
    frame=rows.copy() if rows is not None else pd.DataFrame();frame=frame[frame.complete.astype(bool)] if "complete" in frame else frame
    if at is not None and "time" in frame:frame=frame[pd.to_datetime(frame.time,utc=True)<=pd.Timestamp(at)]
    return frame.sort_values("time").reset_index(drop=True) if "time" in frame else frame.reset_index(drop=True)
