"""Phase 4 checkpoint 14: GBP/USD target selection must be causal and use
only unswept, correctly-sided structural targets. The underlying engine
(analysis/liquidity_target_engine.py) already has 9 comprehensive tests
covering this exact behavior (tests/test_liquidity_target_engine.py,
asset_class='forex') -- this file adds an explicit GBP/USD-symbol
confirmation per the phase's non-negotiable scope, rather than duplicating
that coverage.
"""
import pandas as pd

from analysis.liquidity_target_engine import build_liquidity_targets

NOW = pd.Timestamp("2026-07-16T16:00:00Z")


def _frame():
    lows = [1.2650] * 20
    highs = [1.2750] * 20
    times = pd.date_range(NOW - pd.Timedelta(minutes=5 * 19), periods=20, freq="5min")
    return pd.DataFrame([{"time": t, "open": (l + h) / 2, "high": h, "low": l, "close": (l + h) / 2} for t, l, h in zip(times, lows, highs)])


def _level(price, kind, time="2026-07-16T15:00:00Z"):
    return {"price": price, "formed_at": time, "source_timeframe": "M15", "type": kind, "prominence": 18, "touch_count": 2}


def _engine(direction, entry, stop, levels):
    return build_liquidity_targets(
        symbol="GBP/USD", asset_class="forex", direction=direction, entry_price=entry, stop_price=stop,
        candles_by_timeframe={"M5": _frame()}, decision_timestamp=NOW, higher_timeframe_draw=direction,
        candidate_levels=levels, apply_offset=True,
    )


def test_gbpusd_buy_target_is_above_entry():
    result = _engine("buy", 1.2700, 1.2680, [_level(1.2750, "equal_highs")])
    assert result["selected_targets"]["tp1"]["price"] > 1.2700


def test_gbpusd_sell_target_is_below_entry():
    result = _engine("sell", 1.2700, 1.2720, [_level(1.2650, "equal_lows")])
    assert result["selected_targets"]["tp1"]["price"] < 1.2700


def test_gbpusd_wrong_side_target_is_rejected():
    result = _engine("buy", 1.2700, 1.2680, [_level(1.2650, "equal_lows")])
    reasons = [reason for row in result["candidates"] for reason in row["rejection_reasons"]]
    assert "Target is on the wrong side of entry." in reasons
    assert result["selected_targets"]["tp1"] is None


def test_gbpusd_future_created_level_is_rejected():
    result = _engine("buy", 1.2700, 1.2680, [_level(1.2750, "equal_highs", time="2026-07-16T17:00:00Z")])
    reasons = [reason for row in result["candidates"] for reason in row["rejection_reasons"]]
    assert "Level was confirmed after the decision timestamp." in reasons


def test_gbpusd_no_valid_target_leaves_tp1_null_not_fabricated():
    # No candidate levels at all -- must not invent a target to complete the plan.
    result = _engine("buy", 1.2700, 1.2680, [])
    assert result["selected_targets"]["tp1"] is None
