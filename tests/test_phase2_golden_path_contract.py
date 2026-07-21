"""Phase 2 checkpoint 2: one authoritative R_75 Volatility Structure Pullback
normalized decision — required top-level shape, ownership invariant, and no
conflicting trade-plan representation between the legacy `setup` mirror and
the canonical `active_setup`/`trade_plan` fields.
"""
from validation.strategy_reachability_fixtures import _focused_frames
from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback

REQUIRED_TOP_LEVEL_KEYS = {
    "meta", "ownership", "readiness", "current_market", "active_setup",
    "trade_plan", "previous_setup", "research_scenario", "diagnostics",
    "overlays", "precision",
}


def _decision(direction, truncate_m5=None):
    frames = _focused_frames(direction)
    if truncate_m5:
        frames["M5"] = frames["M5"].iloc[:truncate_m5].copy()
    return evaluate_volatility_structure_pullback(
        symbol="R_75", display_symbol="Volatility 75 Index",
        candles_by_timeframe=frames, tick_size=.01,
        analysis_time=frames["M5"].iloc[-1].time,
    )


def test_required_top_level_keys_are_present_for_ready_and_developing():
    for result in (_decision("buy"), _decision("sell", truncate_m5=80)):
        assert REQUIRED_TOP_LEVEL_KEYS <= set(result)


def test_ownership_invariant_decision_owner_equals_overlay_owner():
    for result in (_decision("buy"), _decision("sell")):
        ownership = result["ownership"]
        assert ownership["decision_owner_id"] == ownership["overlay_owner_id"]
        assert ownership["selected_model_id"] == "volatility_structure_pullback"
        assert ownership["selected_strategy_id"] == "volatility_structure_pullback"


def test_no_conflicting_trade_plan_representation_when_ready():
    result = _decision("sell")
    assert result["decision"]["trade_ready"] is True
    trade_plan, active_setup, legacy_setup = result["trade_plan"], result["active_setup"], result["setup"]
    assert trade_plan["entry"] == active_setup["entry"] == legacy_setup["entry"]
    assert trade_plan["stop"] == active_setup["stop"] == legacy_setup["stop"]
    assert active_setup["setup_id"] == legacy_setup["setup_id"]


def test_no_conflicting_trade_plan_representation_when_not_ready():
    result = _decision("sell", truncate_m5=80)
    assert result["decision"]["trade_ready"] is False
    assert result["trade_plan"]["available"] is False
    assert result["trade_plan"]["entry"] is None
    assert result["setup"]["entry"] is None
    # active_setup may legitimately be a non-null *developing* setup, but its
    # entry/stop must agree with the unavailable trade plan, never contradict it.
    if result["active_setup"] is not None:
        assert result["active_setup"]["entry"] is None


def test_one_setup_id_owns_every_setup_specific_overlay():
    result = _decision("buy", truncate_m5=95)
    setup_id = (result["active_setup"] or {}).get("setup_id")
    setup_owned = [row for row in result["overlays"] if row["category"] in {"developing", "actionable"}]
    if setup_owned:
        assert setup_id is not None
        assert all(row["setup_id"] == setup_id for row in setup_owned)
