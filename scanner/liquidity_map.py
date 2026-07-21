"""Smart liquidity map helpers."""

from __future__ import annotations

import math

import pandas as pd


def build_liquidity_map(
    current_candles: pd.DataFrame,
    daily_candles: pd.DataFrame | None = None,
    weekly_candles: pd.DataFrame | None = None,
    equal_levels: dict[str, list[dict[str, object]]] | None = None,
    bias: str = "NEUTRAL",
) -> dict[str, object]:
    """Build a small roadmap of nearby liquidity pools."""
    if current_candles.empty:
        return {"current_price": None, "buy_side": [], "sell_side": [], "current_target": {}}

    current_price = float(current_candles.iloc[-1]["close"])
    levels: list[dict[str, object]] = []

    levels.extend(_previous_daily_levels(daily_candles))
    levels.extend(_previous_weekly_levels(weekly_candles))
    levels.extend(_asian_range_levels(current_candles))
    levels.extend(_equal_level_rows(equal_levels or {}))
    levels.extend(_round_number_levels(current_price))

    buy_side = _nearest_levels(levels, current_price, side="buy_side")
    sell_side = _nearest_levels(levels, current_price, side="sell_side")
    target = _current_target(bias, buy_side, sell_side, current_price)

    return {
        "current_price": round(current_price, 6),
        "buy_side": buy_side,
        "sell_side": sell_side,
        "current_target": target,
    }


def _previous_daily_levels(candles: pd.DataFrame | None) -> list[dict[str, object]]:
    if candles is None or len(candles) < 2:
        return []

    previous = candles.sort_values("time").iloc[-2]
    return [
        _level("Previous Day High", "buy_side", previous["high"], "daily"),
        _level("Previous Day Low", "sell_side", previous["low"], "daily"),
    ]


def _previous_weekly_levels(candles: pd.DataFrame | None) -> list[dict[str, object]]:
    if candles is None or len(candles) < 2:
        return []

    previous = candles.sort_values("time").iloc[-2]
    return [
        _level("Previous Week High", "buy_side", previous["high"], "weekly"),
        _level("Previous Week Low", "sell_side", previous["low"], "weekly"),
    ]


def _asian_range_levels(candles: pd.DataFrame) -> list[dict[str, object]]:
    clean = candles.copy()
    clean["time"] = pd.to_datetime(clean["time"], errors="coerce")
    clean = clean.dropna(subset=["time"]).tail(500)
    asian = clean[clean["time"].dt.hour.isin([20, 21, 22, 23, 0])]

    if asian.empty:
        return []

    return [
        _level("Asia High", "buy_side", asian["high"].max(), "session"),
        _level("Asia Low", "sell_side", asian["low"].min(), "session"),
    ]


def _equal_level_rows(
    equal_levels: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    rows = []

    for level in equal_levels.get("equal_highs", [])[-3:]:
        rows.append(_level("Equal Highs", "buy_side", level["price"], "equal_highs"))

    for level in equal_levels.get("equal_lows", [])[-3:]:
        rows.append(_level("Equal Lows", "sell_side", level["price"], "equal_lows"))

    return rows


def _round_number_levels(current_price: float) -> list[dict[str, object]]:
    step = _round_step(current_price)
    lower = math.floor(current_price / step) * step
    upper = lower + step

    return [
        _level("Round Number", "sell_side", lower, "round_number"),
        _level("Round Number", "buy_side", upper, "round_number"),
    ]


def _round_step(price: float) -> float:
    if price > 10000:
        return 500
    if price > 1000:
        return 50
    if price > 50:
        return 0.5
    if price > 5:
        return 0.05
    return 0.005


def _nearest_levels(
    levels: list[dict[str, object]],
    current_price: float,
    side: str,
) -> list[dict[str, object]]:
    if side == "buy_side":
        candidates = [level for level in levels if level["price"] > current_price]
    else:
        candidates = [level for level in levels if level["price"] < current_price]

    unique = {}
    for level in candidates:
        key = (level["label"], round(float(level["price"]), 6))
        unique[key] = level

    sorted_levels = sorted(
        unique.values(),
        key=lambda level: abs(float(level["price"]) - current_price),
    )
    return sorted_levels[:4]


def _current_target(
    bias: str,
    buy_side: list[dict[str, object]],
    sell_side: list[dict[str, object]],
    current_price: float,
) -> dict[str, object]:
    if bias == "LONG" and buy_side:
        return {**buy_side[0], "role": "current_target"}
    if bias == "SHORT" and sell_side:
        return {**sell_side[0], "role": "current_target"}

    combined = buy_side + sell_side
    if not combined:
        return {}

    return {
        **min(combined, key=lambda level: abs(float(level["price"]) - current_price)),
        "role": "current_target",
    }


def _level(label: str, side: str, price, source: str) -> dict[str, object]:
    return {
        "label": label,
        "side": side,
        "price": round(float(price), 6),
        "source": source,
    }
