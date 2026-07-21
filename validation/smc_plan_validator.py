def validate_trade_plan(decision):
    payload=decision.get("payload") or decision;smc=payload.get("smc_contract") or {};setup=smc.get("setup") or {};ownership=smc.get("ownership") or {};chart=smc.get("trade_chart") or {};failures=[]
    if setup.get("state")!="TRADE_READY":return {"applicable":False,"valid":True,"failures":[]}
    direction=setup.get("direction");entry=setup.get("entry");stop=setup.get("stop");targets=setup.get("targets") or [];tp1=targets[0].get("price") if targets else None
    if ownership.get("decision_owner_id")!=ownership.get("overlay_owner_id"):failures.append("owner_overlay_mismatch")
    if None in (entry,stop,tp1):failures.append("missing_geometry")
    elif direction=="buy" and not stop<entry<tp1 or direction=="sell" and not tp1<entry<stop:failures.append("wrong_side_geometry")
    if setup.get("rr") is None or setup.get("rr")<1.5:failures.append("minimum_rr_failed")
    target=setup.get("structural_target") or {}
    if not target or target.get("swept") or target.get("accepted_beyond"):failures.append("invalid_structural_target")
    if chart.get("confirmed_entry")!=entry or chart.get("stop")!=stop or (chart.get("targets") or [])!=targets:failures.append("chart_backend_mismatch")
    if str(setup.get("event_risk") or "").upper() in {"EVENT_RISK_ACTIVE","ACTIVE","QUARANTINE"}:failures.append("active_jump_event")
    if (smc.get("event") or {}).get("qualified") and (setup.get("entry_array") or {}).get("origin_time","")<(smc.get("event") or {}).get("event_time",""):failures.append("pre_event_jump_plan")
    return {"applicable":True,"valid":not failures,"failures":failures,"decision_id":payload.get("decision_id")}
