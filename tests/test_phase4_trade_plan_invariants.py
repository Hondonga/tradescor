"""Phase 4 checkpoint 15: actionable trade-plan invariants for GBP/USD.
Overlay values must exactly match trade-plan values; incomplete plans must
never produce actionable overlays.
"""
from analysis.global_overlay_contract import normalize_global_decision


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


def _ready_setup(entry=1.2710, stop=1.2750, tp1=1.2620, tp2=1.2580):
    return {
        "setup_id": "ict-1", "direction": "sell", "stage": "TRADE_READY", "status": "READY TO SELL",
        "trade_ready": True, "entry": entry, "stop": stop,
        "targets": [{"name": "TP1", "price": tp1, "risk_reward": 2.0}, {"name": "TP2", "price": tp2, "risk_reward": 3.5}],
        "rr": 2.0, "entry_area": {"low": entry - 0.0005, "high": entry + 0.0005, "type": "execution_area"},
        "completed_confirmation": {"confirmed": True},
    }


def _ready_overlays(entry=1.2710, stop=1.2750, tp1=1.2620, tp2=1.2580):
    def row(overlay_id, kind, price, actionable=True):
        return {"overlay_id": overlay_id, "decision_owner_id": "ict_2022", "strategy_id": "ict_2022", "setup_id": "ict-1", "symbol_id": "twelve_data:GBP/USD", "provider_symbol": "GBP/USD", "market_type": "forex", "timeframe": "M5", "category": "actionable" if actionable else "context", "type": kind, "label": kind.upper(), "source": "backend", "price": price, "low": None, "high": None, "start_time": None, "end_time": None, "created_at": None, "confirmed_at": None, "expires_at": None, "invalidated_at": None, "active": True, "historical": False, "actionable": actionable, "priority": 100, "display_group": "trade_plan", "metadata": {"plan_role": kind}}
    return [row("entry", "entry", entry), row("stop", "stop", stop), row("tp1", "tp1", tp1), row("tp2", "tp2", tp2)]


def test_no_active_setup_means_no_actionable_overlays():
    product = _base(setup={"setup_id": None, "direction": None, "stage": "NO_CONTEXT", "status": "NO CONTEXT", "trade_ready": False, "entry": None, "stop": None, "targets": []}, decision={"status": "MARKET CONTEXT", "direction": None, "stage": "NO_CONTEXT", "trade_ready": False, "next_action": "x"})
    value = normalize_global_decision(product)
    assert value["active_setup"] is None
    assert not [row for row in value["overlays"] if row.get("actionable")]


def test_entry_null_means_stop_and_targets_are_absent_from_actionable_overlays():
    product = _base()  # entry=None, stop=None, targets=[] already
    value = normalize_global_decision(product)
    actionable = [row for row in value["overlays"] if row.get("actionable")]
    assert not actionable


def test_trade_ready_requires_tp1_or_lifecycle_cannot_be_trade_ready():
    product = _base()
    product["decision"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True)
    product["setup"].update(status="READY TO SELL", stage="TRADE_READY", trade_ready=True, entry=1.2710, stop=1.2750, targets=[])
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"
    assert value["decision"]["trade_ready"] is False


def test_complete_ready_plan_overlay_values_exactly_equal_trade_plan_values():
    product = _base(
        decision={"status": "READY TO SELL", "direction": "sell", "stage": "TRADE_READY", "trade_ready": True, "next_action": "x"},
        setup=_ready_setup(),
        overlays=_ready_overlays(),
    )
    value = normalize_global_decision(product)
    assert value["decision"]["trade_ready"] is True
    plan = value["trade_plan"]
    actionable = {row["type"]: row["price"] for row in value["overlays"] if row.get("actionable")}
    assert actionable["entry"] == plan["entry"]
    assert actionable["stop"] == plan["stop"]
    plan_targets = {t["name"].lower(): t["price"] for t in plan["targets"]}
    assert actionable["tp1"] == plan_targets["tp1"]
    assert actionable["tp2"] == plan_targets["tp2"]


def test_stale_data_makes_trade_plan_unavailable_even_with_complete_geometry():
    product = _base(
        readiness={"state": "stale"},
        decision={"status": "READY TO SELL", "direction": "sell", "stage": "TRADE_READY", "trade_ready": True, "next_action": "x"},
        setup=_ready_setup(),
        overlays=_ready_overlays(),
    )
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"
    assert not [row for row in value["overlays"] if row.get("actionable")]


def test_market_closed_makes_trade_plan_unavailable_even_with_complete_geometry():
    product = _base(
        readiness={"state": "market_closed"},
        decision={"status": "READY TO SELL", "direction": "sell", "stage": "TRADE_READY", "trade_ready": True, "next_action": "x"},
        setup=_ready_setup(),
        overlays=_ready_overlays(),
    )
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"
    assert not [row for row in value["overlays"] if row.get("actionable")]


def test_ownership_mismatch_makes_trade_plan_unavailable():
    product = _base(
        decision={"status": "READY TO SELL", "direction": "sell", "stage": "TRADE_READY", "trade_ready": True, "next_action": "x"},
        setup=_ready_setup(),
        overlays=_ready_overlays(),
    )
    product["ownership"]["overlay_owner_id"] = "some_other_strategy"
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"
