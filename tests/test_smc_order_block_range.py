import pandas as pd
from analysis.smc.smc_order_block_engine import detect_order_blocks
from analysis.smc.smc_dealing_range_engine import build_dealing_range

def test_order_block_requires_displacement_and_structure_break():
    rows=pd.DataFrame([{"time":"1","open":2,"high":2.2,"low":.8,"close":1,"complete":True},{"time":"2","open":1,"high":4,"low":1,"close":3.8,"complete":True}]);event={"structure_event_id":"bos","direction":"bullish"};weak={"displacement_id":"d","candle_time":"2","direction":"bullish","passed":True,"structure_broken":False,"body_atr":1,"close_location":1}
    assert detect_order_blocks(rows,[weak],[event])==[];strong={**weak,"structure_broken":True};assert detect_order_blocks(rows,[strong],[event])[0]["direction"]=="bullish"

def test_dealing_range_invalidates_after_accepted_breakout():
    swings=[{"swing_id":"l1","type":"low","scope":"external","price":1,"confirmation_time":"1"},{"swing_id":"h1","type":"high","scope":"external","price":5,"confirmation_time":"2"},{"swing_id":"l2","type":"low","scope":"external","price":1,"confirmation_time":"3"},{"swing_id":"h2","type":"high","scope":"external","price":5,"confirmation_time":"4"}];active=build_dealing_range(swings);invalid=build_dealing_range(swings,{"type":"accepted_breakout"});assert active["active"] and active["alternating_interactions"]>=2 and not invalid["active"] and invalid["archived"]
