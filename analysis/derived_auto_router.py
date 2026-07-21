"""Selection continuity and orchestration helpers for Derived Auto."""
_SELECTIONS={}
def apply_auto_continuity(symbol,proposed,regime,setup_id=None,minimum_difference=.08,proposed_score=0):
    old=_SELECTIONS.get(symbol);new=proposed;reason="Initial measurable selection."
    if old and old["strategy"]!=proposed:
        if old.get("regime")==regime and old.get("setup_id") and (setup_id==old.get("setup_id") or proposed_score-old.get("score",0)<minimum_difference):new=old["strategy"];reason="Preserved active setup continuity."
        else:reason="Material regime or setup evidence permitted replacement."
    changed=bool(old and old["strategy"]!=new);_SELECTIONS[symbol]={"strategy":new,"regime":regime,"setup_id":setup_id,"score":proposed_score}
    return {"previous_selected_strategy":old.get("strategy") if old else None,"current_selected_strategy":new,"selection_changed":changed,"change_reason":reason}
def clear_auto_continuity():_SELECTIONS.clear()
