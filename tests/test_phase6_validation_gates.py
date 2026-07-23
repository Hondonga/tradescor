"""Phase 6: end-to-end proof that the generic (Forex/crypto/other-derived)
Auto router and the public API surfaces respect the centralized validation
registry -- not just the Volatility-family fast path already covered by
tests/test_strategy_quarantine_registry.py and
tests/test_phase6_paper_eligibility_gate.py.
"""
from datetime import timedelta
import hashlib
import json
from pathlib import Path

import pandas as pd

from analysis.decision_engine import build_decision
from analysis.derived_engine import analyze_derived_index
from analysis.strategy_quarantine_registry import (
    is_auto_eligible,
    strategy_validation_registry,
    VALIDATION_STATES,
)
from analysis.strategy_reachability_gate import NO_VALIDATED_STRATEGY_MESSAGE
from validation.strategy_reachability_fixtures import _focused_frames

ROOT = Path(__file__).resolve().parents[1]


def _trend(timeframe: str, step: float = 0.6) -> pd.DataFrame:
    frequency = {"D1": "1D", "H4": "4h", "H1": "1h", "M15": "15min", "M5": "5min"}[timeframe]
    times = pd.date_range("2025-01-01", periods=80, freq=frequency, tz="UTC")
    rows, price = [], 100.0
    for timestamp in times:
        close = price + step
        rows.append({"time": timestamp, "open": price, "high": close + 0.1, "low": price - 0.1, "close": close})
        price = close
    return pd.DataFrame(rows)


def _decision(requested_strategy="auto") -> dict[str, object]:
    context = {timeframe: _trend(timeframe) for timeframe in ("D1", "H4", "H1", "M15", "M5")}
    boundary = max(frame.iloc[-1]["time"] for frame in context.values()) + timedelta(days=2)
    return build_decision(
        symbol="BTC/USD", asset_class="crypto", display_timeframe="M15", candles_by_timeframe=context,
        analysis_timestamp=boundary, session={"entry_allowed": True, "market_status": "OPEN_24_7"},
        requested_strategy=requested_strategy,
    )


def test_generic_auto_router_never_selects_an_unvalidated_strategy():
    # Regardless of whether a market-eligible candidate exists (ict_2022 /
    # breakout_retest / supply_demand), none has historical_edge_proven, so
    # Auto must report NO_VALIDATED_STRATEGY_AVAILABLE and select nothing.
    decision = _decision("auto")
    routing = decision["strategy_routing"]
    assert routing["no_validated_strategy"] is True
    assert routing["selected_strategy"] == ""
    assert routing["reason"] == NO_VALIDATED_STRATEGY_MESSAGE
    assert routing["evidence_status"] == "NO_VALIDATED_STRATEGY_AVAILABLE"
    assert decision["primary_strategy"] is None
    for strategy_id in ("ict_2022", "breakout_retest", "supply_demand"):
        assert is_auto_eligible(strategy_id) is False


def test_manual_strategy_request_bypasses_the_auto_validation_gate():
    # "Do not remove manual Research selection" -- a direct, non-Auto request
    # must never be forced through the NO_VALIDATED_STRATEGY_AVAILABLE path,
    # even though the same strategy is blocked from Auto above.
    decision = _decision("ict_2022")
    routing = decision["strategy_routing"]
    assert routing.get("no_validated_strategy") is not True
    assert routing["reason"] != NO_VALIDATED_STRATEGY_MESSAGE


def test_validation_registry_covers_every_declared_strategy_with_a_closed_enum():
    registry = strategy_validation_registry()
    assert set(registry) >= {
        "volatility_structure_pullback", "ict_2022", "jump_post_event_continuation",
        "jump_post_event_reversal", "step_range_reaction", "boom_crash_spike_state", "ml",
    }
    for spec in registry.values():
        assert spec["validation_status"] in VALIDATION_STATES
        assert spec["auto_eligible"] is False, f"{spec['strategy_id']} must not default to Auto eligible"
        assert spec["paper_signal_allowed"] is False, f"{spec['strategy_id']} must not default to paper eligible"


def test_diagnostics_api_never_reports_auto_eligible_for_volatility_structure_pullback():
    from app import app
    response = app.test_client().get("/api/strategy-reachability")
    assert response.status_code == 200
    data = response.get_json()
    registry = data["validation_registry"]
    assert registry["volatility_structure_pullback"]["auto_eligible"] is False
    assert data["production_status"]["auto_eligible"] is False
    for strategy_id, spec in registry.items():
        assert spec["paper_signal_allowed"] is False, f"{strategy_id} must not report paper_signal_allowed=true"
        assert spec["auto_eligible"] is False, f"{strategy_id} must not report auto_eligible=true"


def test_r75_auto_response_never_reports_auto_eligible_true_even_when_trade_ready():
    # Regression: derived_engine.py's focused-volatility branch used to
    # overwrite contract["production_status"] with a stale, reachability-only
    # auto_eligible=True right after normalize_global_decision had already
    # computed the correct (False) value -- catches that class of leak.
    frames = _focused_frames("buy")
    result = analyze_derived_index(
        symbol="R_75", metadata={"family": "VOLATILITY", "provider_symbol": "R_75", "display_name": "R_75"},
        candles_by_timeframe=frames, tick_size=0.01, analysis_time=frames["M5"].iloc[-1].time,
        requested_strategy="auto",
    )
    # The underlying setup genuinely reaches TRADE_READY (proving this isn't
    # a reachability failure in disguise) -- Auto must still refuse it.
    assert result["decision"]["status"] == "NO_VALIDATED_STRATEGY_AVAILABLE"
    assert result["decision"]["trade_ready"] is False
    assert result["decision"]["next_action"] == NO_VALIDATED_STRATEGY_MESSAGE
    assert result["strategy_result"]["production_status"]["auto_eligible"] is False
    assert result["strategy_result"]["strategy_evidence"]["historical_edge_proven"] is False


def test_phase5_frozen_experiment_checksums_are_unchanged():
    frozen_dir = ROOT / "data/stabilization/phase5/frozen/phase5-r75-vsp-walkforward-v1"
    record = json.loads((frozen_dir / "experiment_record.json").read_text())
    for filename, expected in record["file_checksums"].items():
        actual = hashlib.sha256((frozen_dir / filename).read_bytes()).hexdigest()
        assert actual == expected, f"{filename} checksum changed -- frozen Phase 5 experiment must never be modified"
    assert record["strategy_verdict"] == "REJECTED_NO_EDGE_AFTER_COSTS"


def test_phase5_holdout_remains_sealed():
    manifest = json.loads((ROOT / "data/stabilization/phase5/holdout/holdout_manifest.json").read_text())
    assert manifest["status"] == "SEALED"
    assert manifest["opened_at"] is None
    assert manifest["result"] is None


def test_frozen_ml_artifacts_are_untouched():
    # No Phase 6 file may live under data/ml/ or analysis/ml_*.py -- ML stays
    # frozen/inactive; this only checks that this phase did not add any.
    import subprocess
    changed = subprocess.run(
        ["git", "diff", "--name-only", "b87e72d8730629734740d4ec1a840d32770813cb", "--"],
        cwd=ROOT, capture_output=True, text=True,
    )
    touched_ml = [line for line in changed.stdout.splitlines() if line.startswith("data/ml/") or line.startswith("analysis/ml_")]
    assert touched_ml == [], f"Phase 6 must not touch ML files, found: {touched_ml}"
