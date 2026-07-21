import pandas as pd
from analysis.smc.smc_router import route_smc,clear_smc_ownership
from analysis.smc.adapters.jump_smc_adapter import detect_jump_event
from analysis.smc.adapters.step_smc_adapter import evaluate_step_smc
from analysis.derived_family_classifier import classify_derived_family

def frame(count=40,spike=None):
    rows=[]
    for i in range(count):
        move=10 if spike==i else .3;open_=100+i*.05;close=open_+move
        rows.append({"time":pd.Timestamp("2026-01-01T00:00:00Z")+pd.Timedelta(minutes=5*i),"open":open_,"high":max(open_,close)+.1,"low":min(open_,close)-.1,"close":close,"complete":True})
    return pd.DataFrame(rows)
def frames():
    row=frame();return {key:row.copy() for key in ("D1","H4","H1","M15","M5")}

def test_invalid_manual_strategy_is_corrected_and_switch_archives():
    clear_smc_ownership();family=classify_derived_family({"provider_symbol":"R_100","display_name":"Volatility 100 Index"});first=route_smc(symbol="R_100",family=family,candles_by_timeframe=frames(),tick_size=.01,requested_strategy="ict_2022",analysis_time="1");ownership=first["ownership"]
    assert ownership["requested_strategy_id"]=="ict_2022" and ownership["corrected"]
    assert ownership["selected_strategy_id"]==ownership["decision_owner_id"]==ownership["overlay_owner_id"]=="volatility_smc"
    second=route_smc(symbol="R_100",family=family,candles_by_timeframe=frames(),tick_size=.01,requested_strategy="auto",analysis_time="2");assert second["previous_setup"] is None and second["trade_chart"]["owner_id"]=="volatility_smc"

def test_jump_detects_completed_up_and_down_events_without_predicting_next():
    up=detect_jump_event(frame(spike=39),.01);down_rows=frame();down_rows.loc[39,["open","high","low","close"]]=[110,110.1,99.8,100]
    down=detect_jump_event(down_rows,.01);assert up["qualified"] and up["direction"]=="up";assert down["qualified"] and down["direction"]=="down"

def test_step_smc_does_not_require_fvg():
    family=classify_derived_family({"provider_symbol":"stp","display_name":"Step Index 100"});result=evaluate_step_smc(symbol="stp",family=family,candles_by_timeframe=frames(),tick_size=.1,requested_strategy="auto");assert result["fvgs"]==[] and "fvg" not in result["scoring"]["essential_failures"]

def test_symbol_switch_does_not_inherit_previous_owner_state():
    clear_smc_ownership();family=classify_derived_family({"provider_symbol":"R_100","display_name":"Volatility 100 Index"});route_smc(symbol="R_100",family=family,candles_by_timeframe=frames(),tick_size=.01,requested_strategy="ict_2022");other=route_smc(symbol="R_50",family={**family,"provider_symbol":"R_50"},candles_by_timeframe=frames(),tick_size=.01,requested_strategy="smc");assert other["previous_setup"] is None
