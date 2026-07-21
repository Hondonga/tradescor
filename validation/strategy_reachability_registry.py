"""Declarative production-strategy inventory for setup-proof validation.

This registry describes behavior that must be observed.  It never creates a
decision and is deliberately separate from the product strategy router.
"""
from __future__ import annotations


COMMON_READY_STAGES=("DIRECTIONAL_CONTEXT","LOCATION","DISPLACEMENT","M5_STRUCTURE_BREAK","ENTRY","TARGET_EVALUATION","PLAN_VALIDATION","TRADE_READY")
COMMON_ENTITIES=("setup_id","direction","completed_confirmation","entry","stop","tp1","reward_to_risk","decision_owner","overlay_owner")


REGISTRY={
    "volatility_structure_pullback":{
        "strategy_id":"volatility_structure_pullback","family":"VOLATILITY","supported_directions":["buy","sell"],
        "required_stages":["H1_DIRECTIONAL","M15_PULLBACK","VALID_LOCATION","M5_DISPLACEMENT","M5_STRUCTURE_BREAK","ENTRY_SELECTED","STOP_SELECTED","TARGET_SELECTED","RR_VALIDATED","TRADE_READY"],"required_entities":[*COMMON_ENTITIES,"bos","pullback_area"],"production_supported":True,
        "fixture_ids":["volatility_structure_pullback_buy","volatility_structure_pullback_sell"],
    },
    "volatility_liquidity_reversal":{
        "strategy_id":"volatility_liquidity_reversal","family":"VOLATILITY","supported_directions":["buy","sell"],
        "required_stages":["DIRECTIONAL_CONTEXT","LIQUIDITY_SWEEP",*COMMON_READY_STAGES[2:]],"required_entities":[*COMMON_ENTITIES,"sweep","mss","retracement_area"],"production_supported":False,"support_status":"FOCUSED_CONFIGURATION_DISABLED",
        "fixture_ids":["volatility_liquidity_reversal_buy","volatility_liquidity_reversal_sell"],
    },
    "volatility_range_reaction":{
        "strategy_id":"volatility_range_reaction","family":"VOLATILITY","supported_directions":["buy","sell"],
        "required_stages":["RANGE_CONFIRMED","BOUNDARY_SWEEP","M5_STRUCTURE_BREAK","ENTRY","TARGET_EVALUATION","PLAN_VALIDATION","TRADE_READY"],"required_entities":[*COMMON_ENTITIES,"dealing_range","sweep","mss"],"production_supported":False,"support_status":"FOCUSED_CONFIGURATION_DISABLED",
        "fixture_ids":["volatility_range_reaction_buy","volatility_range_reaction_sell"],
    },
    "volatility_breakout_and_retest":{
        "strategy_id":"volatility_breakout_and_retest","family":"VOLATILITY","supported_directions":["buy","sell"],
        "required_stages":["RANGE_CONFIRMED","ACCEPTED_BREAKOUT","RETEST","M5_STRUCTURE_BREAK","ENTRY","TARGET_EVALUATION","PLAN_VALIDATION","TRADE_READY"],"required_entities":[*COMMON_ENTITIES,"dealing_range","accepted_breakout","retest_area"],"production_supported":False,"support_status":"FOCUSED_CONFIGURATION_DISABLED",
        "fixture_ids":["volatility_breakout_and_retest_buy","volatility_breakout_and_retest_sell"],
    },
    "jump_post_event_continuation":{
        "strategy_id":"jump_post_event_continuation","family":"JUMP","supported_directions":["buy","sell"],
        "required_stages":["EVENT_COMPLETED","QUARANTINE","FRESH_STRUCTURE",*COMMON_READY_STAGES[2:]],"required_entities":[*COMMON_ENTITIES,"qualified_event","fresh_post_event_swing","bos"],"production_supported":False,"support_status":"NOT_PRODUCTION_SUPPORTED","fixture_ids":["jump_post_event_continuation_buy","jump_post_event_continuation_sell"],
    },
    "jump_post_event_reversal":{
        "strategy_id":"jump_post_event_reversal","family":"JUMP","supported_directions":["buy","sell"],
        "required_stages":["EVENT_COMPLETED","QUARANTINE","POST_EVENT_REJECTION",*COMMON_READY_STAGES[2:]],"required_entities":[*COMMON_ENTITIES,"qualified_event","fresh_post_event_swing","mss"],"production_supported":False,"support_status":"NOT_PRODUCTION_SUPPORTED","fixture_ids":["jump_post_event_reversal_buy","jump_post_event_reversal_sell"],
    },
    "step_range_reaction":{
        "strategy_id":"step_range_reaction","family":"STEP","supported_directions":["buy","sell"],
        "required_stages":["RANGE_CONFIRMED","BOUNDARY_SWEEP","M5_STRUCTURE_BREAK","ENTRY","TARGET_EVALUATION","PLAN_VALIDATION","TRADE_READY"],"required_entities":[*COMMON_ENTITIES,"dealing_range","sweep","mss"],"production_supported":False,"support_status":"FOCUSED_CONFIGURATION_DISABLED","forbidden_entities":["fvg","order_block"],
        "fixture_ids":["step_range_reaction_buy","step_range_reaction_sell"],
    },
    "step_structure_pullback":{
        "strategy_id":"step_structure_pullback","family":"STEP","supported_directions":["buy","sell"],
        "required_stages":list(COMMON_READY_STAGES),"required_entities":[*COMMON_ENTITIES,"bos","structural_retrace"],"production_supported":False,"support_status":"FOCUSED_CONFIGURATION_DISABLED","forbidden_entities":["fvg","order_block"],
        "fixture_ids":["step_structure_pullback_buy","step_structure_pullback_sell"],
    },
    "step_breakout_and_retest":{
        "strategy_id":"step_breakout_and_retest","family":"STEP","supported_directions":["buy","sell"],
        "required_stages":["RANGE_CONFIRMED","ACCEPTED_BREAKOUT","RETEST","M5_STRUCTURE_BREAK","ENTRY","TARGET_EVALUATION","PLAN_VALIDATION","TRADE_READY"],"required_entities":[*COMMON_ENTITIES,"dealing_range","accepted_breakout","retest_area"],"production_supported":False,"support_status":"FOCUSED_CONFIGURATION_DISABLED","forbidden_entities":["fvg","order_block"],
        "fixture_ids":["step_breakout_and_retest_buy","step_breakout_and_retest_sell"],
    },
    "boom_crash_spike_state":{
        "strategy_id":"boom_crash_spike_state","family":"BOOM_CRASH","supported_directions":["buy","sell"],
        "required_stages":["SPIKE_COMPLETED","COOLDOWN","FRESH_STRUCTURE",*COMMON_READY_STAGES[2:]],"required_entities":[*COMMON_ENTITIES,"qualified_spike","fresh_post_spike_structure"],"production_supported":False,"support_status":"LEGACY_RESEARCH_ONLY","fixture_ids":["boom_spike_state","crash_spike_state"],
    },
}


def strategy_reachability_registry():
    return {key:{**value,"required_stages":list(value["required_stages"]),"required_entities":list(value["required_entities"]),"supported_directions":list(value["supported_directions"]),"fixture_ids":list(value["fixture_ids"])} for key,value in REGISTRY.items()}


def production_strategy_ids():
    return tuple(key for key,value in REGISTRY.items() if value["production_supported"])
