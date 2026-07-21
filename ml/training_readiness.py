from __future__ import annotations

POSITIVE={"ENTRY_FILLED_TP1","ENTRY_FILLED_TP2"};NEGATIVE={"ENTRY_FILLED_STOP"}
def evaluate_training_readiness(snapshots,validation,blocks,minimums):
    setups={row.metadata.get("setup_id") or row.metadata.get("structural_context_id") for row in snapshots};ready=[row for row in snapshots if row.metadata.get("trade_ready")];resolved=[row for row in ready if row.labels.get("entry_filled")==1 and row.labels.get("outcome_label") not in {None,"EXPIRED"}];buy=[row for row in resolved if row.metadata.get("direction")=="buy"];sell=[row for row in resolved if row.metadata.get("direction")=="sell"];positive=[row for row in resolved if row.labels.get("outcome_label") in POSITIVE];negative=[row for row in resolved if row.labels.get("outcome_label") in NEGATIVE];unresolved=sum(not _has_label(row) for row in snapshots);ratio=unresolved/max(len(snapshots),1);independent=sum(block.get("candidate_setups",0)>0 and block.get("resolved_entries",0)>0 for block in blocks)
    values={"minimum_unique_setup_candidates":len(setups),"minimum_trade_ready_plans":len(ready),"minimum_resolved_entries":len(resolved),"minimum_buy_resolved":len(buy),"minimum_sell_resolved":len(sell),"minimum_positive_outcomes":len(positive),"minimum_negative_outcomes":len(negative),"maximum_leakage_violations":validation.get("leakage_violations",0),"maximum_unresolved_label_ratio":ratio,"minimum_independent_market_periods":independent}
    requirements=[]
    for name,required in minimums.items():
        current=values[name];passed=current<=required if name.startswith("maximum_") else current>=required;requirements.append({"name":name,"current":current,"required":required,"passed":passed})
    blocking=[row for row in requirements if not row["passed"]]
    return {"ready":not blocking,"requirements":requirements,"blocking_requirements":blocking,"manual_override_allowed":False}

def _has_label(row):
    labels=row.labels
    return bool(labels.get("outcome_label")) or any(labels.get(key) is not None for key in ("reached_valid_location","reached_displacement","reached_structure_confirmation","reached_trade_ready","never_progressed","progression_invalidated"))
