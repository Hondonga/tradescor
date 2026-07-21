from __future__ import annotations
import pandas as pd
from analysis.derived_family_classifier import classify_derived_family
from analysis.derived_market_profile import build_derived_market_profile
from analysis.derived_regime_detector import detect_derived_regime
from analysis.derived_engine import analyze_derived_index
from analysis.derived_risk_engine import build_derived_risk
from analysis.derived_target_engine import build_derived_targets
from strategies.derived.boom_crash_spike_state import evaluate_spike_state
from strategies.derived.range_break_retest import evaluate_range_break

def frame(direction="up",count=120,timeframe="M5"):
    rows=[]
    for i in range(count):
        base=100+i*.15 if direction=="up" else 140-i*.15;close=base+(.08 if direction=="up" else -.08)
        rows.append({"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=5*i),"open":base,"high":max(base,close)+.12,"low":min(base,close)-.12,"close":close,"complete":True,"provider":"deriv","symbol":"R_100","timeframe":timeframe})
    return pd.DataFrame(rows)

def test_family_metadata_covers_new_families_and_override_wins():
    assert classify_derived_family({"provider_symbol":"x","subgroup":"volatility switch"})["family"]=="VOLATILITY_SWITCH"
    assert classify_derived_family({"provider_symbol":"x","underlying_symbol_type":"dex"})["family"]=="DEX"
    assert classify_derived_family({"provider_symbol":"BOOM1000","subgroup":"volatility"},{"BOOM1000":"STEP"})["family"]=="STEP"

def test_profile_and_regime_never_default_missing_data_to_buy():
    profile=build_derived_market_profile(frame(),family="VOLATILITY",tick_size=.01,timeframe="M15")
    assert profile["atr"]>0 and profile["sample_size"]==120 and profile["volatility_regime"] in {"LOW","MEDIUM","HIGH"}
    missing=detect_derived_regime(pd.DataFrame(),{},{});assert missing["direction"]=="neutral" and missing["regime"]=="INSUFFICIENT_DATA"

def test_boom_crash_spike_does_not_automatically_create_trade():
    boom=evaluate_spike_state(family="BOOM",spike={"spike_detected":True,"cooldown_active":True},regime={"direction":"bullish"})
    crash=evaluate_spike_state(family="CRASH",spike={"spike_detected":True,"cooldown_active":True},regime={"direction":"bearish"})
    assert boom["selected_candidate"] is None and crash["selected_candidate"] is None
    assert boom["bearish_candidate"]["required_minimum_rr"]>boom["bullish_candidate"]["required_minimum_rr"]
    assert crash["bullish_candidate"]["required_minimum_rr"]>crash["bearish_candidate"]["required_minimum_rr"]

def test_range_break_retest_zone_is_narrower_than_locked_range():
    rows=frame("up",40);rows.loc[39,"close"]=rows.iloc[:-1].high.max()+2;rows.loc[39,"high"]=rows.loc[39,"close"]+.1
    profile=build_derived_market_profile(rows,family="RANGE_BREAK",tick_size=.01,timeframe="M15");result=evaluate_range_break(candles=rows,profile=profile,minimum_touches=1,minimum_duration=20)
    if result["retest_zone"]:
        assert result["retest_zone"]["high"]-result["retest_zone"]["low"] < result["range"]["high"]-result["range"]["low"]

def test_risk_and_targets_are_directionally_symmetric_and_use_entry_rr():
    buy=build_derived_risk(family="VOLATILITY",direction="buy",entry=100,structure_extreme=99,atr=1,tick_size=.01);sell=build_derived_risk(family="VOLATILITY",direction="sell",entry=100,structure_extreme=101,atr=1,tick_size=.01)
    assert buy["price"]<100<sell["price"]
    bt=build_derived_targets(direction="buy",entry=100,stop=99,candidates=[{"price":102,"type":"swing"}],minimum_rr=1.5);st=build_derived_targets(direction="sell",entry=100,stop=101,candidates=[{"price":98,"type":"swing"}],minimum_rr=1.5)
    assert bt["tp1"]["rr"]==st["tp1"]["rr"]==2

def test_derived_engine_keeps_bias_when_no_trade_is_ready():
    frames={key:frame("down",120,key) for key in ("D1","H4","H1","M15","M5")};result=analyze_derived_index(symbol="R_100",metadata={"provider_symbol":"R_100","subgroup":"volatility"},candles_by_timeframe=frames)
    assert result["decision"]["market_bias"] in {"bearish","mixed","neutral","compression","transition"}
    assert result["decision"]["trade_ready"] is False and result["active_trade_plan"] is None
    assert result["advanced_details"]["data_quality"]["analysis_allowed"] is True
