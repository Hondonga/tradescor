import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, FileClock, FlaskConical, NotebookTabs } from "lucide-react";
import {
  buildMlDataset,
  mlDatasetAction,
  mlDatasetProgress,
  mlDatasets,
  paperEvidence,
  paperRecords,
  replayRuns,
  validateMlDataset,
  mlTrainingRuns,
  startMlTraining,
  mlTrainingProgress,
  cancelMlTraining,
} from "@/lib/api";
import { EmptyState } from "@/components/ui/empty-state";
import { ReplayProgress } from "@/components/terminal/status-components";
import { useTerminalStore } from "@/store/terminal-store";
import { titleCase } from "@/lib/utils";
import type { NormalizedDecision } from "@/types";
const tabs = [
  "Replay",
  "ML Dataset",
  "ML Training",
  "Evidence",
  "Diagnostics",
  "Paper Log",
] as const;
export function ResearchPage() {
  const [tab, setTab] = useState<(typeof tabs)[number]>("Replay");
  return (
    <div className="page research-page">
      <header className="page-title">
        <div>
          <p>Historical and paper research</p>
          <h1>Research</h1>
        </div>
      </header>
      <nav className="research-tabs">
        {tabs.map((value) => (
          <button
            key={value}
            className={tab === value ? "active" : ""}
            onClick={() => setTab(value)}
          >
            {value}
          </button>
        ))}
      </nav>
      <div className="research-content">
        {tab === "Replay" ? (
          <ReplayTab />
        ) : tab === "ML Dataset" ? (
          <MLDatasetTab />
        ) : tab === "ML Training" ? (
          <MLTrainingTab />
        ) : tab === "Evidence" ? (
          <EvidenceTab />
        ) : tab === "Diagnostics" ? (
          <DiagnosticsTab />
        ) : (
          <PaperTab />
        )}
      </div>
    </div>
  );
}
function MLTrainingTab() {
  const [active,setActive]=useState<any>();
  const query=useQuery({queryKey:["ml-training",active?.run_id,active?.state],queryFn:async()=>{
    if(active?.run_id && ["queued","running","cancelling"].includes(active.state))setActive(await mlTrainingProgress(active.run_id));
    return mlTrainingRuns();
  },refetchInterval:active && ["queued","running","cancelling"].includes(active.state)?1000:false});
  const row=active||query.data?.runs?.[0];const report=row?.report;
  return <div className="research-split">
    <section><p className="label">ML Training</p><h2 className="mt-2 text-base">R_75 baseline model validation</h2>
      <p className="mt-2 text-xs leading-5 text-zinc-500">Offline research only. Models cannot alter live SMC direction, entry, stop, targets, or scoring.</p>
      <dl className="detail-grid mt-4"><dt>Dataset</dt><dd className="font-mono text-[10px]">{row?.dataset_id||"ml-r75-f4c52d93c7a8dc3e95f1"}</dd><dt>Stage</dt><dd>{titleCase(row?.stage||"not started")}</dd><dt>Current model</dt><dd>{titleCase(row?.current_model||"—")}</dd><dt>Progress</dt><dd>{row?.progress||0}%</dd><dt>Status</dt><dd>{titleCase(row?.model_status||row?.state||"research only")}</dd></dl>
      <ReplayProgress progress={row?.progress||0}/><div className="mt-4 flex gap-2"><button className="rounded bg-blue-600 px-3 py-2 text-xs" disabled={row&&["queued","running"].includes(row.state)} onClick={async()=>setActive(await startMlTraining("ml-r75-f4c52d93c7a8dc3e95f1"))}>Train Baselines</button><button className="rounded border border-white/10 px-3 py-2 text-xs" disabled={!row||!["queued","running"].includes(row.state)} onClick={async()=>setActive(await cancelMlTraining(row.run_id))}>Cancel</button><button className="rounded border border-white/10 px-3 py-2 text-xs" disabled={row?.state!=="completed"} onClick={()=>window.open(`/api/ml/training/runs/${row.run_id}/report?format=html`,"_blank")}>Open Report</button></div>
    </section><section><p className="label">Models</p><p className="mt-3 text-xs text-zinc-500">Dummy majority · Dummy prior · Logistic regression · Gradient boosting</p><p className="label mt-5">Results</p><pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap text-[10px] text-zinc-500">{JSON.stringify(report?{validation:report.validation,test:report.test,smc_only:report.smc_only,smc_plus_ml:report.smc_plus_ml,calibration:report.selection?.calibration,status:report.model_status}:{status:"Awaiting offline training"},null,2)}</pre></section>
  </div>
}
function MLDatasetTab() {
  const [active, setActive] = useState<any>();
  const [validation, setValidation] = useState<any>();
  const query = useQuery({
    queryKey: ["ml-datasets", active?.dataset_id, active?.state],
    queryFn: async () => {
      if (
        active?.dataset_id &&
        ["queued", "running", "paused"].includes(active.state)
      ) {
        const progress = await mlDatasetProgress(active.dataset_id);
        setActive(progress);
      }
      return mlDatasets();
    },
    refetchInterval:
      active && ["queued", "running", "paused"].includes(active.state)
        ? 1000
        : false,
  });
  const row = active || query.data?.datasets?.[0];
  const action = async (value: "pause" | "resume" | "cancel") =>
    setActive(await mlDatasetAction(row.dataset_id, value));
  return (
    <div className="research-split">
      <section>
        <p className="label">ML Dataset</p>
        <h2 className="mt-2 text-base">Causal SMC dataset foundation</h2>
        <p className="mt-2 text-xs leading-5 text-zinc-500">
          Research data only. No model is trained and ML cannot alter production
          direction, entry, stop, or targets.
        </p>
        <dl className="detail-grid mt-4">
          <dt>Symbol</dt>
          <dd>{row?.symbol || "R_75"}</dd>
          <dt>Strategy</dt>
          <dd>Volatility Structure Pullback</dd>
          <dt>Period</dt>
          <dd>{row?.period_days || row?.period?.days || 90} days</dd>
          <dt>Build status</dt>
          <dd>{titleCase(row?.state || "not built")}</dd>
          <dt>Processed candles</dt>
          <dd>
            {row?.processed_candles || 0} / {row?.total_candles || "—"}
          </dd>
          <dt>Snapshots</dt>
          <dd>{row?.snapshots ?? row?.rows ?? 0}</dd>
          <dt>Unique setups</dt>
          <dd>{row?.unique_setups ?? row?.setups ?? 0}</dd>
          <dt>Trade-ready examples</dt>
          <dd>{row?.trade_ready_examples ?? row?.trade_ready_rows ?? 0}</dd>
          <dt>Resolved examples</dt>
          <dd>{row?.resolved_examples ?? row?.resolved_rows ?? 0}</dd>
          <dt>Leakage violations</dt>
          <dd>{row?.leakage_violations ?? 0}</dd>
          <dt>Dataset checksum</dt>
          <dd className="truncate font-mono text-[10px]">
            {row?.checksum || "Pending"}
          </dd>
        </dl>
        {row?.total_candles > 0 && (
          <ReplayProgress
            progress={Math.min(
              100,
              (row.processed_candles / row.total_candles) * 100,
            )}
          />
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="rounded bg-blue-600 px-3 py-2 text-xs"
            onClick={async () => setActive(await buildMlDataset())}
            disabled={
              row && ["queued", "running", "paused"].includes(row.state)
            }
          >
            Build Dataset
          </button>
          <button
            className="rounded border border-white/10 px-3 py-2 text-xs"
            onClick={() => action("pause")}
            disabled={row?.state !== "running"}
          >
            Pause
          </button>
          <button
            className="rounded border border-white/10 px-3 py-2 text-xs"
            onClick={() => action("resume")}
            disabled={row?.state !== "paused"}
          >
            Resume
          </button>
          <button
            className="rounded border border-white/10 px-3 py-2 text-xs"
            onClick={() => action("cancel")}
            disabled={
              !row || !["queued", "running", "paused"].includes(row.state)
            }
          >
            Cancel
          </button>
          <button
            className="rounded border border-white/10 px-3 py-2 text-xs"
            onClick={async () =>
              setValidation(await validateMlDataset(row.dataset_id))
            }
            disabled={row?.state !== "completed"}
          >
            Validate
          </button>
          <button
            className="rounded border border-white/10 px-3 py-2 text-xs"
            onClick={() =>
              window.open(
                `/api/ml/datasets/${row.dataset_id}/report?format=html`,
                "_blank",
              )
            }
            disabled={row?.state !== "completed"}
          >
            Open Report
          </button>
        </div>
      </section>
      <section>
        <p className="label">Validation</p>
        <pre className="mt-3 whitespace-pre-wrap text-[10px] text-zinc-500">
          {JSON.stringify(
            validation || {
              schema: "smc-ml-features-v1",
              chronological_splits: "60 / 20 / 20",
              test_split: "untouched",
              training_enabled: false,
            },
            null,
            2,
          )}
        </pre>
        <p className="label mt-5">Training readiness</p>
        <h3
          className={`mt-2 text-sm ${row?.training_readiness?.ready ? "text-emerald-400" : "text-amber-300"}`}
        >
          {row?.training_readiness?.ready ? "READY" : "NOT READY"}
        </h3>
        <div className="mt-3 space-y-2">
          {(row?.training_readiness?.requirements || []).map((item: any) => (
            <div
              key={item.name}
              className="flex justify-between gap-3 text-[10px]"
            >
              <span className={item.passed ? "text-zinc-500" : "text-amber-300"}>
                {titleCase(item.name)}
              </span>
              <span className="font-mono">
                {String(item.current)} / {String(item.required)}
              </span>
            </div>
          ))}
        </div>
        <p className="label mt-5">Worker and quality</p>
        <dl className="detail-grid mt-3">
          <dt>Decision time</dt><dd>{row?.current_decision_time || "—"}</dd>
          <dt>ETA</dt><dd>{row?.eta_seconds != null ? `${Math.ceil(row.eta_seconds / 60)} min` : "—"}</dd>
          <dt>Worker</dt><dd>{titleCase(row?.worker_state || "idle")}</dd>
          <dt>Missing intervals</dt><dd>{row?.missing_intervals ?? "—"}</dd>
          <dt>Duplicate snapshots</dt><dd>{row?.duplicate_snapshots ?? "—"}</dd>
          <dt>Unresolved labels</dt><dd>{row?.unresolved_labels ?? "—"}</dd>
          <dt>Buy resolved</dt><dd>{row?.buy_resolved ?? "—"}</dd>
          <dt>Sell resolved</dt><dd>{row?.sell_resolved ?? "—"}</dd>
          <dt>Positive outcomes</dt><dd>{row?.positive_outcomes ?? "—"}</dd>
          <dt>Negative outcomes</dt><dd>{row?.negative_outcomes ?? "—"}</dd>
          <dt>Independent periods</dt><dd>{row?.independent_periods ?? "—"}</dd>
        </dl>
      </section>
    </div>
  );
}
function ReplayTab() {
  const query = useQuery({ queryKey: ["replay-runs"], queryFn: replayRuns });
  const rows = Array.isArray(query.data) ? query.data : query.data?.runs || [];
  if (!rows.length)
    return (
      <EmptyState
        icon={FileClock}
        title="No replay selected"
        description="Create a replay from a preselected dataset to inspect reachability, blockers, and decision-time evidence."
        action="Create replay"
      />
    );
  const run = rows[0];
  return (
    <div className="research-split">
      <section>
        <p className="label">Selected dataset</p>
        <dl className="detail-grid mt-3">
          <dt>Symbol</dt>
          <dd>{run.provider_symbol}</dd>
          <dt>Period</dt>
          <dd>
            {run.start_time} — {run.end_time}
          </dd>
          <dt>Checksum</dt>
          <dd className="truncate">{run.checksum || run.dataset_id}</dd>
          <dt>Status</dt>
          <dd>{titleCase(run.status)}</dd>
        </dl>
        <ReplayProgress
          progress={
            String(run.status).toLowerCase() === "completed"
              ? 100
              : run.progress_percent || 0
          }
        />
      </section>
      <section>
        <p className="label">Decision inspector</p>
        <p className="mt-3 text-xs text-zinc-500">
          Select a completed replay decision to compare decision-time structural
          targets with later lifecycle outcomes.
        </p>
      </section>
    </div>
  );
}
function EvidenceTab() {
  const query = useQuery({
    queryKey: ["paper-evidence"],
    queryFn: paperEvidence,
  });
  const rows = query.data?.groups || query.data?.performance || [];
  if (!rows.length)
    return (
      <EmptyState
        icon={Database}
        title="No evidence yet"
        description="Performance appears after valid paper or replay trades resolve."
        action="Open Replay"
      />
    );
  return <pre>{JSON.stringify(query.data, null, 2)}</pre>;
}
/**
 * Phase 6 Part 11: research presentation must not hide negative results or
 * simplify a rejection into "needs more data" -- the frozen verdict for
 * Volatility Structure Pullback is explicitly REJECTED_NO_EDGE_AFTER_COSTS.
 * Three-part structure, sourced entirely from the backend-authoritative
 * strategy_evidence object: what the engine CAN build, what formal
 * validation FOUND, and what the product ALLOWS as a result.
 */
function StrategyValidationSection({ decision }: { decision: NormalizedDecision }) {
  const evidence = decision.strategy_evidence;
  if (!evidence) return null;
  const reachable = evidence.reachability_status === "REACHABLE_BOTH_DIRECTIONS"
    ? "The engine can produce complete BUY and SELL plans."
    : evidence.reachability_status === "NOT_REACHABLE"
      ? "Complete plan construction has not yet been verified."
      : `Reachability: ${evidence.reachability_status.replace(/_/g, " ").toLowerCase()}.`;
  const validationText = evidence.historical_edge_proven
    ? "This strategy has demonstrated a stable, historically validated post-cost edge."
    : evidence.validation_verdict
      ? `The strategy failed to demonstrate a stable post-cost edge (${evidence.validation_verdict.replace(/_/g, " ").toLowerCase()}).`
      : "Formal historical validation has not yet been completed for this strategy.";
  const productDecisionText = evidence.historical_edge_proven && !evidence.research_only
    ? "Eligible for Auto, paper signals, and further evaluation toward live execution."
    : "Research only. Not eligible for Auto, paper signals, or live execution.";
  return (
    <section className="strategy-validation">
      <h2>Technical capability</h2>
      <p>{reachable}</p>
      <h2>Historical validation</h2>
      <p>{validationText}</p>
      {evidence.experiment_id && <p className="text-zinc-500">Frozen experiment: {evidence.experiment_id}</p>}
      <h2>Product decision</h2>
      <p>{productDecisionText}</p>
    </section>
  );
}
function DiagnosticsTab() {
  const decision = useTerminalStore((s) => s.decision);
  if (!decision)
    return (
      <EmptyState
        icon={FlaskConical}
        title="No diagnostics yet"
        description="Analyze the selected symbol to inspect history readiness, blockers, contradictions, and structural target traces."
        action="Open Workspace"
      />
    );
  return (
    <div className="diagnostic-grid">
      <StrategyValidationSection decision={decision} />
      {[
        ["History readiness", decision.diagnostics.history_depth_audit],
        ["Target trace", decision.diagnostics.target_trace],
        ["Invariants", decision.diagnostics.invariants],
        ["Gate funnel", decision.diagnostics.gate_funnel],
      ].map(([title, value]) => (
        <section key={title as string}>
          <h2>{title as string}</h2>
          <pre>{JSON.stringify(value || {}, null, 2)}</pre>
        </section>
      ))}
    </div>
  );
}
function PaperTab() {
  const query = useQuery({
    queryKey: ["paper-records"],
    queryFn: paperRecords,
  });
  const rows = Array.isArray(query.data)
    ? query.data
    : query.data?.setups || [];
  if (!rows.length)
    return (
      <EmptyState
        icon={NotebookTabs}
        title="No paper plans"
        description="Only backend-registered setups appear here -- developing, contradictory, or historically unvalidated setups are never registered through the production path. Test fixtures used to prove technical reachability are recorded separately and marked test-fixture-only."
        action="Open Workspace"
      />
    );
  return (
    <div className="paper-list">
      {rows.map((row: any) => (
        <article key={row.paper_setup_id || row.setup_id}>
          <b>{row.provider_symbol || row.symbol}</b>
          <span>{titleCase(row.state)}</span>
          <code>
            {row.entry} / {row.stop} / {row.tp1}
          </code>
        </article>
      ))}
    </div>
  );
}
