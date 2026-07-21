"""Normalize one SMC result into the sole live/replay/paper product contract."""
from __future__ import annotations

import hashlib,json
from analysis.smc.smc_data_readiness import evaluate_data_readiness
from analysis.smc.smc_invariants import validate_trade_ready_invariants
from analysis.smc.smc_blockers import blocker_label,target_blocker_detail
from analysis.decision_views import build_market_analysis,build_trade_plan
from analysis.global_overlay_contract import normalize_global_decision

STAGE_MAP={"NO_CONTEXT":"NO_CONTEXT","DATA_LOADING":"DATA_LOADING","HTF_STRUCTURE_IDENTIFIED":"STRUCTURE_IDENTIFIED","DIRECTIONAL_CONTEXT":"DIRECTIONAL_CONTEXT","WAITING_FOR_TARGET":"WAITING_FOR_TARGET","STRUCTURAL_TARGET_IDENTIFIED":"STRUCTURAL_TARGET_IDENTIFIED","WAITING_FOR_BOUNDARY":"WAITING_FOR_BOUNDARY","WAITING_FOR_SWEEP":"WAITING_FOR_SWEEP","SWEEP_DETECTED":"SWEEP_DETECTED","WAITING_FOR_DISPLACEMENT":"WAITING_FOR_DISPLACEMENT","DISPLACEMENT_CONFIRMED":"DISPLACEMENT_CONFIRMED","MSS_CONFIRMED":"MSS_OR_BOS_CONFIRMED","PD_ARRAY_SELECTED":"ENTRY_ARRAY_SELECTED","WAITING_FOR_RETRACE":"WAITING_FOR_RETRACE","IN_ENTRY_AREA":"IN_ENTRY_AREA","WAITING_FOR_ENTRY_CONFIRMATION":"WAITING_FOR_CONFIRMATION","TRADE_READY":"TRADE_READY","PLAN REJECTED":"PLAN_REJECTED","TOO_LATE":"TOO_LATE","INVALIDATED":"INVALIDATED","FILLED":"FILLED","CLOSED":"CLOSED"}

def build_smc_product_contract(*,symbol,display_symbol,timeframe,analysis_time,family,candles_by_timeframe,result,live=True,source="deriv"):
    ownership=_ownership(result.get("ownership") or {});setup=dict(result.get("setup") or {});structure=result.get("structure") or {};scoring=result.get("scoring") or {};readiness=evaluate_data_readiness(candles_by_timeframe,analysis_time,source="deriv_public")
    stage=STAGE_MAP.get(setup.get("state"),setup.get("state") or "NO_CONTEXT");entry_array=setup.get("entry_array") or {};range_=result.get("dealing_range") or {};setup_type=setup.get("setup_type") or _setup_type(result);direction=setup.get("direction") or None
    if stage=="NO_CONTEXT" and setup_type:stage="WAITING_FOR_BOUNDARY" if "range" in setup_type and (range_.get("valid") or range_.get("active")) else "STRUCTURE_IDENTIFIED"
    if stage=="NO_CONTEXT":setup_type=None;direction=None;entry_array={};setup.update({"entry":None,"stop":None,"targets":[],"rr":None,"structural_target":{}})
    invariants=validate_trade_ready_invariants({**result,"setup":setup,"ownership":ownership,"readiness":readiness});ready=bool(stage=="TRADE_READY" and scoring.get("valid") and invariants.get("valid") and readiness["state"]=="ready" and not setup.get("research_only"))
    target_trace=result.get("target_trace") or setup.get("target_trace") or {};blocker_detail=target_blocker_detail(target_trace);blocker_code=_blocker(stage,readiness,scoring,invariants,result.get("gate_funnel") or {});blocker=blocker_label(blocker_code,blocker_detail);status=_status(stage,direction,readiness,ready,setup,scoring,invariants);candidate=stage!="NO_CONTEXT" and bool(setup_type);setup_id=(setup.get("setup_id") or _candidate_setup_id(symbol,ownership,setup_type,direction,setup,result)) if candidate else None
    normalized_setup={"setup_id":setup_id if candidate else None,"setup_type":setup_type,"family_adapter":ownership["family_adapter_id"],"direction":direction,"stage":stage,"status":status,"context_summary":f"H1 {structure.get('external_structure','unknown')} / M15 {structure.get('internal_structure','unknown')}","next_required_condition":setup.get("next_required_condition") or "Wait for completed structural evidence.","first_blocking_gate":blocker,"trade_ready":ready,"entry":setup.get("entry") if ready else None,"stop":setup.get("stop") if ready else None,"targets":setup.get("targets") if ready else [],"rr":setup.get("rr") if ready else None,"target_scope":setup.get("target_scope"),"target_timeframe":setup.get("target_timeframe"),"target_source":setup.get("target_source"),"invalidation":_invalidation(setup,direction),"entry_area":_zone(entry_array),"market_quality_score":scoring.get("quality_score"),"setup_quality_score":scoring.get("quality_score") if candidate else None,"quality_score":scoring.get("quality_score") if candidate else None,"quality_grade":scoring.get("quality_grade") if candidate else None,"essential_failures":scoring.get("essential_failures",[]),"research_only":bool(setup.get("research_only")),"recent_event":setup.get("recent_event"),"confirmation_levels":setup.get("confirmation_levels"),"setup_blocker":setup.get("setup_blocker"),"plan_blocker":setup.get("plan_blocker")}
    normalized_setup["jump_mode"]=setup.get("jump_mode")
    overlays=_overlays(ownership,normalized_setup,result,ready) if invariants.get("valid") else [];decision_id="smc-decision-"+hashlib.sha256(json.dumps([symbol,str(analysis_time),normalized_setup["setup_id"],stage,ownership["decision_owner_id"]],default=str,separators=(",",":")).encode()).hexdigest()[:24]
    diagnostics={"gate_funnel":result.get("gate_funnel") or {},"evaluated_candidates":result.get("evaluated_candidates") or [],"invariants":invariants,"essential_failures":scoring.get("essential_failures") or [],"shadow_candidate":result.get("shadow_candidate"),"target_blocker":blocker_detail,"target_trace":target_trace,"target_source_audit":result.get("target_source_audit") or setup.get("target_source_audit") or {},"history_depth_audit":result.get("history_depth_audit") or setup.get("history_depth_audit") or {}}
    smc={"swings":result.get("swings") or [],"structure_events":[x for x in (structure.get("last_bos"),structure.get("last_mss")) if x],"liquidity_references":result.get("liquidity") or [],"sweeps":[setup.get("sweep")] if (setup.get("sweep") or {}).get("qualified") else [],"breakouts":[setup.get("sweep")] if (setup.get("sweep") or {}).get("type") in {"accepted_breakout","failed_breakout"} else [],"displacements":result.get("displacements") or [],"fvgs":result.get("fvgs") or [],"order_blocks":result.get("order_blocks") or [],"dealing_range":range_}
    contract={"decision_id":decision_id,"meta":{"symbol":symbol,"display_symbol":display_symbol,"timeframe":timeframe,"analysis_time":str(analysis_time),"market_source":source,"market_type":"derived","family":family.get("family"),"variant":family.get("variant"),"live":bool(live and readiness["state"]=="ready"),"market_schedule":"24_7","analysis_clock":"UTC"},"ownership":ownership,"readiness":readiness,"market":{"external_structure":structure.get("external_structure"),"internal_structure":structure.get("internal_structure"),"alignment":structure.get("structure_alignment") or ("aligned" if structure.get("external_structure")==structure.get("internal_structure") else "conflicted"),"volatility_state":((result.get("market_profile") or {}).get("volatility_regime")),"event_state":_event_state(result.get("event") or {}),"current_price":((result.get("trade_chart") or {}).get("current_price"))},"decision":{"status":status,"direction":direction,"setup_type":setup_type,"stage":stage,"headline":status,"summary":normalized_setup["context_summary"],"next_action":_next_action(status,normalized_setup),"first_blocking_gate":blocker,"first_blocking_code":blocker_detail["code"] if blocker_detail else blocker_code,"trade_ready":ready},"setup":normalized_setup,"smc":smc,"diagnostics":diagnostics,"overlays":overlays,"previous_setup":result.get("previous_setup"),"paper_analysis_only":True}
    if setup.get("jump_mode")=="JUMP_POST_EVENT_SMC":
        contract["decision"].update(status="DEVELOPING",headline="JUMP POST-EVENT SMC",stage="WAITING_FOR_DISPLACEMENT",summary=normalized_setup["context_summary"],next_action=normalized_setup["next_required_condition"],first_blocking_gate=normalized_setup.get("setup_blocker") or blocker,trade_ready=False)
        contract["setup"].update(status="DEVELOPING",stage="WAITING_FOR_DISPLACEMENT",trade_ready=False,research_only=True)
    return normalize_global_decision(contract,mode="LIVE" if live else "REPLAY")

def _ownership(source):
    selected=source.get("selected_strategy_id") or "smc_auto";owner=source.get("decision_owner_id") or selected
    return {"selection_mode":source.get("selection_mode","auto"),"requested_model_id":source.get("requested_model") or source.get("requested_strategy_id") or "auto","selected_model_id":source.get("resolved_model") or selected,"selected_strategy_id":selected,"decision_owner_id":owner,"overlay_owner_id":source.get("overlay_owner_id") or owner,"family_adapter_id":source.get("adapter_id") or source.get("family_adapter_id"),"setup_type_id":source.get("setup_type_id"),"selection_reason":source.get("selection_reason",""),"model_corrected":bool(source.get("corrected")),"model_correction_reason":source.get("correction_reason")}

def _candidate_setup_id(symbol,ownership,setup_type,direction,setup,result):
    """Give every real developing candidate a stable owner-scoped identity."""
    area=setup.get("entry_array") or {}
    event=setup.get("recent_event") or result.get("event") or {}
    identity=[symbol,ownership.get("selected_strategy_id"),setup_type,direction,event.get("event_id") or event.get("id") or event.get("status"),area.get("origin_time") or area.get("created_time"),area.get("low"),area.get("high")]
    return "smc-setup-"+hashlib.sha256(json.dumps(identity,sort_keys=True,default=str).encode()).hexdigest()[:20]

def _status(stage,direction,readiness,ready,setup,scoring,invariants):
    if readiness["state"]=="loading":return "LOADING MARKET CONTEXT"
    if readiness["state"]=="stale":return "STALE MARKET DATA"
    if readiness["state"]!="ready":return "INSUFFICIENT HISTORY"
    if not invariants.get("valid",True):return invariants.get("corrected_status") or "STATE CONTRADICTION"
    if ready:return "READY TO BUY" if direction=="buy" else "READY TO SELL"
    if setup.get("event_risk"):return "EVENT RISK"
    if stage=="NO_CONTEXT":return "WAITING FOR STRUCTURE"
    if stage=="WAITING_FOR_BOUNDARY":return "WAITING FOR BOUNDARY"
    if stage=="WAITING_FOR_TARGET":return "WAITING FOR TARGET"
    if stage in {"STRUCTURE_IDENTIFIED","DIRECTIONAL_CONTEXT","STRUCTURAL_TARGET_IDENTIFIED"}:return "WAITING FOR LOCATION"
    if stage=="WAITING_FOR_SWEEP":return "WAITING FOR SWEEP"
    if stage in {"SWEEP_DETECTED","WAITING_FOR_DISPLACEMENT"}:return "WAITING FOR DISPLACEMENT"
    if stage in {"DISPLACEMENT_CONFIRMED","MSS_OR_BOS_CONFIRMED","ENTRY_ARRAY_SELECTED","WAITING_FOR_RETRACE","IN_ENTRY_AREA","WAITING_FOR_CONFIRMATION"}:return "WAITING FOR CONFIRMATION"
    if stage=="TOO_LATE":return "TOO LATE"
    if stage=="PLAN_REJECTED":return "PLAN REJECTED"
    return "NO MARKET OPPORTUNITY"

def _blocker(stage,readiness,scoring,invariants,funnel):
    if readiness["state"]=="stale":return "provider_reconnecting"
    if readiness["state"]!="ready":return "history"
    if not invariants.get("valid",True):return "state_contradiction"
    failures=scoring.get("essential_failures") or []
    return funnel.get("first_blocking_gate") or (failures[0] if failures else {"NO_CONTEXT":"external_structure","WAITING_FOR_BOUNDARY":"location","WAITING_FOR_TARGET":"target","WAITING_FOR_SWEEP":"sweep","WAITING_FOR_DISPLACEMENT":"displacement","WAITING_FOR_RETRACE":"location","WAITING_FOR_CONFIRMATION":"confirmation","TOO_LATE":"chase"}.get(stage,""))

def _zone(value):
    if value.get("low") is None or value.get("high") is None:return None
    return {"low":value.get("low"),"high":value.get("high"),"type":value.get("type") or "structural_area","origin_time":value.get("origin_time") or value.get("created_time")}

def _invalidation(setup,direction):
    area=setup.get("entry_array") or {};price=area.get("invalidation_boundary")
    if price is None and setup.get("stop") is not None:price=setup.get("stop")
    return {"price":price,"condition":("Completed close below protected structure" if direction=="buy" else "Completed close above protected structure" if direction=="sell" else "Structural context invalidates")}

def _setup_type(result):
    setup=result.get("setup") or {};array=setup.get("entry_array") or {};sweep=setup.get("sweep") or {}
    if sweep.get("type")=="accepted_breakout":return "breakout_and_retest"
    if sweep.get("type")=="sweep":return "liquidity_reversal"
    if array.get("type")=="range_boundary":return "range_boundary_reaction"
    return "structure_pullback" if setup.get("direction") else None

def _event_state(event):
    if not event:return "none"
    if event.get("qualified"):return "completed_event"
    return "monitoring"

def _next_action(status,setup):
    if status in {"LOADING MARKET CONTEXT","INSUFFICIENT HISTORY"}:return "No action while completed market history loads."
    if status=="STALE MARKET DATA":return "Live analysis is paused until Deriv reconnects. Cached completed candles remain visible."
    if status=="STATE CONTRADICTION":return "Do not act. Wait for the contradictory state to clear."
    if status.startswith("READY TO"):return "Use the locked paper-analysis plan; no order is submitted."
    if status=="TOO LATE":return "Do not chase. Wait for a fresh setup."
    return setup.get("next_required_condition") or "Wait for the next completed structural condition."

def _overlays(ownership,setup,result,ready):
    owner=ownership["overlay_owner_id"];setup_id=setup.get("setup_id");items=[]
    def add(kind,state,values,category,created=None,invalidated=None,setup_owner=None):
        if not values:return
        oid="overlay-"+hashlib.sha256(json.dumps([owner,setup_owner,kind,values],sort_keys=True,default=str).encode()).hexdigest()[:20];items.append({"overlay_id":oid,"owner_id":owner,"strategy_id":ownership.get("selected_strategy_id") or ownership.get("selected_model_id"),"setup_id":setup_owner,"type":kind,"state":state,"source":values.pop("source",kind),"creation_time":str(created) if created else None,"invalidation_time":str(invalidated) if invalidated else None,"visibility_category":category,**values})
    chart=result.get("trade_chart") or {};area=setup.get("entry_area");target=(result.get("setup") or {}).get("structural_target") or {};range_=(result.get("dealing_range") or {})
    if range_.get("active") or range_.get("valid"):
        add("structural_range","active",{"low":range_.get("low"),"high":range_.get("high"),"name":"Active External Range","priority":80,"source":"locked_dealing_range"},"market_structure",range_.get("created_time"))
        if range_.get("low") is not None and range_.get("high") is not None:add("equilibrium","active",{"price":(float(range_["low"])+float(range_["high"]))/2,"name":"Equilibrium","priority":60,"source":"locked_dealing_range_midpoint"},"context_levels",range_.get("created_time"))
    if target.get("price") is not None:add("structural_target","active",{"price":target.get("price"),"side":target.get("type") or target.get("side"),"name":"Potential Structural Objective","priority":70,"source":target.get("source_type") or "setup_structural_target"},"context_levels",target.get("created_time") or target.get("confirmed_at"),setup_owner=setup_id)
    if area:add("entry_area","active",{**area,"name":"DEVELOPING · NOT AN ENTRY","priority":90,"source":area.get("type") or "active_setup_area"},"trade_plan",area.get("origin_time"),setup_owner=setup_id)
    sweep=chart.get("confirmed_sweep")
    if sweep and sweep.get("reference_price") is not None:add("confirmed_sweep","confirmed",{"price":sweep.get("reference_price"),"direction":sweep.get("direction"),"name":"Completed Liquidity Sweep","priority":50,"source":"confirmed_sweep"},"market_structure",sweep.get("event_time"))
    swings=[row for row in (result.get("swings") or []) if isinstance(row,dict) and row.get("price") is not None]
    for side in ("high","low"):
        external=[row for row in swings if str(row.get("type") or row.get("side") or "").lower().endswith(side) and str(row.get("scope") or "").lower()=="external"]
        if external:
            row=external[-1];add(f"swing_{side}","confirmed",{"price":row["price"],"name":f"Primary External {side.title()}","priority":80,"timeframe":row.get("timeframe") or "H1","source":"confirmed_external_swing"},"market_structure",row.get("confirmation_time") or row.get("confirmed_at"))
    for row in swings:
        add("swing_high" if str(row.get("type") or row.get("side") or "").lower().endswith("high") else "swing_low","confirmed",{"price":row["price"],"name":"SMC Swing","priority":40,"timeframe":row.get("timeframe") or ("H1" if row.get("scope")=="external" else "M15"),"source":"confirmed_swing","metadata":{"advanced":True}},"advanced_smc",row.get("confirmation_time") or row.get("confirmed_at"))
    for event_type,event in (("bos",(result.get("structure") or {}).get("last_bos")),("mss",(result.get("structure") or {}).get("last_mss"))):
        event=event or {};price=event.get("broken_price") if event.get("broken_price") is not None else event.get("level") if event.get("level") is not None else event.get("price")
        if price is not None:add(event_type,"confirmed",{"price":price,"name":event_type.upper(),"priority":50,"timeframe":event.get("timeframe") or "M15","source":f"completed_{event_type}"},"market_structure",event.get("confirmed_at") or event.get("event_time"))
    references=[row for row in (result.get("liquidity") or []) if isinstance(row,dict) and row.get("price") is not None]
    current=chart.get("current_price")
    if current is not None:
        above=sorted((row for row in references if float(row["price"])>float(current)),key=lambda row:float(row["price"]))
        below=sorted((row for row in references if float(row["price"])<float(current)),key=lambda row:float(row["price"]),reverse=True)
        for row in [*(above[:1]),*(below[:1])]:add("liquidity_reference","active",{"price":row["price"],"name":"Nearest Structural Reference","priority":70,"timeframe":row.get("timeframe") or "M15","source":row.get("source") or row.get("type") or "liquidity_reference"},"context_levels",row.get("confirmed_at") or row.get("created_at"))
    for rows,kind in ((result.get("fvgs") or [],"fvg"),(result.get("order_blocks") or [],"order_block")):
        for row in rows:
            if not isinstance(row,dict):continue
            low=row.get("low");high=row.get("high")
            if low is None or high is None:continue
            add(kind,"confirmed",{"low":low,"high":high,"name":kind.replace("_"," ").upper(),"priority":20,"timeframe":row.get("timeframe") or "M15","source":row.get("source") or f"confirmed_{kind}","metadata":{"advanced":True}},"advanced_smc",row.get("created_time") or row.get("confirmed_at"))
    if ready:
        add("entry","confirmed",{"price":setup.get("entry"),"name":"Entry","priority":100,"source":"validated_trade_plan"},"trade_plan",setup_owner=setup_id);add("stop","confirmed",{"price":setup.get("stop"),"name":"Stop","priority":100,"source":"validated_trade_plan"},"trade_plan",setup_owner=setup_id)
        for target_row in setup.get("targets") or []:add("target","confirmed",{"price":target_row.get("price"),"name":target_row.get("name"),"risk_reward":target_row.get("risk_reward"),"priority":100,"source":target_row.get("source") or "validated_trade_plan"},"trade_plan",setup_owner=setup_id)
    return items
