"""Normalized range location using configurable bands."""
def classify_range_location(current_price,locked_range,atr,config=None):
    base={"position_ratio":None,"location":"outside","distance_to_low_points":None,"distance_to_high_points":None,"distance_to_low_atr":None,"distance_to_high_atr":None}
    if current_price is None or not locked_range:return base
    low=float(locked_range["low"]);high=float(locked_range["high"]);width=max(high-low,1e-12);ratio=(float(current_price)-low)/width;cfg=config or {}
    if ratio<0 or ratio>1:location="outside"
    elif ratio<=float(cfg.get("lower_boundary_max_ratio",.22)):location="lower_boundary" if ratio<=.1 else "lower_quartile"
    elif ratio>=float(cfg.get("upper_boundary_min_ratio",.78)):location="upper_boundary" if ratio>=.9 else "upper_quartile"
    elif float(cfg.get("mid_range_low_ratio",.35))<=ratio<=float(cfg.get("mid_range_high_ratio",.65)):location="mid_range"
    else:location="lower_quartile" if ratio<.5 else "upper_quartile"
    dl=abs(float(current_price)-low);dh=abs(high-float(current_price));return {"position_ratio":ratio,"location":location,"distance_to_low_points":dl,"distance_to_high_points":dh,"distance_to_low_atr":dl/atr if atr else None,"distance_to_high_atr":dh/atr if atr else None}
