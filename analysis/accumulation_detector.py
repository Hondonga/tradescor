"""Measurable, no-look-ahead accumulation-range detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AccumulationConfig:
    minimum_bars: int = 12
    maximum_bars: int = 72
    minimum_width_atr: float = 0.8
    maximum_width_atr: float = 3.0
    minimum_overlap_ratio: float = 0.50
    maximum_directional_efficiency: float = 0.35
    boundary_tolerance_atr: float = 0.18
    minimum_boundary_tests: int = 2


def detect_accumulation(candles: pd.DataFrame, config: AccumulationConfig | None = None) -> dict[str, object] | None:
    """Return the latest range locked before subsequent boundary activity."""
    cfg = config or AccumulationConfig()
    if candles is None or len(candles) < cfg.minimum_bars + 1: return None
    # AMD is a current-cycle classifier. Bound the search window so live API and
    # replay cost stays constant as history grows, while retaining enough bars
    # for the full configured range plus its subsequent boundary sequence.
    search_bars = cfg.maximum_bars * 2 + 12
    rows = candles.tail(search_bars).reset_index(drop=True); atr_series = _atr(rows); candidates = []
    highs = rows["high"].to_numpy(dtype=float); lows = rows["low"].to_numpy(dtype=float)
    opens = rows["open"].to_numpy(dtype=float); closes = rows["close"].to_numpy(dtype=float)
    atr_values = atr_series.to_numpy(dtype=float)
    first_end = max(cfg.minimum_bars - 1, len(rows) - cfg.maximum_bars - 12)
    for end in range(first_end, len(rows) - 1):
        maximum_length = min(cfg.maximum_bars, end + 1)
        lengths = list(range(cfg.minimum_bars, maximum_length + 1, 4))
        if maximum_length not in lengths: lengths.append(maximum_length)
        for length in lengths:
            start = end - length + 1; atr = float(atr_values[end])
            if atr <= 0: continue
            window_highs, window_lows = highs[start:end + 1], lows[start:end + 1]
            window_closes = closes[start:end + 1]
            high, low = float(window_highs.max()), float(window_lows.min()); width_atr = (high - low) / atr
            overlap = float(np.mean(np.minimum(window_highs[1:], window_highs[:-1]) > np.maximum(window_lows[1:], window_lows[:-1])))
            path = float(np.abs(np.diff(window_closes)).sum()); efficiency = abs(float(window_closes[-1] - opens[start])) / path if path > 0 else 0.0
            tolerance = atr * cfg.boundary_tolerance_atr
            high_tests = _array_tests(window_highs >= high - tolerance); low_tests = _array_tests(window_lows <= low + tolerance)
            valid = cfg.minimum_width_atr <= width_atr <= cfg.maximum_width_atr and overlap >= cfg.minimum_overlap_ratio and efficiency <= cfg.maximum_directional_efficiency and high_tests >= cfg.minimum_boundary_tests and low_tests >= cfg.minimum_boundary_tests
            if not valid: continue
            quality = min(25, round(7 + overlap * 6 + (1 - efficiency) * 5 + min(4, high_tests + low_tests) + max(0, 3 - abs(width_atr - 1.8))))
            candidates.append({"detected": True, "range_low": low, "range_high": high, "start_time": rows.iloc[start]["time"].isoformat(), "end_time": rows.iloc[end]["time"].isoformat(), "start_index": start, "end_index": end, "duration_bars": length, "width": high - low, "width_atr": width_atr, "overlap_ratio": overlap, "directional_efficiency": efficiency, "boundary_tests_high": high_tests, "boundary_tests_low": low_tests, "quality_score": quality, "atr": atr, "locked": True})
            break
    if not candidates: return None
    # Prefer a range with an observable event after it. Once returned, its
    # boundaries and end index are immutable for the rest of this analysis.
    with_event = [row for row in candidates if _has_boundary_event(rows.iloc[row["end_index"] + 1:], row)]
    pool = with_event or candidates
    return max(pool, key=lambda row: (row["end_index"], row["quality_score"]))


def _atr(rows: pd.DataFrame) -> pd.Series:
    high, low, close = rows["high"].astype(float), rows["low"].astype(float), rows["close"].astype(float); previous = close.shift(1)
    return pd.concat([high - low, (high - previous).abs(), (low - previous).abs()], axis=1).max(axis=1).rolling(14, min_periods=3).mean().bfill()
def _overlap(rows: pd.DataFrame) -> float:
    count = sum(min(float(rows.iloc[i]["high"]), float(rows.iloc[i-1]["high"])) > max(float(rows.iloc[i]["low"]), float(rows.iloc[i-1]["low"])) for i in range(1, len(rows)))
    return count / max(1, len(rows)-1)
def _efficiency(rows: pd.DataFrame) -> float:
    close = rows["close"].astype(float); path = float(close.diff().abs().sum()); return abs(float(close.iloc[-1] - rows.iloc[0]["open"])) / path if path > 0 else 0.0
def _independent_tests(mask: pd.Series) -> int:
    count, previous = 0, False
    for value in mask.tolist():
        if value and not previous: count += 1
        previous = bool(value)
    return count
def _array_tests(mask: np.ndarray) -> int:
    return int(mask[0]) + int(np.sum(mask[1:] & ~mask[:-1])) if len(mask) else 0
def _has_boundary_event(rows: pd.DataFrame, accumulation: dict[str, object]) -> bool:
    if rows.empty: return False
    tolerance = float(accumulation["atr"]) * .05
    return bool((rows["high"].astype(float) > float(accumulation["range_high"]) + tolerance).any() or (rows["low"].astype(float) < float(accumulation["range_low"]) - tolerance).any())
