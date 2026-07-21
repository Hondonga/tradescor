"""Midpoint-first, opposite-boundary objectives for range reactions."""
from analysis.derived_target_engine import build_derived_targets

def build_range_reaction_targets(*,direction,entry,stop,locked_range,current_price,minimum_rr=1.3,atr=None):
    if not locked_range: return {"candidates":[],"tp1":None,"tp2":None,"valid":False,"rejection_reasons":["Locked range is required."]}
    midpoint=(locked_range["low"]+locked_range["high"])/2; opposite=locked_range["high"] if direction=="buy" else locked_range["low"]
    candidates=[{"price":midpoint,"type":"range_midpoint","source_timeframe":"M15","swept":False,"already_reached":current_price>=midpoint if direction=="buy" else current_price<=midpoint,"quality":.8},
                {"price":opposite,"type":"opposite_range_boundary","source_timeframe":"M15","swept":False,"already_reached":current_price>=opposite if direction=="buy" else current_price<=opposite,"quality":.85}]
    return build_derived_targets(direction=direction,entry=entry,stop=stop,candidates=candidates,current_price=current_price,minimum_rr=minimum_rr,atr=atr)
