"""Market-condition-first routing for the existing strategy modules."""

from __future__ import annotations


def route_strategy(top_down: dict[str, object], requested: str = "auto") -> dict[str, object]:
    regime = str((top_down.get("regime") or {}).get("value", "unclear"))
    alignment = str((top_down.get("alignment") or {}).get("state", "mixed"))
    setup = top_down.get("m15_setup") or {}
    setup_type = str(setup.get("setup_type", ""))
    requested_key = str(requested or "auto").lower()

    if regime in {"transition", "range", "unclear"} or alignment == "mixed" or not setup.get("enabled"):
        result = {"selected_strategy": "", "market_condition": "mixed_or_unclear", "reason": "Higher-timeframe context does not support a primary setup.", "eligible_strategies": []}
    elif "breakout" in setup_type or "retest" in setup_type:
        result = {"selected_strategy": "breakout_retest", "market_condition": "broken_range_retest", "reason": "A clean broken range is awaiting a structural retest.", "eligible_strategies": ["breakout_retest", "universal_structure"]}
    elif any(word in setup_type for word in ("liquidity", "ote", "fvg", "ifvg")):
        result = {"selected_strategy": "ict_2022", "market_condition": "ict_liquidity_context", "reason": "Liquidity and ICT location evidence define the setup.", "eligible_strategies": ["ict_2022", "supply_demand"]}
    else:
        result = {"selected_strategy": "supply_demand", "market_condition": "trending_pullback", "reason": "A directional market is pulling back into a structural area.", "eligible_strategies": ["supply_demand", "universal_structure"]}

    if requested_key != "auto":
        result["requested_strategy"] = requested_key
        result["manual_strategy_eligible"] = requested_key in result["eligible_strategies"]
    return result
