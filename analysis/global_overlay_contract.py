"""Global lifecycle and drawing boundary for every market and strategy."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
from analysis.instrument_precision import precision_registry
from analysis.derived_setup_lifecycle import TERMINAL as _DERIVED_TERMINAL
from analysis.forex_decision_normalizer import TERMINAL_STATES as _FOREX_TERMINAL
from analysis.smc.smc_setup_engine import STATES as _SMC_STATES

# This module is the single boundary that decides what the frontend renders, so its
# terminal-state set is a live union of every family-specific lifecycle vocabulary
# (rather than a hand-copied list) to prevent one family adding a terminal state here
# and other families/the render boundary silently disagreeing about it.
_SMC_TERMINAL={"TOO_LATE","INVALIDATED","PLAN REJECTED","FILLED","CLOSED"}&set(_SMC_STATES)
TERMINAL={"EXPIRED","INVALIDATED","CANCELLED","TOO_LATE","CLOSED","REPLACED","EVENT_CANCELLED","STATE_CONTRADICTION","SETUP EXPIRED","SETUP INVALIDATED","FAILED_BREAKOUT","POST_SPIKE_CANCELLED","REGIME_CHANGED","AUTO_ROUTER_REPLACED","STALE_RANGE_INVALIDATED","INVALIDATED_STALE_RANGE"}|_DERIVED_TERMINAL|_FOREX_TERMINAL|_SMC_TERMINAL
OVERLAY_MODES={"LIVE","HISTORICAL_INSPECTION","REPLAY","PREVIOUS_SETUP"}
ACTIONABLE_TYPES={"entry","stop","stop_loss","tp1","tp2","target","trade_plan_invalidation","final_invalidation","trade_ready_entry_zone"}
SETUP_TYPES={"setup_area","entry_area","developing_entry_area","confirmation","confirmation_level","confirmation_zone","retracement_area","pullback_area","monitoring_level","structural_target","structural_objective","potential_objective","event_quarantine","setup_invalidation","fvg","order_block","ote"}|ACTIONABLE_TYPES
SETUP_ONLY_TYPES=SETUP_TYPES-{"fvg","order_block"}
AREA_TYPES={"setup_area","entry_area","developing_entry_area","retracement_area","pullback_area","m15_pullback_area","trade_ready_entry_zone","ote"}
PRIORITY={"entry":100,"stop":100,"stop_loss":100,"tp1":100,"tp2":100,"target":100,"trade_ready_entry_zone":100,"setup_area":90,"entry_area":90,"developing_entry_area":90,"setup_invalidation":90,"structural_range":80,"range_high":80,"range_low":80,"h1_context":80,"structural_target":70,"structural_objective":70,"potential_objective":70,"equilibrium":60,"premium_zone":60,"discount_zone":60,"bos":50,"mss":50,"confirmed_sweep":50,"liquidity_sweep":50,"displacement":50,"confirmation":50,"confirmation_level":50,"equal_high":40,"equal_low":40,"swing_high":40,"swing_low":40,"current_price":110}
TYPE_MAP={"current":"current_price","stop_loss":"stop","target":"target","trade_plan_invalidation":"final_invalidation","confirmed_sweep":"liquidity_sweep","structural_target":"structural_objective"}

def normalize_global_decision(product,*,instrument_metadata=None,mode="LIVE"):
    value=deepcopy(product);meta=value.get("meta") or {};ownership=value.get("ownership") or {};public=value.get("decision") or {};setup=value.get("setup") or {};original_plan=deepcopy(value.get("trade_plan") or {});stage=str(public.get("stage") or setup.get("stage") or "").upper();status=str(public.get("status") or setup.get("status") or "").upper();terminal=_terminal(stage) or _terminal(status);readiness=str((value.get("readiness") or {}).get("state") or "ready").lower();owner=ownership.get("overlay_owner_id") or ownership.get("decision_owner_id") or ownership.get("selected_model_id") or "unknown"
    precision=precision_registry(symbol=meta.get("symbol") or "",provider=meta.get("market_source") or "unknown",market_type=meta.get("market_type") or "",metadata=instrument_metadata,current_price=(value.get("market") or {}).get("current_price"));value["precision"]=precision;requested_mode=str(mode).upper();value["overlay_mode"]=requested_mode if requested_mode in OVERLAY_MODES else "LIVE"
    previous=deepcopy(value.get("previous_setup")) if value.get("previous_setup") else None
    if terminal and setup.get("setup_id"):
        previous={**deepcopy(setup),"terminal_status":status or stage,"terminal_reason":public.get("first_blocking_gate") or setup.get("first_blocking_gate") or setup.get("expiration_reason"),"result":(previous or {}).get("result")};setup={};public.update({"direction":None,"trade_ready":False,"next_action":"Wait for a new qualifying setup.","first_blocking_gate":previous.get("terminal_reason")});value["trade_plan"]={"available":False,"entry":None,"stop":None,"targets":[],"rr":None}
    active=_active_setup(setup,public,terminal,readiness);value["current_market"]=deepcopy(value.get("market") or {});value["active_setup"]=active;value["previous_setup"]=previous
    contradiction=_contradiction(value,active,stage,status,readiness,owner)
    if contradiction:
        if active and not previous:previous={**deepcopy(active),"terminal_status":"STATE CONTRADICTION","terminal_reason":"; ".join(contradiction)}
        active=None;value["active_setup"]=None;value["previous_setup"]=previous;public.update({"status":"STATE CONTRADICTION","headline":"STATE CONTRADICTION","stage":"STATE_CONTRADICTION","direction":None,"trade_ready":False,"summary":"Conflicting lifecycle or ownership fields were blocked.","next_action":"Do not act. Wait for a new coherent decision."});value.setdefault("diagnostics",{})["global_overlay_contradictions"]=contradiction
        value["diagnostics"]["global_overlay_conflicting_fields"]=_conflicting_overlay_fields(value,owner)
    ready=_actionable_ready(value,active,readiness,owner)
    if not ready:public["trade_ready"]=False
    value["trade_plan"]={"available":True,"status":public.get("status"),"entry":active.get("entry"),"stop":active.get("stop"),"targets":deepcopy(active.get("targets") or []),"rr":active.get("rr"),"setup_id":active.get("setup_id"),"entry_zone":deepcopy(active.get("entry_area"))} if ready else {"available":False,"status":"UNAVAILABLE","entry":None,"stop":None,"targets":[],"reason":original_plan.get("reason") or public.get("first_blocking_gate") or (active or {}).get("next_required_condition") or "No complete validated trade plan."}
    rows=[]
    for source in value.get("overlays") or []:
        row=_normalize_row(source,value,active,previous,owner,precision)
        if not row:continue
        if row["category"]=="actionable":continue
        if ready and row["category"]=="developing":continue
        if row["category"]=="developing" and not active:continue
        if row["category"]=="historical" and value["overlay_mode"]!="PREVIOUS_SETUP":continue
        if row["setup_id"] and active and row["category"]!="historical" and row["setup_id"]!=active.get("setup_id"):continue
        rows.append(row)
    rows.extend(_required_rows(value,active,owner,precision,ready))
    if value["overlay_mode"] in {"LIVE","PREVIOUS_SETUP"}:rows.extend(_historical_rows(value,previous,owner,precision))
    rows=_deduplicate(rows);rows=_cluster(rows,precision,(value.get("market") or {}).get("atr"));value["overlays"]=rows;value["decision"]=public;value["setup"]=active or _empty_setup(setup)
    if value["overlay_mode"]=="PREVIOUS_SETUP":value["overlays"]=[row for row in value["overlays"] if row["category"]=="historical"]
    value["paper_registration_allowed"]=bool(value["overlay_mode"]=="LIVE" and ready and not contradiction and readiness=="ready")
    return value

def _active_setup(setup,public,terminal,readiness):
    if terminal or readiness in {"error","provider_error","insufficient","insufficient_history"} or not setup.get("setup_id") or str(public.get("stage") or setup.get("stage") or "").upper() in {"NO_CONTEXT","NO CONTEXT"}:return None
    return deepcopy(setup)

def _contradiction(value,active,stage,status,readiness,owner):
    public=value.get("decision") or {};ownership=value.get("ownership") or {};problems=[];asserted=bool(public.get("trade_ready") or stage=="TRADE_READY" or status.startswith("READY TO"))
    if asserted and not active:problems.append("Trade-ready decision has no active setup.")
    if active is None and (status in {"DEVELOPING","SETUP DEVELOPING"} or any(x in status for x in ("FORMING","WAITING FOR CONFIRMATION","WAITING FOR ENTRY"))):problems.append("Setup-forming status has no active setup.")
    if asserted and active and (active.get("entry") is None or active.get("stop") is None or not _tp1(active)):problems.append("Trade-ready decision lacks entry, stop, or TP1.")
    if asserted and active and (active.get("production_supported") is False or active.get("family_compatible") is False or active.get("research_only") or active.get("chase_valid") is False):problems.append("Trade-ready decision failed production, family, research, or chase validation.")
    if active and (stage in {"NO_CONTEXT","NO CONTEXT"} or status in {"NO_CONTEXT","NO CONTEXT"}):problems.append("No-context decision retained an active setup.")
    if asserted and active and (active.get("direction") or public.get("direction")) not in {"buy","sell"}:problems.append("Trade-ready decision has no directional plan.")
    if asserted and readiness!="ready":problems.append("Live-ready decision uses stale or unavailable data.")
    if asserted and value.get("overlay_mode")=="LIVE" and (value.get("meta") or {}).get("live") is not True:problems.append("Live-ready decision is not backed by live data.")
    decision_owner=ownership.get("decision_owner_id")
    if owner=="unknown" or (decision_owner and owner!=decision_owner):problems.append("Decision and overlay ownership do not match.")
    if _conflicting_overlay_fields(value,owner):problems.append("One or more overlays do not match the active owner, strategy, symbol, or market.")
    return problems

def _conflicting_overlay_fields(value,owner):
    meta=value.get("meta") or {};strategy=_strategy_id(value,owner);conflicts=[]
    for row in value.get("overlays") or []:
        if not isinstance(row,dict) or row.get("historical") or str(row.get("category") or "").lower()=="historical":continue
        row_owner=row.get("decision_owner_id") or row.get("owner_id")
        fields={}
        if row_owner and row_owner!=owner:fields["decision_owner_id"]={"expected":owner,"received":row_owner}
        if row.get("strategy_id") and row.get("strategy_id")!=strategy:fields["strategy_id"]={"expected":strategy,"received":row.get("strategy_id")}
        provider_symbol=row.get("provider_symbol") or row.get("symbol")
        if provider_symbol and provider_symbol!=meta.get("symbol"):fields["provider_symbol"]={"expected":meta.get("symbol"),"received":provider_symbol}
        if row.get("market_type") and row.get("market_type")!=meta.get("market_type"):fields["market_type"]={"expected":meta.get("market_type"),"received":row.get("market_type")}
        if fields:conflicts.append({"overlay_id":row.get("overlay_id"),"fields":fields})
    return conflicts

def _actionable_ready(value,active,readiness,owner):
    if not active or readiness!="ready" or owner=="unknown":return False
    public=value.get("decision") or {};stage=str(public.get("stage") or active.get("stage") or "").upper();direction=active.get("direction") or public.get("direction");entry=active.get("entry");stop=active.get("stop");tp1=_tp1(active);rr=active.get("rr");confirmed=active.get("completed_confirmation") or active.get("mss") or active.get("bos") or active.get("confirmation") or stage=="TRADE_READY"
    if not (public.get("trade_ready") and stage=="TRADE_READY" and direction in {"buy","sell"} and confirmed and entry is not None and stop is not None and tp1 is not None):return False
    diagnostics=value.get("diagnostics") or {};invariants=diagnostics.get("invariants") or {}
    if active.get("production_supported") is False or active.get("family_compatible") is False or active.get("research_only") or active.get("event_risk") or active.get("stale") or active.get("chase_valid") is False or invariants.get("valid") is False:return False
    if active.get("entry_geometry_valid") is False or active.get("stop_geometry_valid") is False or active.get("tp1_geometry_valid") is False:return False
    if value.get("overlay_mode")=="LIVE" and (value.get("meta") or {}).get("live") is not True:return False
    if direction=="buy" and not (stop<entry<tp1) or direction=="sell" and not (tp1<entry<stop):return False
    return rr is not None and float(rr)>=float(active.get("minimum_rr") or 1.5)

def _normalize_row(source,value,active,previous,owner,precision):
    if not isinstance(source,dict):return None
    meta=value.get("meta") or {}
    if source.get("provider_symbol") and source.get("provider_symbol")!=meta.get("symbol"):return None
    if source.get("symbol") and source.get("symbol")!=meta.get("symbol"):return None
    if source.get("timeframe") and source.get("timeframe")!=meta.get("timeframe") and str(source.get("timeframe")).upper() not in {"D1","H4","H1","M15","M5","M1"}:return None
    kind=TYPE_MAP.get(str(source.get("type") or "").lower(),str(source.get("type") or "unknown").lower());setup_id=source.get("setup_id");raw_category=str(source.get("category") or "").lower();visibility=str(source.get("visibility_category") or "").lower();actionable=bool(source.get("actionable") or raw_category=="actionable" or (kind in ACTIONABLE_TYPES and str(source.get("state") or "").lower()=="confirmed"));historical=bool(source.get("historical") or raw_category=="historical")
    if historical:category="historical"
    elif actionable:category="actionable"
    elif setup_id or kind in SETUP_ONLY_TYPES:category="developing"
    else:category="context"
    label_override=None
    if category=="developing" and kind in {"target","tp1","tp2"}:kind="potential_objective";label_override="POTENTIAL STRUCTURAL OBJECTIVE"
    elif category=="developing" and kind in {"structural_objective","potential_objective"}:label_override="POTENTIAL STRUCTURAL OBJECTIVE"
    elif category=="developing" and kind in {"stop","stop_loss","final_invalidation","setup_invalidation"}:kind="setup_invalidation";label_override="IDEA INVALIDATION"
    elif category=="developing" and kind=="entry":return None
    elif category=="developing" and kind in {"confirmation","confirmation_level","confirmation_zone"}:label_override="CONFIRMATION LEVEL"
    elif category=="developing" and kind in {"liquidity_reference","liquidity_sweep"}:label_override="LIQUIDITY REFERENCE"
    elif category=="developing" and kind=="protected_structural_high":label_override=f"PROTECTED {str(source.get('timeframe') or 'M5').upper()} HIGH"
    elif category=="developing" and kind=="protected_structural_low":label_override=f"PROTECTED {str(source.get('timeframe') or 'M5').upper()} LOW"
    elif category=="developing" and kind in {"monitoring_level","event_quarantine"}:label_override="MONITORING LEVEL"
    elif category=="developing" and kind in {"setup_area","entry_area","developing_entry_area","retracement_area","pullback_area","fvg","order_block","ote"}:label_override="DEVELOPING · NOT AN ENTRY"
    elif category=="developing":label_override=f"DEVELOPING · {_strip_status_prefix(source.get('label') or source.get('name') or _label(kind,category))}"
    if category in {"developing","actionable"} and (not active or not setup_id):return None
    if category=="historical" and not setup_id:return None
    if kind in {"structural_objective","potential_objective"} and not active:return None
    label=label_override or source.get("label") or source.get("name") or _label(kind,category);source_owner=source.get("decision_owner_id") or source.get("owner_id") or owner
    if source_owner!=owner and category!="historical":return None
    priority=int(source.get("priority") or PRIORITY.get(kind,20));display_group=_source_group(source,kind,category)
    row={"overlay_id":source.get("overlay_id") or _id(owner,setup_id,kind,source),"decision_owner_id":source_owner,"strategy_id":source.get("strategy_id") or _strategy_id(value,owner),"setup_id":setup_id,"symbol_id":source.get("symbol_id") or precision["symbol_id"],"provider_symbol":source.get("provider_symbol") or meta.get("symbol") or "","market_type":source.get("market_type") or meta.get("market_type") or "","timeframe":meta.get("timeframe") or source.get("timeframe") or "","category":category,"type":kind,"label":label,"source":source.get("source") or "backend_analysis","price":source.get("price"),"high":source.get("high"),"low":source.get("low"),"start_time":source.get("start_time") or source.get("creation_time"),"end_time":source.get("end_time"),"created_at":source.get("created_at") or source.get("creation_time") or meta.get("analysis_time"),"confirmed_at":source.get("confirmed_at") or (source.get("creation_time") if str(source.get("state")).lower()=="confirmed" else None),"expires_at":source.get("expires_at"),"invalidated_at":source.get("invalidated_at") or source.get("invalidation_time"),"active":bool(source.get("active",True)) and not historical,"historical":historical,"actionable":category=="actionable","priority":priority,"display_group":display_group,"metadata":{**(source.get("metadata") or {}),"overlay_mode":value.get("overlay_mode") or "LIVE","source_timeframe":source.get("timeframe") or meta.get("timeframe"),"visibility_reason":source.get("visibility_reason") or f"Backend {category} {kind}","invalidation_condition":source.get("invalidation_condition") or ("Setup expires or is structurally invalidated." if setup_id else "Superseded by newer backend context."),"default_visible":priority>=70 and display_group!="advanced_smc","price_decimals":precision["price_decimals"]}}
    row.update({"owner_id":row["decision_owner_id"],"symbol":row["provider_symbol"],"name":source.get("name") or row["label"],"visibility_category":row["display_group"],"state":"active" if row["active"] else "inactive","actionable_at_decision_time":row["actionable"],"creation_time":row["created_at"],"invalidation_time":row["invalidated_at"]})
    if row["price"] is None and row["high"] is None and row["low"] is None:return None
    return row

CURRENT_PRICE_LABELS={"LIVE":"Current","HISTORICAL_INSPECTION":"Decision-time Current","REPLAY":"Replay Current","PREVIOUS_SETUP":"Previous setup price"}
def _required_rows(value,active,owner,precision,ready):
    meta=value.get("meta") or {};market=value.get("market") or {};rows=[];strategy_id=_strategy_id(value,owner);mode=value.get("overlay_mode") or "LIVE"
    if market.get("current_price") is not None:rows.append(_row(owner,None,meta,precision,"current_price",CURRENT_PRICE_LABELS.get(mode,"Current"),"context",price=market["current_price"],priority=110,source="current_completed_market_data",strategy_id=strategy_id,mode=mode))
    if active and active.get("entry_area"):
        area=active["entry_area"];rows.append(_row(owner,active["setup_id"],meta,precision,"setup_area","TRADE-READY ENTRY" if ready else "DEVELOPING · NOT AN ENTRY","actionable" if ready else "developing",low=area.get("low"),high=area.get("high"),priority=100 if ready else 90,source=area.get("type") or "active_setup",strategy_id=strategy_id,mode=mode))
    if ready:
        rows.append(_row(owner,active["setup_id"],meta,precision,"entry","Entry","actionable",price=active["entry"],priority=100,source="validated_trade_plan",strategy_id=strategy_id,mode=mode));rows.append(_row(owner,active["setup_id"],meta,precision,"stop","Stop","actionable",price=active["stop"],priority=100,source="validated_trade_plan",strategy_id=strategy_id,mode=mode))
        for index,target in enumerate(active.get("targets") or []):
            if index>1 or target.get("price") is None:continue
            rows.append(_row(owner,active["setup_id"],meta,precision,f"tp{index+1}",f"TP{index+1}","actionable",price=target["price"],priority=100,source=target.get("source") or "validated_trade_plan",strategy_id=strategy_id,mode=mode))
    return rows

def _historical_rows(value,previous,owner,precision):
    if not previous:return []
    meta=value.get("meta") or {};setup_id=previous.get("setup_id");rows=[];strategy_id=_strategy_id(value,owner);mode=value.get("overlay_mode") or "LIVE"
    def add(kind,label,price=None,low=None,high=None):
        row=_row(owner,setup_id,meta,precision,kind,label,"historical",price=price,low=low,high=high,priority=20,source="previous_setup_archive",strategy_id=strategy_id,mode=mode);row.update(active=False,historical=True,actionable=False,state="inactive",display_group="previous_setup",visibility_category="previous_setup");rows.append(row)
    area=previous.get("entry_area") or previous.get("entry_array") or previous.get("zone") or {}
    if area.get("low") is not None and area.get("high") is not None:add("historical_setup_area","Previous Setup Area",low=area["low"],high=area["high"])
    if previous.get("entry") is not None:add("historical_entry","Previous Entry",price=previous["entry"])
    if previous.get("stop") is not None:add("historical_stop","Previous Stop",price=previous["stop"])
    for index,target in enumerate(previous.get("targets") or []):
        if index<2 and target.get("price") is not None:add(f"historical_tp{index+1}",f"Previous TP{index+1}",price=target["price"])
    return rows

def _row(owner,setup_id,meta,precision,kind,label,category,*,price=None,low=None,high=None,priority=0,source="backend",strategy_id=None,mode="LIVE"):
    payload={"price":price,"low":low,"high":high};group=_group(kind,category);actionable=category=="actionable";created=meta.get("analysis_time");return {"overlay_id":_id(owner,setup_id,kind,payload),"decision_owner_id":owner,"owner_id":owner,"strategy_id":strategy_id or owner,"setup_id":setup_id,"symbol_id":precision["symbol_id"],"provider_symbol":meta.get("symbol") or "","symbol":meta.get("symbol") or "","market_type":meta.get("market_type") or "","timeframe":meta.get("timeframe") or "","category":category,"type":kind,"label":label,"name":label,"source":source,"price":price,"high":high,"low":low,"start_time":None,"end_time":None,"created_at":created,"creation_time":created,"confirmed_at":created if actionable else None,"expires_at":None,"invalidated_at":None,"invalidation_time":None,"active":True,"state":"active","historical":False,"actionable":actionable,"actionable_at_decision_time":actionable,"priority":priority,"display_group":group,"visibility_category":group,"metadata":{"overlay_mode":mode,"visibility_reason":f"Required {category} overlay","invalidation_condition":"Setup terminates or newer backend context supersedes this object.","default_visible":priority>=70,"price_decimals":precision["price_decimals"]}}

def _deduplicate(rows):
    seen={};
    for row in rows:
        semantic_type="setup_area" if row["type"] in AREA_TYPES else row["type"];key=(row["decision_owner_id"],row["setup_id"],row["category"],semantic_type,row.get("price"),row.get("low"),row.get("high"));current=seen.get(key)
        if current is None or row["priority"]>current["priority"]:seen[key]=row
    return list(seen.values())

def _cluster(rows,precision,atr):
    tolerance=max(float(precision.get("tick_size") or precision.get("pip_size") or 10**-precision["price_decimals"])*1.5,float(atr or 0)*.002);result=[]
    for row in sorted(rows,key=lambda item:item["priority"],reverse=True):
        if row["category"] in {"actionable","historical"} or row.get("price") is None:result.append(row);continue
        match=next((item for item in result if item["category"]==row["category"] and item.get("price") is not None and abs(float(item["price"])-float(row["price"]))<=tolerance),None)
        if not match:result.append(row);continue
        support=match["metadata"].setdefault("supporting_sources",[]);support.append({"type":row["type"],"label":row["label"],"source":row["source"],"timeframe":row["timeframe"]});match["label"]=_cluster_label(match,row)
    return sorted(result,key=lambda item:(-item["priority"],item["overlay_id"]))

def _cluster_label(primary,secondary):
    if primary["type"]=="current_price":return primary["label"]
    frame=primary.get("timeframe") or secondary.get("timeframe") or "Structural";return f"{frame} Structural Cluster"
def _tp1(setup):
    targets=setup.get("targets") or [];return targets[0].get("price") if targets else None
def _empty_setup(setup):return {**deepcopy(setup),"setup_id":None,"direction":None,"trade_ready":False,"entry":None,"stop":None,"targets":[],"rr":None,"entry_area":None}
def _id(owner,setup_id,kind,values):return "overlay-"+hashlib.sha256(json.dumps([owner,setup_id,kind,values],sort_keys=True,default=str).encode()).hexdigest()[:20]
def _group(kind,category):return "trade_plan" if category=="actionable" else "previous_setup" if category=="historical" else "structure" if any(word in kind for word in ("swing","range","bos","mss")) else "context" if category=="context" else "setup"
def _source_group(source,kind,category):
    explicit=source.get("display_group");legacy=source.get("visibility_category")
    if explicit:return explicit
    return {"market_structure":"structure","context_levels":"context","advanced_smc":"advanced_smc","previous_setup":"previous_setup"}.get(legacy,_group(kind,category))
def _strategy_id(value,owner):
    ownership=value.get("ownership") or {}
    return ownership.get("selected_strategy_id") or ownership.get("selected_model_id") or owner
def _label(kind,category):
    if category=="developing" and kind in {"structural_objective","potential_objective"}:return "POTENTIAL STRUCTURAL OBJECTIVE"
    if category=="developing" and kind in {"setup_area","entry_area"}:return "DEVELOPING · NOT AN ENTRY"
    if kind in {"unknown",""}:return "STRUCTURAL REFERENCE"
    return kind.replace("_"," ").title()
def _strip_status_prefix(text):
    text=str(text or "")
    while text.upper().startswith("DEVELOPING · "):text=text[len("DEVELOPING · "):]
    return text or "Structural Reference"
def _terminal(value):return value in TERMINAL or any(value.startswith(prefix+" ") or value.startswith(prefix+"_") for prefix in TERMINAL)
