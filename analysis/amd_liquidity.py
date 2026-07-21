"""Liquidity immediately surrounding a locked accumulation range."""

from __future__ import annotations

import pandas as pd


def identify_amd_liquidity(candles: pd.DataFrame, accumulation: dict[str, object]) -> list[dict[str, object]]:
    end = int(accumulation["end_index"]); rows = candles.reset_index(drop=True); window = rows.iloc[int(accumulation["start_index"]):end + 1]; subsequent = rows.iloc[end + 1:]
    result = []
    for side, price, kind in (("buy_side", float(accumulation["range_high"]), "accumulation_highs"), ("sell_side", float(accumulation["range_low"]), "accumulation_lows")):
        swept_rows = subsequent.loc[subsequent["high"].astype(float) > price] if side == "buy_side" else subsequent.loc[subsequent["low"].astype(float) < price]
        formed_at = window.loc[window["high"].astype(float).idxmax(), "time"] if side == "buy_side" else window.loc[window["low"].astype(float).idxmin(), "time"]
        tests = accumulation["boundary_tests_high"] if side == "buy_side" else accumulation["boundary_tests_low"]
        result.append({"price": price, "side": side, "type": kind, "formed_at": formed_at.isoformat(), "swept": not swept_rows.empty, "swept_at": swept_rows.iloc[0]["time"].isoformat() if not swept_rows.empty else None, "quality": min(15, 5 + int(tests) * 3)})
    return result
