"""Provider selection without cross-provider cache contamination."""
from __future__ import annotations
from providers.twelve_data_provider import TwelveDataProvider

_PROVIDERS={"twelve_data":TwelveDataProvider()}

def get_provider(*,provider: str|None=None,asset_class: str|None=None):
    name="deriv" if str(provider or "").lower()=="deriv" or str(asset_class or "").lower()=="derived_index" else "twelve_data"
    if name not in _PROVIDERS:
        from providers.deriv_provider import DerivProvider
        _PROVIDERS[name]=DerivProvider()
    return _PROVIDERS[name]

def provider_name(*,provider=None,asset_class=None):return get_provider(provider=provider,asset_class=asset_class).name
