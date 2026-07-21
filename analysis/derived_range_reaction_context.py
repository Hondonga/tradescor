"""Family/regime eligibility for boundary fades, separate from breakout routing."""
def build_range_reaction_context(family,regime,profile,volatility,data_quality=None,config=None):
    cfg=config or {};name=family.get("family") if isinstance(family,dict) else str(family);state=regime.get("regime") if isinstance(regime,dict) else str(regime);relationship="primary" if name=="VOLATILITY" else "research" if name=="STEP" else "primary" if name=="DRIFT_SWITCH" else "restricted";status="research" if name=="STEP" else "active" if relationship!="restricted" else "restricted";reasons=[]
    if not cfg.get("enabled",True):reasons.append("Strategy is disabled.")
    if name=="VOLATILITY" and state!="RANGE":reasons.append("Volatility indices require a stable RANGE regime.")
    elif name=="STEP" and state not in {"RANGE","DRIFT_SIDEWAYS"}:reasons.append("Step research requires stable boundary rotation.")
    elif name=="DRIFT_SWITCH" and state!="DRIFT_SIDEWAYS":reasons.append("Drift Switch must be sideways with no transition.")
    elif name not in {"VOLATILITY","STEP","DRIFT_SWITCH"}:reasons.append("Family is unsupported for Range Reaction.")
    if state in {"EXPANSION","ACCEPTED_BREAKOUT","POST_SPIKE","UNSTABLE","VOLATILITY_TRANSITION","INSUFFICIENT_DATA"}:reasons.append(f"Regime {state} is restricted.")
    efficiency=profile.get("directional_efficiency")
    if efficiency is None or float(efficiency)>float(cfg.get("maximum_directional_efficiency",.35)):reasons.append("Directional efficiency is too high for a range fade.")
    allowed={str(value).upper() for value in cfg.get("allowed_volatility_levels",["LOW","NORMAL"])}
    if str(profile.get("volatility_regime","")).upper() not in allowed:reasons.append("Volatility level is not eligible for a boundary fade.")
    if profile.get("profile_quality") not in {"good","partial"}:reasons.append("Market profile is insufficient.")
    if data_quality and (not data_quality.get("analysis_allowed",True) or data_quality.get("status")!="good"):reasons.append("Current synchronized data quality is required.")
    return {"eligible":not reasons,"eligibility_reason":"Eligible stable range context." if not reasons else " ".join(reasons),"family_relationship":relationship,"strategy_status":status,"rejection_reasons":reasons}
