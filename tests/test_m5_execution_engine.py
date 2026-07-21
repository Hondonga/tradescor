from __future__ import annotations

from datetime import timedelta

import pandas as pd

from analysis.m5_execution_engine import build_m5_execution_plan


def _top_down(direction: str = "buy", target: float = 110.0) -> dict[str, object]:
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


def _m5_with_bullish_confirmation(include_live: bool = False) -> pd.DataFrame:
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


def test_every_actionable_plan_is_m5_and_uses_m5_structure_stop():
    candles = _m5_with_bullish_confirmation()
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    result = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive")

    assert result["execution_timeframe"] == "M5"
    assert result["state"] == "entry_valid"
    assert result["confirmed_signal"]["completed"] is True
    assert result["stop"] < 99.0
    assert result["entry"] == result["trigger"]


def test_live_trigger_never_becomes_confirmed_before_close():
    candles = _m5_with_bullish_confirmation(include_live=True)
    live_time = candles.iloc[-1]["time"]
    result = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=candles, analysis_timestamp=live_time + timedelta(minutes=2), current_price=float(candles.iloc[-1]["close"]), mode="aggressive")

    assert result["execution_timeframe"] == "M5"
    assert result.get("confirmed_signal") is None or result["confirmed_signal"]["candle_time"] != live_time.isoformat()


def test_m15_touch_without_m5_confirmation_has_no_entry():
    candles = _m5_with_bullish_confirmation().iloc[:8].copy()
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    result = build_m5_execution_plan(top_down_analysis=_top_down(), m5_candles=candles, analysis_timestamp=boundary, current_price=float(candles.iloc[-1]["close"]))

    assert result["state"] in {"waiting_for_trigger", "trigger_forming"}
    assert result["entry"] is None
    assert result["stop"] is None


def test_rr_is_recalculated_from_m5_entry_and_poor_reward_rejects():
    candles = _m5_with_bullish_confirmation()
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    result = build_m5_execution_plan(top_down_analysis=_top_down(target=102.0), m5_candles=candles, analysis_timestamp=boundary, current_price=101.0, mode="aggressive")

    assert result["state"] == "too_late"
    assert result["entry"] is not None
    assert result["entry_zone"]["low"] < result["entry"] < result["entry_zone"]["high"]
    assert result["risk_reward"] < 1.5


def test_mixed_context_cannot_create_entry():
    candles = _m5_with_bullish_confirmation()
    top_down = _top_down()
    top_down["alignment"]["primary_direction"] = "neutral"
    result = build_m5_execution_plan(top_down_analysis=top_down, m5_candles=candles, analysis_timestamp=candles.iloc[-1]["time"] + timedelta(minutes=5))

    assert result["direction"] == "neutral"
    assert result["entry"] is None


def test_bearish_context_bullish_pullback_can_confirm_sell_on_m5():
    bullish = _m5_with_bullish_confirmation()
    candles = bullish.copy()
    for column in ("open", "high", "low", "close"):
        candles[column] = 200 - bullish[column]
    candles[["high", "low"]] = candles[["low", "high"]]
    top_down = _top_down(direction="sell", target=90.0)
    top_down["m15_setup"]["zone"] = {"low": 100.0, "high": 101.0, "type": "supply"}
    boundary = candles.iloc[-1]["time"] + timedelta(minutes=5)
    result = build_m5_execution_plan(top_down_analysis=top_down, m5_candles=candles, analysis_timestamp=boundary, current_price=99.0, mode="aggressive")

    assert result["execution_timeframe"] == "M5"
    assert result["direction"] == "sell"
    assert result["state"] == "entry_valid"
    assert result["stop"] > 101.0
    assert result["targets"][0]["price"] < result["entry"]
