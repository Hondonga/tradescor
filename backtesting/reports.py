"""Generate frontend-ready backtest reports."""

from __future__ import annotations

from strategies import STRATEGY_LABELS

from .comparison import compare_strategies
from .engine import StrategyDiagnostics, infer_main_reason
from .trade_log import TradeRecord

# Canonical order for run_status display
ALL_STRATEGY_KEYS = [
    "universal_structure",
    "supply_demand",
    "breakout_retest",
    "ict_2022",
]

STANDARD_WARNINGS = [
    "Historical results do not guarantee future performance.",
    "This is analysis software, not financial advice.",
]

ICT_SESSION_WARNING = (
    "ICT 2022 strategy is session-dependent and may produce fewer signals "
    "outside London and New York kill zones."
)

ICT_NOT_TESTED_NOTE = (
    "ICT 2022 was not tested. OTE, FVG, MSS/CHoCH, liquidity sweep, "
    "and kill zone logic were not included in this backtest."
)


def build_report(
    trades_by_strategy: dict[str, list[TradeRecord]],
    *,
    n_candles: int,
    symbol: str,
    timeframe: str,
    risk_per_trade: float,
    starting_balance: float,
    backtest_warnings: list[str],
    metadata: dict[str, object] | None = None,
    diagnostics_by_strategy: dict[str, StrategyDiagnostics] | None = None,
    selected_strategies: list[str] | None = None,
) -> dict[str, object]:
    """Produce the complete backtest report returned to the frontend."""
    meta = metadata or {}
    diag_map = diagnostics_by_strategy or {}
    selected = selected_strategies or list(trades_by_strategy.keys())

    comparison = compare_strategies(trades_by_strategy)

    run_status = _build_run_status(
        selected_keys=selected,
        diagnostics_by_key=diag_map,
        trades_by_strategy=trades_by_strategy,
        n_candles=n_candles,
    )

    # Merge main_reason from run_status into each ranked strategy_result
    reason_map = {s["key"]: s.get("main_reason", "") for s in run_status}
    for item in comparison["ranked"]:
        item["main_reason"] = reason_map.get(str(item.get("strategy_key", "")), "")

    equity_curves = {
        key: _equity_curve(trades, risk_per_trade, starting_balance)
        for key, trades in trades_by_strategy.items()
    }

    trade_logs = {
        key: [t.to_dict() for t in trades]
        for key, trades in trades_by_strategy.items()
    }

    warnings: list[str] = list(backtest_warnings)

    # Small-sample warnings per strategy
    for m in comparison["ranked"]:
        key = str(m.get("strategy_key", ""))
        total = int(m.get("total_trades", 0))
        name = str(m.get("strategy", STRATEGY_LABELS.get(key, key)))
        if total < 20:
            warnings.append(
                f"Backtest sample size for {name} is small ({total} trades). "
                "Increase bar count or date range for more reliable results."
            )

    if "ict_2022" in trades_by_strategy:
        warnings.append(ICT_SESSION_WARNING)
    elif "ict_2022" not in selected:
        warnings.append(ICT_NOT_TESTED_NOTE)

    warnings.extend(STANDARD_WARNINGS)

    return {
        "summary": {
            "symbol": symbol,
            "timeframe": timeframe,
            "n_candles": n_candles,
            "risk_per_trade": risk_per_trade,
            "starting_balance": starting_balance,
            "strategies_tested": selected,
        },
        "metadata": meta,
        "run_status": run_status,
        "strategy_results": comparison["ranked"],
        "comparison": {
            "best_strategy": comparison["best_strategy"],
            "summary": comparison["summary"],
            "result_status": comparison.get("result_status", "no_data"),
        },
        "equity_curves": equity_curves,
        "trade_logs": trade_logs,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Run status builder
# ---------------------------------------------------------------------------

def _build_run_status(
    selected_keys: list[str],
    diagnostics_by_key: dict[str, StrategyDiagnostics],
    trades_by_strategy: dict[str, list[TradeRecord]],
    n_candles: int,
) -> list[dict[str, object]]:
    """Build per-strategy run status for all 4 strategies."""
    status_list = []

    for key in ALL_STRATEGY_KEYS:
        name = STRATEGY_LABELS.get(key, key)

        if key in selected_keys:
            diag = diagnostics_by_key.get(key, StrategyDiagnostics(candles_checked=n_candles))
            all_trades = trades_by_strategy.get(key, [])
            trades_found = len([t for t in all_trades if t.result != "OPEN_AT_END"])
            main_reason = infer_main_reason(diag, key)

            ict_note = None
            if key == "ict_2022":
                ict_note = _build_ict_note(diag)

            status_list.append({
                "strategy": name,
                "key": key,
                "selected": True,
                "ran": True,
                "candles_checked": diag.candles_checked,
                "evaluation_count": diag.evaluation_count,
                "trades_found": trades_found,
                "main_reason": main_reason,
                "error": None,
                "ict_note": ict_note,
                "diagnostics": _diag_to_dict(diag, key),
            })
        else:
            ict_note = ICT_NOT_TESTED_NOTE if key == "ict_2022" else None
            not_tested_reason = "Not tested — checkbox was off."

            status_list.append({
                "strategy": name,
                "key": key,
                "selected": False,
                "ran": False,
                "candles_checked": 0,
                "evaluation_count": 0,
                "trades_found": 0,
                "main_reason": not_tested_reason,
                "error": None,
                "ict_note": ict_note,
                "diagnostics": None,
            })

    return status_list


def _diag_to_dict(diag: StrategyDiagnostics, key: str) -> dict[str, object]:
    base: dict[str, object] = {
        "evaluation_count": diag.evaluation_count,
        "potential_setups": diag.potential_setups,
        "invalid_levels": diag.invalid_levels,
        "trades_opened": diag.trades_opened,
        "missed_entries": diag.missed_entries,
        "invalidated_before_entry": diag.invalidated_before_entry,
        "trades_closed": diag.trades_closed,
        "open_at_end": diag.open_at_end,
        "errors": diag.errors,
        "state_counts": dict(diag.state_counts),
    }

    # Strategy-specific extras with correct terminology
    if key == "breakout_retest":
        sc = diag.state_counts
        base["ranges_found"] = sum(
            sc.get(s, 0)
            for s in ("WAITING_FOR_RETEST", "RETEST_ACTIVE", "ENTRY_READY", "FAILED_BREAKOUT")
        )
        base["retests_found"] = sc.get("RETEST_ACTIVE", 0) + diag.potential_setups
        base["failed_breakouts"] = sc.get("FAILED_BREAKOUT", 0)

    elif key == "supply_demand":
        sc = diag.state_counts
        base["zones_found"] = sum(
            sc.get(s, 0)
            for s in ("ZONE_IDENTIFIED", "WAITING_FOR_REACTION", "REACTION_CONFIRMED",
                      "WAITING_FOR_CONFIRMATION", "WAITING_FOR_ENTRY", "ENTRY_READY")
        )

    elif key == "ict_2022":
        sc = diag.state_counts
        base["kill_zone_seen"] = sc.get("WAITING_FOR_LIQUIDITY_SWEEP", 0) > 0 or diag.potential_setups > 0
        base["liquidity_sweep_seen"] = sc.get("WAITING_FOR_MSS", 0) > 0 or diag.potential_setups > 0
        base["mss_seen"] = sc.get("WAITING_FOR_FVG", 0) > 0 or diag.potential_setups > 0
        base["fvg_seen"] = sc.get("WAITING_FOR_OTE", 0) > 0 or diag.potential_setups > 0
        base["ote_seen"] = diag.potential_setups > 0

    return base


def _build_ict_note(diag: StrategyDiagnostics) -> str:
    """Summarise which ICT steps were and were not reached."""
    sc = diag.state_counts
    reached = []
    missed = []

    steps = [
        ("WAITING_FOR_LIQUIDITY_SWEEP", "Kill zone"),
        ("WAITING_FOR_MSS", "Liquidity sweep"),
        ("WAITING_FOR_FVG", "MSS / CHoCH"),
        ("WAITING_FOR_OTE", "FVG"),
    ]
    for state, label in steps:
        if sc.get(state, 0) > 0 or diag.potential_setups > 0:
            reached.append(label)
        else:
            missed.append(label)

    if diag.potential_setups > 0:
        return f"Full ICT sequence reached OTE {diag.potential_setups} time(s)."

    if missed:
        return f"ICT sequence stalled at: {', '.join(missed)}."
    return "ICT sequence steps detected — no full entry sequence completed."


# ---------------------------------------------------------------------------
# Equity curve
# ---------------------------------------------------------------------------

def _equity_curve(
    trades: list[TradeRecord],
    risk_per_trade: float,
    starting_balance: float,
) -> list[dict[str, object]]:
    """Convert a trade list into balance-over-time data points."""
    curve: list[dict[str, object]] = [
        {"trade": 0, "balance": round(starting_balance, 2), "time": None}
    ]
    balance = starting_balance
    risk_amount = starting_balance * (risk_per_trade / 100.0)

    trade_num = 0
    for trade in trades:
        if trade.result == "OPEN_AT_END":
            continue  # ignore incomplete trades

        trade_num += 1
        pnl = trade.rr_result * risk_amount
        balance = round(balance + pnl, 2)

        curve.append(
            {
                "trade": trade_num,
                "balance": balance,
                "rr": trade.rr_result,
                "result": trade.result,
                "time": trade.exit_time,
                "direction": trade.direction,
            }
        )

    return curve

