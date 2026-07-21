"""Run the deterministic production setup-proof matrix and persist evidence."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path

from validation.strategy_reachability_fixtures import registered_fixtures,production_evaluator,production_paper_lifecycle
from validation.strategy_setup_proof import build_strategy_reachability_report,run_strategy_fixture,validate_registry_fixture_coverage


def run(output_path=None):
    default_dir=Path(__file__).resolve().parents[1]/"data"/"strategy_setup_proof";current=default_dir/"latest.json";baseline=default_dir/"baseline_before_causal_geometry.json"
    if output_path is None and current.exists() and not baseline.exists():
        baseline.parent.mkdir(parents=True,exist_ok=True);baseline.write_text(current.read_text(encoding="utf-8"),encoding="utf-8")
    projection=default_dir/"baseline_geometry_snapshot.json"
    if output_path is None and baseline.exists() and not projection.exists():
        projection.write_text(json.dumps(_baseline_projection(json.loads(baseline.read_text(encoding="utf-8"))),indent=2,default=str)+"\n",encoding="utf-8")
    fixtures=registered_fixtures();coverage=validate_registry_fixture_coverage(fixtures)
    if coverage:raise RuntimeError(f"Missing production fixtures: {coverage}")
    results=[run_strategy_fixture(fixture,production_evaluator,paper_service=production_paper_lifecycle) for fixture in fixtures]
    report=build_strategy_reachability_report(results);production=[row for row in report["strategies"] if row["status"]!="NOT_PRODUCTION_SUPPORTED"]
    deterministic_pass=bool(production) and all(row["status"]=="REACHABLE" for row in production)
    golden=[row for row in results if row["strategy_id"]=="volatility_structure_pullback"]
    report.update({"generated_at":datetime.now(timezone.utc).isoformat(),"pipeline":"analysis.derived_engine.analyze_derived_index","fixture_count":len(fixtures),"deterministic_reachability_passed":deterministic_pass,"real_history_validation":{"run":False,"reason":None if deterministic_pass else "Deterministic production reachability must pass before outcome-independent 30-day validation."},"fixtures":results,"golden_path_funnel":{row["direction"]:_golden_funnel(row) for row in golden},"thresholds_changed":False,"finished_decisions_injected":False,"historical_profitability_claimed":False})
    path=Path(output_path or Path(__file__).resolve().parents[1]/"data"/"strategy_setup_proof"/"latest.json");path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2,default=str)+"\n",encoding="utf-8");return report


def _golden_funnel(result):
    ready=next((row for row in reversed(result["transitions"]) if row.get("invariants_valid") and row.get("asserted_trade_ready")),result["transitions"][-1] if result["transitions"] else {})
    counts=ready.get("geometry_funnel") or {}
    return {"before":{"target_candidates":0,"trade_ready":0},"after":{"target_candidates":counts.get("target_candidates",0),"targets_on_profitable_side":counts.get("profitable_side",0),"targets_passing_rr":counts.get("rr_passed",0),"trade_ready":int(bool(result.get("trade_ready_reached"))),"paper_registered":int(bool(result.get("paper_registered"))),"entry_filled":int(bool(result.get("entry_filled"))),"outcome_resolved":int(bool(result.get("outcome_resolved")))}}

def _baseline_projection(report):
    rows=[]
    for fixture in report.get("fixtures",[]):
        transition=(fixture.get("transitions") or [{}])[-1]
        rows.append({"fixture_id":fixture.get("fixture_id"),"strategy_id":fixture.get("strategy_id"),"direction":fixture.get("direction"),"failed_lifecycle_stage":None if fixture.get("trade_ready_reached") else transition.get("stage"),"blocker_code":transition.get("first_blocker"),"target_trace":transition.get("target_trace"),"entry_trace":transition.get("entry_trace"),"stop_trace":transition.get("stop_trace"),"plan_invariant_violations":transition.get("invariant_violations") or []})
    return {"source":"baseline_before_causal_geometry.json","fixtures":rows}

if __name__=="__main__":
    value=run();print(json.dumps({"strategies":value["strategies"],"deterministic_reachability_passed":value["deterministic_reachability_passed"]},indent=2))
