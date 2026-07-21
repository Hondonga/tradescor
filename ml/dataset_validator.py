from __future__ import annotations
import hashlib,json
from collections import Counter
import pandas as pd
from ml.leakage_validator import validate_dataset

def validate_snapshots(snapshots):
    violations=validate_dataset(snapshots);ids=[row.metadata["snapshot_id"] for row in snapshots];stage_groups=Counter((row.metadata.get("setup_id") or row.metadata.get("structural_context_id"),row.metadata["stage"]) for row in snapshots)
    duplicates=[key for key,count in Counter(ids).items() if count>1];dominant=max(Counter(row.metadata.get("setup_id") or row.metadata.get("structural_context_id") for row in snapshots).values(),default=0)
    if duplicates:violations.append({"code":"DUPLICATE_SNAPSHOT_IDS","count":len(duplicates)})
    if any(count>1 for count in stage_groups.values()):violations.append({"code":"REPEATED_SETUP_STAGE","count":sum(count-1 for count in stage_groups.values() if count>1)})
    return {"valid":not violations,"leakage_violations":len([x for x in violations if x["code"] in {"FEATURE_AVAILABLE_AFTER_DECISION","OUTCOME_DERIVED_FEATURE"}]),"violations":violations,"rows":len(snapshots),"unique_setups":len({row.metadata.get("setup_id") or row.metadata.get("structural_context_id") for row in snapshots}),"maximum_snapshots_per_setup":dominant,"validation_hash":hashlib.sha256(json.dumps(violations,sort_keys=True,default=str).encode()).hexdigest()}

def chronological_splits(snapshots,purge_overlap=False):
    ordered=sorted(snapshots,key=lambda row:row.metadata["decision_time"]);groups=[]
    for row in ordered:
        key=row.metadata.get("structural_context_id") or row.metadata.get("setup_id") or row.metadata.get("snapshot_id")
        existing=next((item for item in groups if item[0]==key),None)
        if existing:existing[1].append(row)
        else:groups.append([key,[row]])
    n=len(ordered);a=n*.6;b=n*.8;output={"train":[],"validation":[],"test":[]};count=0
    for _,rows in groups:
        target="train" if count<a else "validation" if count<b else "test";output[target].extend(rows);count+=len(rows)
    for key in output:output[key].sort(key=lambda row:row.metadata["decision_time"])
    if purge_overlap:
        _purge(output,"train","validation");_purge(output,"validation","test")
    return output

def validate_split_isolation(splits):
    violations=[]
    for field in ("setup_id","structural_context_id","directional_leg_id"):
        owners={}
        for split,rows in splits.items():
            for row in rows:
                value=row.metadata.get(field)
                if value and value in owners and owners[value]!=split:violations.append({"code":"IDENTITY_CROSSES_SPLIT","identity_type":field,"identity":value,"splits":[owners[value],split]})
                elif value:owners[value]=split
    for left,right in (("train","validation"),("validation","test")):
        if splits[left] and splits[right] and pd.Timestamp(splits[right][0].metadata.get("sequence_start_time"))<=pd.Timestamp(splits[left][-1].metadata["decision_time"]):violations.append({"code":"SEQUENCE_OVERLAP_ACROSS_SPLIT","splits":[left,right]})
    return violations

def _purge(output,left,right):
    if not output[left]:return
    cutoff=pd.Timestamp(output[left][-1].metadata["decision_time"]);bad={row.metadata.get("structural_context_id") for row in output[right] if pd.Timestamp(row.metadata.get("sequence_start_time"))<=cutoff}
    output[right]=[row for row in output[right] if row.metadata.get("structural_context_id") not in bad]
