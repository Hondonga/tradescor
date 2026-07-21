import json
import threading
from dataclasses import replace
import pandas as pd

from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback
from ml.candle_sequence_encoder import encode_m5_sequence
from ml.dataset_builder import build_dataset_from_frames,deterministic_period
from ml.dataset_store import DatasetStore
from ml.dataset_validator import chronological_splits,validate_snapshots
from ml.feature_extractor import extract_snapshot
from ml.leakage_validator import validate_snapshot
from ml.models import FeatureSnapshot
from ml.outcome_labeler import label_trade_plan
from ml.training_readiness import evaluate_training_readiness
from ml.dataset_validator import validate_split_isolation
from ml.symbol_compatibility import audit_symbol_compatibility
from validation.strategy_reachability_fixtures import _focused_frames


def ready(direction="buy"):
    frames=_focused_frames(direction);at=frames["M5"].iloc[-1].time
    return frames,evaluate_volatility_structure_pullback(symbol="R_75",candles_by_timeframe=frames,analysis_time=at)


def test_features_consume_production_decision_and_end_at_completed_decision_candle():
    frames,decision=ready();snapshot=extract_snapshot(decision=decision,frames=frames,dataset_id="dataset",config_hash="config")
    assert snapshot.metadata["strategy_id"]=="volatility_structure_pullback"
    assert snapshot.metadata["setup_id"]==decision["setup"]["setup_id"]
    assert snapshot.metadata["decision_time"]==pd.Timestamp(frames["M5"].iloc[-1].time).isoformat()
    assert len(snapshot.sequence)==64 and all(len(row)==8 for row in snapshot.sequence)
    assert validate_snapshot(snapshot)==[]


def test_future_candle_and_later_label_cannot_change_earlier_features():
    frames,decision=ready();before=extract_snapshot(decision=decision,frames=frames,dataset_id="dataset",config_hash="config")
    future=frames["M5"].iloc[-1].copy();future["time"]=pd.Timestamp(future.time)+pd.Timedelta(minutes=5);future["close"]*=2;extended={**frames,"M5":pd.concat([frames["M5"],pd.DataFrame([future])],ignore_index=True)}
    after=extract_snapshot(decision=decision,frames=extended,dataset_id="dataset",config_hash="config")
    assert before.features==after.features and before.sequence==after.sequence
    labeled=replace(before,labels={"outcome_label":"ENTRY_FILLED_TP1","mfe_r":4.0})
    assert labeled.features==before.features and validate_snapshot(labeled)==[]


def test_leakage_validator_rejects_future_availability_and_outcome_feature():
    frames,decision=ready();snapshot=extract_snapshot(decision=decision,frames=frames,dataset_id="dataset",config_hash="config")
    leaked=FeatureSnapshot(snapshot.metadata,{**snapshot.features,"future_outcome":1},snapshot.sequence,(pd.Timestamp(snapshot.available_at_time)+pd.Timedelta(minutes=5)).isoformat())
    codes={row["code"] for row in validate_snapshot(leaked)}
    assert {"FEATURE_AVAILABLE_AFTER_DECISION","OUTCOME_DERIVED_FEATURE"}<=codes


def test_sequence_encoder_ignores_incomplete_and_future_rows():
    frames,_=ready();at=frames["M5"].iloc[-2].time;baseline=encode_m5_sequence(frames["M5"],at,64);changed=frames["M5"].copy();changed.loc[changed.index[-1],"close"]*=100
    assert baseline==encode_m5_sequence(changed,at,64)


def test_stage_snapshots_are_deduplicated_and_setup_cannot_dominate():
    frames,decision=ready();calls=[]
    def pipeline(**kwargs):calls.append(kwargs["analysis_time"]);return {**decision,"meta":{**decision["meta"],"analysis_time":str(kwargs["analysis_time"])}}
    config={"sequence_length":64,"snapshot_policy":"every_stage_transition","checkpoint_every_candles":100,"expiration_candles":12}
    snapshots,_=build_dataset_from_frames(dataset_id="d",frames=frames,config=config,pipeline=pipeline,cancel=threading.Event())
    assert calls and len(snapshots)==1
    assert validate_snapshots(snapshots)["maximum_snapshots_per_setup"]==1


def test_chronological_splits_are_deterministic_and_test_is_last_untouched_period():
    frames,decision=ready();base=extract_snapshot(decision=decision,frames=frames,dataset_id="d",config_hash="c");rows=[]
    for index in range(10):
        metadata={**base.metadata,"snapshot_id":f"s{index}","decision_time":(pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=index*5)).isoformat(),"setup_id":f"setup-{index}","structural_context_id":f"ctx-{index}","directional_leg_id":f"leg-{index}"};rows.append(replace(base,metadata=metadata))
    one=chronological_splits(rows);two=chronological_splits(list(reversed(rows)))
    assert [x.metadata["snapshot_id"] for x in one["test"]]==["s8","s9"]
    assert [[x.metadata["snapshot_id"] for x in one[k]] for k in one]==[[x.metadata["snapshot_id"] for x in two[k]] for k in two]


def test_parquet_manifest_and_logical_checksum_are_stable(tmp_path):
    frames,decision=ready();snapshot=extract_snapshot(decision=decision,frames=frames,dataset_id="d",config_hash="c");store=DatasetStore(tmp_path);manifest={"dataset_id":"d","leakage_violations":0};first=store.save("d",[snapshot],manifest,{"validation":{}});second=store.save("d",[snapshot],manifest,{"validation":{}})
    assert first["checksum"]==second["checksum"]
    assert (tmp_path/"datasets/d/features.parquet").exists() and (tmp_path/"datasets/d/sequences.npz").exists()


def test_ml_layer_has_no_decision_mutation_or_prediction_contract():
    source=open("ml/feature_extractor.py",encoding="utf-8").read()+open("ml/dataset_builder.py",encoding="utf-8").read()
    assert "predict(" not in source and "model.fit" not in source
    assert "evaluate_volatility_structure_pullback" in source


def test_no_plan_never_receives_tp_or_stop_outcome():
    frames,decision=ready();developing={**decision,"trade_plan":{"available":False,"status":"UNAVAILABLE","entry":None,"stop":None,"targets":[]}}
    labels=label_trade_plan(developing,frames["M5"])
    assert labels["outcome_label"] is None and labels["entry_filled"] is None


def test_checkpoint_output_is_deterministic_for_same_causal_history(tmp_path):
    frames,decision=ready();config={"sequence_length":64,"snapshot_policy":"every_stage_transition","checkpoint_every_candles":25,"expiration_candles":12}
    def pipeline(**kwargs):return {**decision,"meta":{**decision["meta"],"analysis_time":str(kwargs["analysis_time"])}}
    first=DatasetStore(tmp_path/"one");second=DatasetStore(tmp_path/"two")
    build_dataset_from_frames(dataset_id="stable",frames=frames,config=config,pipeline=pipeline,store=first)
    build_dataset_from_frames(dataset_id="stable",frames=frames,config=config,pipeline=pipeline,store=second)
    assert first.checkpoint("stable")==second.checkpoint("stable")


def test_training_readiness_cannot_be_manually_forced_when_a_gate_fails():
    frames,decision=ready();snapshot=extract_snapshot(decision=decision,frames=frames,dataset_id="d",config_hash="c");minimums={"minimum_unique_setup_candidates":500,"minimum_trade_ready_plans":100,"minimum_resolved_entries":100,"minimum_buy_resolved":35,"minimum_sell_resolved":35,"minimum_positive_outcomes":25,"minimum_negative_outcomes":25,"maximum_leakage_violations":0,"maximum_unresolved_label_ratio":.35,"minimum_independent_market_periods":6};result=evaluate_training_readiness([snapshot],{"leakage_violations":0},[],minimums)
    assert not result["ready"] and result["manual_override_allowed"] is False
    assert result["blocking_requirements"]


def test_split_isolation_catches_setup_context_leg_and_sequence_crossing():
    frames,decision=ready();base=extract_snapshot(decision=decision,frames=frames,dataset_id="d",config_hash="c");later=replace(base,metadata={**base.metadata,"snapshot_id":"later","decision_time":(pd.Timestamp(base.metadata["decision_time"])+pd.Timedelta(days=1)).isoformat()});violations=validate_split_isolation({"train":[base],"validation":[later],"test":[]});codes={row["code"] for row in violations}
    assert {"IDENTITY_CROSSES_SPLIT","SEQUENCE_OVERLAP_ACROSS_SPLIT"}<=codes


def test_frozen_dataset_rejects_different_content(tmp_path):
    frames,decision=ready();snapshot=extract_snapshot(decision=decision,frames=frames,dataset_id="d",config_hash="c");store=DatasetStore(tmp_path);store.save("d",[snapshot],{"dataset_id":"d","frozen":True},{"validation":{}});changed=replace(snapshot,features={**snapshot.features,"returns_5":99})
    try:store.save("d",[changed],{"dataset_id":"d","frozen":True},{"validation":{}})
    except RuntimeError as error:assert "cannot be overwritten" in str(error)
    else:raise AssertionError("Frozen dataset was overwritten")


def test_additional_symbol_requires_identical_semantics():
    reference={key:"same" for key in ("family_adapter","structure_definitions","setup_lifecycle","entry_construction","stop_construction","target_hierarchy","feature_semantics")}|{"tick_normalized":True,"volatility_normalized":True};candidate={**reference,"target_hierarchy":"different"};result=audit_symbol_compatibility(candidate,reference)
    assert not result["compatible"] and any(row["name"]=="target_hierarchy" for row in result["blocking_requirements"])

def test_90_day_period_selection_is_deterministic_and_utc_aligned():
    one=deterministic_period(90,"2026-07-20T05:47:41Z");two=deterministic_period(90,"2026-07-20T05:47:41Z")
    assert one==two and one[1]-one[0]==pd.Timedelta(days=90) and one[1].minute%5==0

def test_paused_and_uninterrupted_builds_match():
    frames,decision=ready();config={"sequence_length":64,"snapshot_policy":"every_stage_transition","checkpoint_every_candles":100,"expiration_candles":12};pause=threading.Event();pause.set()
    timer=threading.Timer(.02,pause.clear);timer.start()
    def pipeline(**kwargs):return {**decision,"meta":{**decision["meta"],"analysis_time":str(kwargs["analysis_time"])}}
    paused,_=build_dataset_from_frames(dataset_id="paused",frames=frames,config=config,pipeline=pipeline,pause=pause,cancel=threading.Event());timer.join();continuous,_=build_dataset_from_frames(dataset_id="continuous",frames=frames,config=config,pipeline=pipeline,cancel=threading.Event())
    assert [row.features for row in paused]==[row.features for row in continuous]

def test_permanent_live_pressure_is_bounded(monkeypatch):
    frames,decision=ready();config={"sequence_length":64,"snapshot_policy":"every_stage_transition","checkpoint_every_candles":100,"expiration_candles":12,"maximum_live_yield_seconds":.01};monkeypatch.setattr("ml.dataset_builder._live_pressure",lambda _config:True)
    snapshots,_=build_dataset_from_frames(dataset_id="responsive",frames=frames,config=config,pipeline=lambda **kwargs:{**decision,"meta":{**decision["meta"],"analysis_time":str(kwargs["analysis_time"])}})
    assert snapshots
