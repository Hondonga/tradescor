import json
from pathlib import Path

from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback
from validation.strategy_reachability_fixtures import _focused_frames


def _decision(direction):
    frames=_focused_frames(direction)
    return evaluate_volatility_structure_pullback(
        symbol="R_75",candles_by_timeframe=frames,tick_size=.01,
        analysis_time=frames["M5"].iloc[-1].time,
    )


def test_focused_engine_produces_complete_bidirectional_ready_plans():
    buy=_decision("buy");sell=_decision("sell")
    assert buy["decision"]["status"]=="READY TO BUY"
    assert sell["decision"]["status"]=="READY TO SELL"
    for result in (buy,sell):
        setup=result["setup"]
        assert setup["entry"] is not None and setup["stop"] is not None
        assert setup["targets"] and setup["rr"]>=1.5
        assert result["diagnostics"]["target_evaluated_after_entry_stop"] is True
        assert result["diagnostics"]["invariants"]["valid"] is True
        assert result["ownership"]["requested_model"]=="smc_auto"
        assert result["ownership"]["selected_model"]=="volatility_structure_pullback"
        assert result["ownership"]["selection_reason"]=="Only proven production strategy enabled during focused validation."
        assert result["production_status"]=={"strategy_id":"volatility_structure_pullback","production_supported":True,"fixture_buy_reachable":True,"fixture_sell_reachable":True,"historically_observed":False,"live_observed":False,"auto_eligible":True}
        assert result["meta"]["source_timeframe"]=="provided" and result["trade_plan"]["available"]
        assert all({"overlay_id","owner_id","setup_id","type","created_at","actionable_at_decision_time"}<=set(row) for row in result["overlays"])
        assert all(row["owner_id"]=="volatility_structure_pullback" for row in result["overlays"])
        assert all(row["setup_id"] is None for row in result["overlays"] if row["category"]=="context")
        assert all(row["setup_id"]==setup["setup_id"] for row in result["overlays"] if row["category"]=="actionable")
        entry_trace=result["diagnostics"]["entry_trace"];stop_trace=result["diagnostics"]["stop_trace"]
        assert entry_trace["confirmation_time"] and entry_trace["selected_entry"]==setup["entry"]
        assert entry_trace["candidate_sources"][0]["selected_time"]>=entry_trace["confirmation_time"]
        assert stop_trace["selected_stop"]==setup["stop"] and not stop_trace["rejections"]
        intended=stop_trace["candidate_sources"][0]["intended_invalidation"]
        if setup["direction"]=="buy":assert setup["stop"]<intended<setup["entry"]
        else:assert setup["stop"]>intended>setup["entry"]


def test_entry_is_never_emitted_before_completed_confirmation_or_retrace():
    frames=_focused_frames("buy")
    for index in range(80,len(frames["M5"])):
        sliced={key:(value.iloc[:index].copy() if key=="M5" else value.copy()) for key,value in frames.items()}
        at=sliced["M5"].iloc[-1].time;result=evaluate_volatility_structure_pullback(symbol="R_75",candles_by_timeframe=sliced,tick_size=.01,analysis_time=at);trace=result["diagnostics"]["entry_trace"]
        if trace["confirmation_time"] is None:assert trace["selected_entry"] is None and trace["first_blocker"]=="NO_CONFIRMATION"
        if trace["selected_entry"] is not None:assert trace["candidate_sources"][0]["selected_time"]>=trace["confirmation_time"]


def test_developing_workspace_contract_has_specific_backend_stage_fields():
    frames=_focused_frames("sell");frames["M5"]=frames["M5"].iloc[:80].copy();result=evaluate_volatility_structure_pullback(symbol="R_75",display_symbol="Volatility 75 Index",candles_by_timeframe=frames,tick_size=.01,analysis_time=frames["M5"].iloc[-1].time)
    assert result["meta"]["display_symbol"]=="Volatility 75 Index"
    assert result["decision"]["status"]!="NO SETUP"
    assert result["decision"]["stage"] and result["decision"]["first_blocking_gate"]
    assert result["setup"]["m5_confirmation_status"] in {"Waiting for displacement","Waiting for structure break","Waiting for retracement","Passed"}
    assert result["trade_plan"]=={"available":False,"status":"UNAVAILABLE","entry":None,"stop":None,"targets":[],"reason":"Unavailable until all production geometry passes."}


def test_ready_geometry_and_nearest_structural_target_are_coherent():
    for direction in ("buy","sell"):
        result=_decision(direction);setup=result["setup"];target=setup["targets"][0]
        if direction=="buy":assert setup["stop"]<setup["entry"]<target["price"]
        else:assert setup["stop"]>setup["entry"]>target["price"]
        assert target["timeframe"] in {"M5","M15","H1"}


def test_recent_compression_does_not_erase_completed_h1_direction():
    frames=_focused_frames("buy")
    h1=frames["H1"].copy();anchor=float(h1.iloc[-6].close)
    for index in h1.index[-6:]:
        h1.loc[index,["open","close"]]=[anchor,anchor+.01*((index%2)*2-1)]
        h1.loc[index,["high","low"]]=[anchor+.08,anchor-.08]
    frames["H1"]=h1
    result=evaluate_volatility_structure_pullback(symbol="R_75",candles_by_timeframe=frames,tick_size=.01,analysis_time=frames["M5"].iloc[-1].time)
    assert result["market"]["external_structure"]=="bullish"
    assert result["market"]["recent_condition"]=="consolidating"


def test_focused_live_and_replay_inputs_are_deterministic_and_incomplete_is_not_rejected():
    frames=_focused_frames("sell");at=frames["M5"].iloc[-1].time
    live=evaluate_volatility_structure_pullback(symbol="R_75",candles_by_timeframe=frames,tick_size=.01,analysis_time=at)
    replay=evaluate_volatility_structure_pullback(symbol="R_75",candles_by_timeframe={key:value.copy() for key,value in frames.items()},tick_size=.01,analysis_time=at)
    assert live==replay
    early={key:value.iloc[:-12].copy() for key,value in frames.items()}
    developing=evaluate_volatility_structure_pullback(symbol="R_75",candles_by_timeframe=early,tick_size=.01,analysis_time=early["M5"].iloc[-1].time)
    assert "REJECTED" not in developing["decision"]["status"]
    assert not developing["setup"].get("setup_id") or developing["setup"]["direction"] in {"buy","sell"}


def test_fixed_real_month_meets_frequency_and_symmetry_acceptance():
    report=json.loads((Path(__file__).parents[1]/"data"/"volatility75_acceptance"/"latest_audit.json").read_text())
    assert report["dataset"]["selected_before_performance_evaluation"] is True
    assert report["lookahead_violations"]==0 and report["contradictory_states"]==[]
    assert report["counts"]["trade_ready"]>=5
    assert report["counts"]["ready_to_buy"]>=1 and report["counts"]["ready_to_sell"]>=1
    assert report["acceptance"]["passed"] is True
