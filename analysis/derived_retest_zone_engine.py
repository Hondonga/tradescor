"""Narrow boundary-anchored retest zones and live/completed location states."""
def build_retest_zone(locked_range,breakout,atr,config=None):
    if not locked_range or not breakout or not breakout.get("accepted"):return None
    cfg=config or {};direction=breakout["direction"];boundary=float(locked_range["high"] if direction=="bullish" else locked_range["low"]);width=max(float(atr or 0)*float(cfg.get("retest_zone_width_atr",.15)),abs(float(locked_range["high"]-locked_range["low"]))*.03);low=boundary-width if direction=="bullish" else boundary;high=boundary if direction=="bullish" else boundary+width
    return {"boundary":boundary,"low":low,"high":high,"direction":direction,"formed_at":breakout.get("breakout_time"),"source":"locked_range_boundary","width_points":width,"width_atr":width/atr if atr else None,"valid":width>0 and width<float(locked_range["high"]-locked_range["low"])}
def classify_retest_location(completed_close,live_price,retest_zone,locked_range,atr):
    if not retest_zone:return {"completed_candle_state":"WAITING_FOR_RETEST","live_price_state":"WAITING_FOR_RETEST","distance_to_retest_points":None,"distance_to_retest_atr":None}
    direction=retest_zone["direction"];boundary=retest_zone["boundary"]
    def state(price,completed=False):
        if price is None:return "WAITING_FOR_RETEST"
        if direction=="bullish" and completed and price<boundary or direction=="bearish" and completed and price>boundary:return "FAILED_BREAKOUT"
        if retest_zone["low"]<=price<=retest_zone["high"]:return "IN_RETEST_AREA"
        distance=min(abs(price-retest_zone["low"]),abs(price-retest_zone["high"]));return "APPROACHING_RETEST" if atr and distance<=atr*.35 else "WAITING_FOR_RETEST"
    distance=0 if live_price is not None and retest_zone["low"]<=live_price<=retest_zone["high"] else min(abs(live_price-retest_zone["low"]),abs(live_price-retest_zone["high"])) if live_price is not None else None
    return {"completed_candle_state":state(completed_close,True),"live_price_state":state(live_price),"distance_to_retest_points":distance,"distance_to_retest_atr":distance/atr if distance is not None and atr else None}
