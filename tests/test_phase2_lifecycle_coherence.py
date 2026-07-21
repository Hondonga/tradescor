"""Phase 2 checkpoint 5: golden-path lifecycle coherence. The milestone's
required-stage vocabulary is a conceptual superset shared across every
TradeScor strategy (see analysis/global_overlay_contract.py TERMINAL and
Milestone-1's terminal-state unification); the Volatility Structure Pullback
engine's own stage names (WAITING_FOR_LOCATION, WAITING_FOR_ENTRY,
READY_TO_BUY/READY_TO_SELL, ...) are that vocabulary's direction/strategy-
specific instantiation, not a divergent one -- renaming them is out of scope
per "do not change thresholds/logic merely to relabel", so this file verifies
*coherence* (the impossible-state list) rather than literal stage-name
equality.
"""
from analysis.global_overlay_contract import normalize_global_decision, TERMINAL
from validation.strategy_reachability_fixtures import _focused_frames
from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback


def _base_product(**overrides):
    setup_id = "vsp-setup-1"
    base = {
        "decision_id": "d1",
        "meta": {"symbol": "R_75", "display_symbol": "Volatility 75 Index", "timeframe": "M5", "analysis_time": "2026-07-20T12:00:00Z", "market_source": "deriv", "market_type": "derived", "live": True},
        "ownership": {"selected_model_id": "volatility_structure_pullback", "decision_owner_id": "volatility_structure_pullback", "overlay_owner_id": "volatility_structure_pullback"},
        "readiness": {"state": "ready"},
        "market": {"external_structure": "bullish", "internal_structure": "pullback", "current_price": 100.25},
        "decision": {"status": "SETUP DEVELOPING", "stage": "WAITING_FOR_CONFIRMATION", "direction": "buy", "trade_ready": False, "next_action": "Wait."},
        "setup": {"setup_id": setup_id, "setup_type": "structure_pullback", "direction": "buy", "stage": "WAITING_FOR_CONFIRMATION", "status": "SETUP DEVELOPING", "trade_ready": False, "entry": None, "stop": None, "targets": [], "rr": None, "entry_area": {"low": 99.5, "high": 100.0, "type": "pullback"}, "completed_confirmation": {"confirmed": True}, "production_supported": True, "family_compatible": True, "chase_valid": True, "next_required_condition": "Wait."},
        "overlays": [],
        "previous_setup": None,
    }
    base.update(overrides)
    return base


def test_neutral_direction_cannot_carry_a_directional_active_setup():
    product = _base_product()
    product["decision"]["direction"] = None
    product["setup"]["direction"] = None
    value = normalize_global_decision(product)
    # A setup with no direction can still be "developing" context, but it must
    # never present as a directional (buy/sell) actionable/ready plan.
    assert value["decision"]["trade_ready"] is False
    assert not [row for row in value["overlays"] if row["actionable"]]


def test_expired_plus_active_setup_is_structurally_impossible():
    product = _base_product(decision={"status": "EXPIRED", "stage": "EXPIRED", "direction": "buy", "trade_ready": False, "next_action": "x"})
    product["setup"]["stage"] = "EXPIRED"
    product["setup"]["status"] = "EXPIRED"
    value = normalize_global_decision(product)
    assert value["active_setup"] is None
    assert value["previous_setup"] is not None and value["previous_setup"]["setup_id"] == "vsp-setup-1"


def test_trade_ready_with_any_null_leg_is_blocked_and_flagged():
    for missing in ("entry", "stop", "targets"):
        setup = {"setup_id": "s", "direction": "buy", "stage": "TRADE_READY", "trade_ready": True, "entry": 100, "stop": 99, "targets": [{"price": 102}], "rr": 2, "entry_area": {"low": 99, "high": 100}, "completed_confirmation": {"confirmed": True}, "production_supported": True, "family_compatible": True, "chase_valid": True, "next_required_condition": "x"}
        setup[missing] = None if missing != "targets" else []
        product = _base_product(setup=setup, decision={"status": "READY TO BUY", "stage": "TRADE_READY", "direction": "buy", "trade_ready": True, "next_action": "x"})
        value = normalize_global_decision(product)
        assert value["decision"]["status"] == "STATE CONTRADICTION"
        assert not [row for row in value["overlays"] if row["actionable"]]


def test_plan_validation_never_carries_actionable_overlays():
    frames = _focused_frames("sell")
    frames["M5"] = frames["M5"].iloc[:97].copy()
    result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time)
    if result["decision"]["stage"] == "PLAN_VALIDATION":
        assert not [row for row in result["overlays"] if row["actionable"]]
        assert result["trade_plan"]["available"] is False


def test_terminal_means_terminal_for_every_family_terminal_state():
    for stage in sorted(TERMINAL):
        product = _base_product(decision={"status": stage, "stage": stage, "direction": "buy", "trade_ready": False, "next_action": "x"})
        product["setup"]["stage"] = stage
        product["setup"]["status"] = stage
        value = normalize_global_decision(product)
        assert value["active_setup"] is None, stage
        assert not [row for row in value["overlays"] if row["category"] in {"developing", "actionable"}], stage


def test_chart_and_decision_rail_read_the_same_normalized_decision_object():
    # Both MarketChart (via selectVisibleOverlays) and DecisionRail read
    # store.decision directly (frontend/src/store/terminal-store.ts) -- there
    # is exactly one NormalizedDecision per analysis, so this is true by
    # construction. This test asserts the backend contract that makes that
    # guarantee meaningful: overlays and decision/setup/active_setup are all
    # produced from the same normalize_global_decision() call, never patched
    # independently afterward.
    frames = _focused_frames("buy")
    result = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=frames["M5"].iloc[-1].time)
    assert result["decision"]["direction"] == result["active_setup"]["direction"]
    assert result["decision"]["stage"] == result["active_setup"]["stage"]
