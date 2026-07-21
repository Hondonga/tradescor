from __future__ import annotations
import hashlib,json,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import pandas as pd

from analysis.analysis_priority import coordinator
from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback
from ml.dataset_store import DatasetStore
from ml.dataset_validator import validate_snapshots,chronological_splits
from ml.dataset_validator import validate_split_isolation
from ml.dataset_report import build_report
from ml.dataset_audit import chronological_blocks,feature_quality,sequence_quality,outcome_quality
from ml.training_readiness import evaluate_training_readiness
from ml.feature_extractor import extract_snapshot
from ml.feature_schema import SCHEMA_VERSION,ENGINE_VERSION,schema_hash
from ml.outcome_labeler import label_trade_plan,label_progression
from replay.derived_replay_dataset import acquire_deriv_dataset
from analysis.volatility_latest_setup_search import _cached_dataset
from providers.runtime_health import runtime_health
from validation.volatility75_frequency_audit import run as run_frequency_audit

APPLICATION_VERSION="tradescor-smc-ml-foundation-v1"

class MLDatasetService:
    def __init__(self,provider_factory,root="data/ml",config_path="config/ml_dataset.yaml"):
        self.provider_factory=provider_factory;self.store=DatasetStore(root);self.config_path=Path(config_path);self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix="ml-dataset");self.jobs={};self.lock=threading.RLock();self._restore_jobs()
    def build(self,options=None):
        config=_config(self.config_path,options);start,end=deterministic_period(config["period_days"]);config_hash=_hash(config);dataset_id="ml-r75-"+hashlib.sha256(json.dumps([start.isoformat(),end.isoformat(),config_hash]).encode()).hexdigest()[:20]
        job={"dataset_id":dataset_id,"symbol":"R_75","strategy":"volatility_structure_pullback","period_days":config["period_days"],"state":"queued","processed_candles":0,"total_candles":0,"snapshots":0,"unique_setups":0,"trade_ready_examples":0,"resolved_examples":0,"leakage_violations":0,"checksum":None,"error":None,"pause":threading.Event(),"cancel":threading.Event(),"config":config,"start":start.isoformat(),"end":end.isoformat(),"current_decision_time":None,"eta_seconds":None,"worker_state":"queued"}
        with self.lock:
            if any(row["state"] in {"queued","running","paused"} for row in self.jobs.values()):raise RuntimeError("An ML dataset build is already active.")
            self.jobs[dataset_id]=job
        job["future"]=self.executor.submit(self._run,job);return self.progress(dataset_id)
    def list(self):
        stored={row["dataset_id"]:row for row in self.store.list()}
        with self.lock:
            for key,job in self.jobs.items():stored[key]={**stored.get(key,{}),**self._public(job)}
        return sorted(stored.values(),key=lambda row:row.get("dataset_id",""),reverse=True)
    def get(self,dataset_id):
        with self.lock:job=self.jobs.get(dataset_id)
        try:manifest=self.store.manifest(dataset_id)
        except FileNotFoundError:manifest=None
        if not job and not manifest:raise KeyError(dataset_id)
        return {"progress":self._public(job) if job else {"dataset_id":dataset_id,"state":"completed"},"manifest":manifest}
    def progress(self,dataset_id):
        with self.lock:job=self.jobs.get(dataset_id)
        if not job:raise KeyError(dataset_id)
        return self._public(job)
    def action(self,dataset_id,action):
        with self.lock:job=self.jobs.get(dataset_id)
        if not job:raise KeyError(dataset_id)
        if action=="pause" and job["state"]=="running":job["pause"].set();job["state"]="paused"
        elif action=="resume" and job["state"]=="paused":
            job["pause"].clear();job["state"]="running"
            if not job.get("future") or job["future"].done():job["future"]=self.executor.submit(self._run,job)
        elif action=="cancel" and job["state"] in {"queued","running","paused"}:job["cancel"].set();job["pause"].clear();job["state"]="cancelled"
        return self._public(job)
    def report(self,dataset_id):return self.store.report(dataset_id)
    def validate(self,dataset_id):
        manifest=self.store.manifest(dataset_id);report=self.store.report(dataset_id);return {"dataset_id":dataset_id,"valid":manifest.get("leakage_violations")==0 and not report["validation"].get("violations"),"manifest_checksum":manifest["checksum"],"validation":report["validation"]}
    def _public(self,job):return {key:job.get(key) for key in ("dataset_id","symbol","strategy","period_days","state","processed_candles","total_candles","snapshots","unique_setups","trade_ready_examples","resolved_examples","leakage_violations","checksum","error","current_decision_time","eta_seconds","worker_state","training_readiness","missing_intervals","duplicate_snapshots","unresolved_labels","buy_resolved","sell_resolved","positive_outcomes","negative_outcomes","independent_periods")}
    def _restore_jobs(self):
        for path in self.store.checkpoints.glob("*.json"):
            try:
                checkpoint=json.loads(path.read_text())
                if checkpoint.get("completed"):continue
                config=checkpoint["config"];self.jobs[checkpoint["dataset_id"]]={"dataset_id":checkpoint["dataset_id"],"symbol":"R_75","strategy":"volatility_structure_pullback","period_days":config["period_days"],"state":"paused","processed_candles":checkpoint.get("processed_candles",0),"total_candles":checkpoint.get("total_candles",0),"snapshots":checkpoint.get("snapshot_count",0),"unique_setups":checkpoint.get("setup_count",0),"trade_ready_examples":checkpoint.get("trade_ready_examples",0),"resolved_examples":0,"leakage_violations":0,"checksum":None,"error":None,"pause":threading.Event(),"cancel":threading.Event(),"config":config,"start":checkpoint["start"],"end":checkpoint["end"],"current_decision_time":checkpoint.get("decision_time"),"eta_seconds":None,"worker_state":"checkpoint_paused"};self.jobs[checkpoint["dataset_id"]]["pause"].set()
            except Exception:continue
    def _run(self,job):
        try:
            job["state"]="running";start=pd.Timestamp(job["start"]);end=pd.Timestamp(job["end"]);cached=_cached_dataset(Path("data/replay_datasets"),start,end)
            if cached:descriptor,m1=cached
            else:
                provider=self.provider_factory();descriptor,m1=acquire_deriv_dataset(provider,provider_symbol="R_75",display_name="Volatility 75 Index",family="VOLATILITY",start_time=start,end_time=end,base_timeframe="M1",cache_dir="data/replay_datasets")
            m1=_times(m1);m5=_resample(m1,"5min");m15=_resample(m1,"15min");h1=_resample(m1,"1h");job["total_candles"]=len(m5)
            coverage=_coverage(m1,job["start"],job["end"]);started=time.monotonic()
            def progress(**values):
                job.update(values);processed=max(job.get("processed_candles",0),1);job["eta_seconds"]=max(0,(time.monotonic()-started)/processed*(len(m5)-processed));job["worker_state"]="yielding_for_live" if _live_pressure(job["config"]) else "processing"
            checkpoint=self.store.checkpoint(job["dataset_id"]) or {};candidate_indices=checkpoint.get("candidate_indices")
            if candidate_indices is None:
                job["worker_state"]="candidate_scan";audit_input=self.store.checkpoints/f"{job['dataset_id']}-audit-m5.json";m5[["time","open","high","low","close"]].to_json(audit_input,orient="records",date_unit="ms")
                def audit_progress(processed,total,ready):progress(processed_candles=processed,current_decision_time=str(m5.iloc[min(processed,total)-1].time),snapshots=checkpoint.get("snapshot_count",0),unique_setups=checkpoint.get("setup_count",0),trade_ready_examples=ready,worker_state="candidate_scan")
                audit=run_frequency_audit(audit_input,output_path=self.store.checkpoints/f"{job['dataset_id']}-audit.json",progress_callback=audit_progress,cancel_event=job["cancel"]);candidate_indices=audit.get("snapshot_candidate_indices",[]);audit_input.unlink(missing_ok=True)
                if job["cancel"].is_set():job["state"]="cancelled";return
            snapshots,decisions=build_dataset_from_frames(dataset_id=job["dataset_id"],frames={"M1":m1,"M5":m5,"M15":m15,"H1":h1},config=job["config"],progress=progress,pause=job["pause"],cancel=job["cancel"],store=self.store,start=job["start"],end=job["end"],candidate_indices=candidate_indices)
            if job["cancel"].is_set():job["state"]="cancelled";return
            snapshots=_labels(snapshots,decisions,m5,job["config"]);blocks=chronological_blocks(snapshots,job["start"],job["end"],job["config"]["chronological_block_days"]);snapshots=_weight_metadata(snapshots,blocks);validation=validate_snapshots(snapshots);splits=chronological_splits(snapshots,purge_overlap=True);split_violations=validate_split_isolation(splits);validation["violations"].extend(split_violations);validation["valid"]=not validation["violations"];quality=feature_quality(snapshots,splits);sequences=sequence_quality(snapshots);outcomes=outcome_quality(snapshots,blocks);readiness=evaluate_training_readiness(snapshots,validation,blocks,job["config"]["readiness_minimums"]);report=build_report(snapshots,len(m1),splits,validation);report.update({"provider_coverage":coverage,"chronological_blocks":blocks,"feature_quality_audit":quality,"sequence_quality_audit":sequences,"outcome_quality_audit":outcomes,"training_readiness":readiness,"duplicate_snapshot_count":sum(row.get("code")=="DUPLICATE_SNAPSHOT_IDS" for row in validation["violations"]),"sample_weight_metadata_prepared":True,"training_performed":False});candle_checksum=_candle_checksum(m1);setups={row.metadata.get("setup_id") or row.metadata.get("structural_context_id") for row in snapshots};directions={key:{row.metadata.get("setup_id") or row.metadata.get("structural_context_id") for row in snapshots if row.metadata["direction"]==key} for key in ("buy","sell")};manifest={"dataset_id":job["dataset_id"],"schema_version":SCHEMA_VERSION,"symbol":"R_75","strategy":"volatility_structure_pullback","period":{"requested_start":job["start"],"requested_end":job["end"],"actual_start":coverage["actual_start"],"actual_end":coverage["actual_end"],"selection":"fixed_trailing_calendar_period","days":job["period_days"]},"coverage":coverage,"splits":{key:{"rows":len(value),"start":value[0].metadata["decision_time"] if value else None,"end":value[-1].metadata["decision_time"] if value else None,"shuffled":False,"untouched":key=="test","purged_sequence_overlap":True} for key,value in splits.items()},"rows":len(snapshots),"setups":len(setups),"buy_setups":len(directions["buy"]),"sell_setups":len(directions["sell"]),"trade_ready_rows":sum(row.metadata["trade_ready"] for row in snapshots),"resolved_rows":sum(bool(row.labels.get("outcome_label")) for row in snapshots),"checksum":"","candle_checksum":candle_checksum,"config_hash":_hash(job["config"]),"feature_schema_hash":schema_hash(),"application_version":APPLICATION_VERSION,"engine_version":ENGINE_VERSION,"source_dataset_id":descriptor.dataset_id,"source":"real_deriv_public_m1","leakage_violations":validation["leakage_violations"],"training_allowed":False,"training_readiness":readiness,"immutable":True,"frozen":True}
            manifest=self.store.save(job["dataset_id"],snapshots,manifest,report);self.store.save_checkpoint(job["dataset_id"],{"dataset_id":job["dataset_id"],"completed":True,"final_checksum":manifest["checksum"]});gate={row["name"]:row["current"] for row in readiness["requirements"]};job.update(state="completed",worker_state="idle",eta_seconds=0,processed_candles=len(m5),snapshots=len(snapshots),unique_setups=len(setups),trade_ready_examples=manifest["trade_ready_rows"],resolved_examples=manifest["resolved_rows"],leakage_violations=validation["leakage_violations"],checksum=manifest["checksum"],training_readiness=readiness,missing_intervals=coverage["missing_m1_count"],duplicate_snapshots=report["duplicate_snapshot_count"],unresolved_labels=report["unresolved_label_count"],buy_resolved=gate["minimum_buy_resolved"],sell_resolved=gate["minimum_sell_resolved"],positive_outcomes=gate["minimum_positive_outcomes"],negative_outcomes=gate["minimum_negative_outcomes"],independent_periods=gate["minimum_independent_market_periods"])
        except Exception as exc:job.update(state="error",error=str(exc))

def build_dataset_from_frames(*,dataset_id,frames,config,progress=None,pause=None,cancel=None,store=None,pipeline=evaluate_volatility_structure_pullback,start=None,end=None,candidate_indices=None):
    m5=frames["M5"];m15=frames["M15"];h1=frames["H1"];checkpoint=store.checkpoint(dataset_id) if store else None;snapshots=[];decisions={};seen=set();start_index=60;last_stage=None;last_direction=None;last_m15={}
    if checkpoint and checkpoint.get("config_hash")==_hash(config) and not checkpoint.get("completed"):
        snapshots=[_snapshot_from_payload(row) for row in checkpoint.get("snapshots",[])];decisions={key:_compact_decision(value) for key,value in (checkpoint.get("decisions") or {}).items()};seen={(row.metadata.get("setup_id") or row.metadata["structural_context_id"],row.metadata["stage"]) for row in snapshots};start_index=max(60,int(checkpoint.get("processed_candles",60)));state=checkpoint.get("incremental_state") or {};last_stage=(state.get("active_setup") or {}).get("stage");last_direction=(state.get("h1") or {}).get("direction");last_m15=state.get("m15") or {}
    indices=[int(value) for value in candidate_indices if int(value)>=start_index] if candidate_indices is not None else range(start_index,len(m5));last_checkpoint_index=start_index;live_yield_suspended=False
    for index in indices:
        if cancel and cancel.is_set():break
        while pause and pause.is_set() and not (cancel and cancel.is_set()):time.sleep(.1)
        pressure=coordinator.should_yield_research() or _live_pressure(config)
        if not pressure:live_yield_suspended=False
        elif not live_yield_suspended:
            deadline=time.monotonic()+float(config.get("maximum_live_yield_seconds",.5))
            while (coordinator.should_yield_research() or _live_pressure(config)) and time.monotonic()<deadline and not (cancel and cancel.is_set()):time.sleep(.05)
            live_yield_suspended=coordinator.should_yield_research() or _live_pressure(config)
        at=m5.iloc[index].time;batch=int(config.get("maximum_processing_batch",config["checkpoint_every_candles"]));history=m5.iloc[max(0,index-20):index+1];m15_now=m15[m15.time<=at].tail(32)
        if candidate_indices is None and not (_analysis_event(history,m15_now,index,last_stage,last_direction,last_m15) or index%batch==0):continue
        cut={"M5":m5.iloc[max(0,index-220):index+1],"M15":m15[m15.time<=at].tail(180),"H1":h1[h1.time<=at].tail(120)};decision=pipeline(symbol="R_75",display_symbol="Volatility 75 Index",candles_by_timeframe=cut,tick_size=.01,analysis_time=at,requested_model="smc_auto",source_timeframe="M1");last_stage=(decision.get("setup") or {}).get("stage");last_direction=((decision.get("diagnostics") or {}).get("h1") or {}).get("direction");last_m15=(decision.get("diagnostics") or {}).get("m15") or {};snapshot=extract_snapshot(decision=decision,frames=cut,dataset_id=dataset_id,config_hash=_hash(config),sequence_length=config["sequence_length"])
        if snapshot and _policy(snapshot,config["snapshot_policy"]):
            group=snapshot.metadata.get("setup_id") or snapshot.metadata["structural_context_id"];key=(group,snapshot.metadata["stage"])
            if key not in seen:snapshots.append(snapshot);decisions[snapshot.metadata["snapshot_id"]]=_compact_decision(decision);seen.add(key)
        if progress and (index%25==0 or index+1==len(m5)):progress(processed_candles=index+1,current_decision_time=str(at),snapshots=len(snapshots),unique_setups=len({x.metadata.get("setup_id") or x.metadata["structural_context_id"] for x in snapshots}),trade_ready_examples=sum(x.metadata["trade_ready"] for x in snapshots))
        if store and index and index-last_checkpoint_index>=batch:
            partial_hash=_hash([row.metadata["snapshot_id"] for row in snapshots]);payload={"dataset_id":dataset_id,"processed_candles":index+1,"total_candles":len(m5),"decision_time":str(at),"config_hash":_hash(config),"config":config,"start":start,"end":end,"snapshot_count":len(snapshots),"setup_count":len({x.metadata.get("setup_id") or x.metadata["structural_context_id"] for x in snapshots}),"trade_ready_examples":sum(x.metadata["trade_ready"] for x in snapshots),"partial_artifact_checksums":{"snapshots":partial_hash},"incremental_state":_incremental_state(decision),"snapshots":[_snapshot_payload(row) for row in snapshots],"decisions":decisions,"candidate_indices":list(candidate_indices) if candidate_indices is not None else None};payload["checkpoint_hash"]=_hash(payload);store.save_checkpoint(dataset_id,payload);last_checkpoint_index=index
            if config.get("yield_between_batches",True):time.sleep(0)
    return snapshots,decisions
def _labels(snapshots,decisions,m5,config):
    output=[]
    for index,snapshot in enumerate(snapshots):
        decision=decisions[snapshot.metadata["snapshot_id"]];future=m5[m5.time>pd.Timestamp(snapshot.metadata["decision_time"])]
        labels=label_trade_plan(decision,future,config["expiration_candles"]) if snapshot.metadata["trade_ready"] else {**label_progression(snapshot,snapshots[index+1:]),"outcome_label":None}
        output.append(replace(snapshot,labels=labels))
    return output
def _policy(snapshot,policy):return snapshot.metadata["trade_ready"] if policy=="trade_ready_only" else True
def _config(path,options=None):
    config=json.loads(path.read_text());config.update(options or {})
    if config["snapshot_policy"] not in {"trade_ready_only","developing_and_trade_ready","every_stage_transition"}:raise ValueError("Unsupported snapshot policy.")
    if int(config["period_days"])<1:raise ValueError("period_days must be positive.")
    return config
def _hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def deterministic_period(days,end_time=None):
    end=pd.Timestamp(end_time) if end_time is not None else pd.Timestamp.now(tz="UTC")
    if end.tzinfo is None:end=end.tz_localize("UTC")
    else:end=end.tz_convert("UTC")
    end=end.floor("5min");return end-pd.Timedelta(days=int(days)),end
def _times(rows):
    x=rows.copy()
    if pd.api.types.is_datetime64_any_dtype(x.time):x["time"]=pd.to_datetime(x.time,utc=True)
    else:
        v=pd.to_numeric(x.time,errors="coerce");x["time"]=pd.to_datetime(v,unit="s" if v.max()<1e12 else "ms",utc=True)
    x["complete"]=True;return x.sort_values("time").reset_index(drop=True)
def _resample(rows,rule):
    x=rows.set_index("time").resample(rule,label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index();x["complete"]=True;return x
def _candle_checksum(rows):return hashlib.sha256(rows[["time","open","high","low","close"]].to_json(orient="records",date_format="iso",double_precision=15).encode()).hexdigest()
def _snapshot_payload(row):return {"metadata":row.metadata,"features":row.features,"sequence":row.sequence,"available_at_time":row.available_at_time,"labels":row.labels}
def _snapshot_from_payload(row):
    from ml.models import FeatureSnapshot
    return FeatureSnapshot(row["metadata"],row["features"],row["sequence"],row["available_at_time"],row.get("labels") or {})
def _compact_decision(decision):return {"meta":{"analysis_time":(decision.get("meta") or {}).get("analysis_time")},"decision":{"direction":(decision.get("decision") or {}).get("direction"),"trade_ready":bool((decision.get("decision") or {}).get("trade_ready"))},"trade_plan":decision.get("trade_plan") or {"available":False,"targets":[]}}
def _incremental_state(decision):
    diagnostics=decision.get("diagnostics") or {};setup=decision.get("setup") or {};h1=diagnostics.get("h1") or {};m15=diagnostics.get("m15") or {};m5=diagnostics.get("m5") or {}
    return {"h1":{"direction":h1.get("direction"),"recent_condition":h1.get("recent_condition"),"last_break":h1.get("last_break")},"m15":{"condition":m15.get("condition"),"pullback":m15.get("pullback"),"valid_location":m15.get("valid_location"),"depth":m15.get("depth")},"m5":{"confirmation":m5.get("confirmation"),"entry_zone":m5.get("entry_zone"),"entry":m5.get("entry"),"stop":m5.get("stop")},"active_setup":{"setup_id":setup.get("setup_id"),"stage":setup.get("stage"),"direction":setup.get("direction"),"trade_ready":setup.get("trade_ready")}}
def _coverage(rows,requested_start,requested_end):
    times=pd.to_datetime(rows.time,utc=True);duplicates=int(times.duplicated().sum());unique=times.drop_duplicates().sort_values();missing=[]
    for left,right in zip(unique.iloc[:-1],unique.iloc[1:]):
        gap=int((right-left).total_seconds()//60)-1
        if gap>0:missing.append({"after":left.isoformat(),"before":right.isoformat(),"missing_count":gap})
    return {"requested_start":str(requested_start),"requested_end":str(requested_end),"actual_start":unique.iloc[0].isoformat() if len(unique) else None,"actual_end":unique.iloc[-1].isoformat() if len(unique) else None,"total_m1_candles":len(rows),"missing_m1_intervals":missing,"missing_m1_count":sum(row["missing_count"] for row in missing),"duplicate_intervals":duplicates}
def _live_pressure(config):
    health=runtime_health.snapshot();provider=(health.get("providers") or {}).get("deriv") or {};latency=(health.get("latency") or {}).get("flask_request_ms") or 0;history=(health.get("historical_worker") or {}).get("state")
    return provider.get("state") in {"reconnecting","connecting"} or history in {"loading","running"} or float(latency)>float(config.get("live_latency_threshold_ms",750))
def _weight_metadata(snapshots,blocks):
    counts={};
    for row in snapshots:
        key=row.metadata.get("setup_id") or row.metadata.get("structural_context_id");counts[key]=counts.get(key,0)+1
    output=[]
    for row in snapshots:
        key=row.metadata.get("setup_id") or row.metadata.get("structural_context_id");at=pd.Timestamp(row.metadata["decision_time"]);block=next((item["block_id"] for item in blocks if pd.Timestamp(item["start"])<=at<pd.Timestamp(item["end"])),None);metadata={**row.metadata,"setup_snapshot_count":counts[key],"chronological_block":block,"outcome_class":row.labels.get("outcome_label"),"market_volatility_bucket":row.metadata.get("volatility_regime")};output.append(replace(row,metadata=metadata))
    return output
def _analysis_event(rows,m15,index,last_stage,direction,last_m15):
    if index%12==0 or last_stage=="WAITING_FOR_ENTRY":return True
    if index%3==0 and direction in {"bullish","bearish"} and len(m15)>=12:
        recent=m15.tail(32);low=float(recent.low.min());high=float(recent.high.max());current=float(recent.iloc[-1].close);depth=(high-current)/max(high-low,1e-12) if direction=="bullish" else (current-low)/max(high-low,1e-12);pullback=depth>=.18;valid=pullback and depth<=.78
        if pullback!=bool(last_m15.get("pullback")) or valid!=bool(last_m15.get("valid_location")):return True
    if len(rows)<14:return True
    row=rows.iloc[-1];atr=float((rows.high.astype(float)-rows.low.astype(float)).tail(14).mean());body=abs(float(row.close-row.open));span=float(row.high-row.low)
    directional=(float(row.close)>float(row.open)) if direction=="bullish" else (float(row.close)<float(row.open)) if direction=="bearish" else True
    return bool(directional and atr and body/atr>=.55 and span/atr>=.75)
