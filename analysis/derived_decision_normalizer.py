"""One UI-ready decision contract for Derived Index analysis."""
from __future__ import annotations
import hashlib,json

def normalize_derived_decision(*,symbol,family,regime,router,market_context,data_quality,zone=None,confirmation=None,risk=None,targets=None,current_price=None,timestamp=None):
    selected=router.get("selected_candidate");direction=(selected or {}).get("direction");confirmed=bool(confirmation and confirmation.get("complete") and confirmation.get("valid_for_setup_id"));plan_valid=confirmed and risk and risk.get("valid") and targets and targets.get("valid")
    setup_id=(confirmation or {}).get("valid_for_setup_id") or (_id(symbol,family.get("family"),(selected or {}).get("strategy"),direction,zone) if selected else None)
    if not data_quality.get("analysis_allowed",True):status="DATA UNAVAILABLE"
    elif family.get("family") in {"BOOM","CRASH","JUMP","DEX"} and market_context.get("spike_state")=="cooldown":status="POST-SPIKE COOLDOWN"
    elif plan_valid:status="READY TO BUY" if direction=="buy" else "READY TO SELL"
    elif selected:status={"WAITING_FOR_RETEST":"WAITING FOR RETEST","WAITING_FOR_PULLBACK":"WAITING FOR PULLBACK","WAITING_FOR_CONFIRMATION":"WAITING FOR CONFIRMATION","RANGE_FORMING":"RANGE FORMING"}.get(selected.get("state"),"BUY SETUP FORMING" if direction=="buy" else "SELL SETUP FORMING")
    else:status="NO CURRENT SETUP"
    bias=regime.get("direction","neutral")
    active={"confirmed_entry":confirmation.get("entry"),"confirmation":confirmation,"stop":risk,"tp1":targets.get("tp1"),"tp2":targets.get("tp2"),"chase_state":"ENTRY_AVAILABLE"} if plan_valid else None
    scenario={"available":bool(selected),"direction":direction or "","label":selected.get("state","") if selected else "","strategy":selected.get("strategy","") if selected else "","zone":zone if selected else None,"required_event":"Price must reach the execution area." if selected else "","confirmation_requirement":"A completed M5 confirmation must form after zone interaction." if selected else "","invalidation_context":"Invalid beyond fresh execution structure.","target_context":"Nearest unswept structural objective must pass RR."}
    decision={"status":status,"market_bias":bias,"developing_direction":direction or "","trade_ready":bool(plan_valid),"strategy":router.get("selected_strategy") or "","family":family.get("family","OTHER_DERIVED"),"regime":regime.get("regime","INSUFFICIENT_DATA"),"setup_id":setup_id,"summary":status.replace("_"," ").title(),"next_action":"Review the confirmed plan." if plan_valid else "Wait for the required structure. Do not chase." if selected else "Wait for a measurable setup."}
    return {"decision":decision,"market_context":market_context,"developing_scenario":scenario,"active_trade_plan":active,"key_levels":{"support":None,"resistance":None,"liquidity_above":None,"liquidity_below":None},"previous_setup":None,"advanced_details":{"router":router,"data_quality":data_quality,"family":family,"regime":regime}}

def _id(*values):return "derived-"+hashlib.sha256(json.dumps(values,sort_keys=True,default=str).encode()).hexdigest()[:20]
