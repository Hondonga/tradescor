"""Phase 4 checkpoint 2: GBP/USD symbol resolution and alias normalization.

Aliases must normalize internally to the same canonical identity ("GBP/USD")
that the frontend already displays -- they must never become separate
frontend identities, cache entries, setup IDs, or overlay owners.
"""
import pytest

from providers.symbol_map import resolve_symbol
from analysis.instrument_precision import precision_registry


GBPUSD_ALIASES = [
    "GBP/USD",
    "gbp/usd",
    "  GBP/USD  ",
    "GBPUSD",
    "gbpusd",
    "GBP-USD",
    "FX:GBPUSD",
    "FX:GBP/USD",
]


@pytest.mark.parametrize("alias", GBPUSD_ALIASES)
def test_every_valid_alias_resolves_to_the_canonical_gbpusd_identity(alias):
    resolved = resolve_symbol(alias)
    assert resolved["display_symbol"] == "GBP/USD"
    assert resolved["api_symbol"] == "GBP/USD"
    assert resolved["asset_type"] == "forex"


def test_aliases_do_not_leak_into_the_display_symbol():
    # A raw, unrecognized alias-like string must never become its own
    # frontend identity -- every alias collapses to the one canonical form.
    seen_display_symbols = {resolve_symbol(alias)["display_symbol"] for alias in GBPUSD_ALIASES}
    assert seen_display_symbols == {"GBP/USD"}


def test_unrelated_forex_pairs_are_unaffected_by_the_alias_change():
    assert resolve_symbol("EURUSD")["display_symbol"] == "EUR/USD"
    assert resolve_symbol("USD/JPY")["display_symbol"] == "USD/JPY"


def test_non_forex_symbols_still_resolve_normally():
    assert resolve_symbol("BTC/USD")["asset_type"] == "crypto"
    assert resolve_symbol("NASDAQ 100")["api_symbol"] == "NDX"


def test_stale_or_unsupported_alias_forms_still_raise():
    with pytest.raises(ValueError):
        resolve_symbol("NOT-A-REAL-SYMBOL")


def test_precision_is_identical_across_every_alias():
    # The cache key / precision / setup-ID pipeline all key off the
    # resolved display_symbol, so if resolution is canonical, precision
    # cannot split across aliases either.
    precisions = {
        json_key(precision_registry(symbol=resolve_symbol(alias)["display_symbol"], provider="twelve_data", market_type="forex"))
        for alias in GBPUSD_ALIASES
    }
    assert len(precisions) == 1


def json_key(d):
    return tuple(sorted(d.items()))
