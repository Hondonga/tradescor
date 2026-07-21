from analysis.derived_structural_stop import build_structural_stop
def test_buy_and_sell_stops_stay_on_structural_side():
    buy=build_structural_stop(direction="buy",entry=100,execution_zone={"low":99.5,"high":99.9},atr=1,tick_size=.01);sell=build_structural_stop(direction="sell",entry=100,execution_zone={"low":100.1,"high":100.5},atr=1,tick_size=.01)
    assert buy["valid"] and buy["price"]<100 and sell["valid"] and sell["price"]>100
