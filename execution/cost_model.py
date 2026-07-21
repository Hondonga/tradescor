"""Conservative explicit execution-cost assumptions."""

from __future__ import annotations


def execution_costs(*, spread: float = 0.0, slippage: float = 0.0, fee: float = 0.0, weekend_crypto_multiplier: float = 1.25, asset_class: str = "forex", weekend: bool = False) -> dict[str, float]:
    multiplier = weekend_crypto_multiplier if asset_class == "crypto" and weekend else 1.0
    effective_spread = max(0.0, spread) * multiplier
    return {"spread": effective_spread, "slippage": max(0.0, slippage), "fee": max(0.0, fee), "one_way_price_cost": effective_spread / 2 + max(0.0, slippage), "round_trip_fixed_cost": effective_spread + 2 * max(0.0, slippage) + max(0.0, fee)}
