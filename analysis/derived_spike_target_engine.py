"""Post-spike structural targets, with the spike extreme as measured evidence."""
from analysis.derived_target_engine import structural_target_candidates,build_derived_targets
def build_spike_targets(*,candles_by_timeframe,direction,entry,stop,spike,atr,minimum_rr,current_price=None):
    candidates=structural_target_candidates(candles_by_timeframe,direction,entry);extreme=float(spike["extreme_price"])
    if (direction=="buy" and extreme>entry) or (direction=="sell" and extreme<entry):candidates.append({"price":extreme,"type":"locked_spike_extreme","formed_at":spike.get("completed_at"),"source_timeframe":spike.get("source_timeframe","M5"),"swept":False,"already_reached":False,"quality":.8})
    return build_derived_targets(direction=direction,entry=entry,stop=stop,candidates=candidates,current_price=current_price,minimum_rr=minimum_rr,atr=atr)
