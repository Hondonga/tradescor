"""Directionally symmetric structural stop construction."""
def build_structural_stop(*,direction,entry,execution_zone,reaction_extreme=None,atr=None,tick_size=.01,config=None):
    cfg=config or {};base={"price":None,"source":"","structural_level":None,"buffer_points":None,"buffer_atr":None,"valid":False,"rejection_reasons":[]}
    if entry is None or not execution_zone:return {**base,"rejection_reasons":["Confirmed entry and execution structure are required."]}
    structural=float(reaction_extreme if reaction_extreme is not None else execution_zone.get("low") if direction=="buy" else execution_zone.get("high"));buffer=max(float(atr or 0)*float(cfg.get("stop_buffer_atr",.1)),float(tick_size)*2);stop=structural-buffer if direction=="buy" else structural+buffer;risk=float(entry)-stop if direction=="buy" else stop-float(entry);reasons=[]
    if risk<=0:reasons.append("Stop is on the wrong side of entry.")
    if risk<float(tick_size)*2:reasons.append("Stop lies inside normal tick noise.")
    if atr and risk>float(atr)*float(cfg.get("maximum_stop_atr",2)):reasons.append("Structural stop is excessively wide.")
    return {**base,"price":stop if not reasons else None,"source":"m5_execution_structure","structural_level":structural,"buffer_points":buffer,"buffer_atr":buffer/atr if atr else None,"valid":not reasons,"rejection_reasons":reasons}
