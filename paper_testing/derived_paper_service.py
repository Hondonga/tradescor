"""Fast live orchestration for snapshots, registration, and chronological reconciliation."""
from __future__ import annotations
import json,os
from pathlib import Path
from paper_testing.derived_paper_store import DerivedPaperStore
from paper_testing.derived_signal_snapshot import build_derived_signal_snapshot
from paper_testing.derived_setup_tracker import build_paper_setup,terminate_unfilled_setup
from paper_testing.derived_fill_engine import evaluate_paper_fill
from paper_testing.derived_outcome_resolver import resolve_paper_outcome
from paper_testing.derived_mfe_mae_tracker import track_mfe_mae
from paper_testing.derived_evidence_classifier import classify_derived_evidence
from paper_testing.derived_performance_aggregator import aggregate_derived_performance,chronological_drawdown
from analysis.strategy_quarantine_registry import is_paper_signal_allowed,paper_signal_block_reason,validation_entry
class DerivedPaperService:
    def __init__(self,store=None,config=None,enabled=None):
        cfg=config or _config();self.config=cfg;path=os.getenv("DERIVED_PAPER_DB",cfg.get("database_path","data/derived_paper_testing.db"));self.enabled=bool(cfg.get("enabled",True)) if enabled is None else enabled;self.store=store or DerivedPaperStore(path)
    def record_analysis(self,*,provider_symbol,display_name,family,subfamily,requested_strategy,analysis_candle_time,decision_contract,candles=None,data_snapshot_id="",test_fixture_only=False):
        if not self.enabled:return {"enabled":False}
        snapshot=build_derived_signal_snapshot(provider_symbol=provider_symbol,display_name=display_name,family=family,subfamily=subfamily,requested_strategy=requested_strategy,analysis_candle_time=analysis_candle_time,decision_contract=decision_contract,data_snapshot_id=data_snapshot_id);self._archive_replaced_pending(provider_symbol,snapshot.selected_strategy,analysis_candle_time)
        # Phase 6 Part 5/17: paper_engine_capability (can this decision be
        # technically turned into a paper setup) is a different question from
        # strategy_paper_eligibility (may it register through the production
        # path). Fixture/harness callers pass test_fixture_only=True to prove
        # the former without ever proving real eligibility; the live app
        # (test_fixture_only=False, the default) is always subject to the gate.
        strategy_id=snapshot.selected_strategy;validation=validation_entry(strategy_id);paper_allowed=bool(test_fixture_only or validation["paper_signal_allowed"]);block_reason=None if paper_allowed else paper_signal_block_reason(strategy_id)
        snapshot.payload["phase6_record_safety"]={"strategy_id":strategy_id,"strategy_version":decision_contract.get("configuration_hash") or decision_contract.get("strategy_version"),"validation_status_at_registration":validation["validation_status"],"validation_verdict_at_registration":validation["validation_verdict"],"product_actionability_at_registration":{"auto_allowed":validation["auto_eligible"],"paper_allowed":validation["paper_signal_allowed"],"live_allowed":validation["live_execution_allowed"]},"test_fixture_only":bool(test_fixture_only),"experiment_id":validation["experiment_id"],"block_reason":block_reason}
        decision_id,inserted=self.store.insert_decision(snapshot)
        if inserted:self.store.append_event("decision:"+decision_id,"decision_created",snapshot.created_at,payload={"decision_id":decision_id}) if False else None
        setup=build_paper_setup(snapshot,int(((decision_contract.get("active_trade_plan") or {}).get("setup_expiration_candles") or 12)))
        registered=False
        if setup and paper_allowed:registered=self.store.insert_setup(setup,snapshot.payload,snapshot.payload.get("research_mode",False));self.store.append_event(setup.paper_setup_id,"entry_available",snapshot.created_at,setup.entry,{"decision_id":decision_id}) if registered else None
        reconciliation=self.reconcile(candles) if candles is not None else {}
        return {"enabled":True,"decision_id":decision_id,"snapshot_inserted":inserted,"setup_registered":registered,"paper_setup_id":setup.paper_setup_id if (setup and paper_allowed) else None,"paper_signal_allowed":paper_allowed,"paper_signal_block_reason":block_reason,"test_fixture_only":bool(test_fixture_only),"reconciliation":reconciliation}
    def _archive_replaced_pending(self,provider_symbol,current_strategy,at):
        for row in self.store.active_setups():
            if row.get("state")!="waiting_for_fill" or row.get("strategy")==current_strategy:continue
            try:payload=json.loads(row.get("payload_json") or "{}");same=(payload.get("provider_symbol")==provider_symbol)
            except (ValueError,TypeError):same=False
            if same:terminate_unfilled_setup(self.store,row["paper_setup_id"],"cancelled",at)
    def reconcile(self,candles=None):
        if not self.enabled:return {"pending_setups_recovered":0,"open_positions_recovered":0,"candles_replayed":0,"duplicate_events_ignored":0}
        active=self.store.active_setups();pending=sum(row["state"]=="waiting_for_fill" for row in active);opened=sum(row["state"] in {"filled","tp1_hit"} for row in active);events_added=duplicates=processed=0
        if candles is None:return {"pending_setups_recovered":pending,"open_positions_recovered":opened,"candles_replayed":0,"duplicate_events_ignored":0}
        for setup in active:
            if setup["state"]=="waiting_for_fill":
                payload=json.loads(setup["payload_json"]);entry_type=((payload.get("setup") or {}).get("entry_type") or "confirmation_close");fill=evaluate_paper_fill(setup,candles,entry_type,((self.config.get("fill") or {}).get("default_slippage_points",0)));processed+=1
                if not fill["filled"]:continue
                self.store.save_fill(setup["paper_setup_id"],fill);added=self.store.append_event(setup["paper_setup_id"],"entry_filled",fill["fill_time"],fill["filled_entry"],fill);events_added+=added;duplicates+=not added;self.store.update_setup(setup["paper_setup_id"],state="filled",last_processed_time=fill["fill_time"]);setup={**setup,"state":"filled"};fill_time=fill["fill_time"]
            else:
                detail=self.store.setup_detail(setup["paper_setup_id"]);fill_time=(detail.get("fill") or {}).get("fill_time")
            if not fill_time:continue
            outcome=resolve_paper_outcome(setup,candles,fill_time,(self.config.get("ambiguity") or {}).get("policy","mark_ambiguous"),self.config.get("management"));excursion=track_mfe_mae(setup,candles,fill_time,resolved_time=outcome.get("terminal_time"));self.store.save_excursion(setup["paper_setup_id"],excursion)
            for event in outcome["event_log"]:
                added=self.store.append_event(setup["paper_setup_id"],event["event"],event["time"],event.get("price"),event);events_added+=added;duplicates+=not added
            if outcome["outcome"]!="OPEN":self.store.save_outcome(setup["paper_setup_id"],outcome);self.store.update_setup(setup["paper_setup_id"],state="resolved",last_processed_time=outcome["terminal_time"])
        return {"pending_setups_recovered":pending,"open_positions_recovered":opened,"candles_replayed":processed,"duplicate_events_ignored":duplicates,"events_appended":events_added}
    def decisions(self,filters=None,limit=200):return self.store.rows("paper_decisions",filters,limit)
    def setups(self,filters=None,limit=200):return self.store.rows("paper_setups",filters,limit)
    def outcomes(self,filters=None,limit=200):return self.store.rows("paper_outcomes",filters,limit)
    def active(self):return self.store.active_setups()
    def evidence(self):
        outcomes=self.outcomes(limit=100000);return classify_derived_evidence(sum(bool(row.get("entry_filled")) for row in outcomes),False,self.config.get("evidence"))
    def performance(self,filters=None):
        decisions=self.decisions(filters,100000);setups=self.setups(filters,100000);outcomes=self.outcomes(filters,100000);return {"groups":aggregate_derived_performance(decisions,setups,outcomes),"drawdown":chronological_drawdown(outcomes)}
    def summary(self):
        setups=self.setups(limit=100000);outcomes=self.outcomes(limit=100000);active=self.active();rs=[row.get("realized_r") for row in outcomes if row.get("realized_r") is not None];return {"active_setups":sum(row["state"]=="waiting_for_fill" for row in active),"open_simulated_trades":sum(row["state"] in {"filled","tp1_hit"} for row in active),"resolved_trades":len(outcomes),"current_evidence":self.evidence()["evidence_label"],"selected_strategy_sample":len(outcomes),"recent_performance_r":sum(float(value) for value in rs[-20:])}
def _config():
    try:return json.loads((Path(__file__).resolve().parents[1]/"config"/"derived_paper_testing.yaml").read_text())["derived_paper_testing"]
    except (OSError,ValueError,KeyError):return {"enabled":False}
