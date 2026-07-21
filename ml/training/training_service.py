from __future__ import annotations
import hashlib,json,pickle,platform,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import sklearn
from sklearn.inspection import permutation_importance
from .training_config import load_config
from .dataset_loader import load_frozen_dataset,feature_columns
from .preprocessing import fit_preprocessor,transform,persist_preprocessor
from .sample_weighting import setup_equal_weights
from .dummy_baseline import build_dummy_majority,build_dummy_prior
from .logistic_model import build_logistic
from .gradient_boosting_model import build_gradient_boosting
from .calibration import calibrate_prefit
from .evaluator import classification_metrics
from .threshold_selection import select_threshold
from .trading_comparison import trading_metrics
from .model_registry import ModelRegistry
from .model_report import report_html

class MLTrainingService:
    """One-worker, offline-only trainer. Test labels are opened after selection freezes."""
    def __init__(self,config_path="config/ml_training.yaml",root="data/ml"):
        self.config_path=config_path;self.registry=ModelRegistry(root);self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix="ml-training");self._lock=threading.Lock();self._cancel=set()
    def start(self,payload=None):
        config=load_config(self.config_path);dataset_id=(payload or {}).get("dataset_id",config["dataset_id"])
        if dataset_id!=config["dataset_id"]:raise ValueError("Only the configured frozen dataset may be trained.")
        run_id="ml-run-"+uuid.uuid4().hex[:16];run={"run_id":run_id,"dataset_id":dataset_id,"state":"queued","stage":"queued","progress":0,"created_at":_now(),"live_activation_available":False};self.registry.save_run(run);self.executor.submit(self._train,run_id,config);return run
    def list(self):return self.registry.list()
    def get(self,run_id):return self.registry.get(run_id)
    def cancel(self,run_id):
        self.get(run_id);self._cancel.add(run_id);run=self.get(run_id);run.update(state="cancelling",stage="cancelling");self.registry.save_run(run);return run
    def validate(self,run_id):
        run=self.get(run_id);complete=run.get("state")=="completed";return {"run_id":run_id,"valid":complete and Path(run.get("report_path","")).exists(),"dataset_checksum_verified":run.get("dataset_checksum_verified",False),"test_evaluated_after_selection_frozen":run.get("test_evaluated_after_selection_frozen",False),"paper_scoring_eligible":run.get("model_status")=="ACCEPTED_FOR_PAPER_SCORING"}
    def report(self,run_id):return self.get(run_id).get("report") or (_raise(FileNotFoundError(run_id)))
    def _save(self,run_id,**updates):
        run=self.get(run_id);run.update(updates);self.registry.save_run(run);return run
    def _check_cancel(self,run_id):
        if run_id in self._cancel:self._save(run_id,state="cancelled",stage="cancelled",finished_at=_now());raise _Cancelled()
    def _train(self,run_id,config):
        started=time.time()
        try:
            self._save(run_id,state="running",stage="verifying frozen dataset",progress=5);data,manifest,exclusions=load_frozen_dataset(config);self._check_cancel(run_id)
            features=feature_columns();train=data[data.split.eq("train")];validation=data[data.split.eq("validation")];test=data[data.split.eq("test")]
            self._save(run_id,stage="fitting train-only preprocessing",progress=15,dataset_checksum_verified=True,split_counts={x:len(y) for x,y in data.groupby("split")},excluded_samples=len(exclusions))
            pre=fit_preprocessor(train,features);x_train=_dense(transform(pre,train,features));x_validation=_dense(transform(pre,validation,features));weights=setup_equal_weights(train);y_train=train.target.to_numpy();y_validation=validation.target.to_numpy();self._check_cancel(run_id)
            artifact_dir=self.registry.models/run_id;artifact_dir.mkdir(parents=True,exist_ok=False);persist_preprocessor(pre,artifact_dir/"preprocessor.pkl");train.assign(training_weight=weights).loc[:,["snapshot_id","setup_id","training_weight"]].to_parquet(artifact_dir/"training_weights.parquet",index=False)
            specs=[("dummy_majority",build_dummy_majority(),None),("dummy_prior",build_dummy_prior(),None),("logistic_unweighted",build_logistic(seed=config["random_seed"]),None),("logistic_balanced",build_logistic("balanced",config["random_seed"]),None),("logistic_setup_weighted",build_logistic(seed=config["random_seed"]),weights),("gradient_boosting",build_gradient_boosting(config["gradient_boosting"],config["random_seed"]),weights)]
            candidates=[]
            for index,(name,model,sample_weight) in enumerate(specs):
                self._save(run_id,stage=f"training {name}",current_model=name,progress=20+index*9);fit_kwargs={"sample_weight":sample_weight.to_numpy()} if sample_weight is not None else {};model.fit(x_train,y_train,**fit_kwargs);raw=model.predict_proba(x_validation)[:,1]
                methods=["none"] if name.startswith("dummy") else config["calibration_methods"]
                for method in methods:
                    calibrated=calibrate_prefit(model,x_validation,y_validation,method);prob=calibrated.predict_proba(x_validation)[:,1];metrics=classification_metrics(y_validation,prob);threshold,thresholds=select_threshold(validation,prob,config);candidates.append({"name":name,"calibration":method,"base_model":model,"model":calibrated,"raw_probability":raw,"probability":prob,"metrics":metrics,"threshold":threshold,"threshold_table":thresholds})
                self._check_cancel(run_id)
            eligible=[row for row in candidates if not row["name"].startswith("dummy")];best=max(eligible,key=lambda row:(row["metrics"]["pr_auc"],-row["metrics"]["brier_score"]));selection={"model":best["name"],"calibration":best["calibration"],"threshold":best["threshold"],"selected_using":"validation_only","frozen_at":_now()}
            self._save(run_id,stage="model selection frozen",progress=72,selection=selection,test_accessed=False);self._check_cancel(run_id)
            # The final split is transformed and evaluated only after selection is persisted above.
            x_test=_dense(transform(pre,test,features));raw_test=best["base_model"].predict_proba(x_test)[:,1];p_test=best["model"].predict_proba(x_test)[:,1];test_metrics=classification_metrics(test.target.to_numpy(),p_test,best["threshold"]);keep=p_test>=best["threshold"];smc=trading_metrics(test);ml=trading_metrics(test,keep);periods={block:{"smc_only":trading_metrics(rows),"smc_plus_ml":trading_metrics(rows,p_test[test.index.get_indexer(rows.index)]>=best["threshold"])} for block,rows in test.groupby("chronological_block")}
            import pandas as pd
            pd.DataFrame({"snapshot_id":test.snapshot_id,"raw_probability":raw_test,"calibrated_probability":p_test,"accepted":keep}).to_parquet(artifact_dir/"test_predictions.parquet",index=False)
            status=_acceptance(config,best,test_metrics,smc,ml,test.loc[keep],periods,candidates);stability=_stability(test.loc[keep],periods);importance=_importance(best,x_validation,y_validation,pre,features,config["random_seed"])
            metadata={"model_id":"model-"+hashlib.sha256((run_id+best["name"]).encode()).hexdigest()[:16],"model_type":best["name"],"training_timestamp":_now(),"dataset_id":manifest["dataset_id"],"dataset_checksum":manifest["checksum"],"feature_schema_version":manifest["schema_version"],"feature_ordering":features,"transformed_features":list(pre.get_feature_names_out()),"configuration_hash":config["config_hash"],"code_version":"tradescor-offline-baseline-v1","dependencies":{"python":platform.python_version(),"scikit_learn":sklearn.__version__,"numpy":np.__version__},"selected_threshold":best["threshold"],"calibration_method":best["calibration"]}
            (artifact_dir/"model.pkl").write_bytes(pickle.dumps(best["model"]));(artifact_dir/"metadata.json").write_text(json.dumps(metadata,indent=2,sort_keys=True)+"\n")
            report={"dataset":manifest,"target":"TP1_BEFORE_STOP","exclusions":exclusions.reason.value_counts().to_dict(),"models":[{"name":row["name"],"calibration":row["calibration"],"validation_metrics":row["metrics"],"selected_threshold":row["threshold"]} for row in candidates],"selection":selection,"validation":best["metrics"],"test":test_metrics,"smc_only":smc,"smc_plus_ml":ml,"periods":periods,"stability":stability,"feature_importance":importance,"model_status":status,"metadata":metadata}
            report_path=self.registry.reports/f"{run_id}.json";report_path.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+"\n");(self.registry.reports/f"{run_id}.html").write_text(report_html(report))
            self._save(run_id,state="completed",stage="completed",progress=100,current_model=best["name"],finished_at=_now(),elapsed_seconds=round(time.time()-started,3),model_status=status,report_path=str(report_path),artifact_path=str(artifact_dir),test_evaluated_after_selection_frozen=True,report=report)
        except _Cancelled:return
        except Exception as error:self._save(run_id,state="failed",stage="failed",error=str(error),finished_at=_now())

def _dense(value):return value.toarray() if hasattr(value,"toarray") else np.asarray(value)
def _now():return datetime.now(timezone.utc).isoformat()
def _raise(error):raise error
class _Cancelled(Exception):pass
def _stability(retained,periods):
    if len(retained)==0:return "UNSTABLE"
    totals=[abs(row["smc_plus_ml"]["total_realized_r"]) for row in periods.values()];concentration=max(totals,default=0)/max(sum(totals),1e-9)
    return "UNSTABLE" if concentration>.65 or set(retained.direction)!={"buy","sell"} else "MODERATELY_UNSTABLE" if concentration>.45 else "STABLE"
def _acceptance(config,best,test_metrics,smc,ml,retained,periods,candidates):
    dummy=max(row["metrics"]["pr_auc"] for row in candidates if row["name"].startswith("dummy"))
    if best["metrics"]["pr_auc"]<=dummy or test_metrics["pr_auc"]<config["minimum_pr_auc"]:return "REJECTED_NO_PREDICTIVE_VALUE"
    if test_metrics["brier_score"]>config["maximum_brier_score"] or test_metrics["ece"]>config["maximum_ece"]:return "REJECTED_POOR_CALIBRATION"
    if ml["trades"]<config["minimum_test_trades"] or set(retained.direction)!={"buy","sell"} or ml["expectancy"]<=smc["expectancy"] or ml["maximum_drawdown_r"]>smc["maximum_drawdown_r"]+config["maximum_drawdown_worsening_r"]:return "REJECTED_TRADING_METRICS"
    positive=sum(row["smc_plus_ml"]["total_realized_r"]>0 for row in periods.values())
    if positive<max(1,len(periods)//2):return "REJECTED_UNSTABLE_ACROSS_PERIODS"
    return "ACCEPTED_FOR_PAPER_SCORING"
def _importance(best,x,y,pre,features,seed):
    names=list(pre.get_feature_names_out());model=best["model"];base=getattr(model,"estimator",model)
    if hasattr(base,"coef_"):return [{"feature":name,"standardized_coefficient":float(value),"association":"higher" if value>0 else "lower"} for name,value in sorted(zip(names,base.coef_[0]),key=lambda row:abs(row[1]),reverse=True)]
    try:
        result=permutation_importance(model,x,y,n_repeats=5,random_state=seed,scoring="average_precision");return [{"feature":name,"permutation_importance":float(value),"wording":"Associated with predicted probability; not causal."} for name,value in sorted(zip(names,result.importances_mean),key=lambda row:row[1],reverse=True)]
    except Exception:return []
