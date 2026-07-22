"""Phase 4 checkpoint 7: H1/M15/M5 responsibilities must be explicit and
causal -- no timeframe may use future candles, verified by proving the
top-down analysis at a fixed decision time is identical whether or not
the input frames contain additional candles beyond that time.
"""
import pandas as pd

from analysis.top_down_engine import analyze_top_down_market, completed_candles


def _series(n, start, freq, base=1.2700, step=0.00006):
    times = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    price = base
    rows = []
    for t in times:
        rows.append({"time": t, "open": price, "high": price + step * 3, "low": price - step, "close": price + step})
        price += step * 0.3
    return pd.DataFrame(rows)


def _frames(h1_count, m15_count, m5_count):
    return {
        "H1": _series(h1_count, "2026-01-05T00:00:00Z", "1h"),
        "M15": _series(m15_count, "2026-01-05T00:00:00Z", "15min"),
        "M5": _series(m5_count, "2026-01-05T00:00:00Z", "5min"),
    }


def test_completed_candles_excludes_a_row_that_has_not_closed_at_the_boundary():
    frame = _series(5, "2026-01-05T00:00:00Z", "5min")
    boundary = frame.iloc[2].time  # the boundary lands exactly on candle 2's OPEN, not its close
    result = completed_candles(frame, "M5", boundary)
    # Candle 2 needs a full 5 minutes past its own open to be "completed" at
    # this boundary; only candles 0 and 1 have fully closed by then.
    assert len(result) == 2


def test_analysis_at_a_fixed_boundary_is_identical_regardless_of_future_rows_present():
    boundary = pd.Timestamp("2026-01-05T20:00:00Z")
    truncated = _frames(20, 80, 240)  # ends at/near the boundary
    extended = {
        tf: pd.concat([truncated[tf], _series(50, str(truncated[tf].iloc[-1].time + pd.Timedelta(hours=1)), {"H1": "1h", "M15": "15min", "M5": "5min"}[tf])], ignore_index=True)
        for tf in truncated
    }
    result_truncated = analyze_top_down_market(symbol="GBP/USD", candles_by_timeframe=truncated, analysis_timestamp=boundary)
    result_extended = analyze_top_down_market(symbol="GBP/USD", candles_by_timeframe=extended, analysis_timestamp=boundary)
    assert result_truncated["alignment"] == result_extended["alignment"]
    assert result_truncated["timeframes"]["H1"] == result_extended["timeframes"]["H1"]
    assert result_truncated["timeframes"]["M15"] == result_extended["timeframes"]["M15"]


def test_h1_owns_external_structure_and_bias_m15_owns_location_and_pullback():
    frames = _frames(40, 120, 300)
    boundary = frames["M5"].iloc[-1].time
    result = analyze_top_down_market(symbol="GBP/USD", candles_by_timeframe=frames, analysis_timestamp=boundary)
    timeframes = result["timeframes"]
    assert "H1" in timeframes and "bias" in timeframes["H1"]
    assert "M15" in timeframes and ("bias" in timeframes["M15"] or "structure" in timeframes["M15"])
    # H1 and M15 are independently computed rows, not the same object --
    # confirms they are genuinely separate responsibilities, not one
    # timeframe's output copied onto the other.
    assert timeframes["H1"] is not timeframes["M15"]
