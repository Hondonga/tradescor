from analysis.derived_target_engine import build_derived_targets
def test_targets_are_directional_and_swept_or_reached_are_rejected():
    buy=build_derived_targets(direction="buy",entry=100,stop=99,candidates=[{"price":102,"type":"swing"},{"price":103,"swept":True},{"price":104,"already_reached":True}],minimum_rr=1.5);assert buy["tp1"]["price"]==102 and all(not row["valid"] for row in buy["candidates"][1:])
    sell=build_derived_targets(direction="sell",entry=100,stop=101,candidates=[{"price":98}],minimum_rr=1.5);assert sell["tp1"]["price"]<100
