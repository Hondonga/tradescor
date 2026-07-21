"""Provider-aware instrument precision shared by every normalized decision."""
from __future__ import annotations
from decimal import Decimal
from analysis.price_precision import display_precision

def precision_registry(*,symbol,provider,market_type,metadata=None,current_price=None):
    metadata=metadata or {};nested=metadata.get("instrument_precision") or {};tick=_number(metadata.get("tick_size") if metadata.get("tick_size") is not None else nested.get("tick_size"));pip=_number(metadata.get("pip_size") if metadata.get("pip_size") is not None else nested.get("pip_size"));explicit=metadata.get("price_decimals") if metadata.get("price_decimals") is not None else nested.get("price_decimals")
    provider_step=(10**-int(pip) if market_type in {"derived","derived_index"} and pip is not None and pip>=1 and float(pip).is_integer() else pip)
    step=tick if tick is not None and tick>0 else provider_step if market_type in {"derived","derived_index","index","crypto"} and provider_step is not None and provider_step>0 else None
    normalized=str(symbol or "").upper()
    if market_type=="forex":
        if step is None:step=.001 if normalized.endswith("/JPY") else .00001
        if pip is None:pip=.01 if normalized.endswith("/JPY") else .0001
    decimals=int(explicit) if explicit is not None else _decimals(step) if step is not None else display_precision(symbol,"index" if market_type in {"derived","derived_index","index"} else market_type,current_price)
    return {"symbol_id":metadata.get("symbol_id") or nested.get("symbol_id") or f"{provider}:{symbol}","price_decimals":decimals,"pip_size":provider_step if market_type in {"derived","derived_index"} else pip,"tick_size":tick or step,"quantity_decimals":metadata.get("quantity_decimals") if metadata.get("quantity_decimals") is not None else nested.get("quantity_decimals")}

def format_price(value,registry):
    return None if value is None else f"{float(value):.{int(registry['price_decimals'])}f}"

def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
def _decimals(step):return max(0,-Decimal(str(step)).normalize().as_tuple().exponent)
