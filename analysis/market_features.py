"""Common timestamped market features consumed by every strategy expert."""

from __future__ import annotations

import pandas as pd


def calculate_market_features(bundle: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {"calculation_time": bundle["analysis_time_utc"], "timeframes": {}}
    for timeframe, frame in bundle["timeframes"].items():
        candles = frame["candles"]
        result["timeframes"][timeframe] = _frame_features(candles, timeframe, bundle["analysis_time_utc"])
    return result


def feature(value: object, timestamp: str, timeframe: str, valid: bool = True, reason: str | None = None) -> dict[str, object]:
    return {"value": value if valid else None, "calculation_timestamp": timestamp, "source_timeframe": timeframe, "valid": valid, "reason": reason}


def _frame_features(candles: pd.DataFrame, timeframe: str, timestamp: str) -> dict[str, object]:
    if candles is None or len(candles) < 20:
        unavailable = feature(None, timestamp, timeframe, False, "Insufficient completed candles.")
        return {name: unavailable.copy() for name in ("structure_direction", "trend_persistence", "directional_efficiency", "atr", "atr_percentile", "volatility_regime", "range", "compression", "displacement", "swings", "liquidity", "fvg")}
    high, low, close, opened = (candles[name].astype(float) for name in ("high", "low", "close", "open"))
    previous = close.shift(1)
    tr = pd.concat([high - low, (high - previous).abs(), (low - previous).abs()], axis=1).max(axis=1)
    atr_series = tr.rolling(14, min_periods=5).mean(); atr = float(atr_series.iloc[-1])
    atr_history = atr_series.dropna().tail(100); atr_percentile = float((atr_history <= atr).mean() * 100)
    net = abs(float(close.iloc[-1] - close.iloc[-20])); path = float(close.diff().abs().tail(19).sum()); efficiency = net / path if path > 0 else 0.0
    slope = float(close.tail(20).diff().mean()); direction = "bullish" if slope > 0 and close.iloc[-1] > close.tail(20).median() else "bearish" if slope < 0 and close.iloc[-1] < close.tail(20).median() else "neutral"
    recent = candles.tail(30)
    reference = candles.iloc[-31:-1] if len(candles) >= 31 else candles.iloc[:-1]
    range_high, range_low = float(reference["high"].max()), float(reference["low"].min()); width = range_high - range_low
    overlap = _overlap_ratio(recent); compression = width / max(atr, 1e-12) <= 5 and overlap >= 0.55 and float(tr.tail(5).mean()) < float(tr.tail(20).mean())
    last_body = abs(float(close.iloc[-1] - opened.iloc[-1])); displacement = last_body >= atr * 1.2
    swings = _swings(candles)
    equal_highs = _equal_levels(swings["highs"], atr * 0.1); equal_lows = _equal_levels(swings["lows"], atr * 0.1)
    fvg = _active_fvgs(candles, atr)
    boundary_tests = int(((reference["high"] >= range_high - atr * .15) | (reference["low"] <= range_low + atr * .15)).sum())
    position = (float(close.iloc[-1]) - range_low) / max(width, 1e-12)
    return {
        "structure_direction": feature(direction, timestamp, timeframe), "trend_slope": feature(slope / max(atr, 1e-12), timestamp, timeframe),
        "trend_persistence": feature(float((close.diff().tail(20) * (1 if direction == "bullish" else -1)).gt(0).mean()), timestamp, timeframe), "directional_efficiency": feature(efficiency, timestamp, timeframe),
        "atr": feature(atr, timestamp, timeframe), "atr_percentile": feature(atr_percentile, timestamp, timeframe), "volatility_regime": feature("high" if atr_percentile >= 80 else "low" if atr_percentile <= 20 else "normal", timestamp, timeframe),
        "realized_range": feature(float(tr.tail(20).mean()), timestamp, timeframe), "abnormal_candle": feature(bool(float(tr.iloc[-1]) >= atr * 2.5), timestamp, timeframe),
        "range": feature({"high": range_high, "low": range_low, "duration": len(recent), "boundary_tests": boundary_tests, "position": position, "width_atr": width / max(atr, 1e-12)}, timestamp, timeframe),
        "compression": feature({"active": compression, "overlap_ratio": overlap, "width_atr": width / max(atr, 1e-12)}, timestamp, timeframe), "displacement": feature({"active": displacement, "body_atr": last_body / max(atr, 1e-12), "direction": "bullish" if close.iloc[-1] > opened.iloc[-1] else "bearish", "event_time": candles.iloc[-1]["time"].isoformat() if displacement else None}, timestamp, timeframe),
        "swings": feature(swings, timestamp, timeframe), "liquidity": feature({"equal_highs": equal_highs, "equal_lows": equal_lows, "unswept_highs": [row for row in swings["highs"] if not row["swept"]], "unswept_lows": [row for row in swings["lows"] if not row["swept"]]}, timestamp, timeframe),
        "fvg": feature(fvg, timestamp, timeframe),
    }


def _overlap_ratio(candles: pd.DataFrame) -> float:
    overlaps = 0
    for index in range(1, len(candles)):
        overlaps += int(min(float(candles.iloc[index]["high"]), float(candles.iloc[index - 1]["high"])) > max(float(candles.iloc[index]["low"]), float(candles.iloc[index - 1]["low"])))
    return overlaps / max(1, len(candles) - 1)


def _swings(candles: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
    highs, lows = [], []
    rows = candles.reset_index(drop=True)
    for index in range(2, len(rows) - 2):
        row = rows.iloc[index]; future = rows.iloc[index + 1:]
        if float(row["high"]) > float(rows.iloc[index - 2:index]["high"].max()) and float(row["high"]) >= float(rows.iloc[index + 1:index + 3]["high"].max()):
            swept_rows = future.loc[future["high"].astype(float) > float(row["high"])]
            highs.append({"price": float(row["high"]), "time": row["time"].isoformat(), "swept": not swept_rows.empty, "sweep_time": swept_rows.iloc[0]["time"].isoformat() if not swept_rows.empty else None})
        if float(row["low"]) < float(rows.iloc[index - 2:index]["low"].min()) and float(row["low"]) <= float(rows.iloc[index + 1:index + 3]["low"].min()):
            swept_rows = future.loc[future["low"].astype(float) < float(row["low"])]
            lows.append({"price": float(row["low"]), "time": row["time"].isoformat(), "swept": not swept_rows.empty, "sweep_time": swept_rows.iloc[0]["time"].isoformat() if not swept_rows.empty else None})
    return {"highs": highs[-20:], "lows": lows[-20:]}


def _equal_levels(levels: list[dict[str, object]], tolerance: float) -> list[dict[str, object]]:
    return [levels[index] for index in range(1, len(levels)) if abs(float(levels[index]["price"]) - float(levels[index - 1]["price"])) <= tolerance]


def _active_fvgs(candles: pd.DataFrame, atr: float) -> list[dict[str, object]]:
    result = []
    rows = candles.reset_index(drop=True)
    for index in range(2, len(rows)):
        first, third = rows.iloc[index - 2], rows.iloc[index]
        if float(third["low"]) > float(first["high"]): low, high, direction = float(first["high"]), float(third["low"]), "bullish"
        elif float(third["high"]) < float(first["low"]): low, high, direction = float(third["high"]), float(first["low"]), "bearish"
        else: continue
        if high - low < atr * .05: continue
        subsequent = rows.iloc[index + 1:]
        filled = bool((subsequent["low"] <= low).any()) if direction == "bullish" else bool((subsequent["high"] >= high).any())
        if not filled: result.append({"low": low, "high": high, "direction": direction, "formation_time": third["time"].isoformat(), "mitigated": False})
    return result[-3:]
