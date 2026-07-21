"""Risk, stop, target, and RR helpers."""

from __future__ import annotations

import pandas as pd


def build_levels(
    candles: pd.DataFrame,
    direction: str | None,
    sweep: dict[str, object] | None,
    ifvg: dict[str, object] | None,
    htf_fvg: dict[str, object] | None,
    swings: dict[str, list[dict[str, object]]],
    fvgs: list[dict[str, object]],
) -> dict[str, object]:
    """Create suggested levels from current chart structure."""
    entry_zone = ifvg or htf_fvg

    if direction not in {"bullish", "bearish"} or entry_zone is None:
        return _empty_levels(entry_zone)

    entry_top = float(entry_zone["top_price"])
    entry_bottom = float(entry_zone["bottom_price"])
    entry_price = (entry_top + entry_bottom) / 2
    buffer = _buffer(candles)

    if direction == "bullish":
        stop_loss = _long_stop(candles, sweep, swings, buffer)
        tp1, tp2 = _long_targets(entry_price, swings, fvgs)
    else:
        stop_loss = _short_stop(candles, sweep, swings, buffer)
        tp1, tp2 = _short_targets(entry_price, swings, fvgs)

    rr1 = _risk_reward(direction, entry_price, stop_loss, tp1)
    rr2 = _risk_reward(direction, entry_price, stop_loss, tp2)

    return {
        "entry_zone": {"top": round(entry_top, 6), "bottom": round(entry_bottom, 6)},
        "stop_loss": _round_or_none(stop_loss),
        "tp1": _round_or_none(tp1),
        "tp2": _round_or_none(tp2),
        "rr1": _round_or_none(rr1),
        "rr2": _round_or_none(rr2),
    }


def _empty_levels(entry_zone: dict[str, object] | None) -> dict[str, object]:
    zone = {}
    if entry_zone:
        zone = {
            "top": round(float(entry_zone["top_price"]), 6),
            "bottom": round(float(entry_zone["bottom_price"]), 6),
        }

    return {
        "entry_zone": zone,
        "stop_loss": None,
        "tp1": None,
        "tp2": None,
        "rr1": None,
        "rr2": None,
    }


def _buffer(candles: pd.DataFrame) -> float:
    ranges = candles["high"] - candles["low"]
    average_range = float(ranges.tail(20).mean())
    return max(average_range * 0.25, float(candles.iloc[-1]["close"]) * 0.00005)


def _long_stop(
    candles: pd.DataFrame,
    sweep: dict[str, object] | None,
    swings: dict[str, list[dict[str, object]]],
    buffer: float,
) -> float:
    candidates = [float(candles["low"].tail(10).min())]
    if sweep:
        candidates.append(float(sweep["swept_price"]))
    if swings["lows"]:
        candidates.append(float(swings["lows"][-1]["price"]))
    return min(candidates) - buffer


def _short_stop(
    candles: pd.DataFrame,
    sweep: dict[str, object] | None,
    swings: dict[str, list[dict[str, object]]],
    buffer: float,
) -> float:
    candidates = [float(candles["high"].tail(10).max())]
    if sweep:
        candidates.append(float(sweep["swept_price"]))
    if swings["highs"]:
        candidates.append(float(swings["highs"][-1]["price"]))
    return max(candidates) + buffer


def _long_targets(
    entry_price: float,
    swings: dict[str, list[dict[str, object]]],
    fvgs: list[dict[str, object]],
) -> tuple[float | None, float | None]:
    swing_targets = sorted(
        {float(swing["price"]) for swing in swings["highs"] if float(swing["price"]) > entry_price}
    )
    fvg_targets = sorted(
        {float(zone["bottom_price"]) for zone in fvgs if zone["type"] == "bearish" and float(zone["bottom_price"]) > entry_price}
    )
    return _first_two(sorted(set(swing_targets + fvg_targets)))


def _short_targets(
    entry_price: float,
    swings: dict[str, list[dict[str, object]]],
    fvgs: list[dict[str, object]],
) -> tuple[float | None, float | None]:
    swing_targets = sorted(
        {float(swing["price"]) for swing in swings["lows"] if float(swing["price"]) < entry_price},
        reverse=True,
    )
    fvg_targets = sorted(
        {float(zone["top_price"]) for zone in fvgs if zone["type"] == "bullish" and float(zone["top_price"]) < entry_price},
        reverse=True,
    )
    return _first_two(sorted(set(swing_targets + fvg_targets), reverse=True))


def _first_two(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], None
    return values[0], values[1]


def _risk_reward(
    direction: str,
    entry: float,
    stop: float | None,
    target: float | None,
) -> float | None:
    if stop is None or target is None:
        return None

    risk = abs(entry - stop)
    reward = target - entry if direction == "bullish" else entry - target

    if risk <= 0 or reward <= 0:
        return None

    return reward / risk


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)

