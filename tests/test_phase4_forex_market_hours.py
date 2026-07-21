"""Phase 4 checkpoint 4/5/12: Forex is not a continuous seven-day market.

Fixes a real, reproducible bug found during Phase 4 research: every other
gated asset type (index/equity/commodity) ANDs entry_allowed with
market_open in scanner/session_engine.py::get_session_status, but the
forex branch never did -- a Saturday at a time-of-day that overlapped a
defined kill-zone clock window read entry_allowed=True even though the
market was actually closed. Also verifies the new MARKET_CLOSED readiness
state blocks a new live active setup/TRADE_READY the same way
error/insufficient readiness already did.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from scanner.session_engine import get_session_status
from analysis.market_decision_normalizer import normalize_market_decision
from analysis.global_overlay_contract import normalize_global_decision

NEW_YORK = ZoneInfo("America/New_York")


def test_saturday_during_a_kill_zone_clock_window_blocks_entry():
    saturday = datetime(2026, 1, 10, 3, 0, tzinfo=NEW_YORK)  # Saturday, "London Kill Zone" clock window
    ctx = get_session_status(saturday, asset_type="forex")
    assert ctx["name"] == "London Kill Zone"
    assert ctx["kill_zone_active"] is True
    assert ctx["market_open"] is False
    assert ctx["entry_allowed"] is False  # the bug: this used to be True


def test_weekday_during_the_same_kill_zone_clock_window_still_allows_entry():
    tuesday = datetime(2026, 1, 6, 3, 0, tzinfo=NEW_YORK)
    ctx = get_session_status(tuesday, asset_type="forex")
    assert ctx["name"] == "London Kill Zone"
    assert ctx["market_open"] is True
    assert ctx["entry_allowed"] is True


def test_sunday_before_reopen_blocks_entry_sunday_after_reopen_allows_it():
    before_open = datetime(2026, 1, 11, 16, 0, tzinfo=NEW_YORK)  # Sunday, before 17:00 reopen
    after_open = datetime(2026, 1, 11, 18, 0, tzinfo=NEW_YORK)
    assert get_session_status(before_open, asset_type="forex")["market_open"] is False
    assert get_session_status(after_open, asset_type="forex")["market_open"] is True


def test_other_gated_asset_types_are_unaffected_by_the_forex_fix():
    saturday = datetime(2026, 1, 10, 11, 0, tzinfo=NEW_YORK)
    crypto = get_session_status(saturday, asset_type="crypto")
    assert crypto["market_open"] is True and crypto["entry_allowed"] is True


def _legacy_product(*, market_open):
    return {
        "decision_id": "d1",
        "setup": {"setup_id": "fx-1", "direction": "sell", "stage": "entry_valid", "type": "ict_2022"},
        "execution": {"state": "entry_valid", "entry": 1.27, "stop": 1.275, "targets": [{"name": "TP1", "price": 1.26, "risk_reward": 2.0}], "risk_reward": 2.0},
        "quality": {"trade_plan_valid": True, "data_quality": "valid", "score": 80},
        "user_output": {"status": "READY TO SELL", "direction": "sell", "summary": "", "next_action": ""},
        "strategy_routing": {"selected_strategy": "ict_2022", "reason": "test"},
        "top_down": {"H1": {"structure": "bearish"}, "M15": {"structure": "pullback"}},
        "trade_chart": {"current_price": 1.271},
        "filters": {"session": {"market_open": market_open, "entry_allowed": market_open, "name": "London Kill Zone"}},
        "candle_bundle": {"timeframes": {}},
        "previous_setup": None,
        "overlays": [],
    }


def test_market_open_normalizes_to_ready_readiness():
    decision = normalize_market_decision(
        _legacy_product(market_open=True),
        symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M5",
        market_source="twelve_data", market_type="forex", market_schedule="24_5",
        analysis_time="2026-01-06T08:00:00Z",
    )
    assert decision["readiness"]["state"] == "ready"


def test_market_closed_normalizes_to_market_closed_readiness_and_blocks_the_active_setup():
    decision = normalize_market_decision(
        _legacy_product(market_open=False),
        symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M5",
        market_source="twelve_data", market_type="forex", market_schedule="24_5",
        analysis_time="2026-01-10T08:00:00Z",
    )
    assert decision["readiness"]["state"] == "market_closed"
    # Even though the underlying legacy product asserted trade_ready with a
    # full entry/stop/TP1 plan, MARKET_CLOSED readiness must still block a
    # new live active setup / TRADE_READY -- this is the impossible-state
    # guarantee from checkpoint 12 ("market closed with new live TRADE_READY").
    assert decision["active_setup"] is None


def test_market_closed_with_asserted_trade_ready_is_a_state_contradiction_not_a_silent_pass():
    # Defense in depth: even if some future code path forgets to check
    # readiness before asserting trade_ready, the contradiction detector
    # must catch "trade-ready with no active setup" on its own.
    product = {
        "decision_id": "d",
        "overlay_mode": "LIVE",
        "precision": {"symbol_id": "twelve_data:GBP/USD", "price_decimals": 5, "pip_size": 0.0001, "tick_size": 1e-05, "quantity_decimals": None},
        "meta": {"symbol": "GBP/USD", "display_symbol": "GBP/USD", "timeframe": "M5", "analysis_time": "2026-01-10T08:00:00Z", "live": True, "market_schedule": "24_5", "analysis_clock": "UTC", "market_source": "twelve_data", "market_type": "forex"},
        "ownership": {"selected_model_id": "ict_2022", "decision_owner_id": "ict_2022", "overlay_owner_id": "ict_2022"},
        "readiness": {"state": "market_closed"},
        "market": {"external_structure": "bearish", "internal_structure": "pullback", "current_price": 1.271},
        "decision": {"status": "READY TO SELL", "direction": "sell", "stage": "TRADE_READY", "trade_ready": True, "next_action": "x"},
        "setup": {"setup_id": "fx-1", "direction": "sell", "stage": "TRADE_READY", "status": "READY TO SELL", "trade_ready": True, "entry": 1.27, "stop": 1.275, "targets": [{"price": 1.26}], "rr": 2.0, "entry_area": {"low": 1.269, "high": 1.271, "type": "pullback"}},
        "overlays": [],
        "previous_setup": None,
    }
    value = normalize_global_decision(product)
    assert value["decision"]["status"] == "STATE CONTRADICTION"
    assert value["active_setup"] is None
    assert not [row for row in value["overlays"] if row.get("actionable")]
