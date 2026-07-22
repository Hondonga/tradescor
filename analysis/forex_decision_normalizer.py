"""Forex-only ICT projection and cross-field safety invariants."""
from __future__ import annotations
import pandas as pd
from analysis.forex_overlay_contract import build_forex_overlay_contract

TERMINAL_STATES={"EXPIRED","INVALIDATED","TOO_LATE"}
COUNTERTREND_RELATIONSHIPS={"countertrend_reversal_candidate","full_regime_reversal"}
STATE_MAP={"NO_ICT_CONTEXT":"NO_CONTEXT","HTF_NARRATIVE_IDENTIFIED":"HTF_BIAS_IDENTIFIED","WAITING_FOR_OPPOSING_LIQUIDITY":"WAITING_FOR_LIQUIDITY","WAITING_FOR_SWEEP":"WAITING_FOR_LIQUIDITY","SWEEP_FORMING":"WAITING_FOR_LIQUIDITY","WAITING_FOR_MSS":"WAITING_FOR_DISPLACEMENT","WAITING_FOR_FVG":"MSS_CONFIRMED","WAITING_FOR_RETURN":"WAITING_FOR_RETRACE","WAITING_FOR_M5_CLOSE":"WAITING_FOR_M5_CONFIRMATION","ENTRY_AVAILABLE":"TRADE_READY","M5_CONFIRMED":"TRADE_READY","ENTRY_EXTENDED":"TOO_LATE"}

def normalize_forex_fields(legacy):
    ict=legacy.get("ict_model") or ((legacy.get("research_shadow") or {}).get("ict_2022_v2")) or {};setup=ict.get("setup") or {};narrative=ict.get("narrative") or {};execution=ict.get("execution") or {};output=ict.get("user_output") or {};array=setup.get("entry_array") or {};raw_state=str(setup.get("state") or execution.get("state") or "NO_CONTEXT").upper();state=STATE_MAP.get(raw_state,raw_state)
    active=bool(setup.get("setup_id")) and state not in TERMINAL_STATES|{"NO_CONTEXT"}
    # Phase 4 §18 -- displacement/structure_confirmation (MSS) were computed
    # by the strict-ICT engine all along but never surfaced past
    # liquidity_event (the sweep); the Workspace decision rail's ACTIVE
    # SETUP section needs them to show Forex-specific setup detail.
    return {"htf_bias":narrative.get("direction") or "neutral","market_structure":narrative.get("structure") or narrative.get("alignment") or "","session":((legacy.get("filters") or {}).get("session") or {}).get("name") or "","liquidity_event":setup.get("sweep"),"displacement":setup.get("displacement"),"structure_confirmation":setup.get("mss"),"dealing_range":narrative.get("dealing_range"),"entry_zone":{"low":array.get("low"),"high":array.get("high"),"type":array.get("type"),"timeframe":"M15"} if active and array.get("low") is not None and array.get("high") is not None else None,"m5_confirmation":execution.get("confirmed_at") if active and state=="TRADE_READY" else None,"scenario_state":state,"direction":setup.get("direction") if active else None,"trade_plan":{"entry":execution.get("entry"),"stop":execution.get("stop"),"targets":execution.get("targets") or [],"rr":execution.get("remaining_rr")} if active and (ict.get("quality") or {}).get("trade_plan_valid") else None,"status":output.get("status")}

def enforce_forex_invariants(product,legacy):
    ict=legacy.get("ict_model") or ((legacy.get("research_shadow") or {}).get("ict_2022_v2")) or {}
    if not ict:
        setup=product.get("setup") or {};product["forex"]={"htf_bias":"neutral","market_structure":str((product.get("market") or {}).get("external_structure") or ""),"session":str((product.get("market") or {}).get("session") or ""),"liquidity_event":None,"displacement":None,"structure_confirmation":None,"dealing_range":None,"entry_zone":setup.get("entry_area"),"m5_confirmation":None,"scenario_state":str((product.get("decision") or {}).get("stage") or "NO_CONTEXT").upper(),"direction":(product.get("decision") or {}).get("direction"),"trade_plan":None};product.setdefault("diagnostics",{})["forex_invariants"]={"valid":True,"failures":[],"scenario_state":product["forex"]["scenario_state"]};product["paper_registration_allowed"]=bool((product.get("decision") or {}).get("trade_ready"));return product
    fields=normalize_forex_fields(legacy);failures=[];setup=product.get("setup") or {};decision=product.get("decision") or {};state=fields["scenario_state"];status=str(fields.get("status") or decision.get("status") or "");direction=fields.get("direction");zone=fields.get("entry_zone");confirmation=fields.get("m5_confirmation");ict_setup=ict.get("setup") or {};relationship=ict_setup.get("relationship")
    failures.extend(str(row) for row in ((ict.get("validation") or {}).get("failures") or []))
    if direction and zone:
        setup.update({"setup_id":ict_setup.get("setup_id"),"direction":direction,"stage":state,"status":status,"entry_area":zone,"trade_ready":bool(fields.get("trade_plan"))});decision.update({"status":status,"headline":status,"direction":direction,"stage":state,"trade_ready":bool(fields.get("trade_plan"))})
    if state in TERMINAL_STATES and "FORMING" in status:failures.append(f"scenario_state={state} conflicts with status={status}")
    if confirmation is None and (bool(decision.get("trade_ready")) or "CONFIRMED" in status or str(decision.get("stage","")).upper()=="TRADE_READY"):failures.append("m5_confirmation is null while the setup is confirmed or trade ready")
    if zone is None and "M5" in str(setup.get("next_required_condition") or "").upper() and direction:failures.append("entry_zone is null while the setup is waiting for M5 entry confirmation")
    htf=str(fields.get("htf_bias") or "neutral").lower()
    if htf in {"buy","bullish"} and direction=="sell" and relationship not in COUNTERTREND_RELATIONSHIPS:failures.append("bullish HTF structure conflicts with sell direction without an explicit countertrend reversal model")
    if htf in {"sell","bearish"} and direction=="buy" and relationship not in COUNTERTREND_RELATIONSHIPS:failures.append("bearish HTF structure conflicts with buy direction without an explicit countertrend reversal model")
    if direction and zone:_ensure_zone(product,zone,ict_setup)
    if direction and zone and not _matching_zone(product.get("overlays") or [],zone,setup.get("setup_id")):failures.append("referenced entry zone is absent from backend overlays")
    if (direction or decision.get("trade_ready")) and _stale(product):failures.append("ready/forming setup references stale candles")
    if state in TERMINAL_STATES:_clear_actionable(product,"SETUP EXPIRED" if state=="EXPIRED" else f"SETUP {state}",ict_setup.get("expiration_reason") or f"ICT lifecycle reached terminal state {state}.")
    elif state=="NO_CONTEXT":_clear_actionable(product,"WAITING FOR ICT CONTEXT","No completed ICT context currently satisfies the setup sequence.")
    elif failures:_clear_actionable(product,"STATE CONTRADICTION","; ".join(failures))
    if product["decision"].get("direction") is None:fields.update({"direction":None,"entry_zone":None,"m5_confirmation":None,"trade_plan":None})
    overlays,drawing_payload,plan_complete=build_forex_overlay_contract(product,legacy,fields,not failures);product["overlays"]=overlays;product["forex_overlays"]=drawing_payload
    product["forex"]=fields;product.setdefault("diagnostics",{})["forex_invariants"]={"valid":not failures,"failures":failures,"scenario_state":state,"trade_plan_overlay_complete":plan_complete};product["paper_registration_allowed"]=bool(not failures and state not in TERMINAL_STATES and plan_complete);return product

def _clear_actionable(product,status,reason):
    product["decision"].update({"status":status,"headline":status,"direction":None,"trade_ready":False,"summary":reason,"first_blocking_gate":reason,"next_action":"Wait for a new setup from fresh structure."});product["setup"].update({"setup_id":None,"direction":None,"trade_ready":False,"entry":None,"stop":None,"targets":[],"rr":None,"entry_area":None,"first_blocking_gate":reason});product["overlays"]=[row for row in product.get("overlays",[]) if row.get("type")=="current_price"];product["trade_plan"]={"available":False,"status":"UNAVAILABLE","entry":None,"stop":None,"targets":[],"rr":None,"reason":reason}

def _matching_zone(overlays,zone,setup_id):return any(row.get("type") in {"entry_area","setup_zone","zone"} and row.get("setup_id")==setup_id and _same(row.get("low"),zone.get("low")) and _same(row.get("high"),zone.get("high")) for row in overlays)
def _ensure_zone(product,zone,ict_setup):
    setup=product["setup"];source=ict_setup.get("entry_array") or {};metadata={"owner_id":"ict_2022","setup_id":setup.get("setup_id"),"state":"active","timeframe":"M15","source":source.get("type") or "ict_entry_array","created_time":source.get("formed_at"),"expiration_time":ict_setup.get("expires_at")}
    existing=next((row for row in product.get("overlays") or [] if row.get("type") in {"entry_area","setup_zone","zone"} and _same(row.get("low"),zone.get("low")) and _same(row.get("high"),zone.get("high"))),None)
    if existing:existing.update(metadata);return
    product.setdefault("overlays",[]).append({"overlay_id":f"forex-zone-{setup.get('setup_id')}","visibility_category":"trade_plan","type":"entry_area","low":zone["low"],"high":zone["high"],"name":"ICT Entry Area",**metadata})
def _stale(product):
    if not (product.get("meta") or {}).get("live"):return False
    now=pd.Timestamp(product["meta"]["analysis_time"]);now=now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC");frames=(product.get("readiness") or {}).get("timeframes") or {}
    for timeframe,minutes in (("M5",15),("M15",45),("H1",180)):
        value=(frames.get(timeframe) or {}).get("last_completed_time")
        if not value:return True
        stamp=pd.Timestamp(value);stamp=stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
        if now.weekday()<5 and now-stamp>pd.Timedelta(minutes=minutes):return True
    return False
def _same(left,right):
    try:return abs(float(left)-float(right))<=1e-10
    except (TypeError,ValueError):return False
