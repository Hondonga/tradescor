"""Strategy-neutral liquidity analysis."""

from __future__ import annotations

from scanner.liquidity import detect_equal_levels, detect_liquidity_sweeps


def analyze_liquidity(candles, swings: dict[str, object], tolerance: float) -> dict[str, object]:
    """Return reusable liquidity pools and sweeps."""
    equal_levels = detect_equal_levels({"highs": swings.get("highs", []), "lows": swings.get("lows", [])}, tolerance)
    sweeps = detect_liquidity_sweeps(candles, {"highs": swings.get("highs", []), "lows": swings.get("lows", [])}, lookback=80)

    return {
        "equal_highs": equal_levels["equal_highs"],
        "equal_lows": equal_levels["equal_lows"],
        "previous_swing_highs": swings.get("highs", [])[-5:],
        "previous_swing_lows": swings.get("lows", [])[-5:],
        "sweeps": sweeps[-5:],
        "latest_sweep": sweeps[-1] if sweeps else {},
    }
