import pandas as pd

from analysis.liquidity_target_engine import build_liquidity_targets, _cluster


NOW=pd.Timestamp("2026-07-16T16:00:00Z")


def _frame(lows=None,highs=None):
    lows=lows or [99.5]*20; highs=highs or [100.5]*len(lows); times=pd.date_range(NOW-pd.Timedelta(minutes=5*(len(lows)-1)),periods=len(lows),freq="5min")
    return pd.DataFrame([{"time":time,"open":(low+high)/2,"high":high,"low":low,"close":(low+high)/2} for time,low,high in zip(times,lows,highs)])


def _engine(direction,entry,stop,levels,frame=None,offset=True):
    return build_liquidity_targets(symbol="EUR/USD",asset_class="forex",direction=direction,entry_price=entry,stop_price=stop,candles_by_timeframe={"M5":frame if frame is not None else _frame()},decision_timestamp=NOW,higher_timeframe_draw=direction,candidate_levels=levels,apply_offset=offset)


def _level(price,time="2026-07-16T15:00:00Z",kind="equal_lows"):
    return {"price":price,"formed_at":time,"source_timeframe":"M15","type":kind,"prominence":18,"touch_count":2}


def test_buy_target_is_above_entry_and_sell_target_is_below_entry():
    buy=_engine("buy",100,99,[_level(102,kind="equal_highs")]); sell=_engine("sell",100,101,[_level(98)])
    assert buy["selected_targets"]["tp1"]["price"]>100
    assert sell["selected_targets"]["tp1"]["price"]<100


def test_wrong_side_and_future_created_levels_are_rejected():
    result=_engine("buy",100,99,[_level(98),_level(102,"2026-07-16T17:00:00Z")])
    reasons=[reason for row in result["candidates"] for reason in row["rejection_reasons"]]
    assert "Target is on the wrong side of entry." in reasons
    assert "Level was confirmed after the decision timestamp." in reasons


def test_swept_and_already_reached_liquidity_is_rejected():
    frame=_frame(highs=[100.5]*10+[102.5]+[100.5]*9); result=_engine("buy",100,99,[_level(102,"2026-07-16T14:00:00Z")],frame)
    row=next(row for row in result["candidates"] if row["liquidity_objective_price"]==102)
    assert row["swept"] and row["already_reached"] and not row["valid"] and row["swept_at"]


def test_near_equal_levels_form_one_cluster():
    rows=[{"price":price,"side":"sell_side","type":"confirmed_swing","source_timeframe":"M15","formed_at":NOW,"confirmed_at":NOW,"prominence":10,"touch_count":1} for price in (1.40108,1.40112,1.40115)]
    clusters=_cluster(rows,"sell",.0001)
    assert len(clusters)==1 and clusters[0]["level_count"]==3
    assert clusters[0]["cluster_low"]==1.40108 and clusters[0]["cluster_high"]==1.40115


def test_tp1_is_nearer_and_tp2_is_farther_in_trade_direction():
    result=_engine("sell",100,101,[_level(98),_level(96,kind="previous_day_low")])
    tp1,tp2=result["selected_targets"]["tp1"],result["selected_targets"]["tp2"]
    assert 100>tp1["price"]>tp2["price"]


def test_distant_tp2_cannot_hide_poor_nearest_target_reward():
    result=_engine("sell",100,101,[_level(99.5),_level(96)])
    assert result["selected_targets"]["tp1"] is None
    assert result["quality_gate"]["passed"] is False and result["quality_gate"]["nearest_rr"]<1


def test_target_recalculates_when_entry_changes():
    first=_engine("buy",100,99,[_level(102)]); second=_engine("buy",101,99,[_level(102)])
    first_rr=next(row["projected_rr"] for row in first["candidates"] if row["liquidity_objective_price"]==102)
    second_rr=next(row["projected_rr"] for row in second["candidates"] if row["liquidity_objective_price"]==102)
    assert first_rr!=second_rr and second["selected_targets"]["tp1"] is None


def test_executable_offset_is_directionally_conservative():
    buy=_engine("buy",100,99,[_level(102)],offset=True)["selected_targets"]["tp1"]
    sell=_engine("sell",100,101,[_level(98)],offset=True)["selected_targets"]["tp1"]
    assert buy["executable_tp_price"]<buy["liquidity_objective_price"]
    assert sell["executable_tp_price"]>sell["liquidity_objective_price"]


def test_tp3_is_null_by_default():
    result=_engine("buy",100,99,[_level(102),_level(104),_level(106)])
    assert result["selected_targets"]["tp3"] is None
