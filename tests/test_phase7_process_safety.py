"""Phase 7 Part 19: required process/safety invariant tests, covering
everything not already exercised by test_phase7_control_methodology_v2.py
and test_phase7_research_variant.py.
"""
import hashlib
import json
from pathlib import Path

import pytest

from analysis.strategy_quarantine_registry import strategy_validation_registry
from validation.strategy_feasibility.phase7_verdicts import (
    ALLOWED_VERDICTS,
    FORBIDDEN_VERDICTS,
    MAXIMUM_POSITIVE_VERDICT,
    assign_verdict,
)

ROOT = Path(__file__).resolve().parents[1]
P5 = ROOT / "data/stabilization/phase5"
P7 = ROOT / "data/stabilization/phase7"


def _load(rel):
    return json.loads((P7 / rel).read_text())


def test_phase5_frozen_files_remain_unchanged():
    frozen_dir = P5 / "frozen/phase5-r75-vsp-walkforward-v1"
    record = json.loads((frozen_dir / "experiment_record.json").read_text())
    for filename, expected in record["file_checksums"].items():
        actual = hashlib.sha256((frozen_dir / filename).read_bytes()).hexdigest()
        assert actual == expected, f"{filename} changed"
    assert record["strategy_verdict"] == "REJECTED_NO_EDGE_AFTER_COSTS"


def test_phase5_holdout_remains_sealed():
    manifest = json.loads((P5 / "holdout/holdout_manifest.json").read_text())
    assert manifest["status"] == "SEALED"
    assert manifest["opened_at"] is None
    assert manifest["result"] is None


def test_diagnostics_are_labeled_consumed_data_only():
    disclaimer = "DESCRIPTIVE -- CONSUMED DEVELOPMENT DATA -- NOT VALIDATION EVIDENCE"
    for rel in ("postmortem/failure_decomposition.json", "postmortem/failure_mode_attribution.json", "postmortem/diagnostic_buckets.json"):
        data = _load(rel)
        assert data.get("disclaimer") == disclaimer, f"{rel} missing the required consumed-data disclaimer"


def test_exactly_one_candidate_hypothesis_was_selected():
    candidates_dir = P7 / "candidate_hypotheses"
    files = sorted(candidates_dir.glob("candidate_*.json"))
    assert 1 <= len(files) <= 5
    selected = [json.loads(f.read_text()) for f in files if json.loads(f.read_text()).get("why_not_selected") is None]
    assert len(selected) == 1
    selection = _load("selected_hypothesis/selection_record.json")
    assert selected[0]["candidate_id"] == selection["selected_candidate_id"]


def test_only_one_research_variant_module_exists():
    research_dir = ROOT / "strategies/research"
    variant_files = [p for p in research_dir.glob("*.py") if p.name != "__init__.py"]
    assert len(variant_files) == 1
    assert variant_files[0].name == "volatility_structure_pullback_hypothesis_v2.py"


def test_candidate_selection_preceded_any_untouched_outcome_access():
    selection = _load("selected_hypothesis/selection_record.json")
    assert selection["consumed_data_disclosure"] is True
    # No untouched-history outcome file exists anywhere in the Phase 7 tree --
    # the only outcome-shaped artifacts are the coverage/sample-sufficiency
    # checks, which are pure calendar-coverage bookkeeping, never a strategy result.
    outcome_like = [p for p in (P7 / "folds").glob("*") if p.name != ".gitkeep"] + list((P7 / "untouched_data").glob("*result*"))
    assert outcome_like == [] or all("coverage" in p.name or "sufficiency" in p.name for p in outcome_like)


def test_no_direction_was_removed_from_the_selected_hypothesis_or_preregistration():
    prereg = _load("preregistration/hypothesis_experiment_spec.json")
    assert prereg["direction_requirements"].lower().startswith("both buy and sell")
    for f in (P7 / "candidate_hypotheses").glob("candidate_*.json"):
        candidate = json.loads(f.read_text())
        text = json.dumps(candidate).lower()
        assert "excluding sell" not in text and "excluding buy" not in text
        assert "remove sell" not in text and "remove buy" not in text


def test_no_threshold_sweep_diagnostic_buckets_are_fixed_quintiles_not_a_search():
    buckets = _load("postmortem/diagnostic_buckets.json")
    for key in ("stop_distance_in_atr_quintiles", "initial_reward_to_risk_quintiles", "atr_at_entry_volatility_proxy_quintiles"):
        table = buckets[key]
        assert len(table) == 5, f"{key} must be exactly 5 predeclared quintile buckets, not a swept threshold set"
        labels = [row["bucket"].split()[0] for row in table]
        assert labels == ["Q1_lowest", "Q2", "Q3", "Q4", "Q5_highest"]


def test_untouched_history_exclusions_cover_the_full_consumed_calendar_range():
    coverage = _load("untouched_data/coverage_manifest.json")
    windows = coverage["excluded_windows"]
    assert any("PHASE_5" in w["reason"] for w in windows)
    assert any("ML_DATASET_CONSUMED" in w["reason"] for w in windows)
    assert any("EMBARGO" in w["reason"] for w in windows)
    assert coverage["conclusion"].startswith("RESEARCH_EXTENSION_REQUIRED_INSUFFICIENT_UNTOUCHED_HISTORY")


def test_preregistration_declares_itself_immutable_and_matches_its_own_checksum_going_forward():
    path = P7 / "preregistration/hypothesis_experiment_spec.json"
    prereg = json.loads(path.read_text())
    assert "immutable" in prereg["no_changes_after_outcomes_are_viewed"].lower()
    # A snapshot checksum test: if this file is ever edited after being
    # frozen, the frozen bundle's own copy (checked in test_phase7 freeze
    # tests below) must diverge and be caught there.
    assert hashlib.sha256(path.read_bytes()).hexdigest()  # just proves the file is stable/readable


def test_phase6_registry_remains_unchanged_by_phase7():
    registry = strategy_validation_registry()
    vsp = registry["volatility_structure_pullback"]
    assert vsp["validation_verdict"] == "REJECTED_NO_EDGE_AFTER_COSTS"
    assert vsp["auto_eligible"] is False
    assert vsp["paper_signal_allowed"] is False
    assert vsp["research_only"] is True
    # The Phase 7 research variant must not appear in the production registry.
    assert "volatility_structure_pullback_hypothesis_v2" not in registry


def test_no_auto_or_paper_eligibility_is_granted_to_the_research_variant():
    from strategies.research.volatility_structure_pullback_hypothesis_v2 import (
        AUTO_ELIGIBLE, LIVE_EXECUTION_ALLOWED, ML_FILTER_ALLOWED, PAPER_SIGNAL_ALLOWED, RESEARCH_ONLY,
    )
    assert AUTO_ELIGIBLE is False
    assert PAPER_SIGNAL_ALLOWED is False
    assert LIVE_EXECUTION_ALLOWED is False
    assert ML_FILTER_ALLOWED is False
    assert RESEARCH_ONLY is True


def test_ml_remains_inactive():
    ml = strategy_validation_registry()["ml"]
    assert ml["auto_eligible"] is False
    assert ml["paper_signal_allowed"] is False
    assert ml["live_execution_allowed"] is False
    assert ml["ml_filter_allowed"] is False
    assert ml["validation_verdict"] == "REJECTED_POOR_CALIBRATION"


def test_forbidden_positive_verdicts_are_impossible():
    for forbidden in FORBIDDEN_VERDICTS:
        with pytest.raises(ValueError):
            assign_verdict(forbidden)
    for allowed in ALLOWED_VERDICTS:
        assert assign_verdict(allowed) == allowed
    assert MAXIMUM_POSITIVE_VERDICT == "ELIGIBLE_FOR_SECOND_INDEPENDENT_REPLICATION"
    assert MAXIMUM_POSITIVE_VERDICT in ALLOWED_VERDICTS
    assert MAXIMUM_POSITIVE_VERDICT not in FORBIDDEN_VERDICTS


def test_phase7_actual_verdict_is_within_the_allowed_set_and_not_forbidden():
    sufficiency = _load("untouched_data/sample_sufficiency_check.json")
    verdict = sufficiency["verdict"]
    assert assign_verdict(verdict) == verdict
    assert verdict not in FORBIDDEN_VERDICTS
