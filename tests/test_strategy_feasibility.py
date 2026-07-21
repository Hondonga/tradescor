"""Feasibility-harness tests: it must REJECT noise and only a real edge may pass.

The positive control injects a genuine directional edge into synthetic data and
requires the verdict to reach ELIGIBLE_FOR_FORMAL_WALK_FORWARD (the ceiling).
The null control has no edge and must be rejected. Together they prove the
classifier is not biased toward either verdict.
"""
import numpy as np
import pandas as pd

from validation.strategy_feasibility import ExperimentSpec, run_feasibility
from validation.strategy_feasibility.event_matcher import Event


def _series(symbol, days, edge, seed):
    """Build M5-like OHLC. If edge, every 25th bar starts a reliable up-move."""
    rng = np.random.default_rng(seed)
    n = days * 288
    price = 1000.0
    rows = []
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    drift = np.zeros(n)
    signal_bars = set(range(60, n - 30, 25))
    if edge:
        for b in signal_bars:
            drift[b + 1: b + 12] += 1.2   # strong, reliable post-signal up-move
    for i in range(n):
        step = rng.normal(0, 0.5) + drift[i]
        o = price
        c = o + step
        hi = max(o, c) + abs(rng.normal(0, 0.2))
        lo = min(o, c) - abs(rng.normal(0, 0.2))
        rows.append({"time": t0 + pd.Timedelta(minutes=5 * i), "open": o,
                     "high": hi, "low": lo, "close": c})
        price = c
    return pd.DataFrame(rows), sorted(signal_bars)


def _make(symbol, days, edge, seed):
    df, sigs = _series(symbol, days, edge, seed)
    def gen(sym, frame):
        atr = (frame.high - frame.low).rolling(14).mean()
        evs = []
        for b in sigs:
            if b >= len(frame) or not (atr[b] > 0):
                continue
            evs.append(Event(symbol=sym, event_id=f"{sym}:{b}", entry_index=b,
                             entry_price=float(frame.close[b]), atr=float(atr[b]),
                             native_direction=1, day=str(frame.time[b].date())))
        return evs
    return df, gen


def _spec(symbols):
    return ExperimentSpec(experiment_id="selftest", strategy_id="s", strategy_version="v",
                          engine_version="e", symbols=symbols,
                          start_time="2026-01-01", end_time="2026-01-20", hypothesis="h",
                          parameters=dict(risk_atr=1.0, rr=1.5, outcome_window=12),
                          min_resolved_trades=200, min_independent_periods=8)


def test_positive_control_reaches_eligible():
    data = {s: _make(s, 16, edge=True, seed=i) for i, s in enumerate(["A", "B", "C"])}
    loader = lambda s: data[s][0]
    gens = {s: data[s][1] for s in data}
    generator = lambda s, df: gens[s](s, df)
    rep = run_feasibility(_spec(list(data)), loader, generator, freeze=False)
    assert rep["outcome"] == "ELIGIBLE_FOR_FORMAL_WALK_FORWARD", rep["reasons"]
    assert rep["promotion"] != "BLOCKED"


def test_null_control_is_rejected():
    data = {s: _make(s, 16, edge=False, seed=100 + i) for i, s in enumerate(["A", "B", "C"])}
    loader = lambda s: data[s][0]
    gens = {s: data[s][1] for s in data}
    generator = lambda s, df: gens[s](s, df)
    rep = run_feasibility(_spec(list(data)), loader, generator, freeze=False)
    assert rep["outcome"].startswith("REJECTED"), rep["outcome"]
    assert rep["promotion"] == "BLOCKED"


def test_ceiling_is_walk_forward_never_production():
    # The harness must never emit a "production ready" verdict.
    from validation.strategy_feasibility.feasibility_report import Outcome
    values = {o.value for o in Outcome}
    assert "PRODUCTION_READY" not in values
    assert "ELIGIBLE_FOR_FORMAL_WALK_FORWARD" in values
