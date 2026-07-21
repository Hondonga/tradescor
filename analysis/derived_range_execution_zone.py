"""Boundary-anchored M15 and post-rejection M5 execution areas."""
def build_range_boundary_zone(locked_range,direction,atr,config=None):
    cfg=config or {}; base={"low":None,"high":None,"type":"","formed_at":None,"valid":False}
    if not locked_range or direction not in {"buy","sell"}: return base
    depth=min((locked_range["high"]-locked_range["low"])*.18,max(float(atr or 0)*float(cfg.get("boundary_zone_width_atr",.18)),0))
    if depth<=0: depth=(locked_range["high"]-locked_range["low"])*.08
    low=float(locked_range["low"] if direction=="buy" else locked_range["high"]-depth); high=float(locked_range["low"]+depth if direction=="buy" else locked_range["high"])
    width=high-low
    return {**base,"low":low,"high":high,"type":"range_demand" if direction=="buy" else "range_supply","formed_at":locked_range.get("locked_at"),"range_id":locked_range.get("range_id"),"boundary":locked_range["low" if direction=="buy" else "high"],"direction":direction,"width_points":width,"width_atr":width/atr if atr else None,"source":"locked_range_boundary","valid":high>low}

def build_range_m5_execution_zone(m15_zone,rejection,atr):
    if not m15_zone or not m15_zone.get("valid") or not rejection or not rejection.get("valid"):
        return {"low":None,"high":None,"type":"","formed_at":None,"valid":False,"rejection_reasons":["Valid boundary rejection is required."]}
    width=m15_zone["high"]-m15_zone["low"]; center=max(m15_zone["low"],min(m15_zone["high"],rejection["rejection_extreme"])); half=min(width*.28,max(float(atr or 0)*.04,width*.1))
    low=max(m15_zone["low"],center-half); high=min(m15_zone["high"],center+half)
    return {"low":low,"high":high,"type":"m5_range_reaction","formed_at":rejection.get("rejection_time"),"valid":high>low and high-low<width,"rejection_reasons":[]}
