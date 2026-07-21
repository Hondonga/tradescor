import pandas as pd
from analysis.derived_execution_confirmation import build_m5_execution_zone,confirm_m5_execution,lock_confirmed_entry
def frame(complete_last=True):
    values=[100,99.8,99.7,99.9,100.1,100.4,101]
    return pd.DataFrame([{"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=5*i),"open":v-.1,"high":v+.12,"low":v-.15,"close":v,"complete":complete_last or i<len(values)-1} for i,v in enumerate(values)])
def test_confirmation_is_post_touch_complete_and_entry_locks():
    rows=frame();zone={"low":99.5,"high":100.2,"valid":True};touch=rows.iloc[2].time;execution=build_m5_execution_zone(rows,"buy",zone,touch);assert execution["valid"] and execution["high"]-execution["low"]<zone["high"]-zone["low"]
    confirm=confirm_m5_execution(rows,"buy",zone,execution,"s1",touch);assert confirm["complete"]
    if confirm["valid"]:
        one=lock_confirmed_entry(confirm,"s1",price=101);two=lock_confirmed_entry(confirm,"s1",existing=one,price=999);assert two["price"]==101
    incomplete_rows=frame(False);incomplete=confirm_m5_execution(incomplete_rows,"buy",zone,execution,"s1",touch)
    assert incomplete.get("candle_time")!=incomplete_rows.iloc[-1].time.isoformat()
def test_preinteraction_confirmation_is_rejected():assert not confirm_m5_execution(frame(),"buy",{"valid":True},{"valid":True},"x",None)["valid"]
