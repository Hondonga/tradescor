"""Bounded, cancellable real-history search for the focused V75 model."""
from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback
from paper_testing.derived_fill_engine import evaluate_paper_fill
from paper_testing.derived_mfe_mae_tracker import track_mfe_mae
from paper_testing.derived_outcome_resolver import resolve_paper_outcome
from replay.derived_replay_dataset import acquire_deriv_dataset
from validation.volatility75_frequency_audit import run as run_frequency_audit


class LatestVolatilitySetupSearch:
    """One-worker search service; live Flask analysis remains independent."""

    def __init__(self, provider_factory, cache_dir="data/replay_datasets"):
        self.provider_factory = provider_factory
        self.cache_dir = Path(cache_dir)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vsp-history")
        self.jobs = {}
        self._lock = threading.Lock()

    def start(self, period_days=30):
        days = int(period_days)
        if days not in {30, 90}:
            raise ValueError("Historical inspection supports a neutral 30 or 90 day period.")
        job_id = "vsp-search-" + uuid.uuid4().hex[:16]
        job = {"job_id": job_id, "symbol": "R_75", "strategy": "volatility_structure_pullback", "period_days": days, "processed_candles": 0, "total_candles": 0, "trade_ready_found": 0, "state": "queued", "cancel": threading.Event(), "result": None, "future_candles": None, "error": None}
        with self._lock:
            self.jobs[job_id] = job
        self.executor.submit(self._run, job)
        return self.status(job_id)

    def status(self, job_id):
        job = self._job(job_id)
        return {key: job.get(key) for key in ("job_id", "symbol", "strategy", "period_days", "processed_candles", "total_candles", "trade_ready_found", "state", "error")} | {"result_available": job.get("result") is not None}

    def cancel(self, job_id):
        job = self._job(job_id); job["cancel"].set()
        if job["state"] in {"queued", "running"}: job["state"] = "cancelled"
        return self.status(job_id)

    def result(self, job_id):
        job = self._job(job_id)
        if job["state"] not in {"completed", "cancelled", "error"}: return {"progress": self.status(job_id), "result": None}
        return {"progress": self.status(job_id), "result": job.get("result")}

    def reveal(self, job_id):
        job = self._job(job_id); result = job.get("result") or {}
        decision = result.get("decision") or {}; plan = decision.get("trade_plan") or {}; later = job.get("future_candles")
        if not plan.get("available") or later is None:
            return {"available": False, "reason": "No invariant-valid historical plan is available."}
        targets = plan.get("targets") or []
        setup = {"created_at": decision["meta"]["analysis_time"], "direction": decision["decision"]["direction"], "entry": plan["entry"], "stop": plan["stop"], "tp1": targets[0]["price"], "tp2": targets[1]["price"] if len(targets) > 1 else None, "risk_points": abs(float(plan["entry"])-float(plan["stop"]))}
        fill = evaluate_paper_fill(setup, later, entry_type="confirmation_close")
        if not fill["filled"]: return {"available": True, "fill": fill, "outcome": None, "mfe_mae": None, "notice": "This information was unavailable when the setup was generated."}
        outcome = resolve_paper_outcome(setup, later, fill["fill_time"], policy="stop_first")
        return {"available": True, "fill": fill, "outcome": outcome, "mfe_mae": track_mfe_mae(setup, later, fill["fill_time"]), "notice": "This information was unavailable when the setup was generated."}

    def _job(self, job_id):
        with self._lock: job = self.jobs.get(job_id)
        if not job: raise KeyError(job_id)
        return job

    def _run(self, job):
        try:
            job["state"] = "running"
            end = pd.Timestamp.now(tz="UTC").floor("min")
            start = end - pd.Timedelta(days=job["period_days"])
            cached=_cached_dataset(self.cache_dir,start,end)
            if cached: descriptor,m1=cached
            else:
                provider = self.provider_factory()
                descriptor, m1 = acquire_deriv_dataset(provider, provider_symbol="R_75", display_name="Volatility 75 Index", family="VOLATILITY", start_time=start, end_time=end, base_timeframe="M1", cache_dir=str(self.cache_dir))
            m1 = _times(m1); m5 = _resample(m1, "5min"); m15 = _resample(m1, "15min"); h1 = _resample(m1, "1h")
            job["total_candles"] = len(m5)
            if job["cancel"].is_set(): job["state"] = "cancelled"; return
            # The event-cached audit maintains incremental H1/M15 state and only
            # evaluates M5 geometry at causal candidate events.  Every selected
            # candidate is then re-run through the public production engine.
            audit_input=self.cache_dir/f"{job['job_id']}-m5.json"; audit_output=self.cache_dir/f"{job['job_id']}-audit.json"; self.cache_dir.mkdir(parents=True,exist_ok=True); m5.to_json(audit_input,orient="records",date_format="iso")
            def progress(processed,total,found):job.update(processed_candles=processed,total_candles=total,trade_ready_found=found)
            audit=run_frequency_audit(audit_input,audit_output,progress_callback=progress,cancel_event=job["cancel"])
            if audit.get("cancelled"):job["state"]="cancelled";return
            candidates=sorted(audit.get("trade_ready_setups") or [],key=lambda row:pd.Timestamp(row["decision_time"]),reverse=True)
            latest=None;latest_index=None
            for candidate in candidates:
                if job["cancel"].is_set(): job["state"]="cancelled";return
                at=pd.Timestamp(candidate["decision_time"]);eligible=m5.index[m5.time<=at]
                if not len(eligible):continue
                index=int(eligible[-1]);frames={"M5":m5.iloc[max(0,index-220):index+1],"M15":m15[m15.time<=at].tail(180),"H1":h1[h1.time<=at].tail(120)}
                check=evaluate_volatility_structure_pullback(symbol="R_75",display_symbol="Volatility 75 Index",candles_by_timeframe=frames,tick_size=.0001,analysis_time=at,requested_model="smc_auto",source_timeframe="M1",overlay_mode="HISTORICAL_INSPECTION")
                if check["decision"].get("trade_ready"):latest=check;latest_index=index;break
            job["processed_candles"]=len(m5);job["trade_ready_found"]=int((audit.get("counts") or {}).get("trade_ready",0));counts=audit.get("counts") or {}
            final_targets=((latest or {}).get("trade_plan") or {}).get("targets") or []
            report={"period_days":job["period_days"],"completed_m1_candles":len(m1),"h1_bullish_contexts":counts.get("h1_bullish_contexts",0),"h1_bearish_contexts":counts.get("h1_bearish_contexts",0),"m15_pullbacks":counts.get("m15_pullbacks",0),"m5_displacements":counts.get("m5_displacements",0),"m5_structure_breaks":counts.get("m5_structure_breaks",0),"complete_plan_candidates":counts.get("entry_candidates",0),"tp1_candidates":counts.get("target_candidates",0),"tp2_candidates":max(sum(1 for row in candidates if row.get("tp2") is not None),int(len(final_targets)>1)),"rr_passes":counts.get("rr_passes",0),"trade_ready_setups":job["trade_ready_found"],"latest_setup_timestamp":latest["meta"]["analysis_time"] if latest else None,"dominant_blocker":audit.get("dominant_blocker"),"dataset_id":descriptor.dataset_id,"data_source_id":descriptor.metadata.get("data_source_id"),"chronological":True,"future_candles_excluded":True}
            frozen = [] if latest_index is None else _records(m5.iloc[max(0,latest_index-599):latest_index+1])
            job["future_candles"] = m5.iloc[(latest_index+1 if latest_index is not None else len(m5)):].copy()
            job["result"] = {"mode": "historical", "label": "HISTORICAL SETUP", "decision": latest, "candles": frozen, "report": report}
            job["state"] = "completed"
        except Exception as exc:
            job["error"] = str(exc); job["state"] = "error"


def _times(rows):
    rows=rows.copy()
    if pd.api.types.is_datetime64_any_dtype(rows.time):rows["time"]=pd.to_datetime(rows.time,utc=True)
    else:
        values=pd.to_numeric(rows.time,errors="coerce");rows["time"]=pd.to_datetime(values,unit="s",utc=True) if values.max()<1e12 else pd.to_datetime(values,unit="ms",utc=True)
    rows["complete"]=True;return rows.sort_values("time").reset_index(drop=True)

def _resample(rows, rule):
    result=rows.set_index("time").resample(rule,label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index(); result["complete"]=True; return result

def _records(rows):
    return [{"time":row.time.isoformat(),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close)} for _,row in rows.iterrows()]

def _cached_dataset(cache_dir,start,end):
    """Reuse a neutral-period Deriv cache when it covers all but the live edge."""
    for path in sorted(Path(cache_dir).glob("dataset-*.json"),key=lambda item:item.stat().st_mtime,reverse=True):
        try:
            rows=pd.read_json(path);normalized=_times(rows)
            if len(normalized)>=int((end-start).total_seconds()/60)-5 and normalized.iloc[0].time<=start+pd.Timedelta(minutes=5) and normalized.iloc[-1].time>=end-pd.Timedelta(minutes=10):
                descriptor=type("CachedDataset",(),{"dataset_id":path.stem,"metadata":{"data_source_id":"deriv_public_cache"}})()
                return descriptor,normalized[(normalized.time>=start)&(normalized.time<end)].reset_index(drop=True)
        except Exception:continue
    return None
