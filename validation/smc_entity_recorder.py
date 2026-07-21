ENTITY_KEYS=("swings","liquidity","displacements","fvgs","order_blocks")
def extract_smc_entities(decisions):
    records=[]
    for item in decisions:
        payload=item.get("payload") or item;smc=payload.get("smc_contract") or {};owner=(smc.get("ownership") or {}).get("decision_owner_id");adapter=(smc.get("ownership") or {}).get("adapter_id")
        for key in ENTITY_KEYS:
            for entity in smc.get(key) or []:records.append(_record(key[:-1],entity,payload,owner,adapter))
        structure=smc.get("structure") or {}
        for key in ("last_bos","last_mss"):
            if structure.get(key):records.append(_record(key.replace("last_",""),structure[key],payload,owner,adapter))
        for key in ("dealing_range","event"):
            if smc.get(key):records.append(_record(key,smc[key],payload,owner,adapter))
        setup=smc.get("setup") or {}
        if setup:records.append(_record("setup_state",setup,payload,owner,adapter))
        trace=smc.get("target_trace") or setup.get("target_trace") or {}
        for target in trace.get("candidates_found") or []:records.append(_record("structural_target",target,payload,owner,adapter))
    return records
def _record(kind,entity,payload,owner,adapter):
    return {"entity_type":kind,"entity_id":next((entity.get(key) for key in ("target_id","swing_id","reference_id","displacement_id","fvg_id","order_block_id","structure_event_id","range_id","event_id","setup_id") if entity.get(key)),None),"creation_candle":entity.get("candle_time") or entity.get("origin_time") or entity.get("created_time") or entity.get("created_at") or entity.get("event_time"),"confirmation_candle":entity.get("confirmation_time") or entity.get("confirmed_at") or entity.get("created_time") or entity.get("created_at") or entity.get("event_time"),"invalidation_candle":entity.get("invalidated_at") or entity.get("terminal_at"),"owning_strategy":owner,"symbol":payload.get("provider_symbol"),"family_adapter":adapter,"replay_decision_id":payload.get("decision_id"),"payload":entity}
