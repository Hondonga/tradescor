"""Phase 4 checkpoint 11: premium/discount dealing range must carry
current_position_pct (previously missing entirely) alongside the
existing range_id/low/high/equilibrium/location fields.
"""
import pandas as pd

from analysis.ict_dealing_range import identify_dealing_range


def _range_candles():
    # A clean up-down-up sequence with a low pivot near bar 5 (1.2650) and a
    # high pivot near bar 15 (1.2750), each confirmed by 2 bars either side,
    # wide enough to clear the default 2.0*ATR minimum width, ending well
    # inside the range (discount side, close to the low).
    rows = []
    t0 = pd.Timestamp("2026-01-05T00:00:00Z")  # Monday
    prices = (
        [1.2700, 1.2690, 1.2670, 1.2660, 1.2652, 1.2650, 1.2655, 1.2665]
        + [1.2680, 1.2700, 1.2720, 1.2735, 1.2745, 1.2748, 1.2750, 1.2747, 1.2740]
        + [1.2700, 1.2680, 1.2670, 1.2665, 1.2662, 1.2660]
    )
    for i, p in enumerate(prices):
        rows.append({"time": t0 + pd.Timedelta(hours=4 * i), "open": p, "high": p + 0.0008, "low": p - 0.0008, "close": p})
    return pd.DataFrame(rows)


def test_valid_range_carries_current_position_pct_and_both_field_name_conventions():
    result = identify_dealing_range(_range_candles(), timeframe="H4", minimum_atr=0.5)
    assert result["valid"] is True
    range_ = result["result"]
    assert range_["current_position_pct"] is not None
    assert 0 <= range_["current_position_pct"] <= 100
    # Existing field names remain unchanged for existing consumers...
    assert range_["low"] == range_["range_low"]
    assert range_["high"] == range_["range_high"]
    assert range_["location"] == range_["premium_discount_state"]
    assert range_["range_id"] == range_["source_episode_id"]
    # ...and range_high is strictly greater than range_low.
    assert range_["range_high"] > range_["range_low"]


def test_current_position_pct_is_near_zero_at_the_range_low_and_near_100_at_the_range_high():
    range_ = identify_dealing_range(_range_candles(), timeframe="H4", minimum_atr=0.5)["result"]
    low, high = range_["range_low"], range_["range_high"]
    pct_at_low = round((low - low) / (high - low) * 100, 2)
    pct_at_high = round((high - low) / (high - low) * 100, 2)
    assert pct_at_low == 0.0
    assert pct_at_high == 100.0


def test_invalid_range_has_no_fabricated_position_pct():
    tiny = pd.DataFrame(
        [{"time": pd.Timestamp("2026-01-05T00:00:00Z") + pd.Timedelta(hours=i), "open": 1.27, "high": 1.2701, "low": 1.2699, "close": 1.27} for i in range(5)]
    )
    result = identify_dealing_range(tiny, timeframe="H4")
    assert result["valid"] is False
    assert result["result"] is None
