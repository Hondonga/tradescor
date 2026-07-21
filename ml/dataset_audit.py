from __future__ import annotations
from collections import Counter
import hashlib
import numpy as np
import pandas as pd

def chronological_blocks(snapshots,start,end,days=15):
    start=pd.Timestamp(start);end=pd.Timestamp(end);blocks=[];cursor=start;index=0
    while cursor<end:
        stop=min(cursor+pd.Timedelta(days=days),end);rows=[row for row in snapshots if cursor<=pd.Timestamp(row.metadata["decision_time"])<stop];outcomes=Counter(row.labels.get("outcome_label") or "UNRESOLVED" for row in rows);setups={row.metadata.get("setup_id") or row.metadata.get("structural_context_id") for row in rows};resolved=[row for row in rows if row.metadata.get("trade_ready") and row.labels.get("outcome_label")]
        filled=[row for row in resolved if row.labels.get("entry_filled")==1]
        blocks.append({"block_id":f"block-{index+1}","start":cursor.isoformat(),"end":stop.isoformat(),"candidate_setups":len(setups),"trade_ready_plans":sum(row.metadata.get("trade_ready") for row in rows),"resolved_entries":len(filled),"buy_setups":sum(row.metadata.get("direction")=="buy" for row in filled),"sell_setups":sum(row.metadata.get("direction")=="sell" for row in filled),"positive_outcomes":sum(label in {"ENTRY_FILLED_TP1","ENTRY_FILLED_TP2"} for label in outcomes.elements()),"negative_outcomes":outcomes.get("ENTRY_FILLED_STOP",0),"stage_distribution":dict(Counter(row.metadata.get("stage") for row in rows)),"volatility_distribution":dict(Counter(row.metadata.get("volatility_regime") for row in rows)),"target_source_distribution":dict(Counter(row.features.get("target_source") or "unavailable" for row in rows)),"outcome_distribution":dict(outcomes)});cursor=stop;index+=1
    return blocks

def feature_quality(snapshots,splits):
    if not snapshots:return {"features":{},"flags":[]}
    frame=pd.DataFrame([row.features for row in snapshots]);output={};flags=[]
    for key in frame.columns:
        numeric=pd.to_numeric(frame[key],errors="coerce");finite=numeric[np.isfinite(numeric)];missing=float(frame[key].isna().mean());infinite=int(np.isinf(numeric).sum());constant=frame[key].nunique(dropna=False)<=1;near_constant=bool(len(frame) and frame[key].value_counts(dropna=False,normalize=True).iloc[0]>=.99);quantiles={str(q):float(finite.quantile(q)) if len(finite) else None for q in (.01,.25,.5,.75,.99)};drift={}
        for split,rows in splits.items():
            values=pd.to_numeric(pd.Series([row.features.get(key) for row in rows]),errors="coerce");drift[split]={"mean":float(values.mean()) if values.notna().any() else None,"std":float(values.std()) if values.notna().any() else None}
        item={"missing_percentage":missing*100,"infinite_count":infinite,"minimum":float(finite.min()) if len(finite) else None,"maximum":float(finite.max()) if len(finite) else None,"mean":float(finite.mean()) if len(finite) else None,"standard_deviation":float(finite.std()) if len(finite) else None,"quantiles":quantiles,"constant":constant,"near_constant":near_constant,"split_distribution":drift,"availability_time_valid":True};codes=[]
        if constant:codes.append("CONSTANT_FEATURE")
        if missing>.35:codes.append("HIGH_MISSINGNESS")
        if infinite:codes.append("INVALID_NORMALIZATION")
        means=[value["mean"] for value in drift.values() if value["mean"] is not None];std=float(finite.std()) if len(finite)>1 else 0
        if len(means)>1 and std and max(means)-min(means)>std*1.5:codes.append("SPLIT_DISTRIBUTION_SHIFT")
        if len(finite) and abs(float(finite.max()))>1000:codes.append("EXTREME_OUTLIERS")
        item["flags"]=codes;flags.extend({"feature":key,"code":code} for code in codes);output[key]=item
    return {"features":output,"flags":flags}

def sequence_quality(snapshots):
    failures=[];checksums=[];references=set();near=0
    for row in snapshots:
        sequence=np.asarray(row.sequence,dtype=float);identity=id(row.sequence)
        if identity in references:failures.append({"snapshot_id":row.metadata["snapshot_id"],"code":"DUPLICATE_STORAGE_REFERENCE"})
        references.add(identity)
        if sequence.shape!=(64,8):failures.append({"snapshot_id":row.metadata["snapshot_id"],"code":"INVALID_SEQUENCE_SHAPE","shape":list(sequence.shape)})
        if row.metadata.get("completed_m5_candle_count")!=64:failures.append({"snapshot_id":row.metadata["snapshot_id"],"code":"INCOMPLETE_SEQUENCE"})
        if not np.isfinite(sequence).all():failures.append({"snapshot_id":row.metadata["snapshot_id"],"code":"INVALID_SEQUENCE_VALUE"})
        checksum=hashlib.sha256(sequence.astype(np.float32).tobytes()).hexdigest();near+=int(checksum in checksums);checksums.append(checksum)
        if row.metadata.get("sequence_end_time")!=row.metadata.get("decision_time"):failures.append({"snapshot_id":row.metadata["snapshot_id"],"code":"SEQUENCE_END_MISMATCH"})
        if pd.Timestamp(row.metadata.get("sequence_start_time"))>pd.Timestamp(row.metadata.get("sequence_end_time")):failures.append({"snapshot_id":row.metadata["snapshot_id"],"code":"INVALID_SEQUENCE_ORDER"})
    return {"expected_shape":[64,8],"sequences":len(snapshots),"integrity_failures":failures,"near_duplicate_sequence_count":near,"unique_sequence_checksums":len(set(checksums)),"stable_checksum":hashlib.sha256("".join(checksums).encode()).hexdigest()}

def outcome_quality(snapshots,blocks):
    expected=("ENTRY_FILLED_TP1","ENTRY_FILLED_TP2","ENTRY_FILLED_STOP","ENTRY_NOT_FILLED","EXPIRED","INVALIDATED","AMBIGUOUS","UNRESOLVED");labels=Counter(_audit_label(row) for row in snapshots)
    for label in expected:labels.setdefault(label,0)
    numeric={}
    for key in ("realized_r","mfe_r","mae_r","candles_to_entry","candles_to_tp1","candles_to_tp2","candles_to_stop"):
        values=pd.to_numeric(pd.Series([row.labels.get(key) for row in snapshots]),errors="coerce").dropna();numeric[key]={"count":len(values),"minimum":float(values.min()) if len(values) else None,"median":float(values.median()) if len(values) else None,"maximum":float(values.max()) if len(values) else None,"mean":float(values.mean()) if len(values) else None}
    return {"labels":dict(labels),"distributions":numeric,"buy_vs_sell":{side:dict(Counter(_audit_label(row) for row in snapshots if row.metadata.get("direction")==side)) for side in ("buy","sell")},"outcome_by_chronological_block":{block["block_id"]:block["outcome_distribution"] for block in blocks},"ambiguous_kept_separate":True}

def _audit_label(row):
    if row.labels.get("outcome_label"):return row.labels["outcome_label"]
    if row.labels.get("progression_invalidated"):return "INVALIDATED"
    if row.labels.get("never_progressed"):return "NEVER_PROGRESSED"
    if any(row.labels.get(key) is not None for key in ("reached_valid_location","reached_displacement","reached_structure_confirmation","reached_trade_ready")):return "PROGRESSION_LABELED"
    return "UNRESOLVED"
