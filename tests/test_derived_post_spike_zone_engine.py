import pandas as pd
from analysis.derived_post_spike_zone_engine import build_post_spike_zone,narrow_post_spike_execution_zone
def test_m5_zone_is_narrower_and_bound_to_spike():
    rows=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:15:00Z")+pd.Timedelta(minutes=15*i),"low":101+i*.1,"high":102+i*.1,"complete":True} for i in range(8)]);spike={"spike_id":"s","completed_at":"2026-01-01T00:00:00Z"};structure={"formed_after_spike":True,"last_swing_low":{"price":101},"direction":"bullish"};zone=build_post_spike_zone(rows,"buy",spike,structure,1,102,{"minimum_zone_quality":0});execution=narrow_post_spike_execution_zone(zone,1);assert zone["valid_for_spike_id"]=="s" and execution["high"]-execution["low"]<zone["high"]-zone["low"]
