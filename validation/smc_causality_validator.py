from __future__ import annotations
import pandas as pd

def validate_smc_causality(decisions):
    violations=[]
    for decision in decisions:
        payload=decision.get("payload") or decision;smc=payload.get("smc_contract") or {};replay_time=pd.Timestamp(payload.get("replay_time") or payload.get("analysis_candle_time"));decision_id=payload.get("decision_id")
        for swing in smc.get("swings") or []:
            if _after(swing.get("candle_time"),swing.get("confirmation_time")):violations.append(_v(decision_id,"swing_confirmed_before_pivot",swing))
            if _after(swing.get("confirmation_time"),replay_time):violations.append(_v(decision_id,"future_swing_confirmation",swing))
        for event_name in ("last_bos","last_mss"):
            event=(smc.get("structure") or {}).get(event_name)
            if event and _after(event.get("confirmed_at"),replay_time):violations.append(_v(decision_id,"future_"+event_name,event))
        for fvg in smc.get("fvgs") or []:
            source=fvg.get("source_times") or []
            if len(source)!=3 or _after(source[-1],fvg.get("created_time")) or _after(fvg.get("created_time"),replay_time):violations.append(_v(decision_id,"invalid_fvg_timing",fvg))
        displacement={x.get("displacement_id"):x for x in smc.get("displacements") or []}
        for block in smc.get("order_blocks") or []:
            source=displacement.get(block.get("displacement_id"));
            if not source or not source.get("passed") or not source.get("structure_broken"):violations.append(_v(decision_id,"premature_order_block",block))
        event=smc.get("event") or {}
        if event.get("qualified") and _after(event.get("event_time"),replay_time):violations.append(_v(decision_id,"future_jump_event",event))
        setup=smc.get("setup") or {}
        if event.get("qualified") and setup.get("entry_array") and _before((setup.get("entry_array") or {}).get("origin_time") or (setup.get("entry_array") or {}).get("created_time"),event.get("event_time")):violations.append(_v(decision_id,"pre_event_jump_entry_array",setup.get("entry_array")))
    return {"valid":not violations,"causality_violations":violations,"violation_count":len(violations)}
def _v(decision_id,kind,entity):return {"decision_id":decision_id,"violation":kind,"entity_id":entity.get("swing_id") or entity.get("fvg_id") or entity.get("order_block_id") or entity.get("event_id")}
def _after(a,b):
    if a is None or b is None:return False
    return pd.Timestamp(a)>pd.Timestamp(b)
def _before(a,b):
    if a is None or b is None:return False
    return pd.Timestamp(a)<pd.Timestamp(b)

