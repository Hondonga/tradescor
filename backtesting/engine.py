"""Backtesting engine — walks candles one-by-one without look-ahead bias.

At candle index N the strategy only receives candles[0 : N+1].
Higher-timeframe slicing, news timestamps, and target levels all respect the
same boundary — nothing from candle N+1 onwards is visible.

Two modes are supported:
  fast     — signal checked every 15 candles, 80-candle window  (~9 s)
  accurate — legacy strategy signal checked every 5 candles, 150-candle window;
             the top-down M5 pipeline has its own every-close replay.

In BOTH modes every candle is evaluated for active-trade management (SL / TP /
fill).  The mode only affects how often new signals are scanned.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
import pandas as pd

from analysis import build_shared_analysis
from strategies import STRATEGY_LABELS
from strategies import breakout_retest, ict_2022, supply_demand, universal_structure

from .simulator import TradeSimulator
from .trade_log import TradeRecord

# Minimum candles required before any strategy call is made
MIN_WARMUP = 35

SUPPORTED_STRATEGIES: dict[str, object] = {
    "universal_structure": universal_structure,
    "ict_2022": ict_2022,
    "supply_demand": supply_demand,
    "breakout_retest": breakout_retest,
}


# ---------------------------------------------------------------------------
# Mode configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BacktestConfig:
    mode: str
    strategy_step: int    # check for new signals every N candles (watching state)
    analysis_window: int  # candles passed to strategy per call (fixed cost)
    max_bars: int         # API cap applied before the engine runs
    time_limit: float     # hard abort if a single strategy exceeds this (seconds)
    approximate: bool     # whether results may miss setups


FAST_CONFIG = BacktestConfig(
    mode="fast",
    strategy_step=15,
    analysis_window=80,
    max_bars=500,
    time_limit=55,
    approximate=True,
)

ACCURATE_CONFIG = BacktestConfig(
    mode="accurate",
    strategy_step=5,
    analysis_window=150,
    max_bars=300,
    time_limit=110,
    approximate=False,
)


def get_config(mode: str) -> BacktestConfig:
    """Return the BacktestConfig for the requested mode; defaults to fast."""
    if mode == "accurate":
        return ACCURATE_CONFIG
    return FAST_CONFIG


# ---------------------------------------------------------------------------
# Per-strategy diagnostics
# ---------------------------------------------------------------------------

@dataclass
class StrategyDiagnostics:
    """Execution proof and funnel data collected during a single strategy walk."""
    candles_checked: int = 0
    evaluation_count: int = 0          # how many times strategy.analyze() was called
    state_counts: dict = field(default_factory=dict)  # state → count
    potential_setups: int = 0          # ENTRY_READY + valid levels → pending trade opened
    invalid_levels: int = 0            # ENTRY_READY but levels rejected by validator
    trades_opened: int = 0             # pending trades that were actually filled
    missed_entries: int = 0            # pending trades that expired (price never returned)
    invalidated_before_entry: int = 0  # pending cancelled because SL was breached first
    trades_closed: int = 0             # SL + TP1 + TP2 exits
    open_at_end: int = 0               # still active when data ran out
    errors: int = 0

    def record_state(self, state: str) -> None:
        self.state_counts[state] = self.state_counts.get(state, 0) + 1

    @property
    def top_state(self) -> str:
        if not self.state_counts:
            return "NO_SETUP"
        return max(self.state_counts, key=lambda s: self.state_counts[s])


def infer_main_reason(diag: StrategyDiagnostics, strategy_key: str) -> str:
    """Derive a plain-language explanation for the strategy's backtest outcome."""
    if diag.evaluation_count == 0:
        return "Insufficient candles for evaluation."

    top = diag.top_state

    # ---- 0 valid setups ever reached -----------------------------------
    if diag.potential_setups == 0:

        if strategy_key == "breakout_retest":
            if "WAITING_FOR_BREAKOUT" in top:
                return "A range was identified but no decisive breakout occurred."
            if "FAILED_BREAKOUT" in top:
                return "Breakouts were detected but all reversed before a retest could form."
            if "RETEST" in top or "BREAKOUT" in top:
                return "Breakout detected but no clean retest confirmed entry."
            return "No stable range with a confirmed breakout and retest."

        if strategy_key == "supply_demand":
            if "NO_SETUP" in top or "NO_TRADE" in top:
                return "No active supply or demand zone was close enough to current price."
            if "REACTION" in top:
                return "Zones identified, but no clean reaction or confirmation occurred."
            if "CONFIRMATION" in top or "ENTRY" in top:
                return "Zone and reaction found, but confirmation break was not sufficient."
            return "No valid supply or demand zone with entry confirmation."

        if strategy_key == "ict_2022":
            if "KILL_ZONE" in top:
                return "Kill zone was not active during the candles evaluated."
            if "LIQUIDITY" in top:
                return "No liquidity sweep detected before a structure shift."
            if "MSS" in top or "CHOCH" in top:
                return "Liquidity sweep found but no market structure shift (CHoCH/MSS)."
            if "FVG" in top or "OTE" in top:
                return "Structure shift found but no FVG or OTE alignment."
            return "No full ICT sequence (kill zone → sweep → MSS → FVG/OTE) completed."

        # universal_structure (and fallback)
        if "NO_SETUP" in top or "NO_TRADE" in top:
            return "No clear trend or pullback structure to anchor a setup."
        if "CONFIRMATION" in top:
            return "Structure found but price did not break the confirmation level."
        if "ENTRY" in top:
            return "Setup confirmed but price never returned to the entry zone."
        return "No valid confirmation and entry-zone return."

    # ---- At least 1 valid signal was generated -------------------------
    if diag.trades_opened == 0:
        parts = [f"{diag.potential_setups} signal(s) generated"]
        if diag.missed_entries:
            parts.append(f"price never returned to the entry zone ({diag.missed_entries} pending expired)")
        if diag.invalidated_before_entry:
            parts.append(f"{diag.invalidated_before_entry} invalidated before fill")
        return ", ".join(parts) + "."

    if diag.trades_closed == 0 and diag.open_at_end > 0:
        return (
            f"{diag.trades_opened} trade(s) active at end of data — "
            "more candles needed to see outcome."
        )

    return (
        f"{diag.potential_setups} signal(s) → "
        f"{diag.trades_opened} filled → "
        f"{diag.trades_closed} closed"
        + (f", {diag.open_at_end} open at end" if diag.open_at_end else "")
        + "."
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_backtest(
    candles: pd.DataFrame,
    strategy_keys: list[str],
    *,
    symbol: str = "EUR/USD",
    timeframe: str = "M5",
    risk_per_trade: float = 1.0,
    starting_balance: float = 10_000.0,
    mode: str = "fast",
) -> dict[str, object]:
    """Run all requested strategies over a shared historical candle set.

    Parameters
    ----------
    candles:
        Full OHLCV DataFrame with columns time, open, high, low, close.
    strategy_keys:
        Strategy identifiers from SUPPORTED_STRATEGIES.
    mode:
        "fast" (default) or "accurate".

    Returns a dict with keys: trades, warnings, metadata, n_candles,
    symbol, timeframe.
    """
    config = get_config(mode)
    candles = candles.reset_index(drop=True)
    n_candles = len(candles)
    warnings: list[str] = []
    total_evaluated = 0

    if n_candles < MIN_WARMUP + 10:
        warnings.append(
            f"Backtest sample size is very small ({n_candles} candles). "
            "Results will not be statistically meaningful."
        )

    # Mode-specific upfront warning
    if config.approximate:
        warnings.append(
            f"Fast Mode checks signals every {config.strategy_step} candles. "
            "Some setups between evaluation points may be missed. "
            "Use Accurate Mode before trusting results."
        )
    else:
        warnings.append(
            f"Accurate Mode checks signals every {config.strategy_step} candles "
            f"with a {config.analysis_window}-candle analysis window. "
            "This is more thorough but may take longer."
        )

    results: dict[str, list[TradeRecord]] = {}
    diagnostics: dict[str, StrategyDiagnostics] = {}
    total_evaluated = 0

    for key in strategy_keys:
        if key not in SUPPORTED_STRATEGIES:
            warnings.append(f"Unknown strategy '{key}' — skipped.")
            continue

        trade_list, timed_out, diag = _run_strategy(
            candles,
            key,
            symbol=symbol,
            timeframe=timeframe,
            config=config,
        )
        results[key] = trade_list
        diagnostics[key] = diag
        total_evaluated += diag.evaluation_count

        if timed_out:
            name = STRATEGY_LABELS.get(key, key)
            warnings.append(
                f"{name}: backtest hit the {config.time_limit}s time limit. "
                "Results are partial — try fewer bars."
            )

    if not results:
        warnings.append("No valid strategies were run.")

    metadata: dict[str, object] = {
        "mode": config.mode,
        "strategy_step": config.strategy_step,
        "analysis_window": config.analysis_window,
        "evaluated_candles": total_evaluated,
        "total_candles": n_candles,
        "approximate": config.approximate,
    }

    return {
        "trades": results,
        "diagnostics": diagnostics,
        "warnings": warnings,
        "metadata": metadata,
        "n_candles": n_candles,
        "symbol": symbol,
        "timeframe": timeframe,
    }


# ---------------------------------------------------------------------------
# Per-strategy walker
# ---------------------------------------------------------------------------

def _run_strategy(
    candles: pd.DataFrame,
    strategy_key: str,
    *,
    symbol: str,
    timeframe: str,
    config: BacktestConfig,
) -> tuple[list[TradeRecord], bool, StrategyDiagnostics]:
    """Walk candles forward for one strategy.

    Trade management (SL / TP / fill) runs on EVERY candle regardless of mode.
    Signal scanning is throttled by config.strategy_step.

    Returns (trade_records, timed_out, diagnostics).
    """
    module = SUPPORTED_STRATEGIES[strategy_key]
    strategy_name = STRATEGY_LABELS.get(strategy_key, strategy_key)
    simulator = TradeSimulator(strategy_name)
    trades: list[TradeRecord] = []
    diag = StrategyDiagnostics(candles_checked=len(candles))
    n_candles = len(candles)
    timed_out = False
    t_start = time.time()

    for n in range(MIN_WARMUP, n_candles):
        candle = candles.iloc[n]

        # ACTIVE trade: check SL / TP on every candle — never skipped by mode
        if simulator.state == "ACTIVE":
            record = simulator.check_active_trade(candle, n)
            if record is not None:
                trades.append(record)
                if record.result == "OPEN_AT_END":
                    diag.open_at_end += 1
                else:
                    diag.trades_closed += 1
            continue

        # PENDING_ENTRY: check fill / invalidation on every candle — never skipped
        if simulator.state == "PENDING_ENTRY":
            result = simulator.check_pending_entry(candle, n)
            if result == "FILLED":
                diag.trades_opened += 1
            elif result == "EXPIRED":
                diag.missed_entries += 1
            elif result is None and simulator.state == "WATCHING":
                # cancelled due to SL breach before fill
                diag.invalidated_before_entry += 1
            continue

        # Time-limit guard (watching state only — won't interrupt active trades)
        if time.time() - t_start > config.time_limit:
            timed_out = True
            break

        # Signal throttle: only evaluate new signals every strategy_step candles
        if n > MIN_WARMUP and (n - MIN_WARMUP) % config.strategy_step != 0:
            continue

        # Fixed-size window keeps per-call cost O(analysis_window) not O(n)
        window_start = max(0, n - config.analysis_window + 1)
        visible = candles.iloc[window_start : n + 1].copy()
        diag.evaluation_count += 1

        try:
            shared = build_shared_analysis(visible)
            strategy_result, _ = _call_strategy(
                module, strategy_key, visible, shared, symbol, timeframe
            )
        except Exception:  # noqa: BLE001
            diag.errors += 1
            continue

        state = str(strategy_result.get("state", "NO_SETUP"))
        levels_mode = str(strategy_result.get("levels_mode", "hidden"))
        levels = strategy_result.get("levels") or {}
        diag.record_state(state)

        if state != "ENTRY_READY" or levels_mode != "final":
            continue

        entry_zone = levels.get("entry_zone")
        stop_loss = levels.get("stop_loss")
        tp1 = levels.get("tp1")
        tp2 = levels.get("tp2")
        bias = str(strategy_result.get("bias", "Neutral"))

        if not _valid_levels(entry_zone, stop_loss, tp1):
            diag.invalid_levels += 1
            continue

        diag.potential_setups += 1
        simulator.open_pending(
            signal_candle_idx=n,
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            direction=bias,
            entry_zone=entry_zone,
            stop_loss=float(stop_loss),  # type: ignore[arg-type]
            tp1=float(tp1),  # type: ignore[arg-type]
            tp2=float(tp2) if tp2 is not None else None,
            reason=str(strategy_result.get("market_story", ""))[:140],
        )

    # Close any trade still open when data runs out
    last_candle = candles.iloc[-1]
    record = simulator.force_close(last_candle, n_candles - 1)
    if record is not None:
        trades.append(record)
        diag.open_at_end += 1

    return trades, timed_out, diag


# ---------------------------------------------------------------------------
# Strategy dispatch
# ---------------------------------------------------------------------------

def _call_strategy(
    module: object,
    key: str,
    candles: pd.DataFrame,
    shared: dict[str, object],
    symbol: str,
    timeframe: str,
) -> tuple[dict[str, object], object]:
    """Call the correct strategy function with the right signature."""
    if key == "universal_structure":
        return universal_structure.analyze(candles, shared)  # type: ignore[union-attr]

    if key == "ict_2022":
        return ict_2022.analyze(  # type: ignore[union-attr]
            candles,
            shared,
            symbol=symbol,
            timeframe=timeframe,
        )

    if key == "supply_demand":
        return supply_demand.analyze(  # type: ignore[union-attr]
            candles,
            shared,
            symbol=symbol,
            timeframe=timeframe,
        )

    if key == "breakout_retest":
        return breakout_retest.analyze(  # type: ignore[union-attr]
            candles,
            shared,
            symbol=symbol,
            timeframe=timeframe,
        )

    raise ValueError(f"No dispatch for strategy key '{key}'")


# ---------------------------------------------------------------------------
# Level validation
# ---------------------------------------------------------------------------

def _valid_levels(
    entry_zone: object,
    stop_loss: object,
    tp1: object,
) -> bool:
    """Return True only when levels are numeric and directionally coherent."""
    try:
        sl = float(stop_loss)  # type: ignore[arg-type]
        t1 = float(tp1)  # type: ignore[arg-type]

        if isinstance(entry_zone, dict):
            top = float(entry_zone.get("top") or entry_zone.get("high") or 0)
            bottom = float(entry_zone.get("bottom") or entry_zone.get("low") or 0)
            entry_mid = (top + bottom) / 2.0
        elif entry_zone is not None:
            entry_mid = float(entry_zone)
        else:
            return False

        if sl <= 0 or t1 <= 0 or entry_mid <= 0:
            return False

        # TP and SL must be on opposite sides of entry
        if (t1 > entry_mid) == (sl > entry_mid):
            return False

        # Minimum 1.0R reward
        risk = abs(entry_mid - sl)
        if risk <= 0:
            return False
        return abs(t1 - entry_mid) / risk >= 1.0

    except (TypeError, ValueError, ZeroDivisionError):
        return False
