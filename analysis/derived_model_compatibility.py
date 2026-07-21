"""Single authoritative family/model compatibility contract for Derived markets."""
from __future__ import annotations

_STEP={"STEP","STEP_CLASSIC","STEP_MULTI","STEP_SKEW_UP","STEP_SKEW_DOWN"}
_REGISTRY={
 "VOLATILITY":{"allowed_models":["auto","volatility_smc"],"default_model":"volatility_smc","auto_adapter":"volatility_smc_adapter","production_supported":True,"research_supported":True},
 "JUMP":{"allowed_models":["jump_smc"],"default_model":"jump_smc","auto_adapter":"","production_supported":False,"research_supported":True},
 "BOOM":{"allowed_models":["boom_crash_spike_state"],"default_model":"boom_crash_spike_state","auto_adapter":"","production_supported":False,"research_supported":True},
 "CRASH":{"allowed_models":["boom_crash_spike_state"],"default_model":"boom_crash_spike_state","auto_adapter":"","production_supported":False,"research_supported":True},
}
for _family in _STEP:_REGISTRY[_family]={"allowed_models":["step_smc"],"default_model":"step_smc","auto_adapter":"","production_supported":False,"research_supported":True}

LABELS={"auto":"SMC Auto","volatility_smc":"Volatility SMC","jump_smc":"Jump SMC","step_smc":"Step SMC","boom_crash_spike_state":"Boom/Crash Spike-State"}

def compatibility_for(family):
    name=str(family or "OTHER_DERIVED").upper();row=_REGISTRY.get(name,{"allowed_models":[],"default_model":"","auto_adapter":"","production_supported":False,"research_supported":False})
    return {"family":name,**row}

def resolve_family_model(family,requested_model):
    rule=compatibility_for(family);requested=str(requested_model or "auto").lower();allowed=rule["allowed_models"]
    resolved=rule["default_model"] if requested in {"auto","smc","smc_auto"} else requested if requested in allowed else rule["default_model"] or None;corrected=bool(resolved and requested not in allowed and requested not in {"auto","smc","smc_auto"})
    family_label=rule["family"].replace("_"," ").title();requested_label=LABELS.get(requested,requested.replace("_"," ").title())
    reason=f"{requested_label} does not support {family_label} indices." if corrected else f"SMC Auto routes {family_label} exclusively to {LABELS.get(resolved or requested,requested_label)}." if requested in {"auto","smc","smc_auto"} else f"{LABELS.get(resolved or requested,requested_label)} is compatible with {family_label}."
    return {"requested_model":requested,"resolved_model":resolved,"corrected":corrected,"reason":reason,"compatibility":rule}

def model_options(family):
    return [{"id":model,"label":LABELS[model]} for model in compatibility_for(family)["allowed_models"]]
