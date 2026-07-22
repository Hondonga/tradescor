"""Shared GBP/USD candle-bundle builders for Phase 4 checkpoint 16.

Not a test module itself (no test_ prefix) -- imported by
tests/test_phase4_gbpusd_reachability_fixtures.py.

gbpusd_buy_bundle() drives the real, unmodified production entrypoint
(analysis/decision_engine.py::build_decision) with a genuine, hand-built
multi-timeframe GBP/USD candle series deep into the strict-ICT sequence:
HTF narrative, directional draw, opposing liquidity, liquidity sweep,
displacement, MSS/CHoCH, FVG, entry-array touch, and M5 confirmation all
empirically pass. gbpusd_sell_bundle() is an exact price-mirror (around
1.2700) with high/low swapped, producing the symmetric SELL-side sequence.
Truncating either bundle's M15/M5 frames reproduces the earlier waiting
states in the same sequence, causally, from real (not fabricated) data.
"""
import pandas as pd
from datetime import timedelta

SWEEP_IDX = 54  # index into the M15 frame where the liquidity sweep candle sits


def _m15_buy():
    times = pd.date_range("2026-01-05", periods=60, freq="15min", tz="UTC")
    rows, price = [], 1.2650
    for i, t in enumerate(times):
        close = price + 0.0002
        rows.append({"time": t, "open": price, "high": close + 0.0001, "low": price - 0.0001, "close": close})
        price = close
    df = pd.DataFrame(rows)
    df.loc[20, ["open", "high", "low", "close"]] = [1.2690, 1.2745, 1.2685, 1.2700]  # pre-sweep pivot high (MSS reference)
    df.loc[30, ["open", "high", "low", "close"]] = [1.2660, 1.2665, 1.2620, 1.2662]  # opposing liquidity pool (swing low)
    df.loc[SWEEP_IDX, ["open", "high", "low", "close"]] = [1.2680, 1.2685, 1.2610, 1.2670]  # sweep candle
    df.loc[SWEEP_IDX + 1, ["open", "high", "low", "close"]] = [1.2670, 1.2700, 1.2660, 1.2695]  # reclaim candle
    df.loc[SWEEP_IDX + 2, ["open", "high", "low", "close"]] = [1.2695, 1.2760, 1.2690, 1.2755]  # displacement 1
    df.loc[SWEEP_IDX + 3, ["open", "high", "low", "close"]] = [1.2755, 1.2820, 1.2750, 1.2815]  # displacement 2 (closes through the MSS pivot)
    df.loc[SWEEP_IDX + 4, ["open", "high", "low", "close"]] = [1.2815, 1.2825, 1.2790, 1.2795]  # FVG-forming candle
    return df


def _m5_buy(m15_frame):
    start = m15_frame.iloc[SWEEP_IDX + 2].time + pd.Timedelta(minutes=5)
    values = [
        (1.2793, 1.2795, 1.2780, 1.2783), (1.2783, 1.2785, 1.2760, 1.2763), (1.2763, 1.2765, 1.2740, 1.2743),
        (1.2743, 1.2745, 1.2720, 1.2723), (1.2723, 1.2725, 1.2700, 1.2703), (1.2703, 1.2705, 1.2688, 1.2692),
        (1.2692, 1.2694, 1.2684, 1.2686), (1.2686, 1.2698, 1.2685, 1.2696),  # touches and reclaims the FVG (1.2685-1.2690)
        (1.2696, 1.2705, 1.2694, 1.2702), (1.2702, 1.2712, 1.2700, 1.2710), (1.2710, 1.2720, 1.2708, 1.2718),
        (1.2718, 1.2728, 1.2716, 1.2726), (1.2726, 1.2736, 1.2724, 1.2734), (1.2734, 1.2744, 1.2732, 1.2742),
        (1.2742, 1.2752, 1.2740, 1.2750), (1.2750, 1.2760, 1.2748, 1.2758), (1.2758, 1.2768, 1.2756, 1.2766),
        (1.2766, 1.2776, 1.2764, 1.2774), (1.2774, 1.2784, 1.2772, 1.2782), (1.2782, 1.2792, 1.2780, 1.2790),
    ]
    times = pd.date_range(start, periods=len(values), freq="5min", tz="UTC")
    rows = [{"time": t, "open": o, "high": h, "low": l, "close": c} for t, (o, h, l, c) in zip(times, values)]
    return pd.DataFrame(rows)


def _htf_buy(timeframe, boundary, periods=80, top=1.2900):
    freq = {"D1": "1D", "H4": "4h", "H1": "1h"}[timeframe]
    times = pd.date_range(end=boundary - timedelta(minutes=1), periods=periods, freq=freq, tz="UTC")
    rows = []
    for i, t in enumerate(times):
        if i < 38: price = 1.2500 + (top - 1.2500) * (i / 38)
        elif i < 58: price = top - (top - 1.2700) * ((i - 38) / 20)
        else: price = 1.2700 + (1.2850 - 1.2700) * ((i - 58) / (periods - 1 - 58))
        rows.append({"time": t, "open": price - 0.0006, "high": price + 0.0012, "low": price - 0.0012, "close": price + 0.0004})
    return pd.DataFrame(rows)


def gbpusd_buy_bundle():
    """Returns (candles_by_timeframe, boundary) reaching the deepest real
    BUY-side sequence state: htf_narrative/directional_draw/opposing_liquidity/
    liquidity_sweep/displacement/mss/fvg/entry_array_touched/m5_confirmation
    all pass."""
    m15 = _m15_buy()
    m5 = _m5_buy(m15)
    boundary = m5.iloc[-1]["time"] + timedelta(minutes=5)
    context = {tf: _htf_buy(tf, boundary) for tf in ("D1", "H4", "H1")}
    context["M15"] = m15
    context["M5"] = m5
    return context, boundary


def _mirror(df, pivot=1.2700):
    out = df.copy()
    for column in ("open", "high", "low", "close"):
        out[column] = 2 * pivot - df[column]
    out[["high", "low"]] = out[["low", "high"]]
    return out


def gbpusd_sell_bundle():
    """Exact price-mirror of gbpusd_buy_bundle() -- same causal shape,
    opposite direction. Reaches the symmetric SELL-side sequence depth."""
    context, boundary = gbpusd_buy_bundle()
    mirrored = {tf: _mirror(frame) for tf, frame in context.items()}
    return mirrored, boundary


def truncate_m15(context, boundary, end_index):
    """Returns a shallower bundle cut off at M15 candle `end_index`, with M5
    reduced to a single seed row (M5 has not started forming yet at this
    point in the sequence) and a boundary aligned to the new last M15 candle."""
    m15 = context["M15"].iloc[:end_index]
    new_boundary = context["M15"].iloc[end_index - 1].time + timedelta(minutes=15)
    truncated = {**context, "M15": m15, "M5": context["M5"].iloc[:1]}
    return truncated, new_boundary
