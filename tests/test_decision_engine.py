from datetime import timedelta

import pandas as pd

from analysis.decision_engine import build_decision
from paper_testing.logger import PaperDecisionLogger


def _trend(timeframe: str, step: float = 0.1) -> pd.DataFrame:
    frequency = {"D1": "1D", "H4": "4h", "H1": "1h", "M15": "15min", "M5": "5min"}[timeframe]
    times = pd.date_range("2025-01-01", periods=80, freq=frequency, tz="UTC")
    rows, price = [], 100.0
    for timestamp in times:
        close = price + step
        rows.append({"time": timestamp, "open": price, "high": close + 0.05, "low": price - 0.05, "close": close})
        price = close
    return pd.DataFrame(rows)


def _decision() -> dict[str, object]:
    context = {timeframe: _trend(timeframe) for timeframe in ("D1", "H4", "H1", "M15", "M5")}
    boundary = max(frame.iloc[-1]["time"] for frame in context.values()) + timedelta(days=2)
    return build_decision(symbol="BTC/USD", asset_class="crypto", display_timeframe="M15", candles_by_timeframe=context, analysis_timestamp=boundary, session={"entry_allowed": True, "market_status": "OPEN_24_7"})


def test_normalized_decision_has_one_m5_execution_contract():
    decision = _decision()
    assert decision["execution_timeframe"] == "M5"
    assert decision["setup_timeframe"] == "M15"
    assert set(decision["top_down"]) == {"D1", "H4", "H1", "M15", "M5"}
    assert decision["user_output"]["status"] in {"BUY SETUP FORMING", "READY TO BUY", "SELL SETUP FORMING", "READY TO SELL", "NO VALID SETUP"}
    assert decision["quality"]["confidence"] in {"low", "medium", "high"}


def test_unconfirmed_decision_never_exposes_actionable_levels_or_high_confidence():
    decision = _decision()
    if not decision["quality"]["trade_plan_valid"]:
        if decision["execution"]["entry"] is not None:
            assert decision["confirmed_entry"]["price"]==decision["execution"]["entry"]
            assert decision["confirmed_entry"]["confirmed_at"] is not None
            assert decision["execution"]["state"] in {"m5_setup_forming","m5_confirmed","entry_extended","too_late"}
            assert not decision["user_output"]["trade_plan_checks_passed"]
        assert decision["quality"]["confidence"] != "high"
        assert decision["quality"]["score"] <= 90


def test_setup_identity_is_stable_for_same_locked_inputs():
    first, second = _decision(), _decision()
    assert first["setup"]["setup_id"] == second["setup"]["setup_id"]
    assert first["setup"]["zone"] == second["setup"]["zone"]


def test_paper_logger_is_append_only_and_deduplicates_snapshots(tmp_path):
    logger = PaperDecisionLogger(tmp_path / "paper.jsonl")
    decision = _decision()
    assert logger.record_decision(decision) is True
    assert logger.record_decision(decision) is False
    logger.record_outcome(decision_id=decision["decision_id"], setup_id=decision["setup"]["setup_id"], outcome="missed", realized_r=0.0)
    events = logger.read_events()
    assert [event["event_type"] for event in events] == ["decision_created", "outcome_recorded"]
    assert events[0]["snapshot"] == decision
