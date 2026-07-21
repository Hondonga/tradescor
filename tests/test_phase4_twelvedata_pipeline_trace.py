"""Phase 4 checkpoint 3: Twelve Data now records a PipelineTrace the same
way the Deriv provider always has -- previously GET /api/system/data-pipeline
always fell back to an empty placeholder for Forex symbols because nothing
under providers/twelve_data_provider.py ever created a trace.
"""
import pandas as pd
import pytest

from providers.runtime_health import runtime_health
import providers.twelve_data_provider as twelve_data_provider
from providers.twelve_data_provider import TwelveDataProvider


def _fake_candles(rows=5):
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2026-07-20T12:00:00Z", periods=rows, freq="5min", tz="UTC"),
            "open": [1.27] * rows,
            "high": [1.28] * rows,
            "low": [1.26] * rows,
            "close": [1.275] * rows,
        }
    )
    frame.attrs["time_metadata"] = {"raw_rows": rows, "valid_rows": rows, "validation_passed": True}
    return frame


def test_successful_fetch_records_a_pipeline_trace_reachable_by_symbol(monkeypatch):
    monkeypatch.setattr(twelve_data_provider, "get_candles", lambda **kwargs: _fake_candles(5))
    provider = TwelveDataProvider()
    provider.fetch_candles("GBP/USD", "M5", 5)
    trace = runtime_health.latest_trace("GBP/USD")
    assert trace is not None
    assert trace["provider_symbol"] == "GBP/USD"
    assert trace["state"] == "ready"
    stage_status = {row["stage"]: row["status"] for row in trace["stages"]}
    assert stage_status["ACTIVE_SYMBOL_RESOLUTION"] == "passed"
    assert stage_status["HISTORY_REQUEST"] == "passed"
    assert stage_status["HISTORY_RESPONSE"] == "passed"
    assert stage_status["CANDLE_NORMALIZATION"] == "passed"
    assert stage_status["ANALYSIS_READY"] == "passed"


def test_trace_record_counts_reflect_time_metadata_row_counts(monkeypatch):
    monkeypatch.setattr(twelve_data_provider, "get_candles", lambda **kwargs: _fake_candles(42))
    provider = TwelveDataProvider()
    provider.fetch_candles("GBP/USD", "M5", 42)
    trace = runtime_health.latest_trace("GBP/USD")
    by_stage = {row["stage"]: row for row in trace["stages"]}
    assert by_stage["HISTORY_RESPONSE"]["record_count"] == 42
    assert by_stage["CANDLE_NORMALIZATION"]["record_count"] == 42


def test_provider_error_records_a_failed_trace_and_updates_provider_state(monkeypatch):
    def _raise(**kwargs):
        raise RuntimeError("Twelve Data HTTP error 500: server error")

    monkeypatch.setattr(twelve_data_provider, "get_candles", _raise)
    provider = TwelveDataProvider()
    with pytest.raises(RuntimeError):
        provider.fetch_candles("GBP/USD", "M5", 5)
    trace = runtime_health.latest_trace("GBP/USD")
    assert trace["state"] == "error"
    by_stage = {row["stage"]: row for row in trace["stages"]}
    assert by_stage["HISTORY_REQUEST"]["status"] == "failed"
    assert by_stage["HISTORY_REQUEST"]["error_code"] == "PROVIDER_ERROR"
    assert runtime_health.snapshot()["providers"]["twelve_data"]["state"] == "error"


def test_rate_limit_error_is_tagged_distinctly_from_a_generic_provider_error(monkeypatch):
    def _raise(**kwargs):
        raise RuntimeError("Twelve Data rate limit reached. Wait before refreshing.")

    monkeypatch.setattr(twelve_data_provider, "get_candles", _raise)
    provider = TwelveDataProvider()
    with pytest.raises(RuntimeError):
        provider.fetch_candles("GBP/USD", "M5", 5)
    trace = runtime_health.latest_trace("GBP/USD")
    by_stage = {row["stage"]: row for row in trace["stages"]}
    assert by_stage["HISTORY_REQUEST"]["error_code"] == "RATE_LIMITED"
    assert runtime_health.snapshot()["providers"]["twelve_data"]["state"] == "rate_limited"


def test_stages_this_layer_cannot_observe_stay_pending_rather_than_fabricated(monkeypatch):
    # Completed-candle filtering happens later, generically, in
    # analysis/top_down_engine.py -- the provider-level trace must not
    # claim to have done work it did not actually perform.
    monkeypatch.setattr(twelve_data_provider, "get_candles", lambda **kwargs: _fake_candles(5))
    provider = TwelveDataProvider()
    provider.fetch_candles("GBP/USD", "M5", 5)
    trace = runtime_health.latest_trace("GBP/USD")
    by_stage = {row["stage"]: row for row in trace["stages"]}
    assert by_stage["COMPLETED_CANDLE_FILTER"]["status"] == "pending"
    assert by_stage["TIMEFRAME_AGGREGATION"]["status"] == "pending"
