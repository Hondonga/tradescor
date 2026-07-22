"""Phase 4 checkpoint 6: GBP/USD must return the same normalized top-level
contract used by the professional Workspace, with decision_owner_id ==
overlay_owner_id enforced.
"""
from analysis.market_decision_normalizer import normalize_market_decision

REQUIRED_TOP_LEVEL_KEYS = {
    "meta", "ownership", "readiness", "current_market", "active_setup",
    "trade_plan", "previous_setup", "research_scenario", "diagnostics",
    "overlays", "precision",
}


def _legacy_product():
    return {
        "decision_id": "d1",
        "setup": {"setup_id": "fx-1", "direction": "sell", "stage": "entry_valid", "type": "ict_2022"},
        "execution": {"state": "entry_valid", "entry": 1.27, "stop": 1.275, "targets": [{"name": "TP1", "price": 1.26, "risk_reward": 2.0}], "risk_reward": 2.0},
        "quality": {"trade_plan_valid": True, "data_quality": "valid", "score": 80},
        "user_output": {"status": "READY TO SELL", "direction": "sell", "summary": "", "next_action": ""},
        "strategy_routing": {"selected_strategy": "ict_2022", "reason": "test"},
        "top_down": {"H1": {"structure": "bearish"}, "M15": {"structure": "pullback"}},
        "trade_chart": {"current_price": 1.271},
        "filters": {"session": {"market_open": True, "entry_allowed": True, "name": "London Kill Zone"}},
        "candle_bundle": {"timeframes": {}},
        "previous_setup": None,
        "overlays": [],
    }


def _decision():
    return normalize_market_decision(
        _legacy_product(),
        symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M5",
        market_source="twelve_data", market_type="forex", market_schedule="24_5",
        analysis_time="2026-01-06T08:00:00Z",
    )


def test_every_required_top_level_key_is_present():
    decision = _decision()
    missing = REQUIRED_TOP_LEVEL_KEYS - set(decision.keys())
    assert not missing, f"missing keys: {missing}"


def test_decision_owner_id_equals_overlay_owner_id():
    decision = _decision()
    assert decision["ownership"]["decision_owner_id"] == decision["ownership"]["overlay_owner_id"]
    assert decision["ownership"]["selected_model_id"] == decision["ownership"]["decision_owner_id"]


def test_ownership_is_the_real_ict_strategy_id_not_a_placeholder():
    decision = _decision()
    assert decision["ownership"]["decision_owner_id"] == "ict_2022"


def test_uses_the_same_normalization_boundary_as_every_other_market_family():
    # research_scenario and paper_registration_allowed only exist because
    # normalize_global_decision() (analysis/global_overlay_contract.py) sets
    # them for every market family -- their presence on a Forex decision is
    # direct evidence Forex flows through the same shared boundary, not a
    # parallel/forked one.
    decision = _decision()
    assert "research_scenario" in decision
    assert "paper_registration_allowed" in decision
