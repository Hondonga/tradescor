import hashlib,json,time
from pathlib import Path
import pandas as pd
import pytest

from ml.training.dataset_loader import load_frozen_dataset,feature_columns
from ml.training.preprocessing import fit_preprocessor
from ml.training.sample_weighting import setup_equal_weights
from ml.training.threshold_selection import select_threshold
from ml.training.training_config import load_config
from ml.training.training_service import MLTrainingService

DATASET=Path("data/ml/datasets/ml-r75-f4c52d93c7a8dc3e95f1")

@pytest.fixture(scope="module")
def completed_run(tmp_path_factory):
    service=MLTrainingService(root=tmp_path_factory.mktemp("training"));run=service.start()
    for _ in range(300):
        value=service.get(run["run_id"])
        if value["state"] in {"completed","failed","cancelled"}:break
        time.sleep(.05)
    assert value["state"]=="completed",value.get("error")
    return service,value

def test_frozen_dataset_checksum_and_files_remain_read_only():
    before={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in DATASET.iterdir()};data,manifest,excluded=load_frozen_dataset(load_config());after={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in DATASET.iterdir()}
    assert before==after and manifest["checksum"]=="737b02ea7c98fa68131920cc0fb6f5b438a8504dc2898aea14c1ce4c0b178b23"
    assert set(data.target)=={0,1} and "purged_split_boundary" in set(excluded.reason)

def test_checksum_mismatch_is_rejected():
    config=load_config();config["dataset_checksum"]="0"*64
    with pytest.raises(ValueError,match="checksum mismatch"):load_frozen_dataset(config)

def test_chronological_groups_never_cross_splits_and_preprocessing_fits_train_only():
    data,_,_=load_frozen_dataset(load_config());assert data.groupby("setup_id").split.nunique().max()==1
    assert data[data.split.eq("train")].decision_time.max()<data[data.split.eq("validation")].decision_time.min()<data[data.split.eq("test")].decision_time.min()
    pre=fit_preprocessor(data[data.split.eq("train")],feature_columns());assert pre.fitted_split_=="train"

def test_setup_weighting_is_deterministic_and_equalizes_total_setup_weight():
    data,_,_=load_frozen_dataset(load_config());train=data[data.split.eq("train")];one=setup_equal_weights(train);two=setup_equal_weights(train)
    pd.testing.assert_series_equal(one,two);totals=one.groupby(train.setup_id).sum();assert totals.max()-totals.min()<1e-12

def test_threshold_selection_accepts_validation_only_contract():
    data,_,_=load_frozen_dataset(load_config());validation=data[data.split.eq("validation")];probability=validation.target.to_numpy()*.4+.3
    threshold,table=select_threshold(validation,probability,load_config());assert threshold in load_config()["thresholds"] and table

def test_required_models_artifacts_and_version_metadata_are_persisted(completed_run):
    service,run=completed_run;report=run["report"];names={row["name"] for row in report["models"]}
    assert {"dummy_majority","dummy_prior","logistic_unweighted","logistic_balanced","logistic_setup_weighted","gradient_boosting"}<=names
    artifact=Path(run["artifact_path"]);metadata=json.loads((artifact/"metadata.json").read_text())
    assert {"dataset_checksum","feature_schema_version","feature_ordering","configuration_hash","dependencies","selected_threshold"}<=set(metadata)
    assert (artifact/"preprocessor.pkl").exists() and (artifact/"training_weights.parquet").exists() and (artifact/"test_predictions.parquet").exists()

def test_test_is_evaluated_only_after_selection_freezes_and_acceptance_is_bounded(completed_run):
    service,run=completed_run;assert run["selection"]["selected_using"]=="validation_only" and run["test_evaluated_after_selection_frozen"]
    assert run["model_status"] in {"TRAINING_COMPLETED","REJECTED_NO_PREDICTIVE_VALUE","REJECTED_POOR_CALIBRATION","REJECTED_TRADING_METRICS","REJECTED_UNSTABLE_ACROSS_PERIODS","ACCEPTED_FOR_PAPER_SCORING"}
    assert "PRODUCTION_READY" not in json.dumps(run)

def test_offline_models_cannot_mutate_smc_geometry_or_live_workspace(completed_run):
    _,run=completed_run;source="\n".join(path.read_text() for path in Path("analysis").glob("*.py"));assert "ml.training" not in source
    predictions=pd.read_parquet(Path(run["artifact_path"])/"test_predictions.parquet");assert set(predictions.columns)=={"snapshot_id","raw_probability","calibrated_probability","accepted"}
