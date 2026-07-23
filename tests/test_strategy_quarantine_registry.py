from analysis.strategy_quarantine_registry import (
    strategy_quarantine_view, strategy_validation_registry, is_auto_eligible, is_paper_signal_allowed,
    paper_signal_block_reason, validation_entry, product_actionability, VALIDATION_STATES, REQUIRED_FIELDS,
    BLOCK_REASON_REJECTED_NO_EDGE_AFTER_COSTS, BLOCK_REASON_RESEARCH_ONLY,
)
from analysis.strategy_reachability_gate import gate_auto_result, gate_normalized_auto_result


def test_no_strategy_is_auto_eligible():
    # Phase 6: historical_edge_proven is required for Auto eligibility, and no
    # strategy in this codebase has passed formal walk-forward validation.
    view = strategy_quarantine_view()
    eligible = [sid for sid, spec in view.items() if spec["auto_eligible"]]
    assert eligible == []


def test_every_entry_has_the_required_part1_fields():
    for spec in strategy_validation_registry().values():
        for field in REQUIRED_FIELDS:
            assert field in spec
        assert spec["validation_status"] in VALIDATION_STATES


def test_volatility_structure_pullback_carries_the_frozen_phase5_verdict():
    spec = strategy_quarantine_view()["volatility_structure_pullback"]
    assert spec["buy_reachable"] is True
    assert spec["sell_reachable"] is True
    assert spec["reachability_status"] == "REACHABLE_BOTH_DIRECTIONS"
    assert spec["validation_status"] == "REJECTED_NO_EDGE_AFTER_COSTS"
    assert spec["validation_verdict"] == "REJECTED_NO_EDGE_AFTER_COSTS"
    assert spec["historical_edge_proven"] is False
    assert spec["profitability_claim_allowed"] is False
    assert spec["auto_eligible"] is False
    assert spec["paper_signal_allowed"] is False
    assert spec["paper_shadow_eligible"] is False
    assert spec["live_execution_allowed"] is False
    assert spec["research_only"] is True
    assert spec["evidence_source"] == "phase5_walk_forward"
    assert spec["experiment_id"] == "phase5-r75-vsp-walkforward-v1"
    assert spec["experiment_commit"] == "0b28f14f21cae5e8f450e2980ea3090ea3ce97a9"


def test_forex_ict_is_reachability_only_never_rejected_or_validated():
    spec = strategy_quarantine_view()["ict_2022"]
    assert spec["buy_reachable"] is True
    assert spec["sell_reachable"] is True
    assert spec["validation_status"] == "REACHABILITY_ONLY"
    assert spec["historical_edge_proven"] is False
    assert spec["auto_eligible"] is False
    assert spec["paper_signal_allowed"] is False
    assert spec["research_only"] is True
    assert "REJECTED" not in spec["validation_status"]


def test_jump_family_is_quarantined():
    view = strategy_quarantine_view()
    for strategy_id in ("jump_post_event_continuation", "jump_post_event_reversal"):
        spec = view[strategy_id]
        assert spec["research_only"] is True
        assert spec["auto_eligible"] is False
        assert spec["paper_signal_allowed"] is False
        assert spec["validation_verdict"] == "NO_CONFIRMED_DIRECTIONAL_EDGE"
        assert spec["disabled_reason"] == "NO_CONFIRMED_DIRECTIONAL_EDGE"


def test_step_and_boom_crash_are_not_tested_unless_a_frozen_experiment_proves_otherwise():
    view = strategy_quarantine_view()
    for strategy_id in ("step_range_reaction", "step_structure_pullback", "step_breakout_and_retest", "boom_crash_spike_state"):
        assert view[strategy_id]["auto_eligible"] is False
        assert view[strategy_id]["validation_status"] == "NOT_TESTED"
        assert view[strategy_id]["research_only"] is True


def test_ml_is_inactive_and_never_auto_eligible():
    spec = strategy_quarantine_view()["ml"]
    assert spec["auto_eligible"] is False
    assert spec["research_only"] is True
    assert spec["paper_signal_allowed"] is False
    assert spec["ml_filter_allowed"] is False
    assert spec["live_execution_allowed"] is False
    assert spec["validation_verdict"] == "REJECTED_POOR_CALIBRATION"
    assert spec["disabled_reason"] == "INACTIVE_REJECTED_MODEL"
    assert spec["model_status"] == "REJECTED_POOR_CALIBRATION"
    assert spec["decision_owner_allowed"] is False
    assert spec["overlay_owner_allowed"] is False
    assert spec["filtering_allowed"] is False
    assert spec["recommendation_allowed"] is False


def test_is_auto_eligible_helper_matches_view():
    assert is_auto_eligible("volatility_structure_pullback") is False
    assert is_auto_eligible("ict_2022") is False
    assert is_auto_eligible("jump_post_event_continuation") is False
    assert is_auto_eligible("ml") is False
    assert is_auto_eligible("unknown_strategy_id") is False


def test_is_paper_signal_allowed_is_false_for_every_current_strategy():
    for strategy_id in strategy_validation_registry():
        assert is_paper_signal_allowed(strategy_id) is False


def test_paper_signal_block_reason_uses_required_codes():
    assert paper_signal_block_reason("volatility_structure_pullback") == BLOCK_REASON_REJECTED_NO_EDGE_AFTER_COSTS
    assert paper_signal_block_reason("ict_2022") == BLOCK_REASON_RESEARCH_ONLY
    assert paper_signal_block_reason("unknown_strategy_id")


def test_validation_entry_defaults_unknown_strategies_to_safe_values():
    entry = validation_entry("some_future_strategy_nobody_registered")
    assert entry["auto_eligible"] is False
    assert entry["paper_signal_allowed"] is False
    assert entry["historical_edge_proven"] is False


def test_product_actionability_separates_engine_readiness_from_actionability():
    result = product_actionability("volatility_structure_pullback", lifecycle="TRADE_READY", plan_complete=True)
    assert result["engine_readiness"]["lifecycle"] == "TRADE_READY"
    assert result["engine_readiness"]["plan_complete"] is True
    assert result["product_actionability"]["actionable"] is False
    assert result["product_actionability"]["status"] == "RESEARCH_PLAN"
    assert result["product_actionability"]["auto_allowed"] is False
    assert result["product_actionability"]["paper_allowed"] is False


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


def test_auto_gate_blocks_the_reachable_but_unvalidated_volatility_result():
    # Phase 6: unlike Phase 2, being reachable is no longer sufficient for
    # Auto -- volatility_structure_pullback is reachable but its Phase 5
    # verdict is REJECTED_NO_EDGE_AFTER_COSTS, so Auto must still block it.
    fake_ready_volatility = {
        "setup": {"setup_type": "structure_pullback", "state": "TRADE_READY", "entry": 100, "stop": 99, "targets": [{"price": 102}], "rr": 2},
        "decision": {"trade_ready": True},
        "trade_chart": {"targets": [{"price": 102}]},
    }
    gated = gate_auto_result(dict(fake_ready_volatility), "VOLATILITY", "auto")
    assert gated["decision"]["trade_ready"] is False
    assert gated["decision"]["status"] == "NO_VALIDATED_STRATEGY_AVAILABLE"
    assert gated["setup"]["entry"] is None
    assert gated["decision"]["next_action"] == "No strategy for this market has passed the required historical validation."


def test_manual_research_selection_still_reaches_the_golden_path():
    # "Do not remove manual Research selection" -- a direct (non-Auto) request
    # for volatility_structure_pullback must not be touched by the Auto gate.
    fake_ready_volatility = {
        "setup": {"setup_type": "structure_pullback", "state": "TRADE_READY", "entry": 100, "stop": 99, "targets": [{"price": 102}], "rr": 2},
        "decision": {"trade_ready": True},
        "trade_chart": {"targets": [{"price": 102}]},
    }
    gated = gate_auto_result(dict(fake_ready_volatility), "VOLATILITY", "volatility_structure_pullback")
    assert gated["decision"]["trade_ready"] is True
    assert gated["setup"]["entry"] == 100
