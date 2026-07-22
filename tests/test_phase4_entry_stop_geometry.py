"""Phase 4 checkpoint 13: entry must lock once (deterministic, no
retroactive change) after completed M5 execution confirmation; stop must
be structural and on the correct side for each direction.
"""
from datetime import timedelta

import pandas as pd

from analysis.m5_execution_engine import build_m5_execution_plan


def _top_down(direction="buy", target=110.0):
    return {
        "alignment": {"primary_direction": direction},
        "m15_setup": {
            "enabled": True,
            "countertrend": False,
            "zone": {"low": 99.0, "high": 100.0, "type": "demand" if direction == "buy" else "supply"},
            "target_context": {"price": target, "reason": "M15 objective"},
        },
        "timeframes": {"H1": {"last_close": target}},
    }


def _m5_bullish(include_live=False):
    times = pd.date_range("2025-01-01 10:00", periods=12, freq="5min", tz="UTC")
    prices = [100.8, 100.5, 100.2, 99.8, 99.5, 99.9, 100.1, 100.3, 100.2, 101.4, 101.05, 101.1]
    rows = []
    previous = 100.7
    for index, (timestamp, close) in enumerate(zip(times, prices)):
        open_price = previous
        rows.append({"time": timestamp, "open": open_price, "high": max(open_price, close) + 0.1, "low": min(open_price, close) - (0.35 if index == 4 else 0.1), "close": close})
        previous = close
    if include_live:
        rows.append({"time": times[-1] + timedelta(minutes=5), "open": 101.1, "high": 102.2, "low": 101.0, "close": 102.1})
    return pd.DataFrame(rows)


def _m5_bearish():
    bullish = _m5_bullish()
    candles = bullish.copy()
    for column in ("open", "high", "low", "close"):
        candles[column] = 200 - bullish[column]
    candles[["high", "low"]] = candles[["low", "high"]]
    return candles


def test_buy_entry_is_deterministic_across_repeated_evaluation():
    candles = _m5_bullish()
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    first = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive", asset_type="forex")
    second = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive", asset_type="forex")
    assert first["state"] == "entry_valid"
    assert first["entry"] == second["entry"]
    assert first["stop"] == second["stop"]


def test_buy_entry_does_not_change_when_future_candles_are_appended():
    candles = _m5_bullish()
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    truncated = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive", asset_type="forex")
    extended_candles = pd.concat([candles, _m5_bullish(include_live=True).iloc[-1:]], ignore_index=True)
    extended = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=extended_candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive", asset_type="forex")
    assert truncated["entry"] == extended["entry"]
    assert truncated["stop"] == extended["stop"]


def test_buy_stop_is_below_the_protected_execution_structure():
    candles = _m5_bullish()
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    result = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive", asset_type="forex")
    assert result["state"] == "entry_valid"
    assert result["stop"] < result["entry"]
    assert result["stop"] < 99.0  # below the M15 demand zone low


def test_sell_stop_is_above_the_protected_execution_structure():
    candles = _m5_bearish()
    top_down = _top_down(direction="sell", target=90.0)
    top_down["m15_setup"]["zone"] = {"low": 100.0, "high": 101.0, "type": "supply"}
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    result = build_m5_execution_plan(top_down_analysis=top_down, m5_candles=candles, analysis_timestamp=boundary, current_price=99.0, mode="aggressive", asset_type="forex")
    assert result["state"] == "entry_valid"
    assert result["stop"] > result["entry"]
    assert result["stop"] > 101.0  # above the M15 supply zone high


def test_stop_direction_is_never_on_the_profitable_side():
    buy_candles = _m5_bullish()
    boundary = buy_candles.iloc[-1]["time"] + timedelta(minutes=5)
    buy = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=buy_candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive", asset_type="forex")
    assert buy["stop"] != buy["entry"]  # never zero-distance
    assert buy["stop"] < buy["entry"]  # never on the profitable (above-entry) side for a buy
