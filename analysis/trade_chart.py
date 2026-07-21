"""Backend-only projection of one decision into a trader-facing chart plan."""

from __future__ import annotations


def build_trade_chart(decision: dict[str, object], *, current_price, asset_rules: dict[str, object]) -> dict[str, object]:
    setup=decision.get("setup") or {}; execution=decision.get("execution") or {}; quality=decision.get("quality") or {}; zone=setup.get("zone") or {}; direction=str(setup.get("direction","neutral")); low=_number(zone.get("low")); high=_number(zone.get("high")); current=_number(current_price)
    has_setup=bool(setup.get("setup_id") and direction in {"buy","sell"} and low is not None and high is not None)
    if not has_setup:return _empty(current,asset_rules)
    low,high=min(low,high),max(low,high); ready=bool(quality.get("trade_plan_valid")); raw=str(execution.get("state") or setup.get("stage") or "")
    inside=current is not None and low<=current<=high; distance=_distance(current,low,high); unit,unit_value,percent=_units(distance,current,asset_rules)
    state=_state(raw,inside,ready,distance,low,high,asset_rules); idea=direction
    preferred=_preferred(decision,low,high); confirmed_entry=_number((execution.get("confirmed_entry") or {}).get("price")); confirmed_entry=confirmed_entry if confirmed_entry is not None else _number(execution.get("entry")) if ready and state=="entry_available" else None; execution_zone=execution.get("m5_execution_zone") or execution.get("entry_zone"); confirmed_plan=confirmed_entry is not None and state in {"m5_confirmed","entry_available","entry_extended","too_late"}; active_plan=confirmed_plan
    confirmation_source=setup.get("confirmation") or {}; trigger=_number(confirmation_source.get("price")); confirmed=bool(confirmation_source.get("confirmed") and confirmed_entry is not None)
    if state in {"waiting_for_zone","near_zone"}: trigger=None
    invalidation=_number((setup.get("invalidation") or {}).get("price"))
    confirmed_entry=confirmed_entry if active_plan else None; stop=_number(execution.get("stop")) if active_plan else None
    targets=[]
    if active_plan:
        for row in execution.get("targets") or []:
            price=_number(row.get("price")); rr=_number(row.get("risk_reward"))
            if price is not None and ((direction=="buy" and price>confirmed_entry) or (direction=="sell" and price<confirmed_entry)) and not row.get("swept"):
                targets.append({"name":row.get("name") or f"TP{len(targets)+1}","price":price,"risk_reward":rr})
    else:
        for row in execution.get("projected_targets") or []:
            price=_number(row.get("price")); rr=_number(row.get("risk_reward"))
            if price is not None and ((direction=="buy" and price>high) or (direction=="sell" and price<low)) and row.get("valid",True) and not row.get("swept"):
                targets.append({"name":row.get("name") or f"TP{len(targets)+1}","price":price,"risk_reward":rr,"reason":row.get("reason"),"source_timeframe":row.get("source_timeframe"),"projected":True})
    geometry_valid=(invalidation is None or (invalidation<low if direction=="buy" else invalidation>high)) and (not active_plan or (stop is not None and confirmed_entry is not None and (stop<confirmed_entry if direction=="buy" else stop>confirmed_entry)))
    if not geometry_valid:return {**_empty(current,asset_rules),"state":"invalidated","message":"Setup geometry is invalid."}
    relation="inside" if inside else "below" if current is not None and current<low else "above"
    message=_message(direction,state,unit_value,unit,confirmed_entry,relation)
    entry_distance=abs(current-confirmed_entry) if current is not None and confirmed_entry is not None else None; entry_unit,entry_unit_value,_=_units(entry_distance,current,asset_rules)
    return {"idea":idea,"state":state,"current_price":current,"m15_setup_zone":{"low":low,"high":high,"type":zone.get("type","")},"m5_execution_zone":execution_zone or {"low":None,"high":None,"type":""},"expected_entry":{"low":low,"high":high,"preferred":preferred,"origin_time":zone.get("origin_time")},"confirmation":{"price":trigger,"direction":"above" if direction=="buy" else "below","confirmed":confirmed,"timeframe":"M5"},"invalidation":{"price":invalidation},"confirmed_entry":confirmed_entry,"stop":stop,"targets":targets,"distance_to_entry":entry_unit_value if confirmed_entry is not None else unit_value,"distance_unit":entry_unit if confirmed_entry is not None else unit,"distance_percent":percent,"remaining_rr":_number(execution.get("risk_reward")) if confirmed_plan else None,"message":message}


def _state(raw,inside,ready,distance,low,high,rules):
    text=raw.lower()
    return text if text in {"waiting_for_m15_area","in_m15_area","m5_setup_forming","waiting_for_m5_close","m5_confirmed","entry_available","entry_extended","too_late","invalidated"} else "waiting_for_m15_area"
def _preferred(decision,low,high):
    model=decision.get("ict_model") or {}; value=_number((((model.get("setup") or {}).get("entry_array") or {}).get("preferred_price")))
    return value if value is not None and low<=value<=high else None
def _distance(current,low,high):
    if current is None:return None
    if current<low:return low-current
    if current>high:return current-high
    return 0.0
def _units(distance,current,rules):
    if distance is None:return "points",None,None
    if rules.get("asset_class")=="forex":return "pips",round(distance/float(rules["pip_size"]),1),None
    percent=round(distance/current*100,2) if current else None
    return "points",round(distance,2),percent
def _message(direction,state,distance,unit,entry,relation):
    side="buy" if direction=="buy" else "sell"
    if state=="waiting_for_m15_area":return f"Price is {distance:.1f} {unit} {relation} the M15 context area. Wait for M5 execution."
    if state in {"in_m15_area","m5_setup_forming"}:return "M15 context is active; M5 execution is still forming."
    if state=="waiting_for_m5_close":return "Wait for the M5 trigger candle to close."
    if state in {"m5_confirmed","entry_available"}:return f"M5 entry confirmed at {entry:.5f}." if entry is not None else "M5 execution is still forming."
    if state in {"entry_extended","too_late"}:return "Price has moved away from the confirmed M5 entry. Do not chase."
    if state=="invalidated":return "The setup has been invalidated."
    return "No active trade idea."
def _empty(current,rules):return {"idea":"none","state":"none","current_price":_number(current),"m15_setup_zone":{"low":None,"high":None,"type":""},"m5_execution_zone":{"low":None,"high":None,"type":""},"expected_entry":{"low":None,"high":None,"preferred":None,"origin_time":None},"confirmation":{"price":None,"direction":"above","confirmed":False,"timeframe":"M5"},"invalidation":{"price":None},"confirmed_entry":None,"stop":None,"targets":[],"distance_to_entry":None,"distance_unit":"pips" if rules.get("asset_class")=="forex" else "points","distance_percent":None,"remaining_rr":None,"message":"No active trade idea."}
def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
