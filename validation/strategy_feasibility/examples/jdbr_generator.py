"""Example setup generator: JDBR (Jump Displacement Break-Retest).

Reference implementation of the plug-in interface. Emits one Event per
qualifying jump + retest confirmation. Used to self-test the harness; JDBR is
RESEARCH_ONLY and this generator must never feed a live path.
"""
from __future__ import annotations

import glob
import json

import numpy as np
import pandas as pd

from validation.strategy_feasibility.event_matcher import Event

PARAMS = dict(min_jump_atr=2.0, retest_band_atr=0.15, lookback=20,
              retrace_window=24, confirm_window=12, swing_strength=3)


def load_jump_m5(symbol: str, matrix_dir: str = "data/smc_matrix") -> pd.DataFrame:
    files = [p for p in sorted(glob.glob(f"{matrix_dir}/v2-{symbol}-*.json"))
             if not p.endswith(".meta.json")]
    rows = []
    for f in files:
        rows += json.load(open(f))
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    return (df.set_index("time").resample("5min", label="left", closed="left")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna().reset_index())


def _atr(df, n=14):
    h, l, c = df.high, df.low, df.close.shift()
    tr = pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def jdbr_setups(symbol: str, df: pd.DataFrame) -> list[Event]:
    df = df.copy()
    df["atr"] = _atr(df)
    events: list[Event] = []
    i = PARAMS["lookback"] + 15
    n = len(df)
    while i < n - 2:
        a = df.atr[i]
        if not (a > 0):
            i += 1; continue
        body = df.close[i] - df.open[i]
        rng = df.high[i] - df.low[i]
        if abs(body) < PARAMS["min_jump_atr"] * a or rng < PARAMS["min_jump_atr"] * a:
            i += 1; continue
        jdir = 1 if body > 0 else -1
        base_low = min(df.low[i - 1], df.open[i])
        base_high = max(df.high[i - 1], df.open[i])
        band = PARAMS["retest_band_atr"] * a
        entered = None
        for k in range(i + 1, min(i + 1 + PARAMS["retrace_window"], n - 1)):
            zlo, zhi = base_low - band, base_high + band
            tag = df.low[k] <= zhi if jdir > 0 else df.high[k] >= zlo
            if tag:
                for m in range(k, min(k + PARAMS["confirm_window"], n - 1)):
                    confirmed = (df.close[m] > df.open[m]) if jdir > 0 else (df.close[m] < df.open[m])
                    if confirmed:
                        entered = m; break
                break
        if entered is None:
            i += 1; continue
        m = entered
        atr_m = df.atr[m] if df.atr[m] > 0 else a
        events.append(Event(symbol=symbol, event_id=f"{symbol}:{i}", entry_index=m,
                            entry_price=float(df.close[m]), atr=float(atr_m),
                            native_direction=jdir, day=str(df.time[m].date()),
                            structural_episode=f"{symbol}:jump:{i}"))
        i = m + 1
    return events
