"""Normalize strategy stages without permitting partial READY plans."""
def normalize_strategy_decision(*,eligible,direction,pullback,zone,execution_zone,confirmation,entry,stop,targets,rr,chase,setup_id,range_position=None):
    bias="bullish" if direction=="buy" else "bearish" if direction=="sell" else "neutral";ready=all((eligible,zone and zone.get("valid"),execution_zone and execution_zone.get("valid"),confirmation and confirmation.get("valid"),entry and entry.get("valid"),stop and stop.get("valid"),targets and targets.get("tp1"),rr and rr.get("valid"),chase and chase.get("valid"),range_position is None or range_position.get("valid")))
    if not eligible:status="NO VALID SETUP"
    elif range_position is not None and not range_position.get("valid"):status="AT RANGE EXTREME"
    elif chase and chase.get("state") in {"TOO_LATE","MISSED"}:status="TOO LATE"
    elif ready:status="READY TO BUY" if direction=="buy" else "READY TO SELL"
    elif confirmation and confirmation.get("valid"):status="BUY SETUP FORMING" if direction=="buy" else "SELL SETUP FORMING"
    elif execution_zone and execution_zone.get("valid"):status="WAITING FOR M5 CONFIRMATION"
    elif zone and zone.get("valid"):status="WAITING FOR BUY PULLBACK" if direction=="buy" else "WAITING FOR SELL PULLBACK"
    else:status="BUY BIAS" if direction=="buy" else "SELL BIAS" if direction=="sell" else "NO VALID SETUP"
    next_action=("Review the confirmed paper-analysis plan; no order is placed." if ready else "Price is at the hostile extreme of the M15 dealing range. Wait for a healthier location instead of chasing." if status=="AT RANGE EXTREME" else f"Wait for price to retrace into the selected M15 {'demand' if direction=='buy' else 'supply'} area. A {'buy' if direction=='buy' else 'sell'} becomes actionable only after completed M5 {'bullish' if direction=='buy' else 'bearish'} confirmation." if eligible else "Wait for an eligible aligned Volatility trend.")
    return {"status":status,"market_bias":bias,"developing_direction":direction or "","trade_ready":bool(ready),"setup_id":setup_id if eligible else None,"summary":status.title(),"next_action":next_action,"phase":pullback.get("state","NO_PULLBACK")}

def build_derived_trade_chart(strategy,current_price):
    direction=(strategy.get("decision") or {}).get("developing_direction") or "none";zone=strategy.get("m15_setup_zone") or {};execution=strategy.get("m5_execution_zone") or {};confirmation=strategy.get("confirmation") or {};plan=strategy.get("active_trade_plan") or {};decision=strategy.get("decision") or {}
    if not decision.get("setup_id") or not zone.get("valid"):return {"idea":"none","state":"none","current_price":current_price,"m15_setup_zone":{"low":None,"high":None,"type":""},"m5_execution_zone":{"low":None,"high":None,"type":""},"confirmation":{"price":None,"confirmed":False,"timeframe":"M5"},"confirmed_entry":None,"stop":None,"targets":[],"message":decision.get("next_action","No valid setup.")}
    if decision.get("trade_ready"):state="entry_available"
    elif execution.get("valid"):state="waiting_for_m5_close"
    else:state="waiting_for_m15_area"
    targets=[]
    for name in ("tp1","tp2"):
        row=plan.get(name)
        if row and row.get("price") is not None:targets.append({"name":name.upper(),"price":row["price"],"risk_reward":plan.get(name+"_rr")})
    entry=plan.get("entry")
    return {"idea":direction,"state":state,"current_price":current_price,"m15_setup_zone":{"low":zone.get("low"),"high":zone.get("high"),"type":zone.get("type","")},"m5_execution_zone":{"low":execution.get("low"),"high":execution.get("high"),"type":execution.get("type","")},"confirmation":{"price":confirmation.get("trigger_price"),"direction":"above" if direction=="buy" else "below","confirmed":bool(confirmation.get("valid") and entry is not None),"timeframe":"M5"},"confirmed_entry":entry,"stop":plan.get("stop"),"targets":targets,"distance_to_entry":None,"distance_unit":"points","remaining_rr":(strategy.get("chase") or {}).get("remaining_rr"),"message":decision.get("next_action","")}
