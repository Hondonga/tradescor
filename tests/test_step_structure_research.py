import pandas as pd
from strategies.derived.step_structure_research import evaluate_step_structure_research
def _frames(n=220):
    close=[100+((i%10)-5)*.01 for i in range(n)];rows=pd.DataFrame({"time":pd.date_range("2026-01-01",periods=n,freq="15min",tz="UTC"),"open":close,"high":[x+.02 for x in close],"low":[x-.02 for x in close],"close":close,"complete":[True]*n});return {key:rows.copy() for key in ("D1","H4","H1","M15","M5")}
def _run(family="STEP",tick=.01):
    return evaluate_step_structure_research(symbol="S",family={"family":family,"classification_confidence":.98},profile={"profile_quality":"good","atr":.04,"volatility_regime":"NORMAL","directional_efficiency":.1,"expansion_ratio":1},candles_by_timeframe=_frames(),current_price=100,tick_size=tick,data_quality={"analysis_allowed":True,"status":"good"})
def test_only_step_with_known_tick_is_eligible():
    assert _run()["strategy"]["eligible"]
    assert not _run("VOLATILITY")["strategy"]["eligible"]
    assert not _run(tick=None)["strategy"]["eligible"]
def test_response_is_always_research_only():
    row=_run();assert row["strategy_status"]=="research" and row["validated_edge"] is False and row["paper_analysis_only"] is True
    assert row["sequence"]["reversal_due"] is False and len(row["routing"]["eligible_sub_strategies"])<=1
