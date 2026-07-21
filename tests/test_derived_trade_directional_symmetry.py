from analysis.derived_structural_stop import build_structural_stop
from analysis.derived_trade_plan_validator import validate_reward_risk
def test_mirrored_prices_produce_mirrored_trade_geometry():
    buy_stop=build_structural_stop(direction="buy",entry=100,execution_zone={"low":99,"high":99.5},atr=1,tick_size=.01);sell_stop=build_structural_stop(direction="sell",entry=-100,execution_zone={"low":-99.5,"high":-99},atr=1,tick_size=.01)
    assert round(100-buy_stop["price"],8)==round(sell_stop["price"]+100,8)
    buy=validate_reward_risk(direction="buy",entry=100,stop=99,tp1={"price":102});sell=validate_reward_risk(direction="sell",entry=-100,stop=-99,tp1={"price":-102});assert buy["tp1_rr"]==sell["tp1_rr"]
