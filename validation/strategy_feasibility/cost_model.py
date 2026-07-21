"""Cost model applied to every simulated trade, in R units.

Costs are subtracted from realized R so a strategy must beat its trading
friction, not just zero. Supports a flat per-trade R cost and a spread-in-ATR
model translated to R via the trade's risk distance.
"""
from __future__ import annotations


def cost_in_R(cost_model: dict, risk_points: float, atr: float) -> float:
    kind = cost_model.get("type", "per_trade_R")
    if kind == "per_trade_R":
        return float(cost_model.get("cost_R", 0.0))
    if kind == "spread_atr":
        # round-trip spread expressed as a fraction of ATR, converted to R
        spread_points = float(cost_model.get("spread_atr", 0.0)) * atr
        return spread_points / risk_points if risk_points > 0 else 0.0
    if kind == "spread_points":
        spread_points = float(cost_model.get("spread_points", 0.0))
        return spread_points / risk_points if risk_points > 0 else 0.0
    return 0.0
