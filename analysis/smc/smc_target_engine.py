"""Deterministic, causal structural-target creation and selection for SMC plans."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import pandas as pd


SOURCE_RANK = {
    "internal_swing": 1,
    "equal_levels": 2,
    "range_boundary": 3,
    "range_equilibrium": 3,
    "external_swing": 4,
    "accepted_breakout_objective": 5,
}
_LIFECYCLE_CACHE={}


def clear_target_lifecycle_cache():
    _LIFECYCLE_CACHE.clear()


def evaluate_structural_targets(*, symbol, direction, entry, stop, swings, liquidity,
                                dealing_range=None, candles_by_timeframe=None,
                                minimum_rr=1.5, setup_type="structure_pullback",
                                event=None, tick_size=.01, owning_setup_id=None,
                                structural_leg_id=None):
    """Create, lifecycle-check, trace, and select TP1/TP2 without projections."""
    frames=candles_by_timeframe or {};prepared_frames={key:_completed(value) for key,value in frames.items()}; candidates=_create_candidates(
        symbol, direction, swings or [], liquidity or [], dealing_range or {},
        setup_type, event or {}, tick_size,
    )
    if owning_setup_id:
        candidates=[{**row,"owning_setup_id":owning_setup_id} for row in candidates]
    sources=[
        "internal_swing","equal_levels","range_boundary","external_swing",
        "accepted_breakout_objective",
    ]
    trace={"direction":_side(direction),"entry":entry,"stop":stop,
        "sources_checked":sources,"candidate_sources_checked":sources,
        "candidates_created":[],"candidates_found":[],"candidates_rejected":[],
        "selected_target":None,"first_blocker":"","history_window":_history_window(frames),
        "counts":{"confirmed_swings":sum(1 for row in swings or [] if row.get("confirmation_time")),
            "structural_references":len(candidates),"target_candidates":len(candidates),
            "profitable_side":0,"active":0,"rr_passed":0}}
    accepted=[]
    for candidate in candidates:
        evaluated=_evaluate_candidate(candidate,direction,entry,stop,prepared_frames,minimum_rr,event or {})
        trace["candidates_created"].append(evaluated)
        trace["candidates_found"].append({key:evaluated.get(key) for key in (
            "target_id","source_type","timeframe","price","created_at","confirmed_at","state","scope")})
        trace["counts"]["profitable_side"]+=int(bool(evaluated.get("on_profitable_side")))
        trace["counts"]["active"]+=int(evaluated.get("state")=="active")
        trace["counts"]["rr_passed"]+=int(evaluated.get("on_profitable_side") and evaluated.get("state")=="active" and evaluated.get("projected_rr") is not None and evaluated["projected_rr"]>=minimum_rr)
        if evaluated.get("rejection_code"):
            trace["candidates_rejected"].append(evaluated)
        else: accepted.append(evaluated)
    accepted.sort(key=lambda row:(_selection_rank(row,setup_type),row["distance_from_entry"],row["target_id"]))
    # M15-swing objectives are excluded from TP1 for structure pullbacks:
    # 90-day R_75 outcome data showed M15-timeframe TP1s losing in BOTH
    # directions (~-0.5R expectancy) while M5 and H1/H4 tiers were healthy.
    # They remain eligible as TP2 extension objectives.
    tp1_pool=[row for row in accepted if not (setup_type=="structure_pullback" and row.get("timeframe")=="M15")] or []
    trace["tp1_excluded_timeframes"]=["M15"] if setup_type=="structure_pullback" else []
    selected=tp1_pool[0] if tp1_pool else None
    farther=sorted((row for row in accepted if selected and row["target_id"]!=selected["target_id"] and row["distance_from_entry"]>selected["distance_from_entry"]),key=lambda row:(row["distance_from_entry"],_selection_rank(row,setup_type),row["target_id"]))
    external=farther[0] if farther else None
    if selected:
        selected={**selected,"selected":True};trace["selected_target"]=selected
    if external:external={**external,"selected_as":"TP2"};trace["selected_tp2"]=external
    trace["first_blocker"]=_first_blocker(trace,candidates,entry,stop)
    trace["target_scope_diagnostics"]=_target_scope_diagnostics(trace,direction=direction,setup_id=owning_setup_id,structural_leg_id=structural_leg_id)
    return {"tp1":selected,"tp2":external,"target_trace":trace,
            "target_source_audit":_source_audit(candidates,trace),
            "history_depth_audit":history_depth_audit(frames),
            "target_scope":selected.get("scope") if selected else None,
            "target_timeframe":selected.get("timeframe") if selected else None,
            "target_source":selected.get("source_type") if selected else None}


def history_depth_audit(frames):
    minimum={"H4":6,"H1":20,"M15":40,"M5":60};recommended={"H4":42,"H1":168,"M15":672,"M5":2016}
    output={}
    for timeframe in ("H4","H1","M15","M5"):
        count=len(_completed(frames.get(timeframe)));need=minimum[timeframe];recommended_count=recommended[timeframe]
        output[timeframe]={"timeframe":timeframe,"available":count,"minimum_required":need,
            "recommended_for_validation":recommended_count,"sufficient_for_analysis":count>=need,
            "sufficient_for_acceptance_matrix":count>=recommended_count}
    return output


def target_lifecycle_events(target, candles, *, acceptance_buffer=0.0, follow_through=1, prepared=False):
    """Return causal target state; wick interaction alone never means acceptance."""
    rows=candles if prepared and isinstance(candles,pd.DataFrame) else _completed(candles);price=float(target["price"]);side=target["side"]
    created=target.get("confirmed_at") or target.get("created_at")
    scan=rows
    if created is not None and "time" in scan:
        created_at=pd.Timestamp(created);created_at=created_at.tz_localize("UTC") if created_at.tzinfo is None else created_at
        scan=scan[scan.time>created_at]
    events=[];pending=False;terminal=False
    columns={key:scan.columns.get_loc(key) for key in ("time","high","low","close")}
    for row in scan.itertuples(index=False,name=None):
        if terminal:break
        high=float(row[columns["high"]]);low=float(row[columns["low"]]);close=float(row[columns["close"]]);value=row[columns["time"]];time=value.isoformat() if hasattr(value,"isoformat") else str(value)
        touched=high>=price if side=="buy_side" else low<=price
        beyond=high>price if side=="buy_side" else low<price
        closed_beyond=close>price+acceptance_buffer if side=="buy_side" else close<price-acceptance_buffer
        closed_inside=close<=price if side=="buy_side" else close>=price
        if touched: events.append({"event":"touched","time":time})
        if beyond and closed_inside: events.append({"event":"swept","time":time})
        if pending and closed_beyond:
            events.append({"event":"accepted_beyond","time":time});events.append({"event":"consumed","time":time,"reason":"completed_close_and_follow_through"});terminal=True;pending=False;break
        pending=bool(closed_beyond)
    names={row["event"] for row in events};state="consumed" if "consumed" in names else "swept" if "swept" in names else "touched" if "touched" in names else "active"
    result={"state":state,"touched":"touched" in names,"swept":"swept" in names,
            "accepted_beyond":"accepted_beyond" in names,"consumed":"consumed" in names,
            "events":events,"pending_acceptance":pending and "accepted_beyond" not in names}
    return result


def _create_candidates(symbol,direction,swings,liquidity,dealing,setup_type,event,tick_size):
    result=[];seen=set();side="buy_side" if direction=="bullish" else "sell_side"
    for swing in swings:
        if (swing.get("type")=="high")!=(side=="buy_side"):continue
        swing_scope=swing.get("scope");scope="internal" if swing_scope in {"internal","execution"} else "external";source=f"{scope}_swing";timeframe="M5" if swing_scope=="execution" else "M15" if swing_scope=="internal" else "H4" if swing_scope=="external_h4" else "H1"
        _add(result,seen,_candidate(symbol,source,timeframe,scope,side,swing["price"],swing.get("candle_time"),swing.get("confirmation_time"),swing.get("swing_id")))
    for ref in liquidity:
        if ref.get("type")!=side or ref.get("source")!="equal_levels":continue
        scope="setup" if _ref_scope(ref,swings)=="internal" else "external"
        _add(result,seen,_candidate(symbol,"equal_levels","M15" if scope=="setup" else "H1",scope,side,ref["price"],ref.get("created_time"),ref.get("created_time"),ref.get("reference_id")))
    if dealing.get("valid") or dealing.get("low") is not None and dealing.get("high") is not None:
        low=dealing.get("low");high=dealing.get("high")
        if setup_type=="range_reaction" and low is not None and high is not None:
            _add(result,seen,_candidate(symbol,"range_equilibrium","M15","setup",side,(float(low)+float(high))/2,dealing.get("created_time"),dealing.get("confirmed_at"),dealing.get("range_id")))
        boundary=high if side=="buy_side" else low
        if boundary is not None:_add(result,seen,_candidate(symbol,"range_boundary","M15","setup",side,boundary,dealing.get("created_time"),dealing.get("confirmed_at"),dealing.get("range_id")))
    if event.get("type")=="accepted_breakout" and event.get("objective_price") is not None:
        _add(result,seen,_candidate(symbol,"accepted_breakout_objective","M15","setup",side,event["objective_price"],event.get("event_time"),event.get("event_time"),event.get("event_id")))
    return result


def _candidate(symbol,source,timeframe,scope,side,price,created,confirmed,origin):
    identity=hashlib.sha256(json.dumps([symbol,timeframe,source,origin,float(price)],sort_keys=True,default=str).encode()).hexdigest()[:24]
    return {"target_id":"target-"+identity,"symbol":symbol,"timeframe":timeframe,"source_type":source,"scope":scope,"side":side,"price":float(price),"created_at":created,"confirmed_at":confirmed or created,"selected_at":None,"terminal_at":None,"terminal_reason":None,"owning_setup_id":None,"state":"active"}


def _add(rows,seen,row):
    key=(row["timeframe"],round(row["price"],12),row["source_type"])
    if key not in seen:seen.add(key);rows.append(row)


def _evaluate_candidate(candidate,direction,entry,stop,frames,minimum_rr,event):
    life=target_lifecycle_events(candidate,frames.get(candidate["timeframe"]),acceptance_buffer=0.0,prepared=True)
    row={**candidate,**life,"selected":False,"rejection_code":None,"rejection_reason":None,"rejection_explanation":"",
         "on_profitable_side":False,"distance_from_entry":None,"projected_rr":None}
    if entry is None or stop is None:return _reject(row,"ENTRY_OR_STOP_MISSING","Entry and stop are unavailable, so target quality cannot be validated.")
    entry=float(entry);stop=float(stop);price=float(row["price"]);risk=abs(entry-stop);profitable=price>entry if direction=="bullish" else price<entry
    row["on_profitable_side"]=profitable;row["distance_from_entry"]=abs(price-entry);row["projected_rr"]=abs(price-entry)/risk if risk else None
    if event.get("blocking") or event.get("risk_state") in {"ACTIVE","BLOCKING","EVENT_RISK_ACTIVE"}:return _reject(row,"EVENT_INVALIDATED","An active event-risk state blocks target ownership.")
    if life["accepted_beyond"]:return _reject(row,"ACCEPTED_BEYOND","Completed close and follow-through accepted beyond the reference.")
    if life["consumed"] or life["swept"]:return _reject(row,"ALREADY_SWEPT","The structural objective was already swept or consumed.")
    if not profitable:return _reject(row,"WRONG_SIDE_OF_ENTRY","The reference is not on the profitable side of the proposed entry.")
    if not risk:return _reject(row,"INSIDE_STOP_DIRECTION","Entry and stop do not define positive risk.")
    if row["projected_rr"]<minimum_rr:return _reject(row,"RR_BELOW_MINIMUM",f"Target provides {row['projected_rr']:.2f}R; {minimum_rr:.2f}R is required.")
    return row


def _target_scope_diagnostics(trace,*,direction,setup_id,structural_leg_id):
    # Purely explanatory: identifies which rejected candidate the generic
    # TARGET_SCOPE_MISMATCH fallback is standing in for. Never changes
    # selection, rejection, or the target hierarchy above.
    if trace.get("first_blocker")!="TARGET_SCOPE_MISMATCH":return None
    rejected=trace.get("candidates_rejected") or []
    nearest=min(rejected,key=lambda row:row["distance_from_entry"] if row.get("distance_from_entry") is not None else float("inf")) if rejected else None
    side_label={"buy_side":"buy","sell_side":"sell"}
    reasons=sorted({row.get("rejection_reason") for row in rejected if row.get("rejection_reason")})
    if nearest is None:
        reason="No structural target candidates were created that could belong to this setup."
    else:
        reason=f"{len(rejected)} structural candidate(s) were evaluated for this setup; none passed a single consistent rule ({', '.join(reasons)})."
    return {"code":"TARGET_SCOPE_MISMATCH","candidate_target":{"target_id":nearest["target_id"],"price":nearest["price"],"source_type":nearest["source_type"],"timeframe":nearest["timeframe"]} if nearest else None,"expected_setup_id":setup_id,"candidate_setup_id":(nearest or {}).get("owning_setup_id"),"expected_direction":_side(direction),"candidate_side":side_label.get((nearest or {}).get("side")),"expected_structural_leg_id":structural_leg_id,"candidate_structural_leg_id":(nearest or {}).get("target_id"),"reason":reason}

def _reject(row,code,message):row["rejection_code"]=code;row["rejection_reason"]=code;row["rejection_explanation"]=message;return row
def _side(direction):return "buy" if direction=="bullish" else "sell" if direction=="bearish" else ""
def _ref_scope(ref,swings):
    members=set(ref.get("member_swing_ids") or [])
    return "internal" if any(row.get("swing_id") in members and row.get("scope")=="internal" for row in swings) else "external"
def _first_blocker(trace,candidates,entry,stop):
    if trace.get("selected_target"):return ""
    if entry is None or stop is None:return "ENTRY_OR_STOP_MISSING"
    if not candidates:
        return "NO_CONFIRMED_SWINGS" if not trace.get("counts",{}).get("confirmed_swings") else "NO_TARGET_REFERENCES_CREATED"
    codes=[row["rejection_code"] for row in trace["candidates_rejected"]]
    if codes and all(code=="WRONG_SIDE_OF_ENTRY" for code in codes):return "ALL_TARGETS_WRONG_SIDE"
    if codes and all(code=="RR_BELOW_MINIMUM" for code in codes):return "ALL_TARGETS_RR_REJECTED"
    if codes and all(code in {"ALREADY_SWEPT","ACCEPTED_BEYOND","CONSUMED_REFERENCE"} for code in codes):return "ALL_TARGETS_ALREADY_CONSUMED"
    if codes and all(code=="EVENT_INVALIDATED" for code in codes):return "ALL_TARGETS_EVENT_INVALIDATED"
    if "RR_BELOW_MINIMUM" in codes and not any(row.get("on_profitable_side") and not row.get("consumed") and not row.get("swept") for row in trace["candidates_rejected"]):return "ALL_TARGETS_RR_REJECTED"
    return "TARGET_SCOPE_MISMATCH"

def _selection_rank(row,setup_type):
    source=row.get("source_type");timeframe=row.get("timeframe")
    if setup_type=="structure_pullback":
        if source=="internal_swing" and timeframe=="M5":return 1
        if source=="internal_swing" and timeframe=="M15":return 2
        if source=="equal_levels":return 3
        if source=="external_swing" and timeframe=="H1":return 4
    return SOURCE_RANK.get(source,99)
def _source_audit(candidates,trace):
    output={tf:{"confirmed_swings":0,"active_targets":0,"consumed_targets":0,"rejected_targets":0} for tf in ("H4","H1","M15","M5")}
    rejected={row["target_id"] for row in trace["candidates_rejected"]}
    for row in candidates:
        bucket=output[row["timeframe"]];bucket["confirmed_swings"]+=int("swing" in row["source_type"]);bucket["active_targets"]+=int(row["target_id"] not in rejected);bucket["rejected_targets"]+=int(row["target_id"] in rejected)
    for row in trace["candidates_rejected"]:output[row["timeframe"]]["consumed_targets"]+=int(row.get("consumed"))
    return output
def _history_window(frames):
    times=[];count=0
    for rows in frames.values():
        completed=_completed(rows);count+=len(completed)
        if "time" in completed and len(completed):times.extend([_time(completed.iloc[0]),_time(completed.iloc[-1])])
    return {"start":min(times) if times else None,"end":max(times) if times else None,"completed_candles":count}
def _completed(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame()
    return rows[rows.complete.astype(bool)].reset_index(drop=True) if "complete" in rows else rows.reset_index(drop=True)
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
