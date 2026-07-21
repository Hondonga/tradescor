from __future__ import annotations
import pandas as pd

FORBIDDEN_FEATURE_TOKENS=("outcome","eventually","future_","later_","entry_filled","tp1_hit","tp2_hit","stop_hit","realized_r","mfe","mae","final_result","paper_status")
def validate_snapshot(snapshot):
    violations=[];decision=pd.Timestamp(snapshot.metadata["decision_time"]);available=pd.Timestamp(snapshot.available_at_time)
    if available>decision:violations.append({"snapshot_id":snapshot.metadata["snapshot_id"],"code":"FEATURE_AVAILABLE_AFTER_DECISION","available_at_time":str(available),"decision_time":str(decision)})
    for key in snapshot.features:
        if any(token in key.lower() for token in FORBIDDEN_FEATURE_TOKENS):violations.append({"snapshot_id":snapshot.metadata["snapshot_id"],"code":"OUTCOME_DERIVED_FEATURE","feature":key})
    return violations
def validate_dataset(snapshots):return [violation for snapshot in snapshots for violation in validate_snapshot(snapshot)]
