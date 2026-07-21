import pandas as pd

from analysis.accumulation_detector import AccumulationConfig, detect_accumulation
from analysis.amd_liquidity import identify_amd_liquidity
from analysis.manipulation_detector import detect_manipulation
from analysis.distribution_detector import detect_distribution
from analysis.amd_engine import analyze_amd, normalized_amd


CFG = AccumulationConfig(minimum_bars=12, maximum_bars=12, minimum_width_atr=.5, maximum_width_atr=5, minimum_overlap_ratio=.5, maximum_directional_efficiency=.5)


def _range_rows(extra=()):
    times = pd.date_range("2025-01-01", periods=12 + len(extra), freq="5min", tz="UTC")
    base = []
    for index in range(12):
        close = 100.35 if index % 2 else 100.65
        base.append({"time": times[index], "open": 100.5, "high": 101 if index % 3 == 0 else 100.8, "low": 100 if index % 3 == 1 else 100.2, "close": close})
    for offset, values in enumerate(extra, 12):
        base.append({"time": times[offset], **values})
    return pd.DataFrame(base)


def _top_down(direction="buy"):
    return {"alignment": {"primary_direction": direction}, "m15_setup": {"target_context": {"price": 103 if direction == "buy" else 97, "reason": "unswept structure"}}}


def test_accumulation_requires_duration_and_rejects_directional_trend():
    assert detect_accumulation(_range_rows().iloc[:11], CFG) is None
    trend = _range_rows()
    trend[["open", "high", "low", "close"]] = [[100+i, 101+i, 99.9+i, 100.8+i] for i in range(12)]
    assert detect_accumulation(trend, CFG) is None


def test_locked_range_survives_sweep_reclaim_and_distribution():
    sweep = {"open": 100.3, "high": 100.5, "low": 99.5, "close": 100.2}
    reclaim = {"open": 100.2, "high": 100.7, "low": 100.1, "close": 100.6}
    expansion = {"open": 100.6, "high": 102.1, "low": 100.7, "close": 102.0}
    rows = _range_rows((sweep, reclaim, expansion))
    accumulation = detect_accumulation(rows, CFG)
    assert (accumulation["range_low"], accumulation["range_high"]) == (100.0, 101.0)
    manipulation = detect_manipulation(rows, accumulation, identify_amd_liquidity(rows, accumulation))
    assert manipulation["detected"] and manipulation["reclaimed_range"] and manipulation["side"] == "low"
    distribution = detect_distribution(rows, accumulation, manipulation)
    assert distribution["forming"] and distribution["direction"] == "up"
    later = detect_accumulation(_range_rows((sweep, reclaim, expansion, {"open": 102, "high": 102.2, "low": 101.8, "close": 102.1})), CFG)
    assert (later["range_low"], later["range_high"], later["end_time"]) == (accumulation["range_low"], accumulation["range_high"], accumulation["end_time"])


def test_wick_without_reclaim_is_not_confirmed_manipulation():
    rows = _range_rows(({"open": 100.9, "high": 101.4, "low": 100.8, "close": 101.2},))
    accumulation = detect_accumulation(rows, CFG)
    event = detect_manipulation(rows, accumulation, identify_amd_liquidity(rows, accumulation))
    assert event["forming"] and not event["detected"] and not event["reclaimed_range"]


def test_two_outside_closes_are_accepted_breakout_not_manipulation():
    rows = _range_rows((
        {"open": 100.9, "high": 101.4, "low": 100.8, "close": 101.2},
        {"open": 101.2, "high": 101.6, "low": 101.1, "close": 101.4},
    ))
    accumulation = detect_accumulation(rows, CFG)
    event = detect_manipulation(rows, accumulation, identify_amd_liquidity(rows, accumulation))
    assert event["boundary_event"] == "accepted_breakout"
    assert not event["detected"]


def test_normalized_amd_is_context_only_and_crypto_uses_rolling_cycle():
    rows = _range_rows(({"open": 100.3, "high": 100.5, "low": 99.5, "close": 100.2}, {"open": 100.2, "high": 100.7, "low": 100.1, "close": 100.6}))
    amd = analyze_amd(symbol="BTC/USD", asset_class="crypto", analysis_time=rows.iloc[-1].time + pd.Timedelta(minutes=5), m5_candles=rows, top_down=_top_down(), config=CFG)
    contract = normalized_amd(amd)
    assert contract["cycle_type"] == "rolling"
    assert "entry" not in contract and "stop" not in contract
    assert contract["phase"] == "manipulation_confirmed"
    assert contract["confidence"] != "high"


def test_news_and_countertrend_reduce_amd_confidence_and_block_valid_cycle():
    rows = _range_rows(({"open": 100.3, "high": 100.5, "low": 99.5, "close": 100.2}, {"open": 100.2, "high": 100.7, "low": 100.1, "close": 100.6}))
    amd = analyze_amd(symbol="EUR/USD", asset_class="forex", analysis_time=rows.iloc[-1].time + pd.Timedelta(minutes=5), m5_candles=rows, top_down=_top_down("sell"), filters={"news_risk": {"restriction_active": True}}, config=CFG)
    assert amd["event_context"] == "scheduled_news"
    assert amd["countertrend"] is True
    assert amd["confidence"] == "low"
    assert not amd["validation"]["valid_cycle"]
