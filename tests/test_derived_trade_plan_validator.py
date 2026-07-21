from analysis.derived_trade_plan_validator import validate_reward_risk,validate_chase
def test_tp1_must_pass_independently_and_rr_uses_confirmed_entry():
    poor=validate_reward_risk(direction="buy",entry=100,stop=99,tp1={"price":101.2},tp2={"price":105},minimum_rr=1.5);assert not poor["valid"] and poor["tp1_rr"]==1.2
    good=validate_reward_risk(direction="sell",entry=100,stop=101,tp1={"price":98},minimum_rr=1.5);assert good["valid"] and good["tp1_rr"]==2
def test_extended_price_is_too_late():assert validate_chase(direction="buy",current_price=102,entry=100,execution_zone={"low":99.9,"high":100.1},tp1={"price":105},stop=99,atr=1,maximum_chase_atr=.35)["state"]=="TOO_LATE"
