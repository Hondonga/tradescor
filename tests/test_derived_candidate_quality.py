from analysis.derived_candidate_quality import measure_candidate_quality
def test_incomplete_plan_cannot_be_trade_ready_or_strong():
    result={"strategy":{"eligible":True},"decision":{"trade_ready":True,"status":"READY TO BUY","developing_direction":"buy"},"active_trade_plan":{"entry":1,"stop":.9,"tp1":None},"reward_risk":{"valid":False},"chase":{"valid":True}}
    row=measure_candidate_quality("x",result,.9);assert not row["trade_ready"] and row["quality_label"]!="strong" and row["blocking_reasons"]
