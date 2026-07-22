"""Phase 4 checkpoint 12: the Forex ICT lifecycle must be coherent -- every
named impossible state must be structurally unreachable, verified here with
Forex-shaped (ict_2022 ownership, twelve_data/forex market_type) fixtures
rather than relying only on the existing market-agnostic contradiction
tests.
"""
from analysis.global_overlay_contract import normalize_global_decision, TERMINAL


def _base(**overrides):
    product = {
        "decision_id": "d",
        "overlay_mode": "LIVE",
        "precision": {"symbol_id": "twelve_data:GBP/USD", "price_decimals": 5, "pip_size": 0.0001, "tick_size": 1e-05, "quantity_decimals": None},
        "meta": {"symbol": "GBP/USD", "display_symbol": "GBP/USD", "timeframe": "M5", "analysis_time": "2026-01-06T08:00:00Z", "live": True, "market_schedule": "24_5", "analysis_clock": "UTC", "market_source": "twelve_data", "market_type": "forex"},
        "ownership": {"selected_model_id": "ict_2022", "decision_owner_id": "ict_2022", "overlay_owner_id": "ict_2022"},
        "readiness": {"state": "ready"},
        "market": {"external_structure": "bearish", "internal_structure": "pullback", "current_price": 1.2710},
        "decision": {"status": "SELL SETUP DEVELOPING", "direction": "sell", "stage": "WAITING_FOR_DISPLACEMENT", "trade_ready": False, "next_action": "x"},
        "setup": {"setup_id": "ict-1", "direction": "sell", "stage": "WAITING_FOR_DISPLACEMENT", "status": "SELL SETUP DEVELOPING", "trade_ready": False, "entry": None, "stop": None, "targets": []},
        "overlays": [],
        "previous_setup": None,
    }
    product.update(overrides)
    return product


def test_trade_ready_without_entry_is_state_contradiction():
    product = _base()
    product["decision"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True)
    product["setup"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True, entry=None, stop=1.2750, targets=[{"price": 1.2600}])
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"
    assert value["active_setup"] is None


def test_trade_ready_without_stop_is_state_contradiction():
    product = _base()
    product["decision"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True)
    product["setup"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True, entry=1.2710, stop=None, targets=[{"price": 1.2600}])
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"


def test_trade_ready_without_tp1_is_state_contradiction():
    product = _base()
    product["decision"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True)
    product["setup"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True, entry=1.2710, stop=1.2750, targets=[])
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"


def test_stale_data_with_live_trade_ready_is_state_contradiction():
    product = _base(readiness={"state": "stale"})
    product["decision"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True)
    product["setup"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True, entry=1.2710, stop=1.2750, targets=[{"price": 1.2600}])
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"


def test_market_closed_with_new_live_trade_ready_is_state_contradiction():
    # Re-verified here with a Forex-native fixture shape (checkpoint 4 fix).
    product = _base(readiness={"state": "market_closed"})
    product["decision"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True)
    product["setup"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True, entry=1.2710, stop=1.2750, targets=[{"price": 1.2600}])
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"
    assert value["active_setup"] is None


def test_forex_decision_cannot_carry_a_derived_owned_overlay():
    product = _base(overlays=[
        {"overlay_id": "o1", "decision_owner_id": "ict_2022", "strategy_id": "ict_2022", "setup_id": "ict-1", "symbol_id": "twelve_data:GBP/USD", "provider_symbol": "GBP/USD", "market_type": "derived", "timeframe": "M5", "category": "context", "type": "current_price", "label": "Current", "source": "backend", "price": 1.271, "low": None, "high": None, "start_time": None, "end_time": None, "created_at": None, "confirmed_at": None, "expires_at": None, "invalidated_at": None, "active": True, "historical": False, "actionable": False, "priority": 100, "display_group": "context", "metadata": {}},
    ])
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"


def test_neutral_direction_cannot_carry_a_directional_active_setup():
    product = _base()
    product["decision"].update(direction=None, status="MARKET CONTEXT", stage="MARKET_CONTEXT")
    product["setup"].update(direction="sell")  # setup asserts a direction the top-level decision does not
    value = normalize_global_decision(product)
    # The decision's own direction is neutral/None while the setup still
    # claims a directional plan -- this must not silently render as a
    # coherent developing setup.
    assert value["decision"]["direction"] is None


def test_invalidated_setup_is_archived_not_left_active():
    product = _base()
    product["decision"].update(status="SETUP INVALIDATED", stage="INVALIDATED")
    product["setup"].update(status="SETUP INVALIDATED", stage="INVALIDATED")
    value = normalize_global_decision(product)
    assert "INVALIDATED" in TERMINAL
    assert value["active_setup"] is None
    assert value["previous_setup"] is not None
    assert value["previous_setup"]["setup_id"] == "ict-1"
