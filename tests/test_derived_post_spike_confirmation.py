import pandas as pd
from analysis.derived_post_spike_confirmation import confirm_post_spike
def test_confirmation_requires_cooldown_and_post_zone_interaction():
    rows=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:05:00Z")+pd.Timedelta(minutes=5*i),"open":100,"high":101+i,"low":99,"close":100+i,"complete":True} for i in range(6)]);zone={"low":99,"high":101,"valid":True};assert confirm_post_spike(rows,"buy",zone,"setup","spike",None,{"release_allowed":True}) is None and confirm_post_spike(rows,"buy",zone,"setup","spike",rows.iloc[0].time,{"release_allowed":False}) is None
