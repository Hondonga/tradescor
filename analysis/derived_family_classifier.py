"""Metadata-first, registry-overridable Deriv family classification."""
from __future__ import annotations
import json
import re
from pathlib import Path

FAMILIES=("VOLATILITY_SWITCH","RANGE_BREAK","DRIFT_SWITCH","VOLATILITY","BOOM","CRASH","STEP","STEP_CLASSIC","STEP_MULTI","STEP_SKEW_UP","STEP_SKEW_DOWN","JUMP","DEX","HYBRID","OTHER_DERIVED")
_CONFIG=Path(__file__).resolve().parents[1]/"config"/"derived_indices.yaml"

def load_derived_registry(path=None):
    try:return json.loads(Path(path or _CONFIG).read_text(encoding="utf-8"))
    except (OSError,ValueError):return {"symbols":{},"family_defaults":{}}

def classify_derived_family(metadata:dict|None,overrides:dict|None=None)->dict[str,object]:
    metadata=metadata or {};symbol=str(metadata.get("provider_symbol") or metadata.get("symbol") or metadata.get("underlying_symbol") or "")
    display=str(metadata.get("display_name") or metadata.get("underlying_symbol_name") or symbol);registry=load_derived_registry();configured=dict((registry.get("symbols") or {}).get(symbol) or {})
    override=(overrides or {}).get(symbol)
    if override:
        configured.update(override if isinstance(override,dict) else {"family":override});source="explicit_override";confidence=.99
    elif configured:source="registry";confidence=.98
    else:
        family,source,confidence=_metadata_family(metadata,symbol,display);configured={"family":family}
    family=str(configured.get("family") or "OTHER_DERIVED").upper()
    if family not in FAMILIES:family="OTHER_DERIVED"
    expected=configured.get("expected_event_direction",configured.get("expected_spike_direction")) or ((registry.get("family_defaults") or {}).get(family) or {}).get("expected_spike_direction")
    if family in {"VOLATILITY","JUMP","STEP","STEP_CLASSIC","STEP_MULTI","STEP_SKEW_UP","STEP_SKEW_DOWN"}:expected=None
    warnings=[] if family!="OTHER_DERIVED" else ["Symbol family is not recognized; research classification is required."]
    legacy={"VOLATILITY":["supply_demand","breakout_retest","universal_structure"],"RANGE_BREAK":["breakout_retest"],"BOOM":["supply_demand","breakout_retest"],"CRASH":["supply_demand","breakout_retest"],"STEP":["supply_demand","breakout_retest","universal_structure"],"VOLATILITY_SWITCH":["regime_switch"],"DEX":["post_event_structure"]}
    step_size=configured.get("step_size");probability="symmetric" if family in {"VOLATILITY","JUMP","STEP","STEP_CLASSIC","STEP_MULTI"} else "skew_up" if family=="STEP_SKEW_UP" else "skew_down" if family=="STEP_SKEW_DOWN" else "family_specific"
    event_model="abnormal_bidirectional_jump" if family=="JUMP" else "continuous" if family=="VOLATILITY" else "step_distribution" if family.startswith("STEP") or family=="STEP" else "family_specific"
    supports_full=family in {"VOLATILITY","JUMP"};supports_fvg=family=="VOLATILITY";supports_ob=family in {"VOLATILITY","JUMP"}
    return {"provider_symbol":symbol,"symbol":symbol,"display_name":display,"family":family,"variant":str(configured.get("variant") or configured.get("subfamily") or family),"subfamily":str(configured.get("subfamily") or family),"base_volatility":configured.get("base_volatility"),"tick_speed":configured.get("tick_speed"),"step_size":step_size,"direction_probability_model":probability,"event_model":event_model,"expected_event_direction":expected,"supports_full_smc":supports_full,"supports_fvg":supports_fvg,"supports_order_blocks":supports_ob,"supports_post_event_smc":family=="JUMP","classification_confidence":confidence,"classification_source":source,"expected_spike_direction":expected,"market_schedule":"24_7","analysis_clock":"UTC","movement_unit":configured.get("movement_unit","points"),"supported_timeframes":configured.get("supported_timeframes",[]),"risk_classification":configured.get("risk_classification","research_only"),"research_status":configured.get("research_status","research"),"enabled_strategies":configured.get("enabled_strategies",[]),"warnings":warnings,"confidence":confidence,"preferred_strategies":legacy.get(family,[]),"restricted_strategies":[],"blocked_strategies":[],"spike_profile":"symmetric" if expected is None else {"up":"upward","down":"downward"}.get(expected,expected)}

def _metadata_family(metadata,symbol,display):
    # Deriv groups Boom and Crash under the shared ``crash_index`` submarket;
    # the provider symbol is the non-ambiguous discriminator within that
    # metadata group.
    if str(metadata.get("submarket") or "").lower()=="crash_index":
        if symbol.upper().startswith("BOOM"):return "BOOM","market_metadata",.96
        if symbol.upper().startswith("CRASH"):return "CRASH","market_metadata",.96
    fields=("subgroup","submarket","underlying_symbol_type","family","market")
    text=" ".join(str(metadata.get(key) or "") for key in fields).upper().replace("-"," ").replace("_"," ")
    family=_match(text)
    if family:return family,"active_symbol_metadata" if metadata.get("underlying_symbol_type") else "market_metadata",.88
    family=_match(f"{display} {symbol}".upper().replace("_"," "))
    return (family,"name_symbol_fallback",.62) if family else ("OTHER_DERIVED","unknown",.20)

def _match(text):
    rules=(("VOLATILITY SWITCH","VOLATILITY_SWITCH"),("DRIFT SWITCH","DRIFT_SWITCH"),("RANGE BREAK","RANGE_BREAK"),("SKEW STEP UP","STEP_SKEW_UP"),("SKEW STEP DOWN","STEP_SKEW_DOWN"),("MULTI STEP","STEP_MULTI"),("BOOM","BOOM"),("CRASH","CRASH"),("STEP","STEP_CLASSIC"),("JUMP","JUMP"),("DEX","DEX"),("HYBRID","HYBRID"),("VOLATILITY","VOLATILITY"))
    return next((family for token,family in rules if re.search(rf"\b{re.escape(token)}\b",text)),None)
