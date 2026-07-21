"""ICT Change of Character / Market Structure Shift confirmation."""

from __future__ import annotations

import pandas as pd

from scanner.market_structure import detect_mss


def detect_choch(
    candles: pd.DataFrame,
    swings: dict[str, list[dict[str, object]]],
    sweep: dict[str, object] | None,
) -> dict[str, object]:
    """Confirm CHoCH after a sweep and expose the level while waiting."""
    if not sweep:
        return {"confirmed": False, "status": "waiting", "level": None, "direction": None, "event": {}}

    event = detect_mss(candles, swings, sweep, lookback=80)
    level = float(event["level"]) if event else _trigger_level(swings, sweep)
    return {
        "confirmed": event is not None,
        "status": "confirmed" if event else "waiting",
        "level": round(level, 6) if level is not None else None,
        "direction": sweep.get("direction"),
        "event": event or {},
        "label": "CHoCH / MSS",
    }


def _trigger_level(
    swings: dict[str, list[dict[str, object]]],
    sweep: dict[str, object],
) -> float | None:
    sweep_index = int(sweep.get("index", 0))
    key = "highs" if sweep.get("direction") == "bullish" else "lows"
    previous = [swing for swing in swings.get(key, []) if int(swing.get("index", -1)) < sweep_index]
    return float(previous[-1]["price"]) if previous else None
