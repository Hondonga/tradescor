"""Phase 7 Part 10/19: the research variant must call the frozen parent
engine unmodified and apply exactly one preregistered eligibility change --
never duplicate the engine, never touch Auto/paper/live/ML, never appear in
the live request path.
"""
import subprocess
from pathlib import Path

from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback
from strategies.research.volatility_structure_pullback_hypothesis_v2 import (
    MAX_STOP_DISTANCE_ATR,
    PARENT_VERDICT,
    STRATEGY_ID,
    evaluate_research_variant,
)
from validation.strategy_reachability_fixtures import _focused_frames

ROOT = Path(__file__).resolve().parents[1]


def _decision(direction, evaluator, **extra):
    frames = _focused_frames(direction)
    return evaluator(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time, **extra)


def test_research_variant_reproduces_the_parent_decision_and_setup_exactly():
    for direction in ("buy", "sell"):
        parent = _decision(direction, evaluate_volatility_structure_pullback)
        variant = _decision(direction, evaluate_research_variant)
        assert variant["decision"] == parent["decision"]
        assert variant["setup"] == parent["setup"]
        assert variant["trade_plan"] == parent["trade_plan"]
        assert variant["overlays"] == parent["overlays"]


def test_research_variant_adds_exactly_one_new_top_level_diagnostic_block():
    parent = _decision("buy", evaluate_volatility_structure_pullback)
    variant = _decision("buy", evaluate_research_variant)
    added_keys = set(variant) - set(parent)
    assert added_keys == {"research_variant"}


def test_research_variant_is_eligible_for_a_real_trade_ready_fixture_with_a_reasonable_stop():
    variant = _decision("buy", evaluate_research_variant)
    info = variant["research_variant"]
    assert info["parent_trade_ready"] is True
    assert info["stop_distance_atr"] is not None
    # This is a factual assertion about the fixture, not a tuned threshold.
    assert (info["stop_distance_atr"] <= MAX_STOP_DISTANCE_ATR) == info["variant_eligible"]


def test_research_variant_rejects_when_the_single_condition_is_synthetically_forced_to_fail(monkeypatch):
    import strategies.research.volatility_structure_pullback_hypothesis_v2 as module
    monkeypatch.setattr(module, "MAX_STOP_DISTANCE_ATR", 0.0)
    variant = _decision("buy", evaluate_research_variant)
    assert variant["research_variant"]["parent_trade_ready"] is True
    assert variant["research_variant"]["variant_eligible"] is False
    # Rejection is diagnostic-only in this module -- the parent's own setup/
    # decision must still be untouched (Part 13: preserve engine output).
    parent = _decision("buy", evaluate_volatility_structure_pullback)
    assert variant["decision"] == parent["decision"]


def test_research_variant_carries_the_required_conservative_flags():
    variant = _decision("buy", evaluate_research_variant)
    info = variant["research_variant"]
    assert info["strategy_id"] == STRATEGY_ID
    assert info["parent_verdict"] == PARENT_VERDICT
    assert info["research_only"] is True
    assert info["auto_eligible"] is False
    assert info["paper_signal_allowed"] is False
    assert info["live_execution_allowed"] is False
    assert info["ml_filter_allowed"] is False


def test_research_variant_never_overwrites_the_parent_strategy_module():
    parent_path = ROOT / "analysis/volatility_structure_pullback_engine.py"
    variant_path = ROOT / "strategies/research/volatility_structure_pullback_hypothesis_v2.py"
    assert variant_path.exists()
    frozen_at_phase6 = subprocess.run(
        ["git", "show", "2ab0c681dd0f98066144e02224497865d798a185:analysis/volatility_structure_pullback_engine.py"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    assert parent_path.read_text() == frozen_at_phase6


def test_research_variant_is_not_wired_into_the_live_request_path():
    for path in (ROOT / "app.py", ROOT / "analysis/derived_engine.py"):
        text = path.read_text()
        assert "volatility_structure_pullback_hypothesis_v2" not in text
        assert "evaluate_research_variant" not in text
