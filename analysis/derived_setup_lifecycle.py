"""Stable setup identity, lifecycle timestamps, and terminal archival."""
from __future__ import annotations
import hashlib,json
TERMINAL={"INVALIDATED","FAILED_BREAKOUT","POST_SPIKE_CANCELLED","REGIME_SWITCH_CANCELLED","REGIME_CHANGED","NEW_EVENT_CANCELLED","AUTO_ROUTER_REPLACED","EXPIRED","TOO_LATE","MISSED","POOR_REWARD","DATA_ERROR","COMPLETED"}
_records={};_archive=[]

def setup_identity(symbol,direction,zone,structure_event=None):
    values=[symbol,direction,"volatility_structure_pullback",round(float(zone.get("low")),8),round(float(zone.get("high")),8),zone.get("formed_at"),structure_event]
    return "vsp-"+hashlib.sha256(json.dumps(values,sort_keys=True,default=str).encode()).hexdigest()[:20]

def _is_stale(at,last_advanced_at):
    # _records is shared process-wide state; concurrent/out-of-order requests for the
    # same setup must not let an older analysis timestamp regress an already-newer
    # recorded stage (the backend analog of a stale HTTP response restoring old overlays).
    if last_advanced_at is None or at is None:return False
    try:return at<last_advanced_at
    except TypeError:return False

def advance_setup(*,symbol,direction,zone,state,at,setup_id=None,strategy="volatility_structure_pullback",family="VOLATILITY",range_id=None):
    setup_id=setup_id or setup_identity(symbol,direction,zone);existing=_records.get(setup_id)
    if existing and existing["state"] in TERMINAL:return dict(existing)
    if existing and _is_stale(at,existing.get("last_advanced_at")):return dict(existing)
    row=dict(existing or {"setup_id":setup_id,"range_id":range_id,"symbol":symbol,"family":family,"strategy":strategy,"direction":direction,"created_at":at,"zone_reached_at":None,"confirmation_started_at":None,"confirmed_at":None,"entry_available_at":None,"breakout_confirmed_at":None,"retest_started_at":None,"retest_confirmed_at":None,"entry_confirmed_at":None,"cancelled_by_new_spike_at":None,"cancelled_by_event_at":None,"regime_switch_cancelled_at":None,"terminal_reason":None,"invalidated_at":None,"expired_at":None,"missed_at":None,"completed_at":None,"state":"CANDIDATE"})
    row["state"]=state;row["last_advanced_at"]=at;mapping={"IN_ZONE":"zone_reached_at","IN_RETEST_AREA":"retest_started_at","RETEST_HOLDING":"retest_confirmed_at","ACCEPTED_BREAKOUT":"breakout_confirmed_at","WAITING_FOR_CONFIRMATION":"confirmation_started_at","CONFIRMED":"confirmed_at","ENTRY_AVAILABLE":"entry_available_at","INVALIDATED":"invalidated_at","FAILED_BREAKOUT":"invalidated_at","POST_SPIKE_CANCELLED":"cancelled_by_new_spike_at","REGIME_SWITCH_CANCELLED":"regime_switch_cancelled_at","EXPIRED":"expired_at","MISSED":"missed_at","TOO_LATE":"missed_at","COMPLETED":"completed_at"}
    if state in mapping and row[mapping[state]] is None:row[mapping[state]]=at
    _records[setup_id]=row
    if state in TERMINAL and not any(item["setup_id"]==setup_id for item in _archive):_archive.append(dict(row))
    return dict(row)
def cancel_active_setups_for_regime_switch(symbol,at,direction=None):
    cancelled=[]
    for setup_id,row in list(_records.items()):
        if row["symbol"]!=symbol or row["state"] in TERMINAL or direction and row.get("direction")!=direction:continue
        updated=dict(row);updated["state"]="REGIME_SWITCH_CANCELLED";updated["regime_switch_cancelled_at"]=at;updated["terminal_reason"]="REGIME_SWITCH_CANCELLED";_records[setup_id]=updated
        if not any(item["setup_id"]==setup_id for item in _archive):_archive.append(dict(updated))
        cancelled.append(dict(updated))
    return cancelled
def active_setups(symbol=None):return [dict(row) for row in _records.values() if row["state"] not in TERMINAL and (symbol is None or row["symbol"]==symbol)]
def cancel_active_setups_for_new_event(symbol,event_id,at):
    cancelled=[]
    for setup_id,row in list(_records.items()):
        if row["symbol"]!=symbol or row["state"] in TERMINAL:continue
        updated=dict(row);updated.update(state="NEW_EVENT_CANCELLED",cancelled_by_event_at=at,cancelled_by_event_id=event_id,terminal_reason="NEW_EVENT_CANCELLED");_records[setup_id]=updated
        if not any(item["setup_id"]==setup_id for item in _archive):_archive.append(dict(updated))
        cancelled.append(updated)
    return cancelled
def cancel_active_setups_for_regime_change(symbol,at):
    cancelled=[]
    for setup_id,row in list(_records.items()):
        if row["symbol"]!=symbol or row["state"] in TERMINAL:continue
        updated=dict(row);updated.update(state="REGIME_CHANGED",regime_cancelled_at=at,terminal_reason="REGIME_CHANGED");_records[setup_id]=updated
        if not any(item["setup_id"]==setup_id for item in _archive):_archive.append(dict(updated))
        cancelled.append(updated)
    return cancelled
def cancel_active_strategy_for_auto_replacement(symbol,strategy,at,keep_setup_id=None):
    cancelled=[]
    for setup_id,row in list(_records.items()):
        if row["symbol"]!=symbol or row.get("strategy")!=strategy or row["state"] in TERMINAL or setup_id==keep_setup_id:continue
        updated=dict(row);updated.update(state="AUTO_ROUTER_REPLACED",auto_router_replaced_at=at,terminal_reason="AUTO_ROUTER_REPLACED");_records[setup_id]=updated
        if not any(item["setup_id"]==setup_id for item in _archive):_archive.append(dict(updated))
        cancelled.append(updated)
    return cancelled
def archived_setups():return [dict(row) for row in _archive]
def clear_lifecycle():_records.clear();_archive.clear()
