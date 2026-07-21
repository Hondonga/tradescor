"""Family-aware structural stop and execution-risk validation."""
def build_derived_risk(*,family,direction,entry,structure_extreme,atr,tick_size,spike_alignment="neutral",config=None):
    cfg=config or {};base=float(cfg.get("buffer_atr",.12));against=spike_alignment=="opposed";buffer_atr=base*(1.75 if against else 1);buffer=max(float(atr or 0)*buffer_atr,float(tick_size)*3)
    stop=(float(structure_extreme)-buffer if direction=="buy" else float(structure_extreme)+buffer) if structure_extreme is not None else None
    valid=entry is not None and stop is not None and ((direction=="buy" and stop<float(entry)) or (direction=="sell" and stop>float(entry)))
    return {"price":stop if valid else None,"source":"volatility_adjusted_execution_structure" if valid else "","buffer_points":buffer,"buffer_atr":buffer_atr,"gap_risk":"high" if against or family in {"BOOM","CRASH","JUMP","DEX"} else "standard","valid":valid,"required_minimum_rr":float(cfg.get("against_spike_min_rr",2.0) if against else cfg.get("min_rr",1.5)),"position_risk_multiplier":.5 if against else 1.0}
