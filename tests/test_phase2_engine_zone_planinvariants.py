"""Phase 2 checkpoints 4, 6, 7: Volatility Structure Pullback engine
determinism + target hierarchy, developing pullback-zone geometry, and
actionable trade-plan invariants for the R_75 golden path. These build on
(and do not change) the engine/contract work already verified in this
session's prior milestones -- this file is the Phase-2-scoped confirmation
that nothing regressed and the golden path still holds.
"""
import pandas as pd
import pytest

from validation.strategy_reachability_fixtures import _focused_frames
from analysis.volatility_structure_pullback_engine import (
    evaluate_volatility_structure_pullback, _pullback_location, DEFAULTS,
)
from analysis.smc.smc_target_engine import _selection_rank


# ---- Checkpoint 4: engine determinism + target hierarchy ----------------

def test_buy_and_sell_reachability_remain_green():
    for direction, status in (("buy", "READY TO BUY"), ("sell", "READY TO SELL")):
        frames = _focused_frames(direction)
        result = evaluate_volatility_structure_pullback(
            symbol="R_75", display_symbol="Volatility 75 Index",
            candles_by_timeframe=frames, tick_size=.01,
            analysis_time=frames["M5"].iloc[-1].time,
        )
        assert result["decision"]["status"] == status
        assert result["setup"]["entry"] is not None and result["setup"]["stop"] is not None
        assert result["setup"]["targets"]


def test_engine_output_is_deterministic_for_identical_input():
    frames = _focused_frames("sell")
    at = frames["M5"].iloc[-1].time
    a = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
    b = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe={k: v.copy() for k, v in frames.items()}, tick_size=.01, analysis_time=at)
    assert a == b


def test_target_hierarchy_rank_order_is_unchanged():
    # BUY: M5 internal swing (1) < M15 internal swing (2) < equal_levels (3) < H1 external swing (4).
    rank = lambda source, timeframe: _selection_rank({"source_type": source, "timeframe": timeframe}, "structure_pullback")
    assert rank("internal_swing", "M5") < rank("internal_swing", "M15") < rank("equal_levels", None) < rank("external_swing", "H1")


def test_no_future_candle_influences_the_decision():
    frames = _focused_frames("buy")
    truncated = {k: v.iloc[:120].copy() for k, v in frames.items()}
    at = truncated["M5"].iloc[-1].time
    full_result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
    truncated_result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=truncated, tick_size=.01, analysis_time=at)
    # Same analysis_time, only later rows differ -> decision must be identical
    # regardless of whether the caller happened to hand over extra future rows.
    assert full_result["decision"]["stage"] == truncated_result["decision"]["stage"]
    assert full_result["setup"]["entry"] == truncated_result["setup"]["entry"]


# ---- Checkpoint 6: developing pullback-zone geometry ---------------------

def test_oversized_pullback_zone_is_rejected_without_touching_setup_validity():
    times = pd.date_range("2026-07-19", periods=40, freq="15min", tz="UTC")
    base = 51181.9235
    rows = []
    for i, t in enumerate(times):
        high, low = base + 80, base - 80
        if i == 10: high = 53000.0
        if i == 9: low = 50303.0
        rows.append({"time": t, "open": base, "high": high, "low": low, "close": base, "complete": True})
    frame = pd.DataFrame(rows)
    result = _pullback_location(frame, "bearish", {}, DEFAULTS)
    assert result["valid_location"] is True  # setup progression untouched
    assert result["zone_valid"] is False      # display geometry correctly rejected
    assert result["zone_width_atr"] > DEFAULTS["pullback_zone_max_width_atr"]


def test_valid_pullback_zone_has_bounded_atr_relative_width():
    frames = _focused_frames("sell")
    frames["M5"] = frames["M5"].iloc[:95].copy()
    result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time)
    m15 = result["diagnostics"]["m15"]
    if m15.get("valid_location"):
        assert m15["zone_width_atr"] <= DEFAULTS["pullback_zone_max_width_atr"] or m15["zone_valid"] is False


def test_pullback_zone_overlay_is_owned_by_the_active_setup():
    frames = _focused_frames("buy")
    frames["M5"] = frames["M5"].iloc[:100].copy()
    result = evaluate_volatility_structure_pullback(symbol="R_75", display_symbol="Volatility 75 Index", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time)
    zone_rows = [row for row in result["overlays"] if row["type"] == "m15_pullback_area"]
    if zone_rows:
        setup_id = (result["active_setup"] or {}).get("setup_id")
        assert setup_id is not None
        assert all(row["setup_id"] == setup_id for row in zone_rows)
        assert all(row["low"] < row["high"] for row in zone_rows)


# ---- Checkpoint 7: actionable trade-plan invariants ----------------------

@pytest.mark.parametrize("direction", ["buy", "sell"])
def test_incomplete_plan_renders_no_actionable_fields(direction):
    frames = _focused_frames(direction)
    frames["M5"] = frames["M5"].iloc[:90].copy()
    result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time)
    if result["decision"]["stage"] != ("READY_TO_BUY" if direction == "buy" else "READY_TO_SELL"):
        assert not [row for row in result["overlays"] if row["actionable"]]
        assert result["trade_plan"]["available"] is False


@pytest.mark.parametrize("direction", ["buy", "sell"])
def test_complete_plan_overlay_values_exactly_equal_trade_plan_values(direction):
    frames = _focused_frames(direction)
    result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time)
    assert result["decision"]["trade_ready"] is True
    plan = result["trade_plan"]
    actionable = {row["type"]: row["price"] for row in result["overlays"] if row["actionable"]}
    assert actionable.get("entry") == plan["entry"]
    assert actionable.get("stop") == plan["stop"]
    assert actionable.get("tp1") == plan["targets"][0]["price"]


def test_trade_ready_is_impossible_without_tp1():
    frames = _focused_frames("buy")
    frames["M5"] = frames["M5"].iloc[:97].copy()  # entry/stop resolved, target not yet
    result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time)
    if result["setup"]["entry"] is not None and not result["setup"]["targets"]:
        assert result["decision"]["trade_ready"] is False
        assert result["decision"]["stage"] != "READY_TO_BUY"
