"""Top-down multi-timeframe context helpers."""

from __future__ import annotations

import pandas as pd

from scanner.fvg import detect_fvgs, nearest_active_fvg


TIMEFRAME_LABELS = {
    "W1": "Weekly",
    "D1": "Daily",
    "H4": "4H",
    "H1": "1H",
    "M15": "M15",
    "M5": "M5",
    "M1": "M1",
}

MACRO_TIMEFRAMES = ["W1", "D1", "H4", "H1", "M15", "M5"]

TIMEFRAME_CHAIN = {
    "M1": ["W1", "D1", "H4", "H1", "M15", "M5", "M1"],
    "M5": ["W1", "D1", "H4", "H1", "M15", "M5"],
    "M15": ["W1", "D1", "H4", "H1", "M15"],
    "H1": ["W1", "D1", "H4", "H1"],
    "H4": ["W1", "D1", "H4"],
    "D1": ["W1", "D1"],
    "W1": ["W1"],
}


def required_timeframes(current_timeframe: str) -> list[str]:
    """Return the top-down chain needed for the selected chart."""
    if current_timeframe in MACRO_TIMEFRAMES:
        return MACRO_TIMEFRAMES

    return [*MACRO_TIMEFRAMES, current_timeframe]


def analyze_top_down(
    candles_by_timeframe: dict[str, pd.DataFrame],
    current_timeframe: str,
) -> dict[str, object]:
    """Build a compact top-down bias table from fetched candles."""
    rows = []

    for timeframe in required_timeframes(current_timeframe):
        candles = candles_by_timeframe.get(timeframe)
        rows.append(_analyze_timeframe(timeframe, candles))

    return {
        "rows": rows,
        "overall_alignment": _overall_alignment(rows),
        "current_timeframe": current_timeframe,
    }


def _analyze_timeframe(
    timeframe: str,
    candles: pd.DataFrame | None,
) -> dict[str, object]:
    label = TIMEFRAME_LABELS.get(timeframe, timeframe)

    if candles is None or candles.empty or len(candles) < 30:
        return {
            "timeframe": timeframe,
            "label": label,
            "bias": "Neutral",
            "state": "Not enough data",
            "score": 0,
            "active_fvg": {},
        }

    clean = candles.copy().sort_values("time").reset_index(drop=True)
    close = clean["close"].astype(float)
    ema_fast = close.ewm(span=20, adjust=False).mean()
    ema_slow = close.ewm(span=50, adjust=False).mean()
    current = float(close.iloc[-1])
    latest_fast = float(ema_fast.iloc[-1])
    latest_slow = float(ema_slow.iloc[-1])

    if current > latest_fast > latest_slow:
        bias = "Bullish"
        score = 1
    elif current < latest_fast < latest_slow:
        bias = "Bearish"
        score = -1
    elif current > latest_slow and latest_fast > latest_slow:
        bias = "Pullback"
        score = 0
    elif current < latest_slow and latest_fast < latest_slow:
        bias = "Pullback"
        score = 0
    else:
        bias = "Waiting"
        score = 0

    fvgs = detect_fvgs(clean)
    direction = "bullish" if score > 0 else "bearish" if score < 0 else None
    active_fvg = nearest_active_fvg(clean, fvgs, direction, lookback=min(160, len(clean)))
    state = _state_text(bias, current, latest_fast, active_fvg)

    return {
        "timeframe": timeframe,
        "label": label,
        "bias": bias,
        "state": state,
        "score": score,
        "active_fvg": active_fvg or {},
        "last_close": round(current, 6),
    }


def _state_text(
    bias: str,
    current: float,
    ema_fast: float,
    active_fvg: dict[str, object] | None,
) -> str:
    if active_fvg:
        return f"Inside {active_fvg['type'].title()} FVG"
    if bias == "Bullish" and current < ema_fast:
        return "Bullish pullback"
    if bias == "Bearish" and current > ema_fast:
        return "Bearish pullback"
    return bias


def _overall_alignment(rows: list[dict[str, object]]) -> str:
    scores = [int(row.get("score", 0)) for row in rows]

    if not scores:
        return "Neutral"

    total = sum(scores)
    if total >= max(2, len(scores) - 1):
        return "Strong Bullish"
    if total > 0:
        return "Bullish"
    if total <= -max(2, len(scores) - 1):
        return "Strong Bearish"
    if total < 0:
        return "Bearish"
    return "Neutral"
