import pandas as pd
from analysis.derived_post_spike_structure import analyze_post_spike_structure
def test_pre_spike_structure_is_not_reused():
    rows=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:00:00Z")+pd.Timedelta(minutes=15*i),"open":i,"high":i+.2,"low":i-.2,"close":i,"complete":True} for i in range(20)]);spike={"spike_id":"s","completed_at":rows.iloc[-3].time};result=analyze_post_spike_structure(rows,spike);assert not result["formed_after_spike"] and result["valid_for_spike_id"]=="s"
