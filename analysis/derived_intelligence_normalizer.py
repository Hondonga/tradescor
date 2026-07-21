"""Canonical non-actionable Derived market-intelligence response."""
from __future__ import annotations
import math

def strategy_eligibility(family,regime):
    name=family.get("family","OTHER_DERIVED");state=regime.get("regime","INSUFFICIENT_DATA");eligible=[]
    if name=="VOLATILITY":
        if state in {"TREND_BULLISH","TREND_BEARISH"}:eligible=["Structure Pullback"]
        elif state=="COMPRESSION":eligible=["Breakout and Retest"]
        elif state=="RANGE":eligible=["Range Reaction"]
    elif name in {"BOOM","CRASH"}:eligible=["Spike-State Strategy"]
    elif name=="RANGE_BREAK":eligible=["Range Break Retest"]
    elif name=="VOLATILITY_SWITCH":eligible=["Regime Switch Strategy"]
    elif name=="DRIFT_SWITCH":eligible=["Drift Strategy"]
    elif name in {"JUMP","DEX"}:eligible=["Post-Event Strategy"]
    elif name=="STEP":eligible=["Step Structure Research"]
    restricted=[] if eligible else [{"strategy":"Automatic strategy evaluation","reason":"Current family/regime requirements are incomplete."}]
    return {"eligible_strategies":eligible,"restricted_strategies":restricted,"recommended_strategy_family":eligible[0] if eligible else None}

def normalize_derived_intelligence(*,family,profile,volatility,spike,regime,top_down,market_context,data_quality,last_completed_candle=None,live=True):
    eligibility=strategy_eligibility(family,regime)
    result={"symbol":{"provider_symbol":family.get("provider_symbol",""),"display_name":family.get("display_name",""),"family":family.get("family","OTHER_DERIVED"),"subfamily":family.get("subfamily",family.get("family","OTHER_DERIVED"))},"market_status":{"provider":"deriv","schedule":"24_7","live":bool(live),"last_completed_candle":last_completed_candle},"market_profile":profile,"volatility":volatility,"spike_state":spike,"regime":regime,"top_down":top_down,"market_context":market_context,"strategy_eligibility":{"eligible":eligibility["eligible_strategies"],"restricted":eligibility["restricted_strategies"],"recommended_family":eligibility["recommended_strategy_family"]},"data_quality":data_quality,"warnings":list(dict.fromkeys((family.get("warnings") or [])+(data_quality.get("warnings") or [])))}
    return _clean(result)

def _clean(value):
    if isinstance(value,dict):return {key:_clean(item) for key,item in value.items() if key not in {"entry","stop","target","targets","tp1","tp2","tp3"}}
    if isinstance(value,list):return [_clean(item) for item in value]
    if isinstance(value,float) and not math.isfinite(value):return None
    return value
