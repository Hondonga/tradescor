"""Institutional order block detection helpers."""

from __future__ import annotations

import pandas as pd


def detect_order_blocks(
    candles: pd.DataFrame,
    swings: dict[str, list[dict[str, object]]],
    htf_bias: str = "NEUTRAL",
    htf_fvg: dict[str, object] | None = None,
    lookback: int = 140,
) -> dict[str, object]:
    """Detect active order blocks and return the nearest current zone.

    This is intentionally conservative: an order block must be the last
    opposite-color candle before a close through a prior swing level.
    """
    if candles.empty or len(candles) < 20:
        return {"nearest": {}, "active": [], "mitigated_count": 0, "breaker_count": 0}

    clean = candles.sort_values("time").reset_index(drop=True)
    start_index = max(5, len(clean) - lookback)
    candidates: list[dict[str, object]] = []

    for index in range(start_index, len(clean)):
        candle = clean.iloc[index]
        swing_high = _last_swing_before(swings["highs"], index)
        swing_low = _last_swing_before(swings["lows"], index)

        if swing_high and float(candle["close"]) > float(swing_high["price"]):
            source_index = _last_opposite_candle(clean, index, "bearish")
            if source_index is not None:
                candidates.append(_block(clean, source_index, index, "bullish", "BOS", swing_high["price"]))

        if swing_low and float(candle["close"]) < float(swing_low["price"]):
            source_index = _last_opposite_candle(clean, index, "bullish")
            if source_index is not None:
                candidates.append(_block(clean, source_index, index, "bearish", "BOS", swing_low["price"]))

    tracked = [_track_block(clean, block, htf_fvg) for block in candidates]
    active = [block for block in tracked if block["status"] != "mitigated"]
    active = [block for block in active if _aligns_with_bias(block, htf_bias)]
    nearest = _nearest_block(clean, active)

    return {
        "nearest": nearest or {},
        "active": active[-6:],
        "mitigated_count": len([block for block in tracked if block["status"] == "mitigated"]),
        "breaker_count": len([block for block in tracked if block["status"] == "breaker"]),
    }


def _last_swing_before(
    swings: list[dict[str, object]],
    index: int,
) -> dict[str, object] | None:
    previous = [swing for swing in swings if int(swing["index"]) < index]
    return previous[-1] if previous else None


def _last_opposite_candle(
    candles: pd.DataFrame,
    break_index: int,
    color: str,
) -> int | None:
    start = max(0, break_index - 12)

    for index in range(break_index - 1, start - 1, -1):
        candle = candles.iloc[index]
        is_bearish = float(candle["close"]) < float(candle["open"])
        is_bullish = float(candle["close"]) > float(candle["open"])

        if color == "bearish" and is_bearish:
            return index
        if color == "bullish" and is_bullish:
            return index

    return None


def _block(
    candles: pd.DataFrame,
    source_index: int,
    break_index: int,
    direction: str,
    break_type: str,
    break_level,
) -> dict[str, object]:
    source = candles.iloc[source_index]

    return {
        "type": f"{direction}_order_block",
        "direction": direction,
        "status": "active",
        "source_index": source_index,
        "break_index": break_index,
        "start_time": str(source["time"]),
        "confirmed_time": str(candles.iloc[break_index]["time"]),
        "top_price": float(source["high"]),
        "bottom_price": float(source["low"]),
        "break_type": break_type,
        "break_level": float(break_level),
        "label": f"{direction.title()} Order Block",
    }


def _track_block(
    candles: pd.DataFrame,
    block: dict[str, object],
    htf_fvg: dict[str, object] | None,
) -> dict[str, object]:
    tracked = block.copy()
    top = float(tracked["top_price"])
    bottom = float(tracked["bottom_price"])

    for index in range(int(tracked["break_index"]) + 1, len(candles)):
        candle = candles.iloc[index]

        if tracked["direction"] == "bullish":
            if float(candle["close"]) < bottom:
                tracked["status"] = "breaker"
                tracked["type"] = "bearish_breaker_block"
                tracked["direction"] = "bearish"
                tracked["label"] = "Bearish Breaker Block"
            if float(candle["low"]) <= bottom:
                tracked["status"] = "mitigated"
                tracked["mitigated_time"] = str(candle["time"])
                break

        elif tracked["direction"] == "bearish":
            if float(candle["close"]) > top:
                tracked["status"] = "breaker"
                tracked["type"] = "bullish_breaker_block"
                tracked["direction"] = "bullish"
                tracked["label"] = "Bullish Breaker Block"
            if float(candle["high"]) >= top:
                tracked["status"] = "mitigated"
                tracked["mitigated_time"] = str(candle["time"])
                break

    if htf_fvg and _zones_overlap(tracked, htf_fvg):
        tracked["label"] = "High Confluence Zone"
        tracked["confluence"] = "order_block_plus_htf_fvg"

    return tracked


def _aligns_with_bias(block: dict[str, object], htf_bias: str) -> bool:
    if htf_bias == "LONG":
        return block["direction"] == "bullish"
    if htf_bias == "SHORT":
        return block["direction"] == "bearish"
    return True


def _nearest_block(
    candles: pd.DataFrame,
    blocks: list[dict[str, object]],
) -> dict[str, object] | None:
    if not blocks:
        return None

    current = float(candles.iloc[-1]["close"])

    def distance(block: dict[str, object]) -> tuple[float, int]:
        midpoint = (float(block["top_price"]) + float(block["bottom_price"])) / 2
        return abs(current - midpoint), -int(block["break_index"])

    return sorted(blocks, key=distance)[0]


def _zones_overlap(
    first: dict[str, object],
    second: dict[str, object],
) -> bool:
    first_top = float(first["top_price"])
    first_bottom = float(first["bottom_price"])
    second_top = float(second["top_price"])
    second_bottom = float(second["bottom_price"])
    return max(first_bottom, second_bottom) <= min(first_top, second_top)
