import pandas as pd
from analysis.derived_retest_confirmation import confirm_retest,retest_interaction_time
def test_confirmation_is_null_before_retest_and_ignores_incomplete_trigger():
    values=[102,101.1,101.2,101.4,101.8,102.4];rows=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:15:00Z")+pd.Timedelta(minutes=5*i),"open":v-.1,"high":v+.15,"low":v-.15,"close":v,"complete":i<len(values)-1} for i,v in enumerate(values)]);zone={"low":100.9,"high":101.1,"valid":True};interaction=retest_interaction_time(rows,zone,"2026-01-01T00:00:00Z");assert interaction is not None
    result=confirm_retest(rows,"bullish",zone,"s","r",interaction);assert not result["valid"] or result["candle_time"]!=rows.iloc[-1].time.isoformat()
    assert confirm_retest(rows,"bullish",zone,"s","r",None) is None
