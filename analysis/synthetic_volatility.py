"""Rolling synthetic volatility-regime interpretation."""
from __future__ import annotations
from analysis.derived_market_profile import build_derived_market_profile

def detect_synthetic_volatility(profile:dict)->dict[str,object]:
    if profile.get("profile_quality")=="insufficient":return {"regime":"INSUFFICIENT_DATA","level":"normal","direction":"stable","confidence":0.0,"atr_percentile":profile.get("atr_percentile"),"realized_volatility_percentile":profile.get("volatility_percentile"),"evidence":[],"contradictions":["Insufficient completed candles."]}
    atr=float(profile.get("atr_percentile") or 50);rv=float(profile.get("volatility_percentile") or atr);exp=float(profile.get("expansion_ratio") or 1);comp=float(profile.get("compression_ratio") or 1);abnormal=float(profile.get("abnormal_candle_frequency") or 0)
    level="extreme" if max(atr,rv)>=95 else "high" if max(atr,rv)>=75 else "low" if max(atr,rv)<=25 else "normal"
    if abnormal>=.15 and abs(atr-rv)>=25:direction="unstable";regime="UNSTABLE"
    elif exp>=1.35 and atr>=60:direction="rising";regime="RISING"
    elif comp<=.75 and atr<=45:direction="falling";regime="FALLING"
    else:direction="stable";regime={"extreme":"EXTREME","high":"HIGH","low":"LOW","normal":"NORMAL"}[level]
    evidence=[f"ATR percentile {atr:.1f}.",f"Realized-volatility percentile {rv:.1f}.",f"Recent expansion ratio {exp:.2f}."]
    return {"regime":regime,"level":level,"direction":direction,"confidence":min(.95,.55+abs(max(atr,rv)-50)/100),"atr_percentile":atr,"realized_volatility_percentile":rv,"evidence":evidence,"contradictions":[]}

def synthetic_volatility_profile(candles,*,tick_size=.01,family="OTHER_DERIVED"):
    return build_derived_market_profile(candles,family=family,tick_size=tick_size,timeframe="M15")
