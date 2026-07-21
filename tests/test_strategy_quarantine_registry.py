from analysis.strategy_quarantine_registry import strategy_quarantine_view, is_auto_eligible
from analysis.strategy_reachability_gate import gate_auto_result, gate_normalized_auto_result


def test_only_volatility_structure_pullback_is_auto_eligible():
    view = strategy_quarantine_view()
    eligible = [sid for sid, spec in view.items() if spec["auto_eligible"]]
    assert eligible == ["volatility_structure_pullback"]


def test_volatility_structure_pullback_reachable_both_directions():
    spec = strategy_quarantine_view()["volatility_structure_pullback"]
    assert spec["production_supported"] is True
    assert spec["buy_reachable"] is True
    assert spec["sell_reachable"] is True
    assert spec["historical_edge_proven"] is False
    assert spec["profitability_claim_allowed"] is False


def test_jump_family_is_quarantined():
    view = strategy_quarantine_view()
    for strategy_id in ("jump_post_event_continuation", "jump_post_event_reversal"):
        spec = view[strategy_id]
        assert spec["research_only"] is True
        assert spec["production_supported"] is False
        assert spec["auto_eligible"] is False
        assert spec["paper_signal_allowed"] is False
        assert spec["disabled_reason"] == "NO_CONFIRMED_DIRECTIONAL_EDGE"


def test_step_and_boom_crash_are_quarantined_unless_formally_proven():
    view = strategy_quarantine_view()
    for strategy_id in ("step_range_reaction", "step_structure_pullback", "step_breakout_and_retest", "boom_crash_spike_state"):
        assert view[strategy_id]["auto_eligible"] is False
        assert view[strategy_id]["production_supported"] is False


def test_ml_is_inactive_and_never_auto_eligible():
    spec = strategy_quarantine_view()["ml"]
    assert spec["auto_eligible"] is False
    assert spec["research_only"] is True
    assert spec["paper_signal_allowed"] is False
    assert spec["disabled_reason"] == "INACTIVE_REJECTED_MODEL"


def test_is_auto_eligible_helper_matches_view():
    assert is_auto_eligible("volatility_structure_pullback") is True
    assert is_auto_eligible("jump_post_event_continuation") is False
    assert is_auto_eligible("ml") is False
    assert is_auto_eligible("unknown_strategy_id") is False


def test_auto_gate_actually_blocks_a_non_reachable_jump_result():
    # End-to-end proof that the live gate (not just the registry view) rejects
    # a Jump setup that reached TRADE_READY, matching Auto's real behavior.
    fake_ready_jump = {
        "setup": {"setup_type": "jump_post_event_smc", "state": "TRADE_READY", "entry": 100, "stop": 99, "targets": [{"price": 102}], "rr": 2},
        "decision": {"trade_ready": True, "status": "READY TO BUY"},
        "trade_chart": {"targets": [{"price": 102}]},
    }
    gated = gate_auto_result(dict(fake_ready_jump), "JUMP", "auto")
    assert gated["decision"]["trade_ready"] is False
    assert gated["setup"]["entry"] is None and gated["setup"]["targets"] == []
    assert gated["decision"]["status"] == "PLAN REJECTED"


def test_auto_gate_actually_blocks_a_non_reachable_boom_crash_result():
    fake_ready_boom = {
        "setup": {"setup_type": "structure_pullback"},
        "decision": {"trade_ready": True, "status": "READY TO BUY"},
    }
    gated = gate_normalized_auto_result(dict(fake_ready_boom), "BOOM", "auto")
    assert gated["decision"]["trade_ready"] is False
    assert gated["decision"]["status"] == "PLAN REJECTED"


def test_auto_gate_allows_the_golden_path_through():
    fake_ready_volatility = {
        "setup": {"setup_type": "structure_pullback", "state": "TRADE_READY", "entry": 100, "stop": 99, "targets": [{"price": 102}], "rr": 2},
        "decision": {"trade_ready": True},
        "trade_chart": {"targets": [{"price": 102}]},
    }
    gated = gate_auto_result(dict(fake_ready_volatility), "VOLATILITY", "auto")
    assert gated["decision"]["trade_ready"] is True
    assert gated["setup"]["entry"] == 100
