from __future__ import annotations
from dataclasses import replace
import hashlib,json,time
import pandas as pd
from analysis.derived_engine import analyze_derived_index
from analysis.derived_setup_lifecycle import clear_lifecycle
from analysis.derived_range_lock import clear_range_locks
from analysis.derived_spike_identity import clear_spikes
from analysis.derived_event_identity import clear_events
from analysis.derived_regime_hysteresis import clear_regime_hysteresis
from analysis.derived_regime_stability import clear_regime_stability
from analysis.derived_auto_router import clear_auto_continuity
from analysis.smc.smc_router import clear_smc_ownership
from analysis.smc.smc_target_engine import clear_target_lifecycle_cache
from paper_testing.derived_signal_snapshot import build_derived_signal_snapshot
from paper_testing.derived_setup_tracker import build_paper_setup
from replay.derived_replay_clock import DerivedReplayClock
from replay.derived_replay_timeframe_slicer import slice_timeframes
from replay.derived_replay_checkpoint import checkpoint_payload
from replay.derived_replay_outcome_engine import evaluate_fill,evaluate_outcome,evaluate_excursion
from replay.derived_replay_state import DerivedReplayState
from analysis.analysis_priority import coordinator

def reset_production_replay_state():
    for clear in (clear_lifecycle,clear_range_locks,clear_spikes,clear_events,clear_regime_hysteresis,clear_regime_stability,clear_auto_continuity,clear_smc_ownership,clear_target_lifecycle_cache):clear()

class DerivedReplayPipeline:
    """Candle-close orchestrator; all analytical calculations stay in production modules."""
    def __init__(self,store,run,dataset,candles,configuration,pipeline=analyze_derived_index,cancel_event=None):self.store=store;self.run=run;self.dataset=dataset;self.candles=candles;self.config=configuration;self.pipeline=pipeline;self.cancel_event=cancel_event;self.state=DerivedReplayState();self._pause=False
    def run_all(self,start_index=0):
        reset_production_replay_state();interval=60 if self.dataset["base_timeframe"]=="M1" else 300;clock=DerivedReplayClock(self.candles.time.tolist(),interval);clock.current_index=start_index-1;self.store.update_run(self.run["replay_run_id"],status="running")
        for tick in clock:
            if coordinator.should_yield_research():time.sleep(max(.1,float(self.config.get("worker_yield_seconds",.1))*4))
            persisted=self.store.run(self.run["replay_run_id"])
            while persisted and persisted.get("status")=="paused":
                time.sleep(float(self.config.get("worker_yield_seconds",.1)));persisted=self.store.run(self.run["replay_run_id"])
            if persisted and persisted.get("status")=="cancelled":return
            if self.cancel_event and self.cancel_event.is_set():self.store.update_run(self.run["replay_run_id"],status="cancelled");return
            while self._pause:
                import time
                self.store.update_run(self.run["replay_run_id"],status="paused");time.sleep(.1)
                if self.cancel_event and self.cancel_event.is_set():return
            self.process_tick(tick,interval)
            yield_seconds=float(self.config.get("worker_yield_seconds",0))
            if yield_seconds:time.sleep(yield_seconds)
        completed=pd.Timestamp(self.dataset["end_time"]).isoformat();self.store.update_run(self.run["replay_run_id"],status="completed",completed_at=completed)
    def process_tick(self,tick,interval):
        run_id=self.run["replay_run_id"];self.state.candle_index=tick["current_index"];self.state.replay_time=tick["current_time"];visible=self.candles.iloc[:tick["current_index"]+1].copy();visible["time"]=pd.to_datetime(visible.time,unit="s",utc=True);current=visible.tail(1)
        # Existing fills/outcomes are processed before a decision from this close is created.
        for setup in self.store.active_setups(run_id):
            if setup["state"]=="waiting_for_fill":
                entry_type=json.loads(setup["payload_json"]).get("setup",{}).get("entry_type","confirmation_close")
                if entry_type=="confirmation_close" and (self.config.get("execution") or {}).get("confirmation_close_policy")=="next_base_candle_open":entry_type="next_base_candle_open"
                fill=evaluate_fill(setup,current,entry_type,(self.config.get("execution") or {}).get("default_slippage_points",0))
                if fill["filled"]:self.store.save_fill(run_id,setup["paper_setup_id"],fill);self.store.update_setup(setup["paper_setup_id"],"filled");setup={**setup,"state":"filled"}
            fill=self.store.fill(setup["paper_setup_id"])
            if fill:
                outcome=evaluate_outcome(setup,visible,fill["fill_time"],(self.config.get("execution") or {}).get("ambiguity_policy","mark_ambiguous"));exc=evaluate_excursion(setup,visible,fill["fill_time"],resolved_time=outcome.get("terminal_time"));self.store.save_outcome(run_id,setup["paper_setup_id"],outcome,exc)
                if outcome["outcome"]!="OPEN":self.store.update_setup(setup["paper_setup_id"],"resolved")
        frames,audit=slice_timeframes(self.candles,tick["current_time"],self.dataset["base_timeframe"])
        if not len(frames["M5"]):return
        if (self.config.get("analysis") or {}).get("run_on_each_completed_m5",True) and "M5" not in tick["completed_timeframes"]:
            self.store.update_run(run_id,current_index=tick["current_index"],current_time=tick["current_time"]);every=int(self.config.get("checkpoint_every_candles",250))
            if every and (tick["current_index"]+1)%every==0:self.store.save_checkpoint(run_id,tick["current_index"],tick["current_time"],checkpoint_payload(run_id,self.state,self.run["configuration_hash"],self.dataset["checksum"],self.run.get("random_seed",0)))
            return
        result=self.pipeline(symbol=self.run["provider_symbol"],metadata={"provider_symbol":self.run["provider_symbol"],"display_name":self.dataset.get("display_name",self.run["provider_symbol"]),"family":self.run["family"]},candles_by_timeframe=frames,tick_size=(self.dataset.get("metadata") or {}).get("tick_size") or .01,analysis_time=pd.Timestamp(tick["current_time"]),requested_strategy=self.run["requested_strategy"])
        if result.get("product_contract"):result["product_contract"]["meta"]["live"]=False
        snapshot=build_derived_signal_snapshot(provider_symbol=self.run["provider_symbol"],display_name=self.dataset.get("display_name",self.run["provider_symbol"]),family=self.run["family"],subfamily="",requested_strategy=self.run["requested_strategy"],analysis_candle_time=tick["current_time"],decision_contract=result,data_snapshot_id=self.dataset["dataset_id"])
        replay_id="replay-decision-"+hashlib.sha256(json.dumps([run_id,snapshot.decision_id],separators=(",",":")).encode()).hexdigest()[:24];payload={**snapshot.payload,"decision_id":replay_id,"replay_run_id":run_id,"dataset_id":self.dataset["dataset_id"],"replay_time":tick["current_time"],"base_candle_index":tick["current_index"],"configuration_hash":self.run["configuration_hash"],"code_version":self.run["code_version"],"is_replay":True,"timeframe_audit":audit};snapshot=replace(snapshot,decision_id=replay_id,payload=payload)
        self.store.save_decision(run_id,tick["current_index"],tick["current_time"],snapshot);setup=build_paper_setup(snapshot)
        if setup:
            paper_id="replay-setup-"+hashlib.sha256(json.dumps([run_id,setup.setup_id]).encode()).hexdigest()[:24];setup=replace(setup,paper_setup_id=paper_id,decision_id=replay_id);self.store.save_setup(run_id,setup,payload)
        self.state.selected_strategy=payload.get("selected_strategy");self.state.pending_setup_ids=[x["paper_setup_id"] for x in self.store.active_setups(run_id) if x["state"]=="waiting_for_fill"]
        self.state.filled_setup_ids=[x["paper_setup_id"] for x in self.store.active_setups(run_id) if x["state"]=="filled"]
        self.store.update_run(run_id,current_index=tick["current_index"],current_time=tick["current_time"])
        every=int(self.config.get("checkpoint_every_candles",250));
        if every and (tick["current_index"]+1)%every==0:self.store.save_checkpoint(run_id,tick["current_index"],tick["current_time"],checkpoint_payload(run_id,self.state,self.run["configuration_hash"],self.dataset["checksum"],self.run.get("random_seed",0)))
    def pause(self):self._pause=True
    def resume(self):self._pause=False
