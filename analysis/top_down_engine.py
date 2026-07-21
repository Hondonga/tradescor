"""Deterministic D1/H4/H1 context and M15 setup-location analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd


EXECUTION_TIMEFRAME = "M5"
STACK = ("D1", "H4", "H1", "M15", "M5")
TIMEFRAME_DELTA = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
}


def analyze_top_down_market(
    *,
    symbol: str,
    candles_by_timeframe: dict[str, pd.DataFrame],
    analysis_timestamp: object,
) -> dict[str, object]:
    """Return one top-down scenario without allowing M15 to override D1/H4."""
    boundary = _utc_timestamp(analysis_timestamp)
    frames: dict[str, dict[str, object]] = {}
    completed: dict[str, pd.DataFrame] = {}
    for timeframe in STACK:
        source = candles_by_timeframe.get(timeframe, pd.DataFrame())
        clean = completed_candles(source, timeframe, boundary)
        completed[timeframe] = clean
        frames[timeframe] = _timeframe_view(timeframe, clean)

    d1 = str(frames["D1"]["bias"])
    h4 = str(frames["H4"]["bias"])
    h1 = str(frames["H1"]["bias"])
    m15_bias = str(frames["M15"]["bias"])
    regime, regime_confidence, regime_reason = _regime(d1, h4)
    primary = regime if regime in {"bullish", "bearish"} else "neutral"
    setup_direction = _direction(m15_bias)
    alignment_state, alignment_message = _alignment(primary, h1, setup_direction)

    m15_setup = _m15_setup(completed["M15"], primary, setup_direction, alignment_state)
    frames["M15"].update(
        {
            "setup_type": m15_setup.get("setup_type", ""),
            "zone": m15_setup.get("zone"),
            "context": m15_setup.get("context", "No valid setup location"),
        }
    )
    execution_bias = _direction(str(frames["M5"]["bias"]))
    frames["M5"]["trigger_state"] = "waiting"

    if m15_setup.get("direction") not in {_trade_word(primary), "neutral"}:
        m15_setup["countertrend"] = True
        m15_setup["enabled"] = False

    primary_scenario = _primary_scenario(primary, m15_setup, alignment_state)
    alternative = _alternative_scenario(primary, m15_setup, frames)
    score = _top_down_score(regime, h1, m15_setup)
    rows = [
        {
            "timeframe": timeframe,
            "bias": str(frames[timeframe]["bias"]).title(),
            "state": frames[timeframe].get("context") or frames[timeframe].get("structure", ""),
            "score": 1 if frames[timeframe]["bias"] == "bullish" else -1 if frames[timeframe]["bias"] == "bearish" else 0,
        }
        for timeframe in STACK
    ]
    return {
        "symbol": symbol,
        "execution_timeframe": EXECUTION_TIMEFRAME,
        "regime": {"value": regime, "confidence": regime_confidence, "reason": regime_reason},
        "timeframes": frames,
        "alignment": {
            "state": alignment_state,
            "primary_direction": _trade_word(primary),
            "setup_direction": m15_setup.get("direction", "neutral"),
            "execution_direction": execution_bias,
            "message": alignment_message,
        },
        "m15_setup": m15_setup,
        "primary_scenario": primary_scenario,
        "alternative_scenario": alternative,
        "score_before_execution": score,
        # Compatibility with existing read-only consumers.
        "rows": rows,
        "overall_alignment": regime.title() if regime != "transition" else "Neutral",
        "current_timeframe": "M5",
    }


def completed_candles(candles: pd.DataFrame, timeframe: str, boundary: object) -> pd.DataFrame:
    """Slice candles at boundary and exclude a candle that has not closed yet."""
    if candles is None or candles.empty:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close"])
    clean = candles.copy()
    clean["time"] = pd.to_datetime(clean["time"], utc=True, errors="coerce")
    clean = clean.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time")
    cutoff = _utc_timestamp(boundary)
    duration = TIMEFRAME_DELTA.get(timeframe, timedelta(0))
    return clean.loc[clean["time"] + duration <= cutoff].reset_index(drop=True)


def _timeframe_view(timeframe: str, candles: pd.DataFrame) -> dict[str, object]:
    if len(candles) < 20:
        return {"bias": "neutral", "structure": "insufficient_data", "location": "", "last_closed_candle_time": None}
    close = candles["close"].astype(float)
    fast = close.ewm(span=20, adjust=False).mean()
    slow = close.ewm(span=50, adjust=False).mean()
    recent = candles.tail(min(20, len(candles)))
    half = max(3, len(recent) // 2)
    older, newer = recent.iloc[:half], recent.iloc[half:]
    higher_structure = float(newer["high"].max()) > float(older["high"].max()) and float(newer["low"].min()) > float(older["low"].min())
    lower_structure = float(newer["high"].max()) < float(older["high"].max()) and float(newer["low"].min()) < float(older["low"].min())
    last = float(close.iloc[-1])
    bullish = last > float(fast.iloc[-1]) > float(slow.iloc[-1]) and higher_structure
    bearish = last < float(fast.iloc[-1]) < float(slow.iloc[-1]) and lower_structure
    if bullish:
        bias, structure = "bullish", "higher_highs_higher_lows"
    elif bearish:
        bias, structure = "bearish", "lower_highs_lower_lows"
    else:
        slope = float(fast.iloc[-1] - fast.iloc[max(0, len(fast) - 5)])
        bias = "bullish" if last > float(slow.iloc[-1]) and slope > 0 else "bearish" if last < float(slow.iloc[-1]) and slope < 0 else "neutral"
        structure = "overlapping_transition" if bias != "neutral" else "range"
    unswept_highs, unswept_lows = _unswept_swings(candles)
    return {
        "bias": bias,
        "structure": structure,
        "location": "above_mean" if last > float(fast.iloc[-1]) else "below_mean",
        "last_closed_candle_time": candles.iloc[-1]["time"].isoformat(),
        "last_close": last,
        "recent_high": float(recent["high"].max()),
        "recent_low": float(recent["low"].min()),
        "unswept_highs": unswept_highs,
        "unswept_lows": unswept_lows,
    }


def _regime(d1: str, h4: str) -> tuple[str, str, str]:
    if d1 == h4 == "bullish":
        return "bullish", "high", "D1 and H4 retain bullish directional structure."
    if d1 == h4 == "bearish":
        return "bearish", "high", "D1 and H4 retain bearish directional structure."
    if "neutral" in {d1, h4} and d1 == h4:
        return "range", "low", "D1 and H4 do not show sustained displacement."
    if d1 != h4 and "neutral" not in {d1, h4}:
        return "transition", "low", "D1 and H4 conflict; no primary direction is forced."
    direction = h4 if h4 != "neutral" else d1
    return direction if direction in {"bullish", "bearish"} else "range", "medium", "Only one higher timeframe has dependable structure."


def _alignment(primary: str, h1: str, m15: str) -> tuple[str, str]:
    if primary == "neutral":
        return "mixed", "D1 and H4 do not provide a dependable primary direction."
    primary_trade = _trade_word(primary)
    if h1 == primary and m15 in {primary_trade, "neutral"}:
        return "aligned", f"{primary.title()} higher-timeframe and intraday structure are aligned."
    if h1 in {primary, "neutral"} and m15 not in {primary_trade, "neutral"}:
        return "pullback", f"M15 opposition is classified as a {primary}-market pullback."
    if h1 not in {primary, "neutral"} and m15 == _trade_word(h1):
        return "pullback", f"H1 and M15 oppose the {primary} regime; readiness is reduced until stabilization."
    return "mixed", "Intraday timeframes materially conflict with the higher-timeframe regime."


def _m15_setup(candles: pd.DataFrame, primary: str, observed_direction: str, alignment: str) -> dict[str, object]:
    if primary not in {"bullish", "bearish"} or len(candles) < 10:
        return _empty_setup()
    recent = candles.tail(min(24, len(candles))).copy()
    direction = _trade_word(primary)
    if direction == "buy":
        origin = recent.loc[recent["low"].astype(float).idxmin()]
        low, high = float(origin["low"]), max(float(origin["open"]), float(origin["close"]))
        target = float(recent["high"].max())
        setup_type = "demand_retracement"
    else:
        origin = recent.loc[recent["high"].astype(float).idxmax()]
        low, high = min(float(origin["open"]), float(origin["close"])), float(origin["high"])
        target = float(recent["low"].min())
        setup_type = "supply_retracement"
    current = float(recent.iloc[-1]["close"])
    in_zone = low <= current <= high
    status = "in_zone" if in_zone else "watching"
    context = f"{primary.title()}-market pullback" if alignment == "pullback" else f"{primary.title()} continuation"
    return {
        "direction": direction,
        "setup_type": setup_type,
        "zone_low": low,
        "zone_high": high,
        "zone": {"low": low, "high": high, "type": "demand" if direction == "buy" else "supply", "label": "Demand Zone" if direction == "buy" else "Supply Zone", "start_time": origin["time"].timestamp()},
        "confirmation_hint": f"Require a completed M5 {'bullish' if direction == 'buy' else 'bearish'} structure trigger.",
        "invalidation_context": "M5 structure beyond the M15 area.",
        "target_context": {"timeframe": "M15", "price": target, "reason": "Nearest M15 structure objective"},
        "status": status,
        "context": context,
        "observed_m15_direction": observed_direction,
        "countertrend": False,
        "enabled": True,
    }


def _empty_setup() -> dict[str, object]:
    return {"direction": "neutral", "setup_type": "", "zone_low": None, "zone_high": None, "zone": None, "confirmation_hint": "", "invalidation_context": "", "target_context": {}, "status": "watching", "context": "No valid setup location", "countertrend": False, "enabled": False}


def _primary_scenario(primary: str, setup: dict[str, object], alignment: str) -> dict[str, object]:
    direction = _trade_word(primary)
    if direction == "neutral" or not setup.get("enabled"):
        return {"direction": "neutral", "status": "no_trade_direction", "message": "No primary trade direction is available."}
    return {"direction": direction, "status": "forming", "setup_type": setup.get("setup_type"), "zone": setup.get("zone"), "message": f"Use the M15 {setup.get('context', 'setup').lower()} and require M5 confirmation.", "alignment": alignment}


def _alternative_scenario(primary: str, setup: dict[str, object], frames: dict[str, dict[str, object]]) -> dict[str, object] | None:
    if primary not in {"bullish", "bearish"}:
        return None
    opposite = "sell" if primary == "bullish" else "buy"
    return {"direction": opposite, "enabled": False, "label": "Countertrend setup — disabled", "requirement": f"Requires an H1 reversal and completed M5 {opposite} confirmation."}


def _top_down_score(regime: str, h1: str, setup: dict[str, object]) -> int:
    score = 20 if regime in {"bullish", "bearish"} else 5
    if h1 == regime:
        score += 20
    elif h1 != "neutral":
        score += 8
    if setup.get("enabled") and setup.get("zone"):
        score += 20
    return min(score, 60)


def _direction(value: str) -> str:
    text = str(value).lower()
    return "buy" if text == "bullish" else "sell" if text == "bearish" else "neutral"


def _trade_word(value: str) -> str:
    return _direction(value)


def _utc_timestamp(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value if value is not None else datetime.now(timezone.utc))
    return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")


def _unswept_swings(candles: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Return confirmed pivots whose price was not traded through later."""
    highs: list[dict[str, object]] = []
    lows: list[dict[str, object]] = []
    values = candles.reset_index(drop=True)
    for index in range(2, len(values) - 2):
        row = values.iloc[index]
        left, right = values.iloc[index - 2:index], values.iloc[index + 1:index + 3]
        high = float(row["high"]); low = float(row["low"])
        future = values.iloc[index + 1:]
        if high > float(left["high"].max()) and high >= float(right["high"].max()) and not bool((future["high"].astype(float) > high).any()):
            highs.append({"price": high, "time": row["time"].isoformat(), "swept": False})
        if low < float(left["low"].min()) and low <= float(right["low"].min()) and not bool((future["low"].astype(float) < low).any()):
            lows.append({"price": low, "time": row["time"].isoformat(), "swept": False})
    return highs[-5:], lows[-5:]
