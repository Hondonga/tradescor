"""Completed-candle context for Volatility Switch and Drift Switch families."""
from __future__ import annotations

SUPPORTED={"VOLATILITY_SWITCH","DRIFT_SWITCH"}
def build_switch_context(*,family,profile,regime,data_quality=None,last_completed_at=None,previous_regime=""):
    name=family.get("family","") if isinstance(family,dict) else str(family); quality=(data_quality or {}); reasons=[]
    if name not in SUPPORTED: reasons.append("Family is not a supported switch index.")
    if isinstance(family,dict) and float(family.get("classification_confidence",0))<.8: reasons.append("Family classification is uncertain.")
    if not quality.get("analysis_allowed",True): reasons.append("Required timeframe context is unavailable.")
    if quality.get("status") in {"stale","reconnecting"}: reasons.append("Market data is not current.")
    profile_ok=profile.get("profile_quality") in {"good","partial"}; data_ok=not reasons and quality.get("status","good") in {"good","partial"}
    if not profile_ok: reasons.append("Completed-candle market profile is insufficient.")
    raw=_volatility_state(profile,regime) if name=="VOLATILITY_SWITCH" else _drift_state(profile,regime)
    current=raw["state"]; transition=current in {"UNSTABLE_TRANSITION","DRIFT_TRANSITION","POSSIBLE_BULLISH_TRANSITION","POSSIBLE_BEARISH_TRANSITION","UNSTABLE","INSUFFICIENT_DATA"}
    context={"family":name,"previous_regime":previous_regime,"current_regime":current,"candidate_regime":current,"regime_changed":bool(previous_regime and current!=previous_regime),"transition_active":transition,"transition_started_at":last_completed_at if transition else None,"stable_completed_candles":0,"regime_confidence":raw["confidence"],"volatility_state":raw["state"] if name=="VOLATILITY_SWITCH" else str(profile.get("volatility_regime") or ""),"drift_state":raw["state"] if name=="DRIFT_SWITCH" else "","structure_direction":raw.get("direction","neutral"),"evidence":raw["evidence"],"contradictions":raw["contradictions"]}
    eligibility={"eligible":not reasons,"family":name,"eligibility_reason":"Eligible switch-family context." if not reasons else " ".join(reasons),"data_quality_passed":data_ok,"profile_quality_passed":profile_ok,"data_state":"DATA RECONNECTING" if quality.get("status")=="reconnecting" else "INSUFFICIENT HISTORY" if not profile_ok else "DATA UNAVAILABLE" if reasons else "AVAILABLE"}
    return {"eligibility":eligibility,"context":context,"measurement":raw}

def _volatility_state(profile,regime):
    atr=float(profile.get("atr_percentile") or 0); rv=float(profile.get("volatility_percentile") or atr); compression=float(profile.get("compression_ratio") or 1); expansion=float(profile.get("expansion_ratio") or 1); abnormal=float(profile.get("abnormal_candle_frequency") or 0); directional=float(profile.get("directional_efficiency") or 0); evidence=[]
    if profile.get("profile_quality")=="insufficient": state="INSUFFICIENT_DATA"; direction="unstable"
    elif abnormal>.18 or max(atr,rv)>=97: state="EXTREME"; direction="unstable"; evidence=["Extreme completed-candle volatility is present."]
    elif regime.get("regime") in {"UNSTABLE","VOLATILITY_TRANSITION"}: state="UNSTABLE_TRANSITION"; direction="unstable"
    elif compression<=.75: state="COMPRESSION"; direction="rising" if expansion>1.05 else "stable"
    elif expansion>=1.35 and max(atr,rv)>=65: state="RISING_VOLATILITY"; direction="rising"
    elif max(atr,rv)>=70: state="HIGH_STABLE" if directional>=.25 else "UNSTABLE_TRANSITION"; direction="stable" if directional>=.25 else "unstable"
    elif max(atr,rv)<=25: state="LOW_STABLE"; direction="stable"
    else: state="NORMAL_STABLE"; direction="stable"
    confidence=.9 if state in {"LOW_STABLE","NORMAL_STABLE","HIGH_STABLE"} else .78 if state in {"COMPRESSION","RISING_VOLATILITY"} else .55
    return {"level":"high" if max(atr,rv)>=70 else "low" if max(atr,rv)<=25 else "normal","direction":direction,"state":state,"confidence":confidence,"confirmed_at":regime.get("formed_at"),"evidence":evidence or [f"Completed-candle volatility classifies as {state}."],"contradictions":[]}

def _drift_state(profile,regime):
    direction=regime.get("direction","neutral"); state_name=regime.get("regime",""); efficiency=float(profile.get("directional_efficiency") or 0); persistence=float(profile.get("trend_persistence") or 0)
    if profile.get("profile_quality")=="insufficient": state="INSUFFICIENT_DATA"; direction="neutral"
    elif state_name in {"VOLATILITY_TRANSITION","UNSTABLE"} or direction=="mixed": state="DRIFT_TRANSITION"; direction="mixed"
    elif direction=="bullish" and efficiency>=.25 and persistence>=.52: state="BULLISH_DRIFT"
    elif direction=="bearish" and efficiency>=.25 and persistence>=.52: state="BEARISH_DRIFT"
    elif efficiency<=.22 or state_name in {"RANGE","COMPRESSION"}: state="SIDEWAYS_DRIFT"; direction="sideways"
    elif direction=="bullish": state="POSSIBLE_BULLISH_TRANSITION"
    elif direction=="bearish": state="POSSIBLE_BEARISH_TRANSITION"
    else: state="DRIFT_TRANSITION"; direction="neutral"
    return {"state":state,"direction":direction,"confidence":.88 if state in {"BULLISH_DRIFT","BEARISH_DRIFT","SIDEWAYS_DRIFT"} else .55,"confirmed_at":regime.get("formed_at"),"last_valid_drift":state if state in {"BULLISH_DRIFT","BEARISH_DRIFT","SIDEWAYS_DRIFT"} else "","evidence":[f"Completed structure supports {state}."],"contradictions":[]}
