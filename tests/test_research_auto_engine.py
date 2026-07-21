from datetime import datetime, timedelta, timezone

import pandas as pd

from analysis.auto_strategy_router import route_auto
from analysis.candle_bundle import build_candle_bundle, bundle_contract
from analysis.market_features import calculate_market_features, feature
from analysis.regime_classifier import classify_regime
from evidence.expert_weights import update_weight
from evidence.performance_registry import PerformanceRegistry
from paper_testing.auto_shadow_logger import AutoShadowLogger
from strategies import breakout_retest, ict_2022, supply_demand
from pathlib import Path


def _candles(count=80, minutes=5, step=.1):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc); price = 100.0; rows = []
    for index in range(count):
        close = price + step
        rows.append({"time": start + timedelta(minutes=minutes * index), "open": price, "high": max(price, close) + .04, "low": min(price, close) - .04, "close": close})
        price = close
    return pd.DataFrame(rows)


def _feature_frame(direction="bullish", efficiency=.5, compression=False, displacement=False):
    timestamp = "2025-01-01T00:00:00+00:00"
    return {"structure_direction": feature(direction, timestamp, "H1"), "directional_efficiency": feature(efficiency, timestamp, "H1"), "compression": feature({"active": compression}, timestamp, "H1"), "displacement": feature({"active": displacement, "direction": direction}, timestamp, "H1"), "volatility_regime": feature("normal", timestamp, "H1"), "abnormal_candle": feature(False, timestamp, "H1"), "range": feature({"position": .5, "boundary_tests": 3, "low": 99, "high": 101}, timestamp, "H1"), "liquidity": feature({"equal_highs": [], "equal_lows": [], "unswept_highs": [], "unswept_lows": []}, timestamp, "H1"), "fvg": feature([], timestamp, "H1")}


def test_candle_bundle_normalizes_deduplicates_and_excludes_incomplete():
    frame = _candles(30)
    frame = pd.concat([frame, frame.iloc[[-1]]], ignore_index=True)
    boundary = frame.iloc[-1]["time"] + timedelta(minutes=2)
    bundle = build_candle_bundle(symbol="BTC/USD", asset_class="crypto", analysis_time=boundary, candles_by_timeframe={tf: frame for tf in ("D1", "H4", "H1", "M15", "M5")})
    assert len(bundle["timeframes"]["M5"]["available_candles"]) == 30
    assert len(bundle["timeframes"]["M5"]["candles"]) == 29
    assert any("duplicate" in warning for warning in bundle["warnings"])
    assert bundle_contract(bundle)["timeframes"]["M5"]["timezone"] == "UTC"


def test_common_features_are_timestamped_and_validity_tagged():
    boundary = _candles().iloc[-1]["time"] + timedelta(days=5)
    bundle = build_candle_bundle(symbol="BTC/USD", asset_class="crypto", analysis_time=boundary, candles_by_timeframe={tf: _candles(minutes={"D1": 1440, "H4": 240, "H1": 60, "M15": 15, "M5": 5}[tf]) for tf in ("D1", "H4", "H1", "M15", "M5")})
    features = calculate_market_features(bundle)
    atr = features["timeframes"]["M15"]["atr"]
    assert set(("value", "calculation_timestamp", "source_timeframe", "valid", "reason")) <= set(atr)


def test_regime_classifier_distinguishes_pullback_from_reversal():
    features = {"timeframes": {"D1": _feature_frame("bullish"), "H4": _feature_frame("bullish"), "H1": _feature_frame("bearish")}}
    result = classify_regime(features)
    assert result["regime"] == "PULLBACK_BULLISH_REGIME"


def test_auto_selects_supply_demand_for_bullish_pullback_without_ict_or_breakout():
    features = {"timeframes": {tf: _feature_frame("bullish") for tf in ("D1", "H4", "H1", "M15", "M5")}}
    top_down = {"m15_setup": {"enabled": True, "direction": "buy", "setup_type": "demand_retracement", "status": "watching", "zone": {"low": 99, "high": 100, "start_time": 1}, "target_context": {"price": 105}}}
    result = route_auto(symbol="EUR/USD", asset_class="forex", regime={"regime": "PULLBACK_BULLISH_REGIME"}, features=features, top_down=top_down, session={"entry_allowed": True, "name": "London"}, execution_mode="conservative")
    assert result["selected_strategy"] == "supply_demand"
    assert result["evidence_status"] == "INSUFFICIENT_EVIDENCE"


def test_ineligible_strategy_cannot_win_even_with_large_evidence_multiplier():
    class StrongIctEvidence:
        def lookup(self, context):
            return {"evidence_grade": "USABLE", "multiplier": 1.10, "closed_trades": 500, "out_of_sample": True}
    features = {"timeframes": {tf: _feature_frame("bullish") for tf in ("D1", "H4", "H1", "M15", "M5")}}
    top_down = {"m15_setup": {"enabled": True, "direction": "buy", "setup_type": "demand_retracement", "status": "watching", "zone": {"low": 99, "high": 100, "start_time": 1}}}
    result = route_auto(symbol="EUR/USD", asset_class="forex", regime={"regime": "TRENDING_BULLISH"}, features=features, top_down=top_down, session={"entry_allowed": True, "name": "London"}, execution_mode="conservative", registry=StrongIctEvidence())
    assert "ict_2022" in result["ineligible_strategies"]
    assert result["selected_strategy"] == "supply_demand"


def test_small_samples_are_shrunk_and_cannot_claim_best_strategy():
    record = {"symbol": "EUR/USD", "strategy_version": "ict_2022_v1", "closed_trades": 5, "expectancy_r": 2.0, "expectancy_variance": 1.0, "evaluation_period": "fold-1", "out_of_sample": True}
    evidence = PerformanceRegistry(records=[record]).lookup({"symbol": "EUR/USD", "strategy_version": "ict_2022_v1"})
    assert evidence["evidence_grade"] == "INSUFFICIENT"
    assert evidence["shrunk_expectancy_r"] < .2
    assert evidence["multiplier"] <= 1.10


def test_expert_weight_updates_only_after_closed_outcome():
    assert update_weight(1.0, 2.0, outcome_closed=False) == 1.0
    assert update_weight(1.0, 2.0, outcome_closed=True) == 1.04


def test_all_strategy_modules_expose_frozen_research_interface():
    for module, version in ((ict_2022, "ict_2022_v1"), (supply_demand, "supply_demand_v1"), (breakout_retest, "breakout_retest_v1")):
        assert module.STRATEGY_VERSION == version
        for name in ("is_eligible", "detect_setup", "build_candidate", "explain"):
            assert callable(getattr(module, name))


def test_shadow_logger_preserves_selection_and_appends_outcome(tmp_path):
    logger = AutoShadowLogger(tmp_path / "shadow.jsonl")
    decision = {"decision_id": "d1", "setup": {"setup_id": "s1"}, "regime": {"regime": "RANGING"}, "router": {"eligible_strategies": [], "candidates": [], "selected_candidate": None, "selected_strategy": None, "evidence_status": "INSUFFICIENT_EVIDENCE"}, "execution": {}, "user_output": {"status": "NO VALID SETUP"}}
    assert logger.record(decision)
    assert not logger.record(decision)
    logger.record_outcome(decision_id="d1", outcomes={"auto": "no_trade"}, outcome_time="later")
    lines = logger.path.read_text().splitlines()
    assert len(lines) == 2


def test_ui_displays_backend_auto_selection_and_evidence_only():
    root = Path(__file__).resolve().parents[1]
    html = (root / "templates" / "index.html").read_text()
    javascript = (root / "static" / "app.js").read_text()
    assert "Auto · Recommended" in html
    for identifier in ("decision-strategy", "decision-strategy-reason", "decision-evidence"):
        assert f'id="{identifier}"' in html
    assert "analysis.decision?.user_output" in javascript
    assert "decisionOutput.reason_strategy_selected" in javascript
