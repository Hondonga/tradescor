"""Compact, evidence-only presentation projection for the chart workspace."""

from __future__ import annotations


def build_market_presentation(decision,*,top_down,features,current_price):
    current=_number(current_price); context=_context(decision,top_down,features,current); previous=decision.get("previous_setup"); scenario=_scenario(decision,previous) if not decision.get("active_setup") else {"available":False,"direction":"neutral","strategy":"","label":"","zone":None,"required_event":"","confirmation":"","invalidation_context":"","target_context":"","why":[]}; levels=_levels(top_down,features,current)
    status=(decision.get("user_output") or {}).get("status") or "NO CURRENT SETUP"; active=decision.get("active_setup")
    next_action=(decision.get("user_output") or {}).get("next_action") or _next_action(scenario,levels,current)
    if not active: next_action=_next_action(scenario,levels,current)
    presentation={"decision":{"status":status,"direction":active.get("direction") if active else scenario.get("direction","neutral"),"developing_direction":scenario.get("direction","neutral"),"market_bias":context["market_bias"],"phase":context["phase"],"trade_ready":bool((decision.get("quality") or {}).get("trade_plan_valid")),"next_action":next_action},"market_context":context,"developing_scenario":scenario,"key_levels":levels,"active_trade_plan":{"setup":active,"execution":decision.get("execution")} if active else None,"previous_setup":previous,"advanced_details":{"strategy_routing":decision.get("strategy_routing"),"router":decision.get("router"),"top_down":decision.get("top_down"),"directional_structure":decision.get("directional_structure"),"liquidity_targets":decision.get("liquidity_targets"),"amd":decision.get("amd"),"ict":(decision.get("research_shadow") or {}).get("ict_2022_v2"),"quality":decision.get("quality"),"rejections":(decision.get("quality") or {}).get("rejection_reasons",[])}}
    decision["presentation"]=presentation; decision["current_context"]=context; decision["developing_scenario"]=scenario; decision["key_levels"]={"nearest_support":levels["support"],"nearest_resistance":levels["resistance"],"buy_side_liquidity":levels["liquidity_above"],"sell_side_liquidity":levels["liquidity_below"]}
    decision["user_output"]["next_action"]=next_action
    return presentation


def _context(decision,top_down,features,current):
    alignment=decision.get("alignment") or {}; regime=str((decision.get("market_regime") or {}).get("value") or (top_down.get("regime") or {}).get("value") or "neutral").lower(); primary=str(alignment.get("primary_direction","neutral")); local=decision.get("directional_structure") or {}; local_direction=str(local.get("direction","neutral")); htf=[str(((top_down.get("timeframes") or {}).get(tf) or {}).get("bias","neutral")) for tf in ("D1","H4","H1")]; local_supported=local_direction in {"bullish","bearish"} and htf.count(local_direction)>=2; bias="bullish" if primary=="buy" else "bearish" if primary=="sell" else local_direction if local_supported else "mixed" if alignment.get("state") in {"mixed","countertrend"} or regime=="transition" else local_direction if local_direction in {"bullish","bearish"} else "range" if regime in {"range","ranging"} else "neutral"
    m15=(top_down.get("timeframes") or {}).get("M15") or {}; structure=f"{local_direction}_continuation" if local_direction in {"bullish","bearish"} and local.get("structure") in {"continuation","breakdown","breakout"} else str(m15.get("structure") or "unavailable"); frame=((features.get("timeframes") or {}).get("M15") or {}); direction=_feature(frame,"structure_direction") or local_direction; displacement=_feature(frame,"displacement") or {}; volatility=_feature(frame,"volatility_regime") or "unknown"; range_data=_feature(frame,"range") or {}; position=_number(range_data.get("position"))
    momentum=(f"{str(displacement.get('direction')).title()} displacement" if displacement.get("active") else f"{str(direction).title()} momentum" if direction!="neutral" else "Mixed momentum")
    location="Extended above range" if position is not None and position>1 else "Extended below range" if position is not None and position<0 else "Near resistance" if position is not None and position>=.8 else "Near support" if position is not None and position<=.2 else "Mid-range" if position is not None else str(m15.get("location") or "Unavailable").replace("_"," ").title()
    summary=f"{bias.title()} higher-timeframe context · {structure.replace('_',' ')}."
    return {"market_bias":bias,"regime":regime,"phase":str(local.get("structure") or regime),"structure":structure,"momentum":momentum,"price_location":location,"volatility":str(volatility),"summary":summary,"higher_timeframes":_htf_summary(top_down)}


def _scenario(decision,previous):
    candidates=(decision.get("router") or {}).get("candidates") or []; prior_low=_number((previous or {}).get("entry_low")); prior_high=_number((previous or {}).get("entry_high"))
    usable=[]
    for row in candidates:
        zone=row.get("zone") or {}; low=_number(zone.get("low")); high=_number(zone.get("high")); direction=row.get("direction")
        if direction not in {"buy","sell"} or low is None or high is None: continue
        low,high=min(low,high),max(low,high)
        if prior_low is not None and prior_high is not None and abs(low-prior_low)<1e-12 and abs(high-prior_high)<1e-12: continue
        quality=float(row.get("candidate_score") or row.get("present_quality_score") or 0); usable.append((bool(row.get("eligible")),quality,row,low,high))
    local_side="sell" if (decision.get("directional_structure") or {}).get("direction")=="bearish" else "buy" if (decision.get("directional_structure") or {}).get("direction")=="bullish" else None
    if local_side and any(value[2].get("direction")==local_side for value in usable): usable=[value for value in usable if value[2].get("direction")==local_side]
    if not usable:
        local=decision.get("directional_structure") or {}; direction="sell" if local.get("direction")=="bearish" else "buy" if local.get("direction")=="bullish" else "neutral"
        if direction in {"buy","sell"}:
            area=local.get("pullback_area"); bearish=direction=="sell"
            return {"available":True,"direction":direction,"strategy":"supply_demand","setup_type":"pullback_continuation","label":f"Potential {'Sell' if bearish else 'Buy'} Pullback","zone":{"low":area.get("low"),"high":area.get("high"),"type":area.get("type"),"origin_time":area.get("formed_at")} if area else None,"zone_source":area.get("type") if area else None,"required_event":f"Price retraces into {'resistance or supply' if bearish else 'support or demand'}." if area else f"{'Sell' if bearish else 'Buy'} area forming.","confirmation":f"completed M5 {'bearish' if bearish else 'bullish'} reaction","invalidation_context":"above the latest valid lower high" if bearish else "below the latest valid higher low","target_context":f"nearest unswept {'sell-side' if bearish else 'buy-side'} liquidity","stage":"searching_for_pullback","why":local.get("evidence",[])[:2]}
        return {"available":False,"direction":"neutral","strategy":"","label":"","zone":None,"required_event":"","confirmation":"","invalidation_context":"","target_context":"","why":[]}
    _,_,row,low,high=max(usable,key=lambda value:(value[0],value[1])); direction=row["direction"]; relationship=str(row.get("relationship") or (row.get("diagnostics") or {}).get("relationship") or ""); label=f"Potential {'Buy Reversal' if direction=='buy' and 'countertrend' in relationship else 'Sell Reversal' if direction=='sell' and 'countertrend' in relationship else 'Buy Pullback' if direction=='buy' else 'Sell Pullback'}"
    requirements=row.get("confirmation_requirements") or []; confirmation=next((str(value) for value in reversed(requirements) if "M5" in str(value)),str(requirements[-1]) if requirements else "")
    required=next((str(value) for value in requirements if any(word in str(value).lower() for word in ("price","retest","area","zone","array"))),"Price retraces into the developing area.")
    reasons=[str(value) for value in row.get("eligibility_reasons",[]) if value][:2] or [str(value) for value in row.get("rejection_reasons",[]) if value][:2]
    return {"available":True,"direction":direction,"strategy":row.get("strategy_id",""),"setup_type":row.get("setup_type",""),"label":label,"zone":{"low":low,"high":high,"type":zone.get("type",""),"origin_time":zone.get("origin_time")},"required_event":required,"confirmation":confirmation,"invalidation_context":"Invalid if the developing structure fails before M5 confirmation.","target_context":"Targets remain conditional until entry, stop, and RR validate.","why":reasons,"candidate_id":row.get("candidate_id")}


def _levels(top_down,features,current):
    m15=(top_down.get("timeframes") or {}).get("M15") or {}; highs=[_number(row.get("price")) for row in m15.get("unswept_highs") or []]; lows=[_number(row.get("price")) for row in m15.get("unswept_lows") or []]; highs=[value for value in highs if value is not None and (current is None or value>current)]; lows=[value for value in lows if value is not None and (current is None or value<current)]
    local=top_down.get("directional_structure") or {}; structural_highs=[_number(local.get("last_lower_high")),_number(local.get("broken_structure_level"))] if local.get("direction")=="bearish" else []; structural_lows=[_number(local.get("last_higher_low")),_number(local.get("broken_structure_level"))] if local.get("direction")=="bullish" else []; highs.extend(value for value in structural_highs if value is not None and (current is None or value>current)); lows.extend(value for value in structural_lows if value is not None and (current is None or value<current)); resistance=min(highs) if highs else _side(m15.get("recent_high"),current,"above"); support=max(lows) if lows else _side(m15.get("recent_low"),current,"below")
    frame=((features.get("timeframes") or {}).get("M15") or {}); liquidity=_feature(frame,"liquidity") or {}; equal_highs=[_number(row.get("price")) for row in liquidity.get("equal_highs") or []]; equal_lows=[_number(row.get("price")) for row in liquidity.get("equal_lows") or []]
    above=min([value for value in equal_highs if value is not None and (current is None or value>current)],default=None); below=max([value for value in equal_lows if value is not None and (current is None or value<current)],default=None); local_high=_number(local.get("last_higher_high")); local_low=_number(local.get("last_lower_low")); above=above if above is not None else local_high if local_high is not None and (current is None or local_high>current) else None; below=below if below is not None else local_low if local_low is not None and (current is None or local_low<current) else None
    if above is not None and resistance is not None and abs(above-resistance)<1e-12: above=None
    if below is not None and support is not None and abs(below-support)<1e-12: below=None
    atr=_number(_feature(frame,"atr")); band=atr*.12 if atr else None
    return {"support":support,"resistance":resistance,"liquidity_above":above,"liquidity_below":below,"support_zone":{"low":support-band,"high":support+band} if support is not None and band else None,"resistance_zone":{"low":resistance-band,"high":resistance+band} if resistance is not None and band else None}


def _next_action(scenario,levels,current):
    if scenario.get("available"):
        zone=scenario.get("zone") or {}; low=_number(zone.get("low")); high=_number(zone.get("high")); side="buy" if scenario.get("direction")=="buy" else "sell"
        if low is not None and high is not None:return f"Watch for price to reach {low:.5f}–{high:.5f}, then require {scenario.get('confirmation') or f'completed M5 {side} confirmation'}."
        if scenario.get("required_event"):return str(scenario["required_event"])
    if levels.get("support") is not None and levels.get("resistance") is not None:return "Wait for price to react at the nearest support or resistance before evaluating a confirmed M5 setup."
    return "Wait for fresh completed-candle structure before evaluating an entry."


def _htf_summary(top_down):
    frames=top_down.get("timeframes") or {}; values=[str((frames.get(tf) or {}).get("bias","neutral")) for tf in ("D1","H4","H1")]; return " / ".join(value.title() for value in values)
def _feature(frame,name): return ((frame.get(name) or {}).get("value"))
def _side(value,current,side):
    number=_number(value); return number if number is not None and (current is None or (number>current if side=="above" else number<current)) else None
def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
