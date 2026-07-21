"""Backend-owned drawing contract for Forex ICT decisions only."""
from __future__ import annotations
import hashlib,json

def build_forex_overlay_contract(product,legacy,fields,invariants_valid):
    ict=legacy.get("ict_model") or ((legacy.get("research_shadow") or {}).get("ict_2022_v2")) or {};owner="ict_2022";symbol=product["meta"]["symbol"];setup=ict.get("setup") or {};setup_id=setup.get("setup_id") if fields.get("direction") else None;narrative=ict.get("narrative") or {};liquidity=ict.get("liquidity") or {};events=ict.get("sequence_events") or {};execution=ict.get("execution") or {};quality=ict.get("quality") or {};terminal=fields.get("scenario_state") in {"EXPIRED","INVALIDATED","TOO_LATE"};rows=[]
    def add(kind,*,price=None,low=None,high=None,timeframe="M15",source="ict_2022",created=None,expires=None,category="context",visibility="advanced_smc",name=None,setup_owner=setup_id,active=True,actionable=False,extra=None):
        values={"price":price,"low":low,"high":high};seed=[owner,setup_owner,symbol,timeframe,category,kind,source,created,price,low,high];row={"overlay_id":"forex-overlay-"+hashlib.sha256(json.dumps(seed,default=str,separators=(",",":")).encode()).hexdigest()[:20],"decision_owner_id":owner,"owner_id":owner,"setup_id":setup_owner,"symbol":symbol,"timeframe":timeframe,"category":category,"visibility_category":visibility,"type":kind,"source":source,"created_at":created,"creation_time":created,"expires_at":expires,"active":bool(active),"actionable":bool(actionable),"actionable_at_decision_time":bool(actionable),"state":"active" if active else "inactive","name":name or kind.replace("_"," ").title(),**{key:value for key,value in values.items() if value is not None},**(extra or {})};rows.append(row);return row
    current=(product.get("market") or {}).get("current_price")
    if current is not None:add("current_price",price=current,timeframe=product["meta"]["timeframe"],source="twelve_data_completed_candle",created=product["meta"]["analysis_time"],visibility="market_structure",setup_owner=None,name="Current")
    refs=[]
    for label,pool in (("Directional Liquidity",liquidity.get("directional_target")),("Opposing Liquidity",liquidity.get("opposing_pool"))):
        if pool and pool.get("price") is not None:
            refs.append(pool);add("liquidity_reference",price=pool["price"],timeframe=pool.get("source_timeframe") or "M15",source=pool.get("type") or "ict_liquidity",created=pool.get("formed_at"),name=label,setup_owner=None,extra={"liquidity_id":pool.get("liquidity_id"),"side":pool.get("side")})
    feature_frames=(legacy.get("market_features") or {}).get("timeframes") or {}
    for timeframe in ("H1","M15"):
        swings=(((feature_frames.get(timeframe) or {}).get("swings") or {}).get("value") or {})
        for side,label in (("highs",f"{timeframe} Swing High"),("lows",f"{timeframe} Swing Low")):
            candidates=[row for row in swings.get(side,[]) if row.get("price") is not None and not row.get("swept")]
            if candidates:
                row=candidates[-1];add("swing_high" if side=="highs" else "swing_low",price=row["price"],timeframe=timeframe,source="confirmed_swing",created=row.get("time"),setup_owner=None,name=label)
        pools=(((feature_frames.get(timeframe) or {}).get("liquidity") or {}).get("value") or {})
        for side,label in (("equal_highs","Equal Highs"),("equal_lows","Equal Lows")):
            candidates=[row for row in pools.get(side,[]) if row.get("price") is not None and not row.get("swept")]
            if candidates:
                row=candidates[-1];add(side[:-1],price=row["price"],timeframe=timeframe,source=side,created=row.get("time"),setup_owner=None,name=f"{timeframe} {label}")
    sweep={} if terminal else (setup.get("sweep") or {})
    if sweep.get("sweep_extreme") is not None:add("liquidity_sweep",price=sweep["sweep_extreme"],source="confirmed_liquidity_sweep",created=sweep.get("sweep_time"),name="Confirmed Liquidity Sweep",extra={"event_time":sweep.get("sweep_time")})
    mss={} if terminal else (setup.get("mss") or {})
    if mss.get("level") is not None:add("mss",price=mss["level"],source="confirmed_market_structure_shift",created=mss.get("break_time"),name="MSS",extra={"event_time":mss.get("break_time")})
    displacement={} if terminal else (setup.get("displacement") or {})
    if displacement.get("confirmed"):
        add("displacement",price=displacement.get("structure_level_broken"),source="confirmed_displacement",created=displacement.get("start_time"),expires=displacement.get("end_time"),name="Displacement",extra={"event_time":displacement.get("end_time"),"direction":displacement.get("direction")})
    array={} if terminal else (setup.get("entry_array") or {})
    fvg_rows=[]
    if array.get("low") is not None and array.get("high") is not None:
        fvg=add("fvg",low=array["low"],high=array["high"],source=array.get("type") or "displacement_fvg",created=array.get("formed_at"),expires=setup.get("expires_at"),name="FVG");fvg_rows.append(fvg)
        if fields.get("entry_zone"):
            add("developing_entry_area",low=array["low"],high=array["high"],source=array.get("type") or "ict_entry_array",created=array.get("formed_at"),expires=setup.get("expires_at"),visibility="trade_plan",name="DEVELOPING · NOT AN ENTRY",actionable=False)
    dealing=narrative.get("dealing_range") or {}
    if dealing.get("low") is not None and dealing.get("high") is not None:
        add("dealing_range",low=dealing["low"],high=dealing["high"],timeframe=dealing.get("source_timeframe") or "H4",source="locked_ict_dealing_range",created=dealing.get("created_at"),setup_owner=None,name="Dealing Range")
        if dealing.get("equilibrium") is not None:add("equilibrium",price=dealing["equilibrium"],timeframe=dealing.get("source_timeframe") or "H4",source="dealing_range_midpoint",created=dealing.get("created_at"),setup_owner=None,name="Equilibrium")
        if dealing.get("equilibrium") is not None:
            add("discount_zone",low=dealing["low"],high=dealing["equilibrium"],timeframe=dealing.get("source_timeframe") or "H4",source="dealing_range_discount",created=dealing.get("created_at"),setup_owner=None,name="Discount")
            add("premium_zone",low=dealing["equilibrium"],high=dealing["high"],timeframe=dealing.get("source_timeframe") or "H4",source="dealing_range_premium",created=dealing.get("created_at"),setup_owner=None,name="Premium")
    trigger=execution.get("trigger")
    if fields.get("entry_zone") and trigger is not None:add("confirmation_level",price=trigger,timeframe="M5",source="current_ict_execution_trigger",created=product["meta"]["analysis_time"],visibility="trade_plan",name="M5 Confirmation",actionable=False)
    selected=((setup.get("liquidity_targets") or {}).get("selected_targets") or {})
    objectives=[]
    if not fields.get("trade_plan"):
        for target in (selected.get("tp1"),selected.get("tp2")):
            if target and target.get("price") is not None:
                objective={"name":"Potential Structural Objective","price":target["price"],"source":target.get("type") or "structural_liquidity","source_timeframe":target.get("source_timeframe"),"reason":target.get("reason"),"actionable":False};objectives.append(objective);add("structural_objective",price=target["price"],timeframe=target.get("source_timeframe") or "M15",source=target.get("type") or "structural_liquidity",created=target.get("formed_at") or target.get("confirmed_at"),visibility="context_levels",name="Potential Structural Objective",actionable=False,extra={"objective_reason":target.get("reason")})
    plan=fields.get("trade_plan") or {};targets=plan.get("targets") or [];complete=bool(invariants_valid and fields.get("direction") and fields.get("m5_confirmation") and plan.get("entry") is not None and plan.get("stop") is not None and targets and plan.get("rr") is not None and quality.get("trade_plan_valid"))
    if complete:
        add("entry",price=plan["entry"],timeframe="M5",source="completed_m5_confirmation",created=fields["m5_confirmation"],category="actionable",visibility="trade_plan",name="ENTRY",actionable=True)
        add("stop",price=plan["stop"],timeframe="M5",source="protected_m5_structure",created=fields["m5_confirmation"],category="actionable",visibility="trade_plan",name="STOP",actionable=True)
        for index,target in enumerate(targets[:2]):
            if target.get("price") is not None:add("target",price=target["price"],timeframe=target.get("source_timeframe") or "M15",source=target.get("type") or target.get("reason") or "selected_structural_target",created=fields["m5_confirmation"],category="actionable",visibility="trade_plan",name=f"TP{index+1}",actionable=True,extra={"risk_reward":target.get("risk_reward")})
        invalidation=setup.get("invalidation")
        if invalidation is not None:add("trade_plan_invalidation",price=invalidation,timeframe="M15",source="validated_ict_invalidation",created=setup.get("created_at"),category="actionable",visibility="trade_plan",name="INVALIDATION",actionable=True)
    historical=[]
    payload={"liquidity_references":refs,"liquidity_sweeps":[sweep] if sweep else [],"structure_events":[mss] if mss else [],"displacements":[displacement] if displacement else [],"fvgs":[array] if array else [],"order_blocks":[],"dealing_range":dealing or None,"setup_area":array if fields.get("entry_zone") else None,"confirmation_level":trigger if fields.get("entry_zone") else None,"trade_plan":plan if complete else None,"potential_structural_objectives":objectives,"historical":historical}
    return rows,payload,complete
