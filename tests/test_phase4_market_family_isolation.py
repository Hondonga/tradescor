"""Phase 4 checkpoint 1: GBP/USD (Forex) and R_75 (Derived) must never
cross-contaminate strategy, provider, precision, or ownership fields.

This is a verification/inventory checkpoint over already-mature isolation
(analysis/global_overlay_contract.py already unions per-family terminal
states rather than sharing one, and tests/test_forex_pipeline_repair.py
already proves the normalization boundary rejects Deriv-only fields on a
Forex product). This file adds the explicit, symmetric Phase 4 assertions
naming both directions at once.
"""
from providers.market_registry import traditional_registry, derived_registry
from providers.deriv_provider import DerivProvider

DERIVED_STRATEGY_IDS = {"volatility_smc"}
FOREX_STRATEGY_IDS = {"ict_2022", "supply_demand", "breakout_retest", "universal_structure"}


def _gbpusd_row():
    return next(r for r in traditional_registry() if r["provider_symbol"] == "GBP/USD")


def _r75_row():
    return next(r for r in derived_registry(DerivProvider()) if r["provider_symbol"] == "R_75")


def test_gbpusd_resolves_only_to_twelve_data_and_forex_family():
    row = _gbpusd_row()
    assert row["market_source"] == "twelve_data"
    assert row["market_type"] == "forex"
    assert row["family"] == "FOREX"
    assert row["analysis_engine"] == "forex"
    assert row["market_schedule"] == "24_5"


def test_gbpusd_never_offers_a_derived_strategy_model():
    row = _gbpusd_row()
    model_ids = {m["id"] for m in row["available_models"]}
    assert model_ids.isdisjoint(DERIVED_STRATEGY_IDS)
    assert "ict_2022" in model_ids  # the Forex ICT model must be reachable


def test_gbpusd_precision_is_forex_precision_not_derived():
    row = _gbpusd_row()
    assert row["instrument_precision"]["price_decimals"] == 5
    assert row["instrument_precision"]["pip_size"] == 0.0001


def test_r75_resolves_only_to_deriv_and_volatility_family():
    row = _r75_row()
    assert row["market_source"] == "deriv"
    assert row["market_type"] == "derived"
    assert row["family"] == "VOLATILITY"
    assert row["analysis_engine"] == "derived_smc"
    assert row["market_schedule"] == "24_7"


def test_r75_never_offers_a_forex_strategy_model():
    row = _r75_row()
    model_ids = {m["id"] for m in row["available_models"]}
    assert model_ids.isdisjoint(FOREX_STRATEGY_IDS)
    assert "volatility_smc" in model_ids


def test_r75_market_schedule_is_24_7_not_forex_24_5():
    # A derived synthetic index must never inherit Forex weekend closure --
    # confirmed structurally via the registry's own market_schedule field,
    # independent of whatever session/market-hours logic Phase 4 adds for
    # Forex specifically.
    assert _r75_row()["market_schedule"] == "24_7"
    assert _gbpusd_row()["market_schedule"] == "24_5"
