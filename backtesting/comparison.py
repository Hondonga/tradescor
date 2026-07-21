"""Compare multiple strategies and rank them by composite quality score.

Ranking deliberately avoids using win rate as the primary criterion.
Expectancy, profit factor, and drawdown are the primary signals.
"""

from __future__ import annotations

from strategies import STRATEGY_LABELS

from .metrics import calculate_metrics
from .trade_log import TradeRecord


def compare_strategies(
    strategy_trades: dict[str, list[TradeRecord]],
) -> dict[str, object]:
    """Return ranked metrics and a plain-language comparison summary."""
    all_metrics: list[dict[str, object]] = []

    for key, trades in strategy_trades.items():
        name = STRATEGY_LABELS.get(key, key)
        m = calculate_metrics(trades, name)
        m["strategy_key"] = key
        m["trade_records"] = [t.to_dict() for t in trades]
        all_metrics.append(m)

    ranked = _rank(all_metrics)
    best = ranked[0] if ranked else None
    summary, result_status = _summary_and_status(ranked, best)

    return {
        "ranked": ranked,
        "best_strategy": best,
        "summary": summary,
        "result_status": result_status,
    }


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def _rank(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    """Composite score: expectancy, profit factor, drawdown, sample size."""

    def _score(m: dict[str, object]) -> float:
        total = int(m.get("total_trades", 0))
        if total < 5:
            return -9999.0  # too few trades to rank meaningfully

        expectancy = float(m.get("expectancy", 0.0))
        pf = float(m.get("profit_factor", 0.0))
        dd = abs(float(m.get("max_drawdown", 0.0)))
        sample_bonus = min(total / 30.0, 1.0)  # more trades = more confidence

        return (
            expectancy * 3.0
            + max(pf - 1.0, 0.0) * 2.0
            - dd * 0.8
            + sample_bonus * 0.5
        )

    return sorted(metrics, key=_score, reverse=True)


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------

def _summary_and_status(
    ranked: list[dict[str, object]],
    best: dict[str, object] | None,
) -> tuple[str, str]:
    """Return (summary_text, result_status).

    result_status is one of:
      "no_data" | "insufficient" | "early_leader" | "confirmed"
    """
    if not ranked or best is None:
        return "Not enough data to compare strategies.", "no_data"

    total_best = int(best.get("total_trades", 0))
    total_all = sum(int(m.get("total_trades", 0)) for m in ranked)

    if total_best == 0:
        return (
            "No strategy produced any closed trades. "
            "Try a longer date range or more bars.",
            "no_data",
        )

    if total_best < 10:
        return (
            "Not enough trades to compare strategies. "
            "More bars or a different timeframe may produce more signals.",
            "insufficient",
        )

    name = best.get("strategy", "Unknown")
    expectancy = float(best.get("expectancy", 0.0))
    pf = float(best.get("profit_factor", 0.0))
    pf_infinite = bool(best.get("profit_factor_infinite", False))
    dd = abs(float(best.get("max_drawdown", 0.0)))
    win_rate = float(best.get("win_rate", 0.0))

    pf_text = (
        "N/A (no losses yet — small sample)" if pf_infinite and total_best < 20
        else "very high (no losses yet)" if pf_infinite
        else f"{pf:.2f}"
    )

    # Early leader — weak sample
    if total_best < 20:
        return (
            f"{name} is the early leader ({total_best} trades, "
            f"expectancy {expectancy:+.2f}R, profit factor {pf_text}). "
            "Sample is too small to draw reliable conclusions — "
            "increase bar count for a more meaningful comparison.",
            "early_leader",
        )

    # Confirmed result — adequate sample
    parts = [
        f"{name} produced the best results with expectancy {expectancy:+.2f}R, "
        f"profit factor {pf_text}, "
        f"and max drawdown {dd:.1f}R."
    ]
    if total_best < 50:
        parts.append(
            f"The sample has {total_best} trades — treat as directional evidence."
        )

    other_names = [
        str(m.get("strategy", ""))
        for m in ranked[1:]
        if int(m.get("total_trades", 0)) >= 5
    ]
    if other_names:
        parts.append("Compared with: " + ", ".join(other_names) + ".")

    parts.append(f"Win rate was {win_rate:.1f}% (not used as primary criterion).")
    parts.append("Historical results do not guarantee future performance.")

    status = "confirmed" if total_best >= 20 and expectancy > 0 and pf > 1.3 else "early_leader"
    return " ".join(parts), status
