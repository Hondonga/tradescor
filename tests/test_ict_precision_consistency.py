from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from analysis.decision_engine import build_decision
from analysis.ict_consistency_validator import validate_ict_consistency
from analysis.ict_precision_engine import build_ict_precision, _zone_relation


def _frame(timeframe, kind="bull", count=80):
    minutes = {"D1": 1440, "H4": 240, "H1": 60, "M15": 15, "M5": 5}[timeframe]
    end = datetime(2026, 7, 15, 15, tzinfo=timezone.utc); rows = []
    for index in range(count):
        timestamp = end - timedelta(minutes=minutes * (count - index))
        base = 100 + index * .1 if kind == "bull" else 100 + (index % 2) * .02
        close = base + (.06 if kind == "bull" else -.01 if index % 2 else .01)
        rows.append({"time": timestamp, "open": base, "high": max(base, close) + .03, "low": min(base, close) - .03, "close": close})
    return pd.DataFrame(rows)


def test_partial_bullish_manual_ict_context_with_missing_m5_is_not_neutral():
    context = {"D1": _frame("D1"), "H4": _frame("H4", "flat"), "H1": _frame("H1"), "M15": _frame("M15"), "M5": pd.DataFrame(columns=["time", "open", "high", "low", "close"])}
    boundary = datetime(2026, 7, 15, 15, tzinfo=timezone.utc)
    decision = build_decision(symbol="USD/JPY", asset_class="forex", display_timeframe="M15", candles_by_timeframe=context, analysis_timestamp=boundary, requested_strategy="ict_2022", session={"entry_allowed": True})
    assert decision["user_output"]["status"] == "POTENTIAL BUY CONTEXT"
    assert decision["user_output"]["direction"] == "Long bias"
    assert decision["user_output"]["requested_strategy"] == "ICT Precision"
    assert decision["user_output"]["eligibility"] == "Not yet eligible"
    assert decision["ict_context"]["alignment"] == "partial"
    assert decision["ict_context"]["zone"]["type"] == "demand"
    assert decision["ict_eligibility"]["state"] == "context_only"
    assert decision["sequence"]["liquidity_sweep"] != "pass"
    assert decision["sequence"]["displacement"] != "pass"
    assert decision["sequence"]["mss_choch"] != "pass"
    assert decision["execution"]["available"] is False
    assert decision["execution"]["execution_blocker"] == "missing_m5_data"
    assert decision["execution"]["entry"] is None and decision["execution"]["stop"] is None and decision["execution"]["targets"] == []
    assert decision["overlays"]["confirmation"] is None and decision["overlays"]["conditional_arrow"] is None
    assert decision["quality"]["score"] <= 40 and decision["quality"]["confidence"] == "low"
    assert "Load valid M5 data" in decision["user_output"]["next_action"]


def test_zone_formatter_uses_actual_zone_type_and_relative_position():
    assert _zone_relation({"low": 100, "high": 101, "type": "demand"}, 102, "forex", "USD/JPY").endswith("above demand.")
    assert _zone_relation({"low": 100, "high": 101, "type": "supply"}, 99, "forex", "USD/JPY").endswith("below supply.")
    assert _zone_relation({"low": 100, "high": 101, "type": "ote"}, 102, "forex", "USD/JPY").endswith("above OTE area.")
    assert _zone_relation({"low": 100, "high": 101, "type": "demand"}, 100.5, "forex", "USD/JPY") == "Price is inside demand."


def test_complete_strict_ict_sequence_reaches_ready_to_buy():
    times = pd.date_range("2026-01-01", periods=10, freq="5min", tz="UTC")
    m5 = pd.DataFrame([
        {"time": times[i], "open": 100, "high": high, "low": low, "close": close}
        for i, (high, low, close) in enumerate([(100.5,99.5,100),(100.6,99.6,100.1),(100.7,99.7,100.2),(100.8,99.8,100.3),(102.2,99.9,102),(102.1,100,101),(101.5,99.4,100),(101,99.3,99.5),(100.5,99.4,99.5),(100.4,99.4,99.5)])
    ])
    bundle = {"symbol": "EUR/USD", "asset_class": "forex", "analysis_time_utc": times[-1].isoformat(), "timeframes": {"M5": {"candles": m5, "available_candles": m5, "valid": True}, "M15": {"candles": m5, "available_candles": m5, "valid": True}}}
    timestamp = times[-1].isoformat()
    def wrapped(value): return {"value": value, "valid": True, "calculation_timestamp": timestamp, "source_timeframe": "M15", "reason": None}
    features = {"timeframes": {"H1": {"liquidity": wrapped({"unswept_highs": [{"price": 105, "time": times[0].isoformat()}], "unswept_lows": []})}, "M15": {"liquidity": wrapped({"unswept_lows": [{"price": 99.4, "time": times[0].isoformat()}], "equal_lows": []}), "swings": wrapped({"lows": [{"price": 99.2, "time": times[0].isoformat(), "swept": True, "sweep_time": times[1].isoformat()}], "highs": []}), "displacement": wrapped({"active": True, "direction": "bullish", "event_time": times[4].isoformat()}), "fvg": wrapped([{"low": 99.4, "high": 99.6, "direction": "bullish", "formation_time": times[5].isoformat(), "mitigated": False}])}}}
    top_down = {"timeframes": {"D1": {"bias": "bullish"}, "H4": {"bias": "bullish"}, "H1": {"bias": "bullish"}}, "m15_setup": {"enabled": True, "direction": "buy", "zone": {"low": 99, "high": 100, "type": "demand", "start_time": times[0].isoformat()}}}
    execution = {"state": "entry_valid", "entry": 100, "trigger": 100, "stop": 98.9, "targets": [{"price": 105, "valid": True, "swept": False}], "risk_reward": 2.0, "confirmed_signal": {"candle_time": times[-1].isoformat()}}
    ict = build_ict_precision(bundle=bundle, features=features, top_down=top_down, execution=execution, minimum_rr=1.5)
    assert ict["status"] == "READY TO BUY"
    assert ict["score"] == 100 and ict["confidence"] == "high"
    assert all(state == "pass" for state in ict["sequence"].values())
    assert all(row["timestamp"] for row in ict["sequence_events"].values() if row["state"] == "pass")
    assert validate_ict_consistency(ict)["valid"]


def test_validator_rejects_ready_without_m5_and_wrong_side_geometry():
    ict = {"status": "READY TO BUY", "ict_context": {"direction": "buy", "zone": {"type": "demand"}}, "execution": {"available": False, "entry": 100, "stop": 101, "targets": [{"price": 99}]}, "sequence": {"m5_confirmation": "waiting"}, "sequence_events": {}, "overlays": {"entry": {"price": 100}}}
    result = validate_ict_consistency(ict)
    assert not result["valid"]
    assert result["downgrade_status"] == "EXECUTION DATA UNAVAILABLE"


def test_frontend_uses_backend_manual_ict_contract_and_disables_context_path():
    root = Path(__file__).resolve().parents[1]; html = (root / "templates" / "index.html").read_text(); js = (root / "static" / "app.js").read_text()
    assert 'id="decision-strategy-heading"' in html and 'id="ict-sequence"' in html
    assert 'analysis.decision?.requested_strategy === "ict_2022"' in js
    assert "decisionOutput.strategy_label" in js and "decisionOutput.eligibility" in js
    assert "decision.ict_checklist" in js
    assert "if (setup?.allow_path === false) return" in js
    assert "if (setup?.zone_relation) return setup.zone_relation" in js
