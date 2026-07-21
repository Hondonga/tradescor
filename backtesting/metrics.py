"""Performance metrics calculator for backtested trade logs."""

from __future__ import annotations

from .trade_log import TradeRecord


# ---------------------------------------------------------------------------
# Sample quality labels
# ---------------------------------------------------------------------------

def sample_quality_label(total: int) -> str:
    """Return a human-readable quality label for a trade sample size."""
    if total == 0:
        return "No Sample"
    if total < 10:
        return "Insufficient Data"
    if total < 20:
        return "Weak Sample"
    if total < 50:
        return "Usable Sample"
    return "Stronger Sample"


def calculate_metrics(
    trades: list[TradeRecord],
    strategy_name: str,
) -> dict[str, object]:
    """Return comprehensive performance metrics for a completed trade list."""
    closed = [t for t in trades if t.result != "OPEN_AT_END"]

    if not closed:
        return _empty_metrics(strategy_name)

    wins = [t for t in closed if t.is_win]
    losses = [t for t in closed if t.is_loss]
    total = len(closed)

    win_rate = round(len(wins) / total * 100, 1)

    gross_profit = sum(t.rr_result for t in wins)
    gross_loss = abs(sum(t.rr_result for t in losses))
    pf_infinite = gross_loss == 0 and gross_profit > 0
    profit_factor = (
        round(gross_profit / gross_loss, 3)
        if gross_loss > 0
        else (999.0 if gross_profit > 0 else 0.0)
    )

    avg_win_rr = round(sum(t.rr_result for t in wins) / len(wins), 3) if wins else 0.0
    avg_loss_rr = round(abs(sum(t.rr_result for t in losses)) / len(losses), 3) if losses else 0.0
    win_rate_dec = len(wins) / total
    loss_rate_dec = len(losses) / total
    expectancy = round(win_rate_dec * avg_win_rr - loss_rate_dec * avg_loss_rr, 3)
    average_rr = round(sum(t.rr_result for t in closed) / total, 3)

    max_drawdown = _max_drawdown_r(closed)
    longest_losing_streak = _longest_losing_streak(closed)
    best_trade = round(max(t.rr_result for t in closed), 3)
    worst_trade = round(min(t.rr_result for t in closed), 3)
    avg_duration = round(sum(t.duration_candles for t in closed) / total)

    rating = _rating(expectancy, profit_factor, total)
    sample_quality = sample_quality_label(total)

    # Display hint for infinite profit factor
    if pf_infinite and total < 20:
        pf_display_hint = "N/A — no losses yet, but sample too small"
    elif pf_infinite:
        pf_display_hint = "Very high — no losing trades in sample"
    else:
        pf_display_hint = None

    return {
        "strategy": strategy_name,
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "profit_factor_infinite": pf_infinite,
        "profit_factor_display_hint": pf_display_hint,
        "expectancy": expectancy,
        "average_rr": average_rr,
        "avg_win_rr": avg_win_rr,
        "avg_loss_rr": avg_loss_rr,
        "max_drawdown": round(max_drawdown, 3),
        "longest_losing_streak": longest_losing_streak,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "average_duration_candles": avg_duration,
        "rating": rating,
        "sample_quality": sample_quality,
        "sample_size_warning": total < 20,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _max_drawdown_r(trades: list[TradeRecord]) -> float:
    """Peak-to-trough drawdown expressed in R (negative number)."""
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for trade in trades:
        equity += trade.rr_result
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
    return -max_dd


def _longest_losing_streak(trades: list[TradeRecord]) -> int:
    max_streak = 0
    current = 0
    for trade in trades:
        if trade.is_loss:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _rating(expectancy: float, profit_factor: float, total: int) -> str:
    if total < 10:
        return "Insufficient Data"
    if total < 20:
        if expectancy > 0.3 and profit_factor > 1.3:
            return "Promising (small sample)"
        return "Unproven"
    if expectancy > 0.5 and profit_factor >= 1.5:
        return "Strong"
    if expectancy > 0.2 and profit_factor >= 1.3:
        return "Promising"
    if expectancy > 0.0:
        return "Marginal"
    return "Avoid"


def _empty_metrics(strategy_name: str) -> dict[str, object]:
    return {
        "strategy": strategy_name,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "profit_factor_infinite": False,
        "profit_factor_display_hint": None,
        "expectancy": 0.0,
        "average_rr": 0.0,
        "avg_win_rr": 0.0,
        "avg_loss_rr": 0.0,
        "max_drawdown": 0.0,
        "longest_losing_streak": 0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "average_duration_candles": 0,
        "rating": "No Trades",
        "sample_quality": "No Sample",
        "sample_size_warning": True,
    }
