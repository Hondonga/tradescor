def normalize_event_decision(*,eligible,event,cooldown,volatility,structure,selected,confirmation,ready,chase=None):
    if not eligible:status="DATA UNAVAILABLE"
    elif not event:status="NORMAL MARKET"
    elif cooldown and cooldown.get("active"):status="POST-EVENT COOLDOWN" if volatility and volatility.get("volatility_state")!="uncontrolled" else "RECALIBRATING VOLATILITY"
    elif not structure.get("formed_after_event"):status="WAITING FOR FRESH STRUCTURE"
    elif not selected:status="NO VALID SETUP"
    elif chase and chase.get("state") in {"TOO_LATE","MISSED"}:status="TOO LATE"
    elif ready:status=("READY TO BUY" if selected["direction"]=="buy" else "READY TO SELL")+(" — POST-EVENT RECOVERY" if selected["scenario"]=="down_event_bullish_recovery" else " — POST-EVENT REJECTION" if selected["scenario"]=="up_event_bearish_rejection" else "")
    elif confirmation and confirmation.get("valid"):status="WAITING FOR M5 CONFIRMATION"
    else:status={"up_event_bullish_continuation":"POTENTIAL BUY CONTINUATION","up_event_bearish_rejection":"POTENTIAL SELL REJECTION","down_event_bearish_continuation":"POTENTIAL SELL CONTINUATION","down_event_bullish_recovery":"POTENTIAL BUY RECOVERY"}.get(selected.get("scenario"),"WAITING FOR PULLBACK")
    direction=selected.get("direction") if selected else "";return {"status":status,"market_bias":"bullish" if direction=="buy" else "bearish" if direction=="sell" else "neutral","developing_direction":direction,"trade_ready":bool(ready),"scenario":selected.get("scenario","") if selected else "","event_relationship":selected.get("event_relationship","") if selected else "","event_id":event.get("event_id") if event else None,"setup_id":selected.get("setup_id") if selected else None,"summary":status.title(),"next_action":"Review the validated paper-analysis plan; no order is placed." if ready else "Wait for fresh completed-candle post-event structure. Do not chase the event."}
