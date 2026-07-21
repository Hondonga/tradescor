from analysis.derived_strategy_registry import derived_strategy_registry
def derived_data_quality_gate(family,profile,data_quality,frames):
    missing=[key for key in ("D1","H4","H1","M15","M5") if key not in frames or frames[key] is None or frames[key].empty];reasons=[]
    if float(family.get("classification_confidence",0))<.8:reasons.append("Family classification is unavailable or uncertain.")
    if missing:reasons.append("Required completed-candle timeframes are missing.")
    if data_quality.get("status")!="good" or not data_quality.get("analysis_allowed",True):reasons.append("Historical/live data is unavailable, partial, or reconnecting.")
    if profile.get("profile_quality") not in {"good","partial"}:reasons.append("Market intelligence profile is insufficient.")
    return {"passed":not reasons,"status":data_quality.get("status","invalid"),"missing_timeframes":missing,"warnings":data_quality.get("warnings",[]),"blocking_reasons":reasons}
def eligible_registry_entries(family,regime,data_passed=True,overrides=None):
    eligible=[];ineligible=[];name=family.get("family","");state=regime.get("regime","")
    for strategy_id,row in derived_strategy_registry().items():
        reasons=[]
        if not row["enabled"]:reasons.append("Strategy is disabled.")
        if name not in row["supported_families"]:reasons.append("Family is unsupported.")
        if state in row["restricted_regimes"]:reasons.append("Current regime is restricted.")
        if "*" not in row["supported_regimes"] and state not in row["supported_regimes"]:reasons.append("Current regime is not suitable.")
        if not data_passed:reasons.append("Data-quality gate failed.")
        (eligible if not reasons else ineligible).append(row if not reasons else {"strategy":strategy_id,"blocking_reasons":reasons})
    return {"eligible":eligible,"ineligible":ineligible}
