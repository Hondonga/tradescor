"""Shared projections separating useful context from actionable plan readiness."""
def build_market_analysis(*,market,setup,smc=None,scenario=None):
    smc=smc or {};events=smc.get("structure_events") or [];sweeps=smc.get("sweeps") or []
    view={"available":True,"regime":market.get("volatility_state") or market.get("alignment") or "unknown","external_structure":market.get("external_structure"),"internal_structure":market.get("internal_structure"),"alignment":market.get("alignment"),"directional_bias":setup.get("direction"),"active_leg":setup.get("context_summary"),"recent_bos":next((x for x in reversed(events) if x.get("type")=="bos"),None),"recent_mss":next((x for x in reversed(events) if x.get("type")=="mss"),None),"recent_sweep":sweeps[-1] if sweeps else None,"price_location":setup.get("stage"),"developing_scenario":scenario or setup.get("context_summary"),"invalidation":(setup.get("invalidation") or {}).get("condition"),"next_confirmation":setup.get("next_required_condition")}
    if setup.get("jump_mode")=="JUMP_POST_EVENT_SMC":
        view.update(recent_event=setup.get("recent_event"),confirmation_levels=setup.get("confirmation_levels"),setup_blocker=setup.get("setup_blocker"),price_location="Near lower compression area" if str(market.get("internal_structure") or "").lower()=="compression" else setup.get("stage"))
    external=str(market.get("external_structure") or "").lower();internal=str(market.get("internal_structure") or "").lower();raw_scenario=str(scenario or "").lower()
    bearish_pullback=external in {"bearish","bearish_to_compression","bearish-to-compression"} and internal in {"compression","range","retracement","transition"} and "bullish" not in raw_scenario
    if bearish_pullback and setup.get("jump_mode")!="JUMP_POST_EVENT_SMC":
        view.update(
            continuation_context="bearish_pullback",
            external_structure_display="Bearish directional leg or bearish-to-compression transition",
            internal_structure_display="Retracement / local consolidation",
            developing_scenario="Potential bearish continuation pullback",
            price_location="Price has retraced from the recent structural low toward internal resistance",
            next_confirmation="Completed bearish M5 displacement and break of the latest internal swing low",
        )
    return view
def build_trade_plan(setup,status,reason):
    ready=bool(setup.get("trade_ready"));focused=setup.get("strategy_id")=="volatility_structure_pullback";missing_geometry=setup.get("entry") is None and not setup.get("targets");fallback="Unavailable until all production geometry passes." if focused else "No confirmed entry location and opposing structural target currently produce valid geometry" if missing_geometry and setup.get("direction") in {"sell","bearish"} else reason;return {"available":ready,"status":status,"entry":setup.get("entry") if ready else None,"stop":setup.get("stop") if ready else None,"targets":setup.get("targets") if ready else [],"rr":setup.get("rr") if ready else None,"reason":None if ready else setup.get("plan_blocker") or fallback,"confirmation_present":bool(status and ("CONFIRM" in status or ready)),"entry_geometry_valid":bool(setup.get("entry") is not None and setup.get("stop") is not None),"target_candidates_checked":[]}
