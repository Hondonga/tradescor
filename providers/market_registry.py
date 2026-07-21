"""Unified product registry for every TradeScor market surface."""
from __future__ import annotations

from providers.symbol_map import SYMBOL_MAP
from analysis.derived_model_compatibility import compatibility_for,model_options
from analysis.instrument_precision import precision_registry

MODEL_REGISTRY={
 "derived":[{"id":"auto","label":"SMC Auto"},{"id":"volatility_smc","label":"Volatility SMC"},{"id":"jump_smc","label":"Jump SMC"},{"id":"step_smc","label":"Step SMC"}],
 "forex":[{"id":"auto","label":"Structure Context"},{"id":"ict_2022","label":"ICT Precision"},{"id":"supply_demand","label":"Supply and Demand"},{"id":"breakout_retest","label":"Breakout and Retest"},{"id":"universal_structure","label":"Structure Context"}],
 "crypto":[{"id":"auto","label":"Structure Context"},{"id":"supply_demand","label":"Supply and Demand"},{"id":"breakout_retest","label":"Breakout and Retest"}],
 "index":[{"id":"auto","label":"Structure Context"},{"id":"supply_demand","label":"Supply and Demand"},{"id":"breakout_retest","label":"Breakout and Retest"}],
}

def traditional_registry():
    rows=[]
    for display,details in SYMBOL_MAP.items():
        market_type=details["type"];schedule="24_7" if market_type=="crypto" else "exchange" if market_type=="index" else "24_5"
        engine="crypto_strategy" if market_type=="crypto" else "index_strategy" if market_type=="index" else "forex";default="universal_structure" if market_type=="forex" else "auto"
        instrument=precision_registry(symbol=details["api_symbol"],provider="twelve_data",market_type=market_type,metadata={"symbol_id":f"twelve_data:{details['api_symbol']}"})
        rows.append({"symbol_id":f"twelve_data:{details['api_symbol']}","display_name":display,"provider_symbol":details["api_symbol"],"market_source":"twelve_data","market_type":market_type,"family":market_type.upper(),"variant":display.replace("/","_").replace(" ","_").upper(),"market_schedule":schedule,"analysis_engine":engine,"default_model":default,"supported":True,"available_models":MODEL_REGISTRY[market_type],"instrument_precision":instrument,"price_decimals":instrument["price_decimals"],"tick_size":instrument["tick_size"]})
    return rows

def derived_registry(provider):
    rows=[]
    for source in provider.list_symbols():
        rule=compatibility_for(source.get("family"));support="SUPPORTED" if rule["production_supported"] else "LEGACY_RESEARCH_ONLY" if rule["research_supported"] else "UNSUPPORTED_MODEL"
        symbol_id=f"deriv:{source['provider_symbol']}";instrument=precision_registry(symbol=source["provider_symbol"],provider="deriv",market_type="derived",metadata={**source,"symbol_id":symbol_id})
        rows.append({"symbol_id":symbol_id,"display_name":source["display_name"],"provider_symbol":source["provider_symbol"],"market_source":"deriv","market_type":"derived","family":source.get("family") or "OTHER_DERIVED","family_display":source.get("family_display"),"variant":source.get("variant") or source.get("family"),"market_schedule":"24_7","analysis_engine":"derived_smc","supported":bool(rule["production_supported"] or rule["research_supported"]),"production_supported":rule["production_supported"],"research_supported":rule["research_supported"],"default_model":rule["default_model"],"auto_adapter":rule["auto_adapter"],"available_models":_derived_models(source),**{key:source.get(key) for key in ("market","submarket","pip_size","market_open","smc_adapter")},"instrument_precision":instrument,"price_decimals":instrument["price_decimals"],"tick_size":instrument["tick_size"],"analysis_support_status":support})
    return rows

def unified_registry(deriv_provider=None):
    rows=traditional_registry()
    errors={}
    if deriv_provider is not None:
        try:rows=derived_registry(deriv_provider)+rows
        except Exception as error:errors["deriv"]={"state":"error","error":str(error)}
    return rows,errors

def resolve_market(symbol_id_or_provider_symbol,deriv_provider=None):
    rows,_=unified_registry(deriv_provider)
    value=str(symbol_id_or_provider_symbol)
    row=next((row for row in rows if row["symbol_id"]==value or row["provider_symbol"]==value or row["display_name"]==value),None)
    if not row:raise ValueError(f"Unsupported market '{value}'.")
    return row

def _derived_models(source):
    return model_options(source.get("family"))
