"""Phase 6 Part 5/17: production paper registration must be blocked for any
strategy that has not been historically validated, while the technical
paper-engine capability used by reachability fixtures/tests stays isolated
and clearly marked TEST_FIXTURE_ONLY, and future records carry the
verdict/actionability/experiment metadata in effect at registration time.
"""
import json
import tempfile, os

import pandas as pd

from paper_testing.derived_paper_service import DerivedPaperService
from paper_testing.derived_paper_store import DerivedPaperStore
from analysis.strategy_quarantine_registry import BLOCK_REASON_REJECTED_NO_EDGE_AFTER_COSTS


def _contract(direction="buy"):
    entry, stop, tp1, tp2 = (100, 98, 104, 106) if direction == "buy" else (100, 102, 96, 94)
    return {
        "decision": {"setup_id": "vsp-1", "status": "READY", "developing_direction": direction, "trade_ready": True, "strategy": "volatility_structure_pullback"},
        "auto_evaluation": {"selected_strategy": "volatility_structure_pullback", "eligible_strategies": ["volatility_structure_pullback"]},
        "active_trade_plan": {"entry": entry, "stop": stop, "tp1": tp1, "tp2": tp2, "tp1_rr": 2, "tp2_rr": 3, "entry_type": "confirmation_close"},
    }


def _service():
    handle, path = tempfile.mkstemp(prefix="tradescor-phase6-paper-", suffix=".db")
    os.close(handle)
    service = DerivedPaperService(store=DerivedPaperStore(path), config={"enabled": True}, enabled=True)
    return service, path


def _cleanup(path):
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except OSError:
            pass


def test_production_path_blocks_paper_registration_for_a_rejected_strategy():
    service, path = _service()
    try:
        result = service.record_analysis(
            provider_symbol="R_75", display_name="Volatility 75", family="VOLATILITY", subfamily="VOLATILITY",
            requested_strategy="Auto", analysis_candle_time="2026-01-01T00:00:00+00:00", decision_contract=_contract(),
        )
        assert result["setup_registered"] is False
        assert result["paper_setup_id"] is None
        assert result["paper_signal_allowed"] is False
        assert result["paper_signal_block_reason"] == BLOCK_REASON_REJECTED_NO_EDGE_AFTER_COSTS
        assert result["test_fixture_only"] is False
        assert service.setups(limit=10) == []
    finally:
        _cleanup(path)


def test_test_fixture_only_path_registers_and_is_clearly_marked():
    service, path = _service()
    try:
        result = service.record_analysis(
            provider_symbol="R_75", display_name="Volatility 75", family="VOLATILITY", subfamily="VOLATILITY",
            requested_strategy="volatility_structure_pullback", analysis_candle_time="2026-01-01T00:00:00+00:00",
            decision_contract=_contract(), test_fixture_only=True,
        )
        assert result["setup_registered"] is True
        assert result["paper_setup_id"] is not None
        assert result["test_fixture_only"] is True
        stored = service.setups(limit=10)[0]
        payload = json.loads(stored["payload_json"])
        safety = payload["phase6_record_safety"]
        assert safety["test_fixture_only"] is True
        assert safety["validation_verdict_at_registration"] == "REJECTED_NO_EDGE_AFTER_COSTS"
        assert safety["product_actionability_at_registration"]["paper_allowed"] is False
        assert safety["experiment_id"] == "phase5-r75-vsp-walkforward-v1"
    finally:
        _cleanup(path)


def test_analysis_snapshot_is_still_logged_even_when_the_paper_signal_is_blocked():
    # Blocking the tradeable setup must not silently discard the underlying
    # analysis record -- diagnostics/history must remain readable.
    service, path = _service()
    try:
        result = service.record_analysis(
            provider_symbol="R_75", display_name="Volatility 75", family="VOLATILITY", subfamily="VOLATILITY",
            requested_strategy="Auto", analysis_candle_time="2026-01-01T00:00:00+00:00", decision_contract=_contract(),
        )
        assert result["snapshot_inserted"] is True
        assert service.decisions(limit=10)
    finally:
        _cleanup(path)


def test_existing_historical_records_remain_readable_without_the_new_fields():
    # Phase 6 must never rewrite or require the new metadata on records that
    # were created before this change existed.
    service, path = _service()
    try:
        legacy_payload = {"decision_id": "legacy-1", "setup": {"entry": 100}, "research_mode": False}
        service.store.insert_decision(
            type("Row", (), {"as_dict": lambda self: {
                "decision_id": "legacy-1", "dedupe_key": "legacy-key", "created_at": "2025-01-01T00:00:00Z",
                "analysis_candle_time": "2025-01-01T00:00:00Z", "provider_symbol": "R_75", "family": "VOLATILITY",
                "selected_strategy": "volatility_structure_pullback", "setup_id": None, "payload": legacy_payload,
            }})()
        )
        rows = service.decisions(limit=10)
        assert any(row["decision_id"] == "legacy-1" for row in rows)
    finally:
        _cleanup(path)
