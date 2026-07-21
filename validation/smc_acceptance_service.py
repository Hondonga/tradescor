from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,os
from validation.smc_acceptance_store import SMCAcceptanceStore
from validation.smc_entity_recorder import extract_smc_entities
from validation.smc_causality_validator import validate_smc_causality
from validation.smc_plan_validator import validate_trade_plan
from validation.smc_reachability import build_reachability,aggregate_blockers
from validation.smc_optional_confluence import audit_optional_confluence
from validation.smc_acceptance_report import build_acceptance_report,render_acceptance_html
from validation.smc_decision_inspector import inspect_historical_decision

class SMCAcceptanceService:
    def __init__(self,replay_service,store=None):self.replay=replay_service;self.store=store or SMCAcceptanceStore(os.getenv("SMC_ACCEPTANCE_DB","data/smc_acceptance.db"))
    def validate_run(self,run_id,dataset_metadata):
        run=self.replay.get_run(run_id)
        if not run:raise KeyError("Replay run not found.")
        stored,_=self.replay.store.load_dataset(run["dataset_id"]);dataset_metadata={"dataset_id":stored["dataset_id"],"symbol":run["provider_symbol"],"family":run["family"],"variant":dataset_metadata.get("variant") or run["family"],"start_time":stored.get("start_time"),"end_time":stored.get("end_time"),"source_timeframe":stored.get("base_timeframe"),"candle_count":stored.get("candle_count"),"checksum":stored.get("checksum"),"missing_intervals":stored.get("missing_intervals",[]),"duplicate_intervals":dataset_metadata.get("duplicate_intervals",[]),"data_quality":stored.get("quality"),"downloaded_at":dataset_metadata.get("downloaded_at"),"selection_reason":dataset_metadata.get("selection_reason","Replay dataset was selected by its persisted pre-analysis configuration."),**dataset_metadata}
        decisions=self.replay.records(run_id,"decisions");setups=self.replay.records(run_id,"setups");outcomes=self.replay.records(run_id,"outcomes");entities=extract_smc_entities(decisions);causality=validate_smc_causality(decisions)
        if not causality["valid"]:self.replay.store.update_run(run_id,status="failed",error="SMC causality validation failed.")
        invalid=[row for row in (validate_trade_plan(x) for x in decisions) if row["applicable"] and not row["valid"]];reachability=build_reachability(decisions,setups,outcomes);blockers=aggregate_blockers(reachability);optional=audit_optional_confluence(decisions,outcomes);report=build_acceptance_report(dataset=dataset_metadata,run=run,decisions=decisions,setups=setups,outcomes=outcomes,reachability=reachability,blockers=blockers,causality=causality,invalid_plans=invalid,optional_confluence=optional);report_id="smc-report-"+hashlib.sha256(json.dumps([run_id,dataset_metadata["checksum"]],separators=(",",":")).encode()).hexdigest()[:24];report["report_id"]=report_id;created=datetime.now(timezone.utc).isoformat();self.store.save_dataset(dataset_metadata);self.store.save_entities(dataset_metadata["dataset_id"],run_id,entities);self.store.save_report(report_id,run_id,dataset_metadata["dataset_id"],created,report);return report
    def reports(self):return self.store.reports()
    def report(self,report_id):return self.store.report(report_id)
    def html(self,report_id):
        report=self.report(report_id)
        if not report:raise KeyError("Acceptance report not found.")
        return render_acceptance_html(report)
    def inspect(self,run_id,decision_id):
        decisions=self.replay.records(run_id,"decisions");decision=next((x for x in decisions if x.get("decision_id")==decision_id or (x.get("payload") or {}).get("decision_id")==decision_id),None)
        if not decision:raise KeyError("Historical decision not found.")
        setup_id=((decision.get("payload") or {}).get("smc_contract") or {}).get("setup",{}).get("setup_id");outcome=next((x for x in self.replay.records(run_id,"outcomes") if x.get("setup_id")==setup_id),None);return inspect_historical_decision(decision,outcome)
