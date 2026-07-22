"""Phase 4 checkpoint 21: Forex paper-testing safety gate.

registerable_forex_paper_setup() must only ever narrow the shared
paper_registration_allowed gate (analysis/global_overlay_contract.py), and
must always record historical_edge_proven/profitability_claim_allowed/
live_execution_allowed as False -- Phase 4 proves reachability and contract
correctness only, never profitability or live-trading readiness.
"""
from analysis.forex_paper_eligibility import registerable_forex_paper_setup
from analysis.global_overlay_contract import normalize_global_decision


def _base(direction="sell", readiness="ready", **overrides):
    product = {
        "decision_id": "d", "overlay_mode": "LIVE",
        "precision": {"symbol_id": "twelve_data:GBP/USD", "price_decimals": 5, "pip_size": 0.0001, "tick_size": 1e-05, "quantity_decimals": None},
        "meta": {"symbol": "GBP/USD", "display_symbol": "GBP/USD", "timeframe": "M5", "analysis_time": "2026-01-06T08:00:00Z", "live": True, "market_schedule": "24_5", "analysis_clock": "UTC", "market_source": "twelve_data", "market_type": "forex"},
        "ownership": {"selected_model_id": "ict_2022", "decision_owner_id": "ict_2022", "overlay_owner_id": "ict_2022"},
        "readiness": {"state": readiness},
        "market": {"external_structure": "bearish", "internal_structure": "pullback", "current_price": 1.2710},
        "decision": {"status": f"{direction.upper()} SETUP DEVELOPING", "direction": direction, "stage": "WAITING_FOR_DISPLACEMENT", "trade_ready": False, "next_action": "x"},
        "setup": {"setup_id": "ict-1", "direction": direction, "stage": "WAITING_FOR_DISPLACEMENT", "status": f"{direction.upper()} SETUP DEVELOPING", "trade_ready": False, "entry": None, "stop": None, "targets": []},
        "overlays": [],
        "previous_setup": None,
    }
    product.update(overrides)
    return product


def _ready_setup(direction, entry, stop, tp1, tp2):
    return {
        "setup_id": "ict-1", "direction": direction, "stage": "TRADE_READY",
        "status": "READY TO BUY" if direction == "buy" else "READY TO SELL", "trade_ready": True,
        "entry": entry, "stop": stop,
        "targets": [{"name": "TP1", "price": tp1, "risk_reward": 2.0}, {"name": "TP2", "price": tp2, "risk_reward": 3.5}],
        "rr": 2.0, "entry_area": {"low": entry - 0.0005, "high": entry + 0.0005, "type": "execution_area"},
        "completed_confirmation": {"confirmed": True},
    }


def _ready_overlays(entry, stop, tp1, tp2):
    def row(overlay_id, kind, price):
        return {"overlay_id": overlay_id, "decision_owner_id": "ict_2022", "strategy_id": "ict_2022", "setup_id": "ict-1", "symbol_id": "twelve_data:GBP/USD", "provider_symbol": "GBP/USD", "market_type": "forex", "timeframe": "M5", "category": "actionable", "type": kind, "label": kind.upper(), "source": "backend", "price": price, "low": None, "high": None, "start_time": None, "end_time": None, "created_at": None, "confirmed_at": None, "expires_at": None, "invalidated_at": None, "active": True, "historical": False, "actionable": True, "priority": 100, "display_group": "trade_plan", "metadata": {"plan_role": kind}}
    return [row("entry", "entry", entry), row("stop", "stop", stop), row("tp1", "tp1", tp1), row("tp2", "tp2", tp2)]


def _trade_ready_product(direction="sell", **overrides):
    if direction == "sell":
        entry, stop, tp1, tp2 = 1.2710, 1.2750, 1.2620, 1.2580
    else:
        entry, stop, tp1, tp2 = 1.2710, 1.2670, 1.2800, 1.2840
    product = _base(direction=direction, **overrides)
    product["decision"] = {"status": "READY TO SELL" if direction == "sell" else "READY TO BUY", "direction": direction, "stage": "TRADE_READY", "trade_ready": True, "next_action": "x"}
    product["setup"] = _ready_setup(direction, entry, stop, tp1, tp2)
    product["overlays"] = _ready_overlays(entry, stop, tp1, tp2)
    return product


def _eval(product, mode="LIVE"):
    return normalize_global_decision(product, mode=mode)


def test_trade_ready_buy_is_eligible_and_never_claims_profitability_or_live_execution():
    result = registerable_forex_paper_setup(_eval(_trade_ready_product("buy")))
    assert result["eligible"] is True
    assert result["historical_edge_proven"] is False
    assert result["profitability_claim_allowed"] is False
    assert result["live_execution_allowed"] is False
    assert result["reason"] is None


def test_trade_ready_sell_is_eligible():
    result = registerable_forex_paper_setup(_eval(_trade_ready_product("sell")))
    assert result["eligible"] is True


def test_market_context_is_blocked():
    product = _base(direction="sell")
    product["decision"] = {"status": "MARKET CONTEXT", "direction": None, "stage": "NO_CONTEXT", "trade_ready": False, "next_action": "x"}
    product["setup"] = {"setup_id": None, "direction": None, "stage": "NO_CONTEXT", "status": "NO CONTEXT", "trade_ready": False, "entry": None, "stop": None, "targets": []}
    result = registerable_forex_paper_setup(_eval(product))
    assert result["eligible"] is False


def test_waiting_state_is_blocked():
    result = registerable_forex_paper_setup(_eval(_base(direction="sell")))
    assert result["eligible"] is False
    assert "not reached TRADE_READY" in result["reason"]


def test_plan_validation_with_no_target_is_blocked():
    product = _trade_ready_product("sell")
    product["setup"]["targets"] = []
    result = registerable_forex_paper_setup(_eval(product))
    assert result["eligible"] is False


def test_stale_data_is_blocked_even_with_complete_geometry():
    result = registerable_forex_paper_setup(_eval(_trade_ready_product("sell", readiness="stale")))
    assert result["eligible"] is False


def test_market_closed_is_blocked_even_with_complete_geometry():
    result = registerable_forex_paper_setup(_eval(_trade_ready_product("buy", readiness="market_closed")))
    assert result["eligible"] is False


def test_expired_is_blocked():
    product = _trade_ready_product("sell")
    product["decision"].update(status="SETUP EXPIRED", stage="EXPIRED")
    product["setup"].update(status="SETUP EXPIRED", stage="EXPIRED")
    result = registerable_forex_paper_setup(_eval(product))
    assert result["eligible"] is False


def test_invalidated_is_blocked():
    product = _trade_ready_product("buy")
    product["decision"].update(status="SETUP INVALIDATED", stage="INVALIDATED")
    product["setup"].update(status="SETUP INVALIDATED", stage="INVALIDATED")
    result = registerable_forex_paper_setup(_eval(product))
    assert result["eligible"] is False


def test_replay_mode_is_blocked_even_with_a_complete_ready_plan():
    result = registerable_forex_paper_setup(_eval(_trade_ready_product("sell"), mode="REPLAY"))
    assert result["eligible"] is False
    assert "not LIVE" in result["reason"]


def test_historical_inspection_mode_is_blocked():
    result = registerable_forex_paper_setup(_eval(_trade_ready_product("buy"), mode="HISTORICAL_INSPECTION"))
    assert result["eligible"] is False


def test_state_contradiction_is_blocked():
    product = _trade_ready_product("sell")
    product["setup"]["targets"] = []  # trade_ready=True but no TP1 -> contradiction
    result = registerable_forex_paper_setup(_eval(product))
    assert result["eligible"] is False


def test_never_grants_eligibility_the_shared_gate_denied():
    # Defense-in-depth: even if paper_registration_allowed were somehow
    # True on a non-forex/non-live product, the Forex-specific checks must
    # still refuse it.
    evaluated = _eval(_trade_ready_product("buy"))
    evaluated["meta"]["market_type"] = "derived"  # tamper after the shared gate ran
    result = registerable_forex_paper_setup(evaluated)
    assert result["eligible"] is False
