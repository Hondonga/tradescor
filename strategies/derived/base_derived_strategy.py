"""Shared contracts and gates for actionable Derived strategies."""
from __future__ import annotations
import json
from pathlib import Path

ELIGIBLE_PULLBACK_REGIMES={"TREND_BULLISH","TREND_BEARISH","PULLBACK_IN_BULLISH_TREND","PULLBACK_IN_BEARISH_TREND"}
RESTRICTED_PULLBACK_REGIMES={"RANGE","COMPRESSION","UNSTABLE","POST_SPIKE","VOLATILITY_TRANSITION","INSUFFICIENT_DATA"}

def load_strategy_thresholds():
    path=Path(__file__).resolve().parents[2]/"config"/"derived_strategy_thresholds.yaml"
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):return {"volatility_structure_pullback":{}}

def strategy_eligibility(*,family,regime,profile_quality="insufficient",data_quality=None):
    cfg=load_strategy_thresholds()["volatility_structure_pullback"];name=family.get("family") if isinstance(family,dict) else family;state=regime.get("regime") if isinstance(regime,dict) else regime;reasons=[]
    if not cfg.get("enabled",True):reasons.append("Strategy is disabled.")
    if name!="VOLATILITY":reasons.append("Only ordinary Volatility indices are supported.")
    if state not in ELIGIBLE_PULLBACK_REGIMES:reasons.append(f"Regime {state or 'unavailable'} is restricted.")
    required=str(cfg.get("minimum_profile_quality","good"));quality_rank={"insufficient":0,"partial":1,"good":2}
    if quality_rank.get(profile_quality,0)<quality_rank.get(required,2):reasons.append(f"Market profile quality must be {required}.")
    if data_quality and not data_quality.get("analysis_allowed",True):reasons.append("Data quality blocks strategy evaluation.")
    return {"eligible":not reasons,"eligibility_reason":"Eligible: aligned Volatility trend and usable profile." if not reasons else " ".join(reasons),"rejection_reasons":reasons}

def candidate(strategy,direction,*,eligible=False,state="NO_SETUP",zone=None,quality=0,reasons=None,confirmation=None):
    return {"strategy":strategy,"direction":direction,"eligible":bool(eligible),"state":state,"zone":zone,"quality":float(quality),"reasons":reasons or [],"confirmation":confirmation,"entry":None,"stop":None,"targets":[],"rr":None}
def directional_result(strategy,bullish,bearish):
    eligible=[row for row in (bullish,bearish) if row["eligible"]];selected=max(eligible,key=lambda row:row["quality"],default=None);return {"strategy":strategy,"bullish_candidate":bullish,"bearish_candidate":bearish,"selected_candidate":selected}
