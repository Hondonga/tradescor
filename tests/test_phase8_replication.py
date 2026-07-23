"""Phase 8 Part 14: required tests for the untouched-history replication
attempt of the Phase 7 stop-distance hypothesis.
"""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from analysis.strategy_quarantine_registry import strategy_validation_registry
from strategies.research.volatility_structure_pullback_hypothesis_v2 import (
    AUTO_ELIGIBLE,
    LIVE_EXECUTION_ALLOWED,
    MAX_STOP_DISTANCE_ATR,
    ML_FILTER_ALLOWED,
    PAPER_SIGNAL_ALLOWED,
    RESEARCH_ONLY,
    _stop_distance_atr,
    evaluate_research_variant,
)
from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback
from validation.strategy_feasibility.control_methodology_v2 import finite_sample_p_value, geometry_control_v2
from validation.strategy_feasibility.phase7_verdicts import FORBIDDEN_VERDICTS, assign_verdict
from validation.strategy_reachability_fixtures import _focused_frames

ROOT = Path(__file__).resolve().parents[1]
P7 = ROOT / "data/stabilization/phase7"
P8 = ROOT / "data/stabilization/phase8"


def _load8(rel):
    return json.loads((P8 / rel).read_text())


def test_parent_engine_is_unchanged():
    parent_path = ROOT / "analysis/volatility_structure_pullback_engine.py"
    frozen_at_phase6 = subprocess.run(
        ["git", "show", "2ab0c681dd0f98066144e02224497865d798a185:analysis/volatility_structure_pullback_engine.py"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    assert parent_path.read_text() == frozen_at_phase6


def test_variant_has_exactly_one_behavioral_difference():
    for direction in ("buy", "sell"):
        frames = _focused_frames(direction)
        at = frames["M5"].iloc[-1].time
        parent = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
        variant = evaluate_research_variant(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
        assert variant["decision"] == parent["decision"]
        assert variant["setup"] == parent["setup"]
        assert set(variant) - set(parent) == {"research_variant"}


def test_threshold_equals_exactly_3975():
    assert MAX_STOP_DISTANCE_ATR == 3.975
    diff = _load8("manifests/single_change_diff_report.json")
    assert diff["exactly_one_declared_change"] is True
    assert diff["second_behavioral_change_found"] is False
    prereg = _load8("preregistration/experiment_spec.json")
    assert prereg["exact_threshold"] == 3.975
    assert prereg["threshold_unchanged_from_phase7"] is True


def test_atr_uses_trailing_14_completed_m5_candles():
    import pandas as pd
    times = pd.date_range("2026-01-01", periods=20, freq="5min", tz="UTC")
    rows = [{"time": t, "open": 100, "high": 101, "low": 99, "close": 100.5, "complete": True} for t in times]
    frame = pd.DataFrame(rows)
    atr = _stop_distance_atr({"M5": frame}, times[-1], entry=100.0, stop=98.0)
    # high-low is a constant 2.0 for all rows -> ATR = 2.0 -> stop distance (2.0) / ATR (2.0) = 1.0
    assert atr == pytest.approx(1.0)
    too_short = frame.iloc[:10]
    assert _stop_distance_atr({"M5": too_short}, times[9], entry=100.0, stop=98.0) is None


def test_threshold_selection_predates_untouched_outcome_access():
    # The threshold was fixed in Phase 7 (selection_record.json, before any
    # untouched-history outcome existed anywhere) and Phase 8 explicitly
    # reuses it unchanged -- no Phase 8 outcome was ever computed to derive it.
    selection = json.loads((P7 / "selected_hypothesis/selection_record.json").read_text())
    assert selection["selected_candidate_id"] == "candidate_1_max_stop_distance_atr_ceiling"
    replay_status = _load8("replay/replay_pipeline_status.json")
    assert replay_status["status"] == "NOT EXECUTED"


def test_untouched_windows_exclude_all_consumed_data():
    inventory = _load8("manifests/untouched_history_inventory.json")
    reasons = {p["exclusion_reason"] for p in inventory["periods"]}
    assert any("PHASE_5" in r for r in reasons)
    assert any("ML_DATASET" in r for r in reasons)
    for period in inventory["periods"]:
        if period["eligible_for_phase8"]:
            pytest.fail("No period should be eligible_for_phase8 given the known insufficiency")
    assert inventory["sufficient_untouched_data_exists"] is False


def test_phase5_holdout_remains_sealed():
    manifest = json.loads((ROOT / "data/stabilization/phase5/holdout/holdout_manifest.json").read_text())
    assert manifest["status"] == "SEALED"
    assert manifest["opened_at"] is None
    assert manifest["result"] is None


def test_no_duplicate_setup_ids_in_frozen_phase5_data():
    import pandas as pd
    df = pd.read_csv(ROOT / "data/stabilization/phase5/data/resolved_setups.csv")
    assert df["setup_id"].duplicated().sum() == 0


def test_parent_and_variant_retained_setups_remain_paired_by_construction():
    # The variant never re-derives entry/stop/targets -- it only reads the
    # parent's own setup dict, so retained variant setups are the identical
    # object/values as their parent counterpart, never a re-simulated copy.
    frames = _focused_frames("buy")
    at = frames["M5"].iloc[-1].time
    parent = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
    variant = evaluate_research_variant(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
    assert variant["setup"]["entry"] == parent["setup"]["entry"]
    assert variant["setup"]["stop"] == parent["setup"]["stop"]
    assert variant["setup"]["targets"] == parent["setup"]["targets"]


def test_rejected_variant_setups_are_not_altered(monkeypatch):
    import strategies.research.volatility_structure_pullback_hypothesis_v2 as module
    monkeypatch.setattr(module, "MAX_STOP_DISTANCE_ATR", 0.0)
    frames = _focused_frames("buy")
    at = frames["M5"].iloc[-1].time
    parent = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
    variant = evaluate_research_variant(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
    assert variant["research_variant"]["variant_eligible"] is False
    # Even when rejected, the underlying setup/decision are untouched (Part 13: preserve engine output).
    assert variant["setup"] == parent["setup"]
    assert variant["decision"] == parent["decision"]


def test_costs_are_identical_for_parent_and_variant():
    prereg = _load8("preregistration/experiment_spec.json")
    assert prereg["cost_model"]["conservative_cost"] == 0.1
    assert prereg["cost_model"]["note"].startswith("Identical for parent and variant")


def test_geometry_control_v2_is_non_degenerate():
    import numpy as np
    rng = np.random.default_rng(1)
    same = rng.normal(0.1, 1.0, size=1000)
    opposite = rng.normal(-0.1, 1.0, size=1000)
    geometry = geometry_control_v2(same, opposite)
    assert not np.array_equal(geometry, same)


def test_empirical_p_value_is_never_zero():
    import numpy as np
    permutations = np.full(500, -1.0)
    p = finite_sample_p_value(0.0, permutations, alternative="greater")
    assert p > 0.0


def test_buy_and_sell_remain_included_in_the_preregistered_plan():
    prereg = _load8("preregistration/experiment_spec.json")
    assert prereg["direction_requirements"].lower().startswith("both buy and sell")
    assert prereg["sample_requirements"]["minimum_retained_buy"] == 75
    assert prereg["sample_requirements"]["minimum_retained_sell"] == 75


def test_no_grid_search_exists():
    # Phase 8 must not sweep the threshold -- confirm the single hardcoded value.
    text = (ROOT / "strategies/research/volatility_structure_pullback_hypothesis_v2.py").read_text()
    assert text.count("MAX_STOP_DISTANCE_ATR = ") == 1


def test_no_second_hypothesis_is_tested():
    research_dir = ROOT / "strategies/research"
    variant_files = [p for p in research_dir.glob("*.py") if p.name != "__init__.py"]
    assert len(variant_files) == 1
    candidates = list((P7 / "candidate_hypotheses").glob("candidate_*.json"))
    assert len(candidates) == 5
    selected = [json.loads(f.read_text()) for f in candidates if json.loads(f.read_text()).get("why_not_selected") is None]
    assert len(selected) == 1


def test_production_registry_remains_unchanged():
    vsp = strategy_validation_registry()["volatility_structure_pullback"]
    assert vsp["validation_verdict"] == "REJECTED_NO_EDGE_AFTER_COSTS"
    assert vsp["auto_eligible"] is False
    assert vsp["paper_signal_allowed"] is False
    assert "volatility_structure_pullback_hypothesis_v2" not in strategy_validation_registry()


def test_auto_paper_and_live_remain_disabled():
    assert AUTO_ELIGIBLE is False
    assert PAPER_SIGNAL_ALLOWED is False
    assert LIVE_EXECUTION_ALLOWED is False
    assert RESEARCH_ONLY is True


def test_ml_remains_inactive():
    ml = strategy_validation_registry()["ml"]
    assert ml["auto_eligible"] is False
    assert ml["validation_verdict"] == "REJECTED_POOR_CALIBRATION"
    assert ML_FILTER_ALLOWED is False


def test_forbidden_verdicts_are_impossible():
    for forbidden in FORBIDDEN_VERDICTS:
        with pytest.raises(ValueError):
            assign_verdict(forbidden)
    gate_results = _load8("reports/acceptance_gate_results.json")
    actual = gate_results["verdict_controlled_by_first_failed_gate"]
    assert assign_verdict(actual) == actual
    assert actual not in FORBIDDEN_VERDICTS


def test_phase5_and_phase7_frozen_files_remain_unchanged():
    frozen5 = ROOT / "data/stabilization/phase5/frozen/phase5-r75-vsp-walkforward-v1"
    record5 = json.loads((frozen5 / "experiment_record.json").read_text())
    for filename, expected in record5["file_checksums"].items():
        assert hashlib.sha256((frozen5 / filename).read_bytes()).hexdigest() == expected

    frozen7 = ROOT / "data/stabilization/phase7/frozen/phase7-r75-vsp-hypothesis-v2-stopatr-ceiling"
    record7 = json.loads((frozen7 / "experiment_record.json").read_text())
    for filename, expected in record7["file_checksums"].items():
        assert hashlib.sha256((frozen7 / filename).read_bytes()).hexdigest() == expected
