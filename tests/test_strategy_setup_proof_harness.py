import pandas as pd

from analysis.smc.smc_invariants import validate_trade_ready_invariants
from analysis.strategy_reachability_gate import gate_auto_result,reachability_status
from validation.strategy_history_selection import select_fixed_30_day_period
from validation.strategy_reachability_fixtures import registered_fixtures,production_evaluator
from validation.strategy_reachability_fixtures import production_paper_lifecycle
from validation.strategy_reachability_registry import strategy_reachability_registry
from validation.strategy_setup_proof import (
    build_strategy_reachability_report,
    classify_historical_funnel,
    completed_slice,
    run_strategy_fixture,
    validate_registry_fixture_coverage,
)


def test_every_production_strategy_has_directional_fixture_coverage():
    fixtures=registered_fixtures();assert validate_registry_fixture_coverage(fixtures)=={}
    registry=strategy_reachability_registry()
    for strategy_id,spec in registry.items():
        if spec["production_supported"]:
            assert {x.direction for x in fixtures if x.strategy_id==strategy_id}==set(spec["supported_directions"])


def test_registered_fixtures_are_completed_and_chronological():
    for fixture in registered_fixtures():
        for rows in fixture.candles_by_timeframe.values():
            assert rows.complete.all() and list(rows.time)==sorted(rows.time)
        for cutoff in fixture.decision_times:
            sliced=completed_slice(fixture.candles_by_timeframe["M5"],cutoff)
            assert sliced.empty or pd.Timestamp(sliced.iloc[-1].time)<=pd.Timestamp(cutoff)


def test_harness_calls_production_pipeline_and_rejects_strategy_mismatch():
    fixture=next(x for x in registered_fixtures() if x.fixture_id=="volatility_structure_pullback_buy")
    result=run_strategy_fixture(fixture,production_evaluator)
    assert result["production_pipeline"] is True and result["future_candle_access"] is False
    assert all("strategy_identity_matches" in row for row in result["transitions"])


def test_fake_trade_ready_is_rejected_by_hard_invariants():
    fake={"ownership":{"selected_strategy_id":"x","decision_owner_id":"x","overlay_owner_id":"x"},"decision":{"status":"TRADE_READY","trade_ready":True},"setup":{"setup_id":"fake","state":"TRADE_READY","direction":"buy","entry":None,"stop":None,"targets":[],"rr":None}}
    result=validate_trade_ready_invariants(fake);codes={x["code"] for x in result["violations"]}
    assert not result["valid"] and {"MISSING_CONFIRMATION","MISSING_ENTRY","MISSING_STOP","MISSING_TP1","RR_BELOW_MINIMUM"}<=codes


def test_report_never_calls_unresolved_fixture_reachable():
    result={"strategy_id":"volatility_structure_pullback","direction":"buy","trade_ready_reached":True,"paper_registered":False,"outcome_resolved":False,"classification":"REACHABLE"}
    row=next(x for x in build_strategy_reachability_report([result])["strategies"] if x["strategy_id"]==result["strategy_id"])
    assert row["status"]=="PARTIALLY_REACHABLE" and not row["reachable"]


def test_zero_setup_classification_is_specific_and_deterministic():
    row={"evaluations":10,"code_path_entered":True,"sweeps_or_events":2,"directional_contexts":2,"valid_locations":1,"structure_confirmations":1,"target_candidates":0,"rr_passes":0}
    assert classify_historical_funnel(row)=="TARGET_CREATION_FAILURE"
    assert classify_historical_funnel(dict(reversed(list(row.items()))))=="TARGET_CREATION_FAILURE"


def test_real_history_period_selection_cannot_use_outcomes():
    first=select_fixed_30_day_period("R_75","2025-01-01","2025-12-31");second=select_fixed_30_day_period("R_75","2025-01-01","2025-12-31")
    assert first==second and first["selected_before_evaluation"] and not first["performance_input_used"]


def test_jump_and_boom_support_status_is_explicit():
    registry=strategy_reachability_registry()
    assert registry["jump_post_event_continuation"]["support_status"]=="NOT_PRODUCTION_SUPPORTED"
    assert registry["jump_post_event_reversal"]["support_status"]=="NOT_PRODUCTION_SUPPORTED"
    assert registry["boom_crash_spike_state"]["support_status"]=="LEGACY_RESEARCH_ONLY"


def test_step_proofs_forbid_fvg_and_order_block_dependencies():
    registry=strategy_reachability_registry()
    for strategy_id in ("step_range_reaction","step_structure_pullback","step_breakout_and_retest"):
        assert set(registry[strategy_id]["forbidden_entities"])=={"fvg","order_block"}


def test_proved_focused_behavior_is_available_to_auto():
    source={"setup":{"setup_type":"structure_pullback","state":"TRADE_READY","entry":100,"stop":99,"targets":[{"price":102}],"rr":2},"decision":{"trade_ready":True},"trade_chart":{"targets":[{"price":102}]}}
    gated=gate_auto_result(source,"VOLATILITY","auto")
    assert reachability_status("volatility_structure_pullback")=="REACHABLE"
    assert gated["decision"]["trade_ready"] is True
    manual={"setup":{"setup_type":"structure_pullback","state":"TRADE_READY"},"decision":{"trade_ready":True}}
    assert gate_auto_result(manual,"VOLATILITY","volatility_smc")["decision"]["trade_ready"] is True


def test_latest_reachability_report_is_exposed_read_only():
    from app import app
    response=app.test_client().get("/api/strategy-reachability")
    assert response.status_code==200
    body=response.get_json();assert body["fixture_count"]==20 and body["thresholds_changed"] is False


def test_focused_buy_and_sell_complete_paper_lifecycle():
    fixtures=[x for x in registered_fixtures() if x.strategy_id=="volatility_structure_pullback"]
    results=[run_strategy_fixture(x,production_evaluator,paper_service=production_paper_lifecycle) for x in fixtures]
    assert {x["direction"] for x in results}=={"buy","sell"}
    assert all(x["trade_ready_reached"] and x["paper_registered"] and x["entry_filled"] and x["outcome_resolved"] for x in results)
    assert all(x["paper_result"]["excursion"] and x["paper_result"]["realized_r"] is not None for x in results)
