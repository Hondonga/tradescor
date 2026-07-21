from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analysis.decision_engine import build_decision
from analysis.ict_displacement import detect_displacement
from analysis.ict_fvg import identify_displacement_fvg
from analysis.ict_state import load_config
from analysis.ict_structure_shift import detect_mss
from analysis.ict_sweep import classify_sweep
from analysis.ict_targets import select_targets


def _rows(values, start="2026-01-01"):
    times=pd.date_range(start,periods=len(values),freq="15min",tz="UTC")
    return pd.DataFrame([{"time":times[i],"open":o,"high":h,"low":l,"close":c} for i,(o,h,l,c) in enumerate(values)])


def test_configuration_is_frozen_and_hashed():
    config,digest=load_config()
    assert config["profile"]=="strict_core" and config["minimum_rr"]==1.5
    assert len(digest)==64


def test_wick_only_sweep_is_forming_not_confirmed():
    rows=_rows([(100,101,99,100),(100,100.5,98.8,99.1)])
    pool={"liquidity_id":"liq-1","price":99,"formed_at":rows.iloc[0].time.isoformat()}
    result=classify_sweep(rows.iloc[:1],pool,direction="buy",forming_candle=rows.iloc[1:])
    assert result["state"]=="forming" and not result["valid"]


def test_accepted_breakout_is_not_an_ict_sweep():
    rows=_rows([(100,101,99,100),(99,99.2,98.4,98.6),(98.6,98.8,98.1,98.3)])
    pool={"liquidity_id":"liq-1","price":99,"formed_at":rows.iloc[0].time.isoformat()}
    result=classify_sweep(rows,pool,direction="buy",accepted_closes=2)
    assert result["state"]=="fail" and result["result"]["accepted_breakout"] and not result["valid"]


def test_displacement_is_atr_normalized_and_after_sweep():
    rows=_rows([(100,100.4,99.6,100)]*6+[(100,102,99.9,101.9)])
    sweep={"confirmed":True,"sweep_time":rows.iloc[4].time.isoformat(),"reclaim_time":rows.iloc[5].time.isoformat()}
    result=detect_displacement(rows,sweep,direction="buy",body_atr_threshold=.8,range_atr_threshold=1)
    assert result["valid"] and result["result"]["body_atr"]>=.8
    assert result["timestamp"]>sweep["reclaim_time"]


def test_mss_uses_pre_sweep_pivot_and_completed_close():
    values=[(100,101,99.5,100),(100,101.5,99.8,101),(101,102,100,100.5),(100.5,101,99.7,100),(100,100.8,99.6,100.2),(100.2,100.7,99.7,100),(100,100.6,99.4,99.8),(99.8,102.2,99.7,102.1)]
    rows=_rows(values); sweep={"sweep_time":rows.iloc[6].time.isoformat()}; displacement={"start_time":rows.iloc[7].time.isoformat()}
    result=detect_mss(rows,sweep,displacement,direction="buy")
    assert result["valid"] and result["result"]["close_confirmed"]
    assert result["result"]["pivot_time"]<sweep["sweep_time"]<=result["result"]["break_time"]


def test_fvg_uses_exact_three_candle_geometry_and_displacement_id():
    rows=_rows([(100,100.5,99.8,100.2),(100.2,102,100.1,101.8),(101.8,102.2,100.8,102)])
    displacement={"displacement_id":"disp-1","candle_index":1,"start_time":rows.iloc[1].time.isoformat()}
    result=identify_displacement_fvg(rows,displacement,direction="buy",tick_size=.01,minimum_ticks=2)
    assert result["valid"]
    assert result["result"]["low"]==100.5 and result["result"]["high"]==100.8
    assert result["result"]["displacement_id"]=="disp-1"


def test_fully_filled_fvg_is_rejected():
    rows=_rows([(100,100.5,99.8,100.2),(100.2,102,100.1,101.8),(101.8,102.2,100.8,102),(102,102.1,100.4,100.6)])
    displacement={"displacement_id":"disp-1","candle_index":1,"start_time":rows.iloc[1].time.isoformat()}
    assert not identify_displacement_fvg(rows,displacement,direction="buy",tick_size=.01)["valid"]


def test_swept_target_and_poor_remaining_rr_are_rejected():
    swept={"directional_target":{"price":102,"side":"buy_side","swept":True,"source_timeframe":"H1"}}
    assert not select_targets(liquidity=swept,direction="buy",entry=100,stop=99,minimum_rr=1.5)["valid"]
    poor={"directional_target":{"price":100.8,"side":"buy_side","swept":False,"formed_at":"2026-01-01T00:00:00+00:00","source_timeframe":"H1"}}
    result=select_targets(liquidity=poor,direction="buy",entry=100,stop=99,minimum_rr=1.5)
    assert not result["valid"] and result["result"]["remaining_rr"]<1


def test_manual_decision_exposes_v2_and_optional_context_cannot_replace_core():
    def frame(tf):
        freq={"D1":"1D","H4":"4h","H1":"1h","M15":"15min","M5":"5min"}[tf]; times=pd.date_range("2025-01-01",periods=80,freq=freq,tz="UTC"); price=100.; data=[]
        for time in times:
            data.append({"time":time,"open":price,"high":price+.2,"low":price-.1,"close":price+.1}); price+=.1
        return pd.DataFrame(data)
    candles={tf:frame(tf) for tf in ("D1","H4","H1","M15","M5")}; boundary=datetime(2026,1,1,tzinfo=timezone.utc)
    decision=build_decision(symbol="BTC/USD",asset_class="crypto",display_timeframe="M15",candles_by_timeframe=candles,analysis_timestamp=boundary,requested_strategy="ict_2022",session={"entry_allowed":True})
    assert decision["ict_model"]["strategy_version"]=="ict_2022_v2"
    assert decision["execution_timeframe"]=="M5"
    assert all(not row["can_replace_core_sequence"] for row in decision["ict_model"]["optional_context"].values())
    if not decision["ict_model"]["quality"]["trade_plan_valid"]:
        assert decision["execution"]["entry"] is None and decision["execution"]["stop"] is None


def test_frontend_contains_no_v2_strategy_calculation():
    js=(Path(__file__).resolve().parents[1]/"static"/"app.js").read_text()
    assert "ict_2022_v2" not in js
    assert "decision.ict_checklist" in js
