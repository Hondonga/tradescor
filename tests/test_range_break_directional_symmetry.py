import pandas as pd
from analysis.derived_breakout_classifier import classify_breakout
def test_mirrored_breakouts_have_equivalent_acceptance():
    lock={"low":99,"high":101,"locked_at":"2026-01-01T00:00:00Z"};cfg={"breakout_buffer_atr":.1,"minimum_breakout_body_ratio":.45};bull=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:15:00Z"),"open":100.5,"high":102,"low":100.4,"close":101.8,"complete":True}]);bear=bull.copy();bear[["open","high","low","close"]]=[[-100.5,-100.4,-102,-101.8]];mirrored={"low":-101,"high":-99,"locked_at":lock["locked_at"]};a=classify_breakout(bull,lock,1,cfg);b=classify_breakout(bear,mirrored,1,cfg);assert a["accepted"]==b["accepted"] and a["direction"]=="bullish" and b["direction"]=="bearish"
