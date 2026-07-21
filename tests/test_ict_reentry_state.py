import pandas as pd

from strategies.ict_2022_v2 import _interaction, _score


def _candles(prices):
    times=pd.date_range("2026-07-16T12:00:00Z",periods=len(prices),freq="5min")
    return pd.DataFrame([{"time":time,"open":close,"high":high,"low":low,"close":close} for time,(high,low,close) in zip(times,prices)])


def _array():
    return {"low":1.40436,"high":1.40498,"formed_at":"2026-07-16T11:55:00Z"}


def test_current_price_below_sell_reentry_is_not_currently_inside():
    result=_interaction(_array(),_candles([(1.40470,1.40430,1.40450),(1.40410,1.40370,1.40383)]),"2026-07-16T12:10:00Z","sell",{"sweep_extreme":1.40529},None)
    assert result["entry_array_touched"] is True
    assert result["currently_inside_entry_array"] is False
    assert result["current_location"]=="below_entry_array"
    assert result["reentry_required"] is True


def test_multiple_deep_mitigations_reduce_freshness_and_expire_zone():
    prices=[(1.40490,1.40420,1.40460),(1.40420,1.40390,1.40400),(1.40494,1.40420,1.40470),(1.40410,1.40380,1.40390),(1.40496,1.40420,1.40470)]
    result=_interaction(_array(),_candles(prices),"2026-07-16T12:30:00Z","sell",{"sweep_extreme":1.40529},None)
    assert result["touch_count"]==3
    assert result["freshness"]=="expired"
    assert result["expired"] is True


def test_unconfirmed_reentry_score_is_capped_at_80():
    sequence={key:"pass" for key in ("htf_narrative","directional_draw","opposing_liquidity","liquidity_sweep","displacement","mss","fvg","entry_array_touched","price_in_entry_array","stop_valid","target_valid","risk_reward")}
    sequence["m5_confirmation"]="waiting"; sequence["stop_valid"]=sequence["target_valid"]=sequence["risk_reward"]="waiting"
    interaction={"entry_array_touched":True}
    assert _score(sequence,False,"valid",interaction,True)<=80


def test_historical_touch_alone_caps_score_at_75():
    sequence={key:"pass" for key in ("htf_narrative","directional_draw","opposing_liquidity","liquidity_sweep","displacement","mss","fvg","entry_array_touched","stop_valid","target_valid","risk_reward")}
    sequence.update({"price_in_entry_array":"waiting","m5_confirmation":"waiting","stop_valid":"waiting","target_valid":"waiting","risk_reward":"waiting"})
    assert _score(sequence,False,"valid",{"entry_array_touched":True},False)<=75


def test_score_100_requires_confirmation_stop_target_and_rr():
    sequence={key:"pass" for key in ("htf_narrative","directional_draw","opposing_liquidity","liquidity_sweep","displacement","mss","fvg","entry_array_touched","price_in_entry_array","m5_confirmation","stop_valid","target_valid","risk_reward")}
    assert _score(sequence,True,"valid",{"entry_array_touched":True},True)==100
    sequence["risk_reward"]="waiting"
    assert _score(sequence,False,"valid",{"entry_array_touched":True},True)<100

