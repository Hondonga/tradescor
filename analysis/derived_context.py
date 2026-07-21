"""Completed-candle top-down context and family-aware interpretation."""
from analysis.derived_market_profile import build_derived_market_profile
from analysis.derived_regime_detector import detect_derived_regime
from analysis.synthetic_volatility import detect_synthetic_volatility

def build_top_down_context(candles_by_timeframe,family="OTHER_DERIVED",tick_size=.01):
    frames={}
    for timeframe in ("D1","H4","H1","M15","M5"):
        profile=build_derived_market_profile(candles_by_timeframe.get(timeframe),family=family,tick_size=tick_size,timeframe=timeframe)
        volatility=detect_synthetic_volatility(profile);regime=detect_derived_regime(candles_by_timeframe.get(timeframe),profile,volatility=volatility,family=family)
        frames[timeframe.lower()]={"direction":regime["direction"],"regime":regime["regime"]}
    directions=[frames[key]["direction"] for key in ("d1","h4","h1","m15","m5") if frames[key]["direction"] in {"bullish","bearish"}]
    bull=directions.count("bullish");bear=directions.count("bearish");count=max(1,len(directions))
    if bull and not bear:alignment="bullish"
    elif bear and not bull:alignment="bearish"
    elif bull and bear and abs(bull-bear)<=1:alignment="conflicted"
    else:alignment="mixed"
    return {**frames,"alignment":alignment,"alignment_score":max(bull,bear)/count if directions else 0.0}

def build_derived_context(*,timeframes,profile,regime,spike,current_price=None):
    # Backward-compatible projection for the legacy derived decision contract.
    return {"d1":timeframes.get("D1",{}),"h4":timeframes.get("H4",{}),"h1":timeframes.get("H1",{}),"m15":timeframes.get("M15",{}),"m5":timeframes.get("M5",{}),"structure":regime.get("regime","INSUFFICIENT_DATA"),"momentum":regime.get("direction","neutral"),"volatility":profile.get("volatility_regime","INSUFFICIENT_DATA"),"price_location":"unavailable" if current_price is None else "current market","spike_state":"cooldown" if spike.get("cooldown_recommended") else "detected" if spike.get("spike_detected") else "normal"}

def interpret_market(family,regime,volatility,spike):
    direction=regime.get("direction","neutral");name=regime.get("regime","INSUFFICIENT_DATA");vol=volatility.get("regime","INSUFFICIENT_DATA")
    if name=="INSUFFICIENT_DATA":summary="More completed candles are required before the market can be classified."
    elif spike.get("spike_detected"):summary=f"A {spike.get('direction')} abnormal event is active; structure is being recalibrated."
    elif name=="COMPRESSION":summary="Price ranges are compressing; expansion has not yet been accepted."
    elif name=="RANGE":summary="Price is rotating inside a stable range without directional acceptance."
    elif name.startswith("TREND_"):summary=f"Confirmed structure supports a {direction} trend under {vol.lower()} volatility."
    else:summary=f"The market is in {name.lower().replace('_',' ')} with {direction} local context."
    return {"bias":direction,"structure":name,"momentum":volatility.get("direction","stable"),"price_location":"current market","summary":summary}
