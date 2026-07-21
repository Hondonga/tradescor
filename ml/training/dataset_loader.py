from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.dataset_store import _logical_checksum
from ml.feature_schema import FEATURE_NAMES,SCHEMA_VERSION

EXCLUSIONS={"not_trade_ready":"not a production trade-ready plan","not_filled":"entry not filled","ambiguous_or_unresolved":"outcome is not TP1-before-stop or stop-before-TP1"}

def load_frozen_dataset(config,root="data/ml/datasets"):
    folder=Path(root)/config["dataset_id"];manifest=json.loads((folder/"manifest.json").read_text());frame=pd.read_parquet(folder/"features.parquet");archive=np.load(folder/"sequences.npz",allow_pickle=False)
    checksum=_logical_checksum(frame,archive["sequences"],archive["snapshot_ids"])
    if manifest.get("checksum")!=config["dataset_checksum"] or checksum!=config["dataset_checksum"]:raise ValueError("Frozen dataset checksum mismatch.")
    if manifest.get("schema_version")!=SCHEMA_VERSION or config["schema_version"]!=SCHEMA_VERSION:raise ValueError("Unknown feature schema version.")
    frame=frame.copy();frame["decision_time"]=pd.to_datetime(frame.decision_time,utc=True);frame["split"]=_splits(frame,manifest)
    _validate_groups(frame.loc[frame.split.notna()]);eligible=frame.split.notna() & frame.trade_ready & frame.entry_filled.eq(1) & frame.outcome_label.isin(["ENTRY_FILLED_TP1","ENTRY_FILLED_TP2","ENTRY_FILLED_STOP"])
    exclusions=frame.loc[~eligible,["snapshot_id","setup_id"]].copy();exclusions["reason"]="ambiguous_or_unresolved";exclusions.loc[~frame.loc[~eligible,"trade_ready"],"reason"]="not_trade_ready";exclusions.loc[frame.loc[~eligible,"trade_ready"] & ~frame.loc[~eligible,"entry_filled"].eq(1),"reason"]="not_filled";exclusions.loc[frame.loc[~eligible,"split"].isna(),"reason"]="purged_split_boundary"
    data=frame.loc[eligible].copy();data["target"]=data.tp1_before_stop.astype(int)
    return data,manifest,exclusions

def _splits(frame,manifest):
    result=pd.Series(index=frame.index,dtype="object")
    for name,bounds in manifest["splits"].items():
        mask=frame.decision_time.between(pd.Timestamp(bounds["start"]),pd.Timestamp(bounds["end"]),inclusive="both");result.loc[mask]=name
    return result

def _validate_groups(frame):
    for key in ("setup_id","directional_leg_id","structural_context_id"):
        if (frame.groupby(key).split.nunique()>1).any():raise ValueError(f"{key} crosses frozen splits.")
    order=frame.groupby("split").decision_time.agg(["min","max"]);assert order.loc["train","max"]<order.loc["validation","min"]<order.loc["test","min"]

def feature_columns():return list(FEATURE_NAMES)
