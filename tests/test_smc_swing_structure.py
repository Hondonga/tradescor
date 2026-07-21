import pandas as pd
from analysis.smc.smc_swing_engine import confirmed_swings
from analysis.smc.smc_structure_engine import analyze_structure

def candles(highs,lows=None,closes=None):
    lows=lows or [x-2 for x in highs];closes=closes or [x-1 for x in highs]
    return pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:00:00Z")+pd.Timedelta(minutes=5*i),"open":c-.2,"high":h,"low":l,"close":c,"complete":True} for i,(h,l,c) in enumerate(zip(highs,lows,closes))])

def test_confirmed_swing_is_causal_and_does_not_repaint():
    prefix=candles([2,3,5,3,2]);first=confirmed_swings(prefix,atr=2,tick_size=.1,left_strength=2,right_strength=2,minimum_prominence_atr=0,minimum_prominence_ticks=0);assert len(first)==1 and first[0]["confirmation_time"]==prefix.iloc[4].time.isoformat()
    extended=pd.concat([prefix,candles([8,7]).assign(time=lambda x:x.time+pd.Timedelta(minutes=25))],ignore_index=True);second=confirmed_swings(extended,atr=2,tick_size=.1,left_strength=2,right_strength=2,minimum_prominence_atr=0,minimum_prominence_ticks=0);assert first[0] in second

def test_bos_requires_displacement_and_completed_close():
    rows=candles([2,4,3],[0,1,1],[1,3,5]);swing={"swing_id":"h","type":"high","price":4,"scope":"internal","candle_time":"t","confirmation_time":"t"}
    assert analyze_structure(rows,[swing],{"passed":False,"direction":"bullish"})["last_bos"] is None
    assert analyze_structure(rows,[swing],{"passed":True,"direction":"bullish"})["last_bos"]["direction"]=="bullish"

def test_mss_requires_sweep_displacement_and_opposing_break():
    rows=candles([3,4,3],[1,2,1],[2,3,.5]);low={"swing_id":"l","type":"low","price":1,"scope":"internal","candle_time":"t","confirmation_time":"t"}
    sweep={"type":"sweep","qualified":True,"direction":"bearish","reference_id":"bsl"};result=analyze_structure(rows,[low],{"passed":True,"direction":"bearish"},sweep);assert result["last_mss"]["direction"]=="bearish"

