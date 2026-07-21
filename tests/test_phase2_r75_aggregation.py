"""Phase 2 checkpoint 3: R_75 M1 -> M5/M15/H1 resampling determinism. This is
the exact function get_multi_timeframe_context uses for provider=="deriv"
and asset_class=="derived_index" (the golden path), so M5/M15/H1 are always
resampled from one M1 source rather than fetched independently per timeframe.
"""
import pandas as pd

from providers.multi_timeframe import _resample_completed, _normalize_candles


def _m1_candles(count, start="2026-07-01T00:00:00Z"):
    times = pd.date_range(start, periods=count, freq="1min", tz="UTC")
    rows = []
    price = 50000.0
    for i, t in enumerate(times):
        close = price + (i % 7) - 3
        rows.append({"time": t, "open": price, "high": max(price, close) + 1, "low": min(price, close) - 1, "close": close})
        price = close
    return pd.DataFrame(rows)


def test_m15_contains_exactly_the_completed_m5_windows():
    # 45 completed M1 candles = exactly 3 completed M15 buckets (15 each).
    m1 = _m1_candles(45)
    m15 = _resample_completed(m1, "M15")
    assert len(m15) == 3
    for i, row in m15.iterrows():
        window = m1[(m1.time >= row.time) & (m1.time < row.time + pd.Timedelta(minutes=15))]
        assert len(window) == 15
        assert row.open == window.iloc[0].open
        assert row.close == window.iloc[-1].close
        assert row.high == window.high.max()
        assert row.low == window.low.min()


def test_h1_contains_exactly_the_completed_lower_timeframe_candles():
    m1 = _m1_candles(180)  # exactly 3 completed H1 buckets
    h1 = _resample_completed(m1, "H1")
    assert len(h1) == 3
    for i, row in h1.iterrows():
        window = m1[(m1.time >= row.time) & (m1.time < row.time + pd.Timedelta(hours=1))]
        assert len(window) == 60
        assert row.open == window.iloc[0].open
        assert row.close == window.iloc[-1].close


def test_forming_final_bucket_is_excluded_not_just_the_last_row():
    # 44 M1 candles: 2 complete M15 windows (30) + 14 forming candles that must not appear.
    m1 = _m1_candles(44)
    m15 = _resample_completed(m1, "M15")
    assert len(m15) == 2
    last_complete_end = m15.iloc[-1].time + pd.Timedelta(minutes=15)
    assert last_complete_end <= pd.Timestamp(m1.iloc[-1].time)


def test_resampling_is_deterministic_across_repeated_calls():
    m1 = _m1_candles(93)
    first = _resample_completed(m1.copy(), "M5")
    second = _resample_completed(m1.copy(), "M5")
    pd.testing.assert_frame_equal(first, second)


def test_out_of_order_and_duplicate_m1_candles_normalize_before_resampling():
    m1 = _m1_candles(30)
    shuffled = pd.concat([m1.iloc[10:], m1.iloc[:10], m1.iloc[[5]]]).reset_index(drop=True)  # reordered + one duplicate
    normalized = _normalize_candles(shuffled)
    assert list(normalized.time) == sorted(normalized.time)
    assert normalized.time.is_unique
    assert len(normalized) == 30  # duplicate collapsed, nothing lost or duplicated
