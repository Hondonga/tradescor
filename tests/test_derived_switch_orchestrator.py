import pandas as pd
from strategies.derived.derived_switch_orchestrator import evaluate_derived_switch
from analysis.derived_regime_stability import clear_regime_stability
from analysis.derived_regime_hysteresis import clear_regime_hysteresis
def _frame(n=30):
    return pd.DataFrame({"time":pd.date_range("2026-01-01",periods=n,freq="15min",tz="UTC"),"open":[100]*n,"high":[101]*n,"low":[99]*n,"close":[100]*n,"complete":[True]*n})
def test_orchestrator_owns_only_one_delegation_and_no_levels_while_unstable():
    clear_regime_stability();clear_regime_hysteresis();frames={key:_frame() for key in ("D1","H4","H1","M15","M5")};profile={"profile_quality":"good","atr":2,"atr_percentile":20,"volatility_percentile":20,"compression_ratio":1,"expansion_ratio":1,"abnormal_candle_frequency":0,"directional_efficiency":.1,"trend_persistence":.5}
    result=evaluate_derived_switch(symbol="VS",family={"family":"VOLATILITY_SWITCH","classification_confidence":.98},regime={"regime":"RANGE","direction":"neutral","formed_at":"t","structure":{}},profile=profile,volatility={},candles_by_timeframe=frames,current_price=100,data_quality={"analysis_allowed":True,"status":"good"},config={"stability":{"minimum_confirmed_candles":3}})
    assert result["routing"]["delegated_strategy"] is None
    assert result["active_trade_plan"] is None and result["decision"]["trade_ready"] is False
