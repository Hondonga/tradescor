from __future__ import annotations
from collections import Counter,defaultdict
import pandas as pd

def build_report(snapshots,total_candles,splits,validation):
    frame=pd.DataFrame([row.as_record() for row in snapshots]);feature_cols=list(snapshots[0].features) if snapshots else [];missing={key:round(float(frame[key].isna().mean()*100),3) for key in feature_cols};constant=[key for key in feature_cols if frame[key].nunique(dropna=False)<=1];numeric=frame[feature_cols].select_dtypes("number") if len(frame) else pd.DataFrame();pairs=[]
    if len(numeric.columns)>1:
        corr=numeric.corr().abs()
        for i,left in enumerate(corr.columns):
            for right in corr.columns[i+1:]:
                if pd.notna(corr.loc[left,right]) and corr.loc[left,right]>=.95:pairs.append({"left":left,"right":right,"correlation":round(float(corr.loc[left,right]),4)})
    grouped=defaultdict(Counter)
    for row in snapshots:
        label=row.labels.get("outcome_label") or ("PROGRESSION" if _has_label(row) else "UNRESOLVED")
        for key in ("direction","structure_state","volatility_regime","quality_grade","stage"):grouped[key][f"{row.metadata.get(key)}::{label}"]+=1
    setup_counts=Counter(row.metadata.get("setup_id") or row.metadata.get("structural_context_id") for row in snapshots)
    return {"total_candles":total_candles,"total_snapshots":len(snapshots),"unique_setups":len(setup_counts),"snapshots_per_setup":{"minimum":min(setup_counts.values(),default=0),"maximum":max(setup_counts.values(),default=0),"mean":sum(setup_counts.values())/max(len(setup_counts),1),"median":float(pd.Series(list(setup_counts.values())).median()) if setup_counts else 0},"direction_balance":dict(Counter(row.metadata.get("direction") for row in snapshots)),"stage_balance":dict(Counter(row.metadata.get("stage") for row in snapshots)),"outcome_balance":dict(Counter(row.labels.get("outcome_label") or ("PROGRESSION" if _has_label(row) else "UNRESOLVED") for row in snapshots)),"missing_value_percentages":missing,"constant_features":constant,"highly_correlated_features":pairs,"feature_distributions":{key:{"min":float(numeric[key].min()),"median":float(numeric[key].median()),"max":float(numeric[key].max())} for key in numeric if numeric[key].notna().any()},"splits":{key:len(value) for key,value in splits.items()},"leakage_violations":validation["leakage_violations"],"unresolved_label_count":sum(not _has_label(row) for row in snapshots),"ambiguous_outcome_count":sum(row.labels.get("outcome_label")=="AMBIGUOUS" for row in snapshots),"outcomes_by_group":{key:dict(value) for key,value in grouped.items()},"validation":validation,"model_accuracy":None}

def _has_label(row):
    labels=row.labels
    return bool(labels.get("outcome_label")) or any(labels.get(key) is not None for key in ("reached_valid_location","reached_displacement","reached_structure_confirmation","reached_trade_ready","never_progressed","progression_invalidated"))
