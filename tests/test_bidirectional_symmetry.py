from datetime import datetime,timedelta,timezone

import pandas as pd

from analysis.auto_strategy_router import route_auto,_breakout_candidate,_ict_candidate
from analysis.market_features import feature
from analysis.top_down_engine import analyze_top_down_market


def _features(direction):
    timestamp="2025-01-01T00:00:00Z"
    frame={"structure_direction":feature(direction,timestamp,"H1"),"directional_efficiency":feature(.6,timestamp,"H1"),"compression":feature({"active":False},timestamp,"H1"),"displacement":feature({"active":True,"direction":direction},timestamp,"H1"),"volatility_regime":feature("normal",timestamp,"H1"),"abnormal_candle":feature(False,timestamp,"H1"),"range":feature({"position":1.2 if direction=="bullish" else -.2,"boundary_tests":3,"low":99,"high":101},timestamp,"H1"),"liquidity":feature({"equal_highs":[],"equal_lows":[],"unswept_highs":[],"unswept_lows":[]},timestamp,"H1"),"fvg":feature([],timestamp,"H1")}
    return {"timeframes":{tf:frame for tf in ("D1","H4","H1","M15","M5")}}


def _top(direction):
    return {"m15_setup":{"enabled":True,"direction":direction,"setup_type":"demand_retracement" if direction=="buy" else "supply_retracement","status":"watching","zone":{"low":99,"high":100,"type":"demand" if direction=="buy" else "supply","start_time":"2025-01-01T00:00:00Z"}}}


def test_auto_always_returns_three_independent_candidates_per_direction():
    result=route_auto(symbol="EUR/USD",asset_class="forex",regime={"regime":"TRENDING_BEARISH"},features=_features("bearish"),top_down=_top("sell"),session={"entry_allowed":True},execution_mode="conservative")
    assert len(result["candidates"])==6
    assert result["directional_candidates"]["buy"]["diagnostics"]["candidates_found"]==3
    assert result["directional_candidates"]["sell"]["diagnostics"]["candidates_found"]==3
    assert result["selected_direction"]=="sell" and result["selected_strategy"]=="supply_demand"


def test_supply_demand_buy_and_sell_router_scores_are_mirrored():
    buy=route_auto(symbol="EUR/USD",asset_class="forex",regime={"regime":"TRENDING_BULLISH"},features=_features("bullish"),top_down=_top("buy"),session={"entry_allowed":True},execution_mode="conservative")
    sell=route_auto(symbol="EUR/USD",asset_class="forex",regime={"regime":"TRENDING_BEARISH"},features=_features("bearish"),top_down=_top("sell"),session={"entry_allowed":True},execution_mode="conservative")
    assert buy["selected_direction"]=="buy" and sell["selected_direction"]=="sell"
    assert buy["buy_best_score"]==sell["sell_best_score"]


def test_breakout_directional_candidates_use_equivalent_gates():
    bullish=_breakout_candidate("BREAKOUT_EXPANSION",_features("bullish"),_top("buy"),{},"buy")
    bearish=_breakout_candidate("BREAKOUT_EXPANSION",_features("bearish"),_top("sell"),{},"sell")
    assert bullish["eligible"] and bearish["eligible"]
    assert bullish["present_quality_score"]==bearish["present_quality_score"]


def test_strict_ict_router_reads_both_candidate_contracts_not_selected_side():
    event={"opposing_pool":{"price":99}}; core={"state":"forming","relationship":"aligned_continuation","liquidity":event,"sweep":{"sweep_time":"t"},"displacement":{"start_time":"t"},"mss":{"break_time":"t"},"fvg":{"low":99,"high":100},"entry":{"low":99,"high":100,"formed_at":"t","type":"fvg"}}
    model={"sequence":{},"narrative":{"direction":"buy"},"setup":{"state":"WAITING"},"quality":{"setup_score":70},"bullish_candidate":{"candidate_id":"b",**core},"bearish_candidate":{"candidate_id":"s",**core}}
    buy=_ict_candidate("forex","RANGING",_features("bullish"),_top("buy"),{"entry_allowed":True},{},model,"buy")
    sell=_ict_candidate("forex","RANGING",_features("bearish"),_top("sell"),{"entry_allowed":True},{},model,"sell")
    assert buy["eligible"] and sell["eligible"] and buy["present_quality_score"]==sell["present_quality_score"]


def _candles(step,minutes):
    start=datetime(2025,1,1,tzinfo=timezone.utc); price=100.; rows=[]
    for index in range(80):
        close=price+step; rows.append({"time":start+timedelta(minutes=minutes*index),"open":price,"high":max(price,close)+.04,"low":min(price,close)-.04,"close":close}); price=close
    return pd.DataFrame(rows)


def _mirror(frame,constant=300):
    result=frame.copy(); result["open"]=constant-frame.open; result["close"]=constant-frame.close; result["high"]=constant-frame.low; result["low"]=constant-frame.high; return result


def test_price_mirror_produces_opposite_top_down_direction_with_equal_score():
    minutes={"D1":1440,"H4":240,"H1":60,"M15":15,"M5":5}; bullish={tf:_candles(.1,value) for tf,value in minutes.items()}; bearish={tf:_mirror(frame) for tf,frame in bullish.items()}; boundary=max(frame.time.max() for frame in bullish.values())+timedelta(days=2)
    buy=analyze_top_down_market(symbol="TEST",candles_by_timeframe=bullish,analysis_timestamp=boundary); sell=analyze_top_down_market(symbol="TEST",candles_by_timeframe=bearish,analysis_timestamp=boundary)
    assert buy["alignment"]["primary_direction"]=="buy" and sell["alignment"]["primary_direction"]=="sell"
    assert buy["score_before_execution"]==sell["score_before_execution"]
    assert buy["m15_setup"]["direction"]=="buy" and sell["m15_setup"]["direction"]=="sell"

