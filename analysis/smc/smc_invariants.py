"""Absolute trade-readiness invariants shared by live, replay, and paper flows."""
READY_STATUSES={"TRADE_READY","READY TO BUY","READY TO SELL","RESEARCH BUY SETUP","RESEARCH SELL SETUP"}


def validate_trade_ready_invariants(decision):
    setup=decision.get("setup") or {};public=decision.get("decision") or {};ownership=decision.get("ownership") or {}
    status=str(public.get("status") or setup.get("state") or "").upper();asserted=bool(public.get("trade_ready") or setup.get("state")=="TRADE_READY" or status in READY_STATUSES)
    violations=[]
    def require(condition,code,message):
        if not condition:violations.append({"code":code,"message":message,"blocking":True})
    selected=ownership.get("selected_strategy_id") or ownership.get("selected_model_id");owner=ownership.get("decision_owner_id");overlay=ownership.get("overlay_owner_id") or (decision.get("trade_chart") or {}).get("owner_id")
    require(bool(selected and owner and overlay and selected==owner==overlay),"OWNER_MISMATCH","Selected model, decision owner, and overlay owner must match.")
    if asserted:
        direction=setup.get("direction") or public.get("developing_direction") or public.get("direction");entry=setup.get("entry");stop=setup.get("stop");targets=setup.get("targets") or [];tp1=targets[0].get("price") if targets else None;rr=setup.get("rr")
        require(decision.get("production_supported",setup.get("production_supported",True)) is not False,"STRATEGY_NOT_PRODUCTION_SUPPORTED","Only a production-supported strategy may become trade-ready.")
        require(decision.get("family_compatible",setup.get("family_compatible",True)) is not False,"FAMILY_INCOMPATIBLE","The strategy and selected market family must be compatible.")
        require(bool(setup.get("setup_id") or public.get("setup_id")),"MISSING_SETUP_ID","Trade-ready state requires a stable setup ID.")
        require(direction in {"buy","sell"},"INVALID_DIRECTION","Trade-ready direction must be buy or sell.")
        require(bool(setup.get("mss") or setup.get("bos") or setup.get("completed_confirmation")),"MISSING_CONFIRMATION","A completed confirmation is required.")
        require(entry is not None,"MISSING_ENTRY","Trade-ready state requires an entry.")
        require(stop is not None,"MISSING_STOP","Trade-ready state requires a structural stop.")
        require(tp1 is not None,"MISSING_TP1","Trade-ready state requires TP1.")
        if entry is not None and stop is not None:
            require(stop<entry if direction=="buy" else stop>entry,"INVALID_STOP_GEOMETRY","Stop must remain on the risk side of entry.")
        if entry is not None and tp1 is not None:
            require(tp1>entry if direction=="buy" else tp1<entry,"INVALID_TARGET_GEOMETRY","TP1 must remain on the profitable side of entry.")
        require(rr is not None and float(rr)>=1.5,"RR_BELOW_MINIMUM","TP1 reward-to-risk must meet the configured minimum.")
        require(setup.get("chase_valid",setup.get("state")!="TOO_LATE"),"CHASE_REJECTED","Entry extension or chase validation failed.")
        target=setup.get("structural_target") or {}
        require(not (target.get("swept") or target.get("accepted_beyond") or target.get("consumed")),"TARGET_CONSUMED","Selected TP1 is no longer an active structural objective.")
        require(not setup.get("event_risk"),"EVENT_RISK_ACTIVE","Active event risk blocks readiness.")
        require(setup.get("state") not in {"INVALIDATED","CLOSED","EXPIRED"},"INVALID_LIFECYCLE","Setup lifecycle is terminal.")
        require(not setup.get("stale"),"STALE_SETUP","Stale setups cannot be trade-ready.")
        require(not (decision.get("future_data_access") or setup.get("future_data_access")),"LOOKAHEAD_VIOLATION","Every actionable value must be visible at the decision timestamp.")
        readiness=decision.get("readiness")
        if readiness is not None:require(bool(readiness.get("ready") or readiness.get("state")=="ready"),"DATA_NOT_READY","Required completed-candle history is unavailable.")
    corrected=_corrected_status(violations)
    return {"valid":not violations,"violations":violations,"failures":[row["message"] for row in violations],"corrected_status":corrected,"corrective_action":"Block readiness, clear actionable overlays, and preserve developing context." if violations else None}


def validate_smc_contract(contract):
    """Compatibility name retained for existing callers."""
    return validate_trade_ready_invariants(contract)


def _corrected_status(violations):
    codes={row["code"] for row in violations}
    if "EVENT_RISK_ACTIVE" in codes:return "EVENT RISK"
    if "DATA_NOT_READY" in codes:return "INSUFFICIENT DATA"
    if "OWNER_MISMATCH" in codes:return "STATE CONTRADICTION"
    return "PLAN REJECTED" if violations else None
