"""Phase 4 checkpoint 8: liquidity sweeps must carry an explicit, stable
identity plus the required field set, causal and structure-owned.
"""
import pandas as pd

from analysis.ict_sweep import classify_sweep


def _rows(values, start="2026-01-01"):
    times = pd.date_range(start, periods=len(values), freq="15min", tz="UTC")
    return pd.DataFrame([{"time": times[i], "open": o, "high": h, "low": l, "close": c} for i, (o, h, l, c) in enumerate(values)])


def _confirmed_buy_sweep():
    # Candle 0 forms the pool reference point; candle 1 trades below the
    # pool (99) then closes back above it -- a swept-and-reclaimed low.
    rows = _rows([(100, 101, 99.5, 100), (99.5, 99.9, 98.7, 99.3), (99.3, 100.2, 99.1, 100.1)])
    pool = {"liquidity_id": "liq-1", "price": 99, "type": "prominent_swing", "formed_at": rows.iloc[0].time.isoformat()}
    result = classify_sweep(rows, pool, direction="buy")
    return result


def test_a_confirmed_sweep_carries_every_required_field():
    result = _confirmed_buy_sweep()
    assert result["valid"] is True
    sweep = result["result"]
    for field in ("sweep_id", "liquidity_id", "direction", "liquidity_type", "liquidity_price", "sweep_price", "swept_at", "confirmed_at", "active"):
        assert field in sweep, field
    assert sweep["direction"] == "buy"
    assert sweep["sweep_id"].startswith("sweep-")
    assert sweep["liquidity_type"] == "prominent_swing"
    assert sweep["liquidity_price"] == 99
    assert sweep["confirmed_at"] is not None
    assert sweep["active"] is True


def test_sweep_id_is_deterministic_for_the_same_pool_direction_and_time():
    first = _confirmed_buy_sweep()["result"]
    second = _confirmed_buy_sweep()["result"]
    assert first["sweep_id"] == second["sweep_id"]


def test_sweep_id_differs_for_a_different_pool():
    rows = _rows([(100, 101, 99.5, 100), (99.5, 99.9, 98.7, 99.3), (99.3, 100.2, 99.1, 100.1)])
    pool_a = {"liquidity_id": "liq-1", "price": 99, "type": "prominent_swing", "formed_at": rows.iloc[0].time.isoformat()}
    pool_b = {"liquidity_id": "liq-2", "price": 99, "type": "prominent_swing", "formed_at": rows.iloc[0].time.isoformat()}
    result_a = classify_sweep(rows, pool_a, direction="buy")["result"]
    result_b = classify_sweep(rows, pool_b, direction="buy")["result"]
    assert result_a["sweep_id"] != result_b["sweep_id"]


def test_no_pool_means_no_fabricated_sweep():
    rows = _rows([(100, 101, 99, 100)] * 3)
    result = classify_sweep(rows, None, direction="buy")
    assert result["result"] is None
    assert result["valid"] is False
    assert result["rejection_reason"]


def test_accepted_breakout_is_not_confirmed_and_is_marked_inactive():
    rows = _rows([(100, 101, 99, 100), (99, 99.2, 98.4, 98.6), (98.6, 98.8, 98.1, 98.3)])
    pool = {"liquidity_id": "liq-1", "price": 99, "type": "prominent_swing", "formed_at": rows.iloc[0].time.isoformat()}
    result = classify_sweep(rows, pool, direction="buy", accepted_closes=2)
    sweep = result["result"]
    assert sweep["accepted_breakout"] is True
    assert sweep["active"] is False
    assert sweep["confirmed"] is False


def test_wick_only_sweep_still_forming_produces_no_confirmed_identity_yet():
    rows = _rows([(100, 101, 99, 100), (100, 100.5, 98.8, 99.1)])
    pool = {"liquidity_id": "liq-1", "price": 99, "type": "prominent_swing", "formed_at": rows.iloc[0].time.isoformat()}
    result = classify_sweep(rows.iloc[:1], pool, direction="buy", forming_candle=rows.iloc[1:])
    assert result["state"] == "forming"
    assert result["valid"] is False
