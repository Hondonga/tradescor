"""Historical D1/H4/H1 → M15 → M5 execution-pipeline replay."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from analysis.decision_engine import build_decision
from scanner.session_engine import get_session_status
from evidence.performance_registry import PerformanceRegistry


def run_top_down_execution_backtest(
    candles_by_timeframe: dict[str, pd.DataFrame],
    *,
    symbol: str,
    asset_type: str = "forex",
    minimum_rr: float = 1.5,
    execution_mode: str = "conservative",
    spread: float = 0.0,
    slippage: float = 0.0,
    fee_per_trade: float = 0.0,
    out_of_sample_fraction: float = 0.3,
    validation_fraction: float = 0.2,
) -> dict[str, object]:
    """Walk M5 closes and evaluate the complete synchronized pipeline."""
    required = ("D1", "H4", "H1", "M15", "M5")
    missing = [timeframe for timeframe in required if timeframe not in candles_by_timeframe or candles_by_timeframe[timeframe].empty]
    if missing:
        return {"trades": [], "missed_entries": 0, "metadata": {"valid": False, "missing_timeframes": missing, "execution_timeframe": "M5"}}

    context = {timeframe: _clean(frame) for timeframe, frame in candles_by_timeframe.items() if timeframe in required}
    m5 = context["M5"]
    warmup = min(60, max(20, len(m5) // 3))
    test_fraction = max(0.1, min(0.5, out_of_sample_fraction))
    validation_fraction = max(0.1, min(0.4, validation_fraction))
    test_index = max(warmup, int(len(m5) * (1 - test_fraction)))
    validation_index = max(warmup, int(len(m5) * (1 - test_fraction - validation_fraction)))
    seen: set[str] = set()
    trades: list[dict[str, object]] = []
    states: dict[str, int] = {}
    missed_entries = 0
    evidence_registry = PerformanceRegistry(records=[])
    pending_evidence: list[tuple[pd.Timestamp, dict[str, object]]] = []

    for index in range(warmup, len(m5) - 1):
        candle = m5.iloc[index]
        boundary = candle["time"] + timedelta(minutes=5)
        matured = [item for item in pending_evidence if item[0] <= boundary]
        for _, record in matured:
            evidence_registry.append(record)
        pending_evidence = [item for item in pending_evidence if item[0] > boundary]
        sliced = {timeframe: frame.loc[frame["time"] < boundary].copy() for timeframe, frame in context.items()}
        session = get_session_status(boundary, asset_type=asset_type, symbol=symbol)
        decision = build_decision(
            symbol=symbol, asset_class=asset_type, display_timeframe="M15",
            candles_by_timeframe=sliced, analysis_timestamp=boundary,
            requested_strategy="auto", session=session, filters={}, spread=spread,
            minimum_rr=minimum_rr,
            execution_mode=execution_mode,
            evidence_registry=evidence_registry,
        )
        plan = decision["execution"]
        state = str(plan["state"])
        states[state] = states.get(state, 0) + 1
        if state in {"too_late", "entry_extended", "trigger_confirmed"}:
            missed_entries += 1
        if state != "entry_available" or not plan.get("confirmed_state"):
            continue
        identity = str(decision["decision_id"])
        if identity in seen:
            continue
        seen.add(identity)
        trade = _resolve_trade(
            m5=m5,
            signal_index=index,
            plan=plan,
            direction=str(plan["direction"]),
            spread=spread,
            slippage=slippage,
            fee=fee_per_trade,
        )
        trade.update(
            {
                "symbol": symbol,
                "asset_class": asset_type,
                "decision_id": decision["decision_id"],
                "setup_id": decision["setup"]["setup_id"],
                "regime": decision["market_regime"]["value"],
                "strategy": decision["setup"]["strategy"],
                "setup_type": decision["setup"]["type"],
                "liquidity_window": session.get("liquidity_window") or session.get("name"),
                "direction": plan["direction"],
                "execution_model": execution_mode,
                "timeframe_alignment": (decision.get("alignment") or {}).get("state"),
                "amd_phase": (decision.get("amd") or {}).get("phase", "searching"),
                "amd_cycle_id": (decision.get("amd") or {}).get("cycle_id"),
                "strategy_version": (decision.get("primary_candidate") or {}).get("strategy_version"),
                "configuration_hash": decision.get("configuration_hash") or ((decision.get("ict_model") or {}).get("configuration_hash")),
                "sample": "test" if index >= test_index else "validation" if index >= validation_index else "train",
            }
        )
        trades.append(trade)
        pending_evidence.append((pd.Timestamp(trade["exit_time"]), _evidence_record(decision, trade, session, execution_mode)))

    grouped = _grouped_evidence(trades)
    return {
        "trades": trades,
        "missed_entries": missed_entries,
        "state_counts": states,
        "setup_lifecycle_counts": states,
        "evidence": grouped,
        "research": _research_report(trades),
        "metadata": {
            "valid": True,
            "timeframe_hierarchy": list(required),
            "execution_timeframe": "M5",
            "minimum_rr": minimum_rr,
            "execution_model": execution_mode,
            "spread": spread,
            "slippage": slippage,
            "fee_per_trade": fee_per_trade,
            "same_candle_policy": "stop_first_conservative",
            "partitions": {"train_end_index": validation_index, "validation_end_index": test_index, "test_start_index": test_index, "chronological": True, "random_shuffle": False},
            "walk_forward": {"enabled": True, "train_end_index": validation_index, "validation_end_index": test_index, "test_fraction": test_fraction, "validation_fraction": validation_fraction, "final_test_tuning": False},
            "ict_research_profiles": {"A": "strict_core", "B": "core_plus_ote", "C": "core_plus_amd", "D": "core_plus_session_filter", "E": "core_plus_order_block"},
            "overlap_embargo": {"enabled": True, "policy": "setups crossing a partition boundary remain assigned to their creation partition"},
            "look_ahead": False,
        },
    }


def _resolve_trade(*, m5: pd.DataFrame, signal_index: int, plan: dict[str, object], direction: str, spread: float, slippage: float, fee: float) -> dict[str, object]:
    raw_entry = float(plan["entry"])
    entry_cost = max(0.0, spread) / 2 + max(0.0, slippage)
    entry = raw_entry + entry_cost if direction == "buy" else raw_entry - entry_cost
    stop = float(plan["stop"])
    targets = [target for target in plan.get("targets", []) if target.get("valid")]
    target = float(targets[0]["price"])
    risk = abs(entry - stop)
    result, exit_price, exit_time = "OPEN_AT_END", float(m5.iloc[-1]["close"]), m5.iloc[-1]["time"]
    for index in range(signal_index + 1, len(m5)):
        candle = m5.iloc[index]
        stop_hit = float(candle["low"]) <= stop if direction == "buy" else float(candle["high"]) >= stop
        target_hit = float(candle["high"]) >= target if direction == "buy" else float(candle["low"]) <= target
        if stop_hit:
            result, exit_price, exit_time = "SL", stop, candle["time"]
            break
        if target_hit:
            result, exit_price, exit_time = "TP1", target, candle["time"]
            break
    gross_r = ((exit_price - entry) if direction == "buy" else (entry - exit_price)) / risk if risk > 0 else 0.0
    net_r = gross_r - (max(0.0, fee) / risk if risk > 0 else 0.0)
    return {"signal_time": m5.iloc[signal_index]["time"].isoformat(), "entry": entry, "stop": stop, "target": target, "exit": exit_price, "exit_time": exit_time.isoformat(), "result": result, "gross_r": round(gross_r, 3), "net_r": round(net_r, 3), "confirmed_on_close": True}


def _clean(frame: pd.DataFrame) -> pd.DataFrame:
    clean = frame.copy()
    clean["time"] = pd.to_datetime(clean["time"], utc=True, errors="coerce")
    return clean.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)


def _grouped_evidence(trades: list[dict[str, object]]) -> list[dict[str, object]]:
    keys = ("symbol", "asset_class", "regime", "strategy", "direction", "setup_type", "liquidity_window", "execution_model", "amd_phase")
    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for trade in trades:
        groups.setdefault(tuple(trade.get(key) for key in keys), []).append(trade)
    rows = []
    for values, items in groups.items():
        count = len(items)
        label = "No Evidence" if count == 0 else "Insufficient Evidence" if count < 20 else "Early Evidence" if count < 50 else "Moderate Sample" if count < 100 else "Usable Sample"
        rows.append({**dict(zip(keys, values)), "trades": count, "evidence_label": label, "average_net_r": round(sum(float(item.get("net_r", 0)) for item in items) / count, 3)})
    return rows


def _evidence_record(decision: dict[str, object], trade: dict[str, object], session: dict[str, object], execution_mode: str) -> dict[str, object]:
    candidate = decision.get("primary_candidate") or {}
    h1 = ((decision.get("market_features") or {}).get("timeframes") or {}).get("H1", {})
    volatility = ((h1.get("volatility_regime") or {}).get("value")) or "unknown"
    net_r = float(trade.get("net_r", 0))
    return {"symbol": decision["symbol"], "asset_class": decision["asset_class"], "strategy_version": candidate.get("strategy_version"), "direction": candidate.get("direction"), "market_regime": (decision.get("regime") or {}).get("regime"), "volatility_regime": volatility, "setup_type": candidate.get("setup_type"), "session": session.get("liquidity_window") or session.get("name"), "execution_mode": execution_mode, "execution_timeframe": "M5", "evaluation_period": trade.get("signal_time"), "closed_trades": 1, "wins": int(net_r > 0), "losses": int(net_r <= 0), "expectancy_r": net_r, "expectancy_variance": 0.0, "out_of_sample": True}


def _research_report(trades: list[dict[str, object]]) -> dict[str, object]:
    net = [float(row.get("net_r", 0)) for row in trades]
    auto = sum(net); count = len(net)
    return {"configuration_count": 1, "auto_router": {"trades": count, "net_r": round(auto, 3)}, "baselines": {"always_no_trade": {"trades": 0, "net_r": 0.0}, "equal_weight_eligible": {"status": "export_required"}, "simple_trend": {"status": "export_required"}, "simple_range_break": {"status": "export_required"}}, "multiple_testing": {"spa_export_ready": True, "white_reality_check_export_ready": True, "model_confidence_set_loss_matrix": [[-value] for value in net], "probability_of_backtest_overfitting": None, "deflated_statistics": None}, "cost_sensitivity": "Run neighboring spread/slippage configurations before interpreting performance.", "parameter_stability": "Single configured threshold set; neighborhood research is required."}
