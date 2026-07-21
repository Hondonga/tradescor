"""Non-Forex market rules for Deriv Derived Indices."""
from __future__ import annotations

def derived_index_rules(symbol: str, metadata: dict|None=None)->dict[str,object]:
    metadata=metadata or {}; pip=metadata.get("pip_size")
    if isinstance(pip,int) and pip>=0 or isinstance(pip,float) and pip>=1 and pip.is_integer():precision=int(pip);tick=10**(-precision)
    elif isinstance(pip,(float,int)) and float(pip)>0:
        from decimal import Decimal
        tick=float(pip);precision=max(0,-Decimal(str(pip)).normalize().as_tuple().exponent)
    else:tick=.01;precision=2
    return {"asset_class":"derived_index","symbol":symbol,"market_schedule":"24_7","market_open":not bool(metadata.get("suspended",False)),
            "news_filter_applicable":False,"dxy_applicable":False,"forex_session_gate_applicable":False,
            "movement_unit":"points","provider":"deriv","exchange_timezone":"UTC","tick_size":tick,
            "pip_size":tick,"precision":precision}
