"""ICT-specific liquidity pool and sweep interpretation."""

from __future__ import annotations

import pandas as pd

from scanner.liquidity import detect_liquidity_sweeps, most_recent_sweep


def analyze_liquidity_sweep(
    candles: pd.DataFrame,
    swings: dict[str, list[dict[str, object]]],
    equal_levels: dict[str, list[dict[str, object]]],
    direction: str | None,
    lookback: int = 80,
) -> dict[str, object]:
    """Return the active directional liquidity pool and confirmed sweep."""
    normalized = _direction(direction)
    pool = _select_pool(swings, equal_levels, normalized)
    sweeps = detect_liquidity_sweeps(candles, swings, lookback=lookback)
    aligned = [sweep for sweep in sweeps if normalized is None or sweep.get("direction") == normalized]
    sweep = most_recent_sweep(aligned)

    return {
        "pool_identified": bool(pool),
        "pool": pool,
        "swept": sweep is not None,
        "sweep": sweep or {},
        "status": "swept" if sweep else "waiting",
        "expected_side": "sell-side" if normalized == "bullish" else "buy-side" if normalized == "bearish" else "either side",
    }


def _select_pool(
    swings: dict[str, list[dict[str, object]]],
    equal_levels: dict[str, list[dict[str, object]]],
    direction: str | None,
) -> dict[str, object]:
    if direction == "bullish":
        equal = equal_levels.get("equal_lows", [])
        swing = swings.get("lows", [])
        return _pool(equal[-1] if equal else swing[-1] if swing else {}, "sell-side", "Equal Lows" if equal else "Swing Low")
    if direction == "bearish":
        equal = equal_levels.get("equal_highs", [])
        swing = swings.get("highs", [])
        return _pool(equal[-1] if equal else swing[-1] if swing else {}, "buy-side", "Equal Highs" if equal else "Swing High")

    highs = equal_levels.get("equal_highs", []) or swings.get("highs", [])
    lows = equal_levels.get("equal_lows", []) or swings.get("lows", [])
    candidate = highs[-1] if highs else lows[-1] if lows else {}
    side = "buy-side" if highs else "sell-side" if lows else ""
    return _pool(candidate, side, "Liquidity Pool")


def _pool(level: dict[str, object], side: str, label: str) -> dict[str, object]:
    if not level or level.get("price") is None:
        return {}
    return {
        "label": label,
        "side": side,
        "price": round(float(level["price"]), 6),
        "time": level.get("end_time") or level.get("time") or level.get("start_time"),
    }


def _direction(value: str | None) -> str | None:
    text = str(value or "").lower()
    if text in {"bullish", "long"}:
        return "bullish"
    if text in {"bearish", "short"}:
        return "bearish"
    return None
