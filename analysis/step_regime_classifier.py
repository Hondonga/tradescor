"""Structure-aware Step condition classification."""
from analysis.derived_regime_detector import detect_derived_structure
def classify_step_regime(candles,profile,sequence):
    base={"regime":"INSUFFICIENT_DATA","direction":"neutral","confidence":0.0,"formed_at":None,"evidence":[],"contradictions":[]}
    if profile.get("quality")=="insufficient":return base
    structure=detect_derived_structure(candles);eff=float(profile.get("directional_efficiency") or 0);persistence=float(profile.get("trend_persistence") or 0);compression=float(profile.get("compression_ratio") or 1);expansion=float(profile.get("expansion_ratio") or 1);direction=structure.get("direction","neutral")
    if compression<=.72:regime="COMPRESSION";direction="neutral"
    elif expansion>=1.45 and (structure.get("bullish_break") or structure.get("bearish_break")):regime="ACCEPTED_BREAKOUT"
    elif eff<=.22 and float(profile.get("range_stability") or 0)>=.35:regime="STABLE_RANGE";direction="neutral"
    elif direction=="bullish" and eff>=.35 and persistence>=.52:regime="BULLISH_RUN"
    elif direction=="bearish" and eff>=.35 and persistence>=.52:regime="BEARISH_RUN"
    elif direction in {"bullish","bearish"}:regime="TRANSITION";direction="mixed"
    else:regime="UNSTABLE";direction="mixed"
    formed=getattr(candles.iloc[-1].get("time"),"isoformat",lambda: str(candles.iloc[-1].get("time")))() if len(candles) else None
    return {**base,"regime":regime,"direction":direction,"confidence":.85 if regime in {"STABLE_RANGE","BULLISH_RUN","BEARISH_RUN"} else .7,"formed_at":formed,"evidence":[f"Completed-candle structure supports {regime}."],"structure":structure}
