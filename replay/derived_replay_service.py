from __future__ import annotations
import hashlib,json,os,platform,subprocess,threading
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from models.derived_replay_models import DerivedReplayRun
from replay.derived_replay_store import DerivedReplayStore
from replay.derived_replay_dataset import build_replay_dataset
from replay.derived_replay_checkpoint import validate_checkpoint
from replay.derived_replay_pipeline import DerivedReplayPipeline
from replay.derived_replay_report import build_replay_report
from replay.derived_replay_validator import validate_dataset
from providers.runtime_health import runtime_health

def _execute_replay_process(database_path,run_id,start):
    store=DerivedReplayStore(database_path);run=store.run(run_id)
    if not run:return
    dataset,rows=store.load_dataset(run["dataset_id"]);configuration=json.loads(run["configuration_json"])
    pipeline=DerivedReplayPipeline(store,run,dataset,rows,configuration,cancel_event=None)
    try:pipeline.run_all(start)
    except Exception as error:store.update_run(run_id,status="failed",error=f"{type(error).__name__}: {error}")

def load_replay_config():
    try:
        text=(Path(__file__).resolve().parents[1]/"config"/"derived_replay.yaml").read_text();return json.loads(text)["derived_replay"]
    except (OSError,ValueError,KeyError):return {"enabled":False}

def configuration_hash(configuration):return hashlib.sha256(json.dumps(configuration,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def code_version():
    root=Path(__file__).resolve().parents[2]
    try:
        commit=subprocess.run(["git","rev-parse","HEAD"],cwd=root,text=True,capture_output=True,timeout=2).stdout.strip() or "unavailable";dirty=bool(subprocess.run(["git","status","--porcelain"],cwd=root,text=True,capture_output=True,timeout=2).stdout.strip()) if commit!="unavailable" else None
    except (OSError,subprocess.SubprocessError):commit="unavailable";dirty=None
    return {"git_commit":commit,"dirty":dirty,"application_version":"derived-replay-v1","python_version":platform.python_version(),"strategy_registry_version":"derived-v1","database_schema_version":1}

class DerivedReplayService:
    def __init__(self,store=None,config=None):
        self.config=config or load_replay_config();self.store=store or DerivedReplayStore(os.getenv("DERIVED_REPLAY_DB",self.config.get("database_path","data/derived_replay.db")));self.executor=ProcessPoolExecutor(max_workers=1);self.jobs={};self.lock=threading.RLock()
    def create_run(self,*,provider_symbol,display_name,family,candles,base_timeframe=None,strategy="Auto",metadata=None,start_time=None,end_time=None,background=True):
        if not self.config.get("enabled",True):raise RuntimeError("Derived replay is disabled.")
        active=sum(row["status"] in {"pending","running","paused"} for row in self.store.runs())
        if active>=int(self.config.get("maximum_concurrent_runs",1)):raise RuntimeError("The bounded replay queue is full.")
        if start_time or end_time:
            import pandas as pd
            source=candles.copy() if hasattr(candles,"copy") else pd.DataFrame(candles or []);times=pd.to_datetime(source["time"],unit="s",utc=True,errors="coerce") if pd.api.types.is_numeric_dtype(source["time"]) else pd.to_datetime(source["time"],utc=True,errors="coerce")
            if start_time:source=source[times>=pd.Timestamp(start_time)];times=times[times>=pd.Timestamp(start_time)]
            if end_time:source=source[times<pd.Timestamp(end_time)]
            candles=source
        dataset,rows=build_replay_dataset(provider_symbol=provider_symbol,display_name=display_name,family=family,candles=candles,base_timeframe=base_timeframe or self.config.get("default_base_timeframe","M1"),metadata=metadata)
        validation=validate_dataset(dataset)
        if not validation["valid"]:raise ValueError(" ".join(validation["errors"]))
        self.store.save_dataset(dataset,rows);effective=json.loads(json.dumps(self.config));cfg_hash=configuration_hash(effective);version=code_version();version_text=json.dumps(version,sort_keys=True,separators=(",",":"));identity=[dataset.dataset_id,strategy,cfg_hash,version_text,start_time or dataset.start_time,end_time or dataset.end_time];run_id="replay-"+hashlib.sha256(json.dumps(identity,separators=(",",":")).encode()).hexdigest()[:24];started=dataset.start_time
        run=DerivedReplayRun(run_id,dataset.dataset_id,provider_symbol,family,strategy.lower(),start_time or dataset.start_time,end_time or dataset.end_time,cfg_hash,version_text,0,started,None,"pending");self.store.create_run(run,effective);pipeline=DerivedReplayPipeline(self.store,run.as_dict(),dataset.as_dict(),rows,effective, cancel_event=threading.Event())
        with self.lock:self.jobs[run_id]=pipeline
        if background:
            future=self.executor.submit(_execute_replay_process,str(self.store.path),run_id,0);self.jobs[run_id]=future;runtime_health.worker.update({"state":"running","queue_depth":0});future.add_done_callback(lambda _future: runtime_health.worker.update({"state":"idle","queue_depth":0}))
        else:self._execute(run_id,pipeline,0)
        return self.get_run(run_id)
    def _execute(self,run_id,pipeline,start):
        try:pipeline.run_all(start)
        except Exception as error:self.store.update_run(run_id,status="failed",error=f"{type(error).__name__}: {error}")
    def get_run(self,run_id):
        row=self.store.run(run_id)
        if not row:return None
        row.pop("configuration_json",None);return row
    def list_runs(self):
        rows=self.store.runs()
        for row in rows:row.pop("configuration_json",None)
        return rows
    def pause(self,run_id):
        if not self.get_run(run_id):raise KeyError("Replay run is not active.")
        self.store.update_run(run_id,status="paused");runtime_health.worker["state"]="paused";return self.get_run(run_id)
    def resume(self,run_id):
        job=self.jobs.get(run_id)
        if job and not job.done():self.store.update_run(run_id,status="running");runtime_health.worker["state"]="running";return self.get_run(run_id)
        run=self.store.run(run_id)
        if not run:raise KeyError("Replay run not found.")
        dataset,rows=self.store.load_dataset(run["dataset_id"]);checkpoint=self.store.latest_checkpoint(run_id)
        if checkpoint:validate_checkpoint(checkpoint,run["configuration_hash"],dataset["checksum"])
        checkpoint_start=(int(checkpoint["replay_candle_index"])+1) if checkpoint else 0;start=max(checkpoint_start,int(run.get("current_index",-1))+1);future=self.executor.submit(_execute_replay_process,str(self.store.path),run_id,start);self.jobs[run_id]=future;self.store.update_run(run_id,status="running");runtime_health.worker.update({"state":"running","queue_depth":0,"progress":None});future.add_done_callback(lambda _future: runtime_health.worker.update({"state":"idle","queue_depth":0}));return self.get_run(run_id)
    def cancel(self,run_id):
        self.store.update_run(run_id,status="cancelled");runtime_health.worker["state"]="idle";return self.get_run(run_id)
    def records(self,run_id,kind):return self.store.rows("replay_"+kind,run_id)
    def progress(self,run_id):
        run=self.get_run(run_id)
        if not run:raise KeyError("Replay run not found.")
        dataset,_=self.store.load_dataset(run["dataset_id"]);count=max(1,dataset["candle_count"]);decisions=len(self.records(run_id,"decisions"));outcomes=self.records(run_id,"outcomes");rs=[x.get("realized_r") for x in outcomes if x.get("realized_r") is not None]
        result={"replay_run_id":run_id,"status":run["status"],"current_index":run["current_index"],"total_candles":count,"progress_percent":round(100*max(0,run["current_index"]+1)/count,4),"current_replay_date":run.get("current_time"),"decisions":decisions,"filled_trades":sum(bool(x.get("entry_filled")) for x in outcomes),"realized_r":sum(float(x) for x in rs)};runtime_health.worker.update({"state":"running" if run["status"]=="running" else run["status"],"progress":result["progress_percent"]});return result
    def report(self,run_id):
        run=self.get_run(run_id)
        if not run:raise KeyError("Replay run not found.")
        dataset,_=self.store.load_dataset(run["dataset_id"]);return build_replay_report(run,dataset,self.records(run_id,"decisions"),self.records(run_id,"setups"),self.records(run_id,"outcomes"),[x["payload"] for x in self.records(run_id,"excursions")],dataset.get("warnings"))
    def validate(self,run_id):
        run=self.get_run(run_id);dataset,_=self.store.load_dataset(run["dataset_id"]);return {**validate_dataset(type("Dataset",(),dataset)()),"replay_run_id":run_id,"configuration_hash":run["configuration_hash"],"code_version":json.loads(run["code_version"])}
