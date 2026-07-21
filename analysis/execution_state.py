"""One authoritative M15-context/M5-execution state for every consumer."""

from __future__ import annotations


ALLOWED={"waiting_for_m15_area","in_m15_area","m5_setup_forming","waiting_for_m5_close","m5_confirmed","entry_available","entry_extended","too_late","invalidated"}


def normalize_execution_state(decision:dict[str,object],*,current_price,minimum_rr=1.5,tolerance=1e-10):
    setup=decision.get("setup") or {}; execution=decision.get("execution") or {}; quality=decision.get("quality") or {}; zone=setup.get("zone") or {}; direction=setup.get("direction"); current=_number(current_price); low=_number(zone.get("low")); high=_number(zone.get("high")); invalidation=_number((setup.get("invalidation") or {}).get("price")); raw=_raw_state(execution.get("state")); entry=_number(execution.get("entry")); stop=_number(execution.get("stop")); trigger=_number((execution.get("confirmed_entry") or {}).get("trigger_price")) or _number((setup.get("confirmation") or {}).get("price")); signal=execution.get("confirmed_state") or {}; confirmed_at=signal.get("candle_time") or (execution.get("confirmed_entry") or {}).get("confirmed_at"); execution_zone=execution.get("m5_execution_zone") or execution.get("entry_zone") or {}; ez_low=_number(execution_zone.get("low")); ez_high=_number(execution_zone.get("high")); targets=execution.get("targets") or []
    if direction not in {"buy","sell"} or low is None or high is None or current is None:
        state="waiting_for_m15_area"; location="UNAVAILABLE"
    else:
        low,high=min(low,high),max(low,high); epsilon=max(tolerance,abs(high)*1e-10); location="BELOW_M15_AREA" if current<low-epsilon else "ABOVE_M15_AREA" if current>high+epsilon else "IN_M15_AREA"; geometry_invalid=invalidation is not None and (invalidation>=low-epsilon if direction=="buy" else invalidation<=high+epsilon)
        completed=bool(signal.get("completed",bool(confirmed_at)) and confirmed_at); locked=bool(completed and entry is not None and trigger is not None and ez_low is not None and ez_high is not None)
        rr=_recalculate_rr(direction,entry,stop,targets); nearest_rr=rr[0] if rr else None; execution["risk_reward"]=nearest_rr; execution["remaining_rr_by_target"]=rr
        stop_valid=entry is not None and stop is not None and (stop<entry if direction=="buy" else stop>entry); targets_valid=bool(rr and nearest_rr is not None and nearest_rr>0); hard_gates=bool(locked and stop_valid and targets_valid and setup.get("setup_id"))
        execution["confirmation_missing_requirements"]=[label for condition,label in ((completed,"completed M5 trigger candle"),(trigger is not None,"confirmed trigger price"),(entry is not None,"confirmed entry price"),(ez_low is not None and ez_high is not None,"M5 execution zone"),(stop_valid,"structural stop"),(targets_valid,"valid unswept target"),(nearest_rr is not None,"remaining RR"),(bool(setup.get("setup_id")),"setup identity"),(bool(confirmed_at),"confirmation timestamp")) if not condition]
        if "invalid" in raw or geometry_invalid:state="invalidated"
        elif completed and not locked:
            state="m5_setup_forming"; execution["entry"]=None; execution["confirmed_entry"]={"price":None,"confirmed_at":None,"trigger_price":None,"trigger_close":None}; execution["stop"]=None; execution["targets"]=[]; entry=None
        elif hard_gates:
            risk=entry-stop if direction=="buy" else stop-entry; chase=max(0.0,current-entry) if direction=="buy" else max(0.0,entry-current); execution["entry_distance"]=chase; remaining_reward=(float(targets[0]["price"])-current if direction=="buy" else current-float(targets[0]["price"])) if targets else None; remaining_rr=remaining_reward/risk if risk>0 and remaining_reward is not None and remaining_reward>0 else None; execution["remaining_rr_from_current"]=remaining_rr
            if nearest_rr<minimum_rr or remaining_rr is None or remaining_rr<1:state="too_late"
            elif raw in {"entry_extended","too_late"} or _extended(chase,entry,execution_zone):state="entry_extended"
            elif quality.get("trade_plan_valid") or raw=="entry_available":state="entry_available"
            else:state="m5_confirmed"
        elif completed:state="m5_setup_forming"
        elif raw=="m5_confirmed":state="m5_setup_forming"
        elif raw=="waiting_for_m5_close":state="waiting_for_m5_close"
        elif location=="IN_M15_AREA":state="m5_setup_forming" if execution.get("forming_state") else "in_m15_area"
        else:state="waiting_for_m15_area"
        execution["confirmation_requirements_passed"]=hard_gates and nearest_rr is not None and nearest_rr>=minimum_rr
    execution["state"]=state; execution["price_location"]=location; decision["execution"]=execution; setup["stage"]=state; setup_confirmation=setup.get("confirmation") or {}; setup_confirmation["confirmed"]=state in {"m5_confirmed","entry_available","entry_extended","too_late"} and entry is not None and confirmed_at is not None; setup["confirmation"]=setup_confirmation; decision["setup"]=setup
    quality["trade_plan_valid"]=bool(state=="entry_available" and execution.get("confirmation_requirements_passed")); decision["quality"]=quality; _sync_output(decision,state,direction)
    return state


def _recalculate_rr(direction,entry,stop,targets):
    if entry is None or stop is None:return []
    risk=entry-stop if direction=="buy" else stop-entry
    if risk<=0:return []
    result=[]
    for row in targets:
        price=_number(row.get("price")); reward=(price-entry if direction=="buy" else entry-price) if price is not None else None; value=reward/risk if reward is not None and reward>0 else None; row["risk_reward"]=round(value,3) if value is not None else None; result.append(row["risk_reward"])
    return result


def _extended(chase,entry,zone):
    low,high=_number(zone.get("low")),_number(zone.get("high")); width=abs(high-low) if low is not None and high is not None else abs(entry)*1e-6; return chase>max(width,abs(entry)*1e-6)


def _raw_state(value):
    text=str(value or "").lower(); return {"waiting_for_zone":"waiting_for_m15_area","waiting_for_area":"waiting_for_m15_area","in_zone":"in_m15_area","in_entry_zone":"in_m15_area","waiting_for_trigger":"m5_setup_forming","confirmation_forming":"m5_setup_forming","trigger_forming":"waiting_for_m5_close","confirmed":"m5_confirmed","trigger_confirmed":"m5_confirmed","extended":"entry_extended","poor_reward":"too_late"}.get(text,text)


def _sync_output(decision,state,direction):
    output=decision.get("user_output") or {}; relationship=((decision.get("ict_model") or {}).get("direction_resolution") or {}).get("relationship")
    if not (decision.get("setup") or {}).get("setup_id") and str(output.get("status","")).startswith("POTENTIAL"):
        output["execution_stage"]=state; output["trade_plan_checks_passed"]=False; decision["user_output"]=output; return
    if state=="entry_available":status="READY TO BUY" if direction=="buy" else "READY TO SELL"; status+=(" — COUNTERTREND" if relationship=="countertrend_reversal_candidate" else "")
    elif state=="invalidated":status="SETUP INVALIDATED"
    elif state=="too_late":status="TOO LATE"
    elif state=="entry_extended":status="ENTRY EXTENDED"
    elif direction in {"buy","sell"}:status=("BUY" if direction=="buy" else "SELL")+" SETUP FORMING"
    else:status="NO VALID SETUP"
    output["status"]=status; output["execution_stage"]=state; output["trade_plan_checks_passed"]=bool(state=="entry_available" and (decision.get("quality") or {}).get("trade_plan_valid"))
    if state=="waiting_for_m15_area":output["next_action"]="Wait for price to reach the M15 setup area."
    elif state in {"in_m15_area","m5_setup_forming"}:
        missing=(decision.get("execution") or {}).get("confirmation_missing_requirements") or []; output["next_action"]=(f"M5 execution is incomplete: waiting for {missing[0]}." if missing else "M15 context is active; wait for a complete M5 execution setup.")
    elif state=="waiting_for_m5_close":output["next_action"]="Wait for the M5 trigger candle to close."
    elif state=="m5_confirmed":output["next_action"]="M5 confirmation is locked; wait for entry availability."
    elif state=="entry_extended":output["next_action"]="The confirmed M5 entry is extended. Wait for a controlled retest."
    elif state=="too_late":output["next_action"]="Poor remaining reward or excessive chase distance. Do not enter."
    decision["user_output"]=output


def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
