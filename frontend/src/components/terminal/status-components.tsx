import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  LoaderCircle,
  ShieldAlert,
  WifiOff,
} from "lucide-react";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatPrice, titleCase } from "@/lib/utils";
import {
  canonicalStatus,
  canonicalStatusTone,
  directionLabel,
  productStatusLabel,
  productStatusSubtitle,
  productStatusTone,
  resolveProductStatus,
} from "@/lib/status-labels";
import type { NormalizedDecision } from "@/types";

export function DecisionHeader({ decision }: { decision: NormalizedDecision }) {
  // Product status (validation-aware, backend-authoritative) is what the
  // user sees; canonicalStatus (raw engine lifecycle) is preserved under
  // Details so the technical state is never hidden, only not conflated with
  // "you may act on this" -- ENGINE TRADE_READY is not PRODUCT ACTIONABILITY.
  const productStatus = resolveProductStatus(decision);
  const engineStatus = canonicalStatus(decision);
  const researchOnly = decision.strategy_evidence?.research_only ?? decision.setup.research_only;
  return (
    <motion.header layout className="border-b border-white/[.07] p-4">
      <div className="flex items-center justify-between gap-3">
        <StatusBadge tone={productStatusTone(productStatus)}>{productStatusLabel(productStatus)}</StatusBadge>
        <span className="font-mono text-[10px] text-zinc-500">
          {decision.setup.setup_quality_score == null
            ? "Quality —"
            : `${decision.setup.quality_grade} · ${decision.setup.setup_quality_score}`}
        </span>
      </div>
      <p className="mt-3 text-xs text-zinc-400">
        Looking for: {directionLabel(decision.decision.direction)}
      </p>
      <h2 className="mt-1 text-base font-semibold">
        {productStatusSubtitle(productStatus)}
      </h2>
      <p className="mt-1 text-xs text-zinc-500">
        {titleCase(decision.ownership.selected_model_id)}
      </p>
      <p className="mt-1 text-[10px] text-zinc-600">
        Details: engine reached {engineStatus === "TRADE READY" ? "TRADE_READY" : titleCase(decision.decision.stage)}
      </p>
      {decision.ownership.model_corrected && (
        <p className="mt-2 rounded border border-blue-400/20 bg-blue-400/5 px-2 py-1.5 text-[10px] leading-4 text-blue-200">
          Model changed: {decision.ownership.model_correction_reason}
        </p>
      )}
      {researchOnly && (
        <StatusBadge tone="neutral">Research only</StatusBadge>
      )}
      <StrategyValidationPanel decision={decision} />
    </motion.header>
  );
}

const VALIDATION_REASON_TEXT: Record<string, string> = {
  REJECTED_NO_EDGE_AFTER_COSTS: "No stable post-cost edge was confirmed.",
  NO_CONFIRMED_DIRECTIONAL_EDGE: "The strategy design is coherent, but paired testing did not confirm reliable directional information.",
  REJECTED_POOR_CALIBRATION: "The model's confidence calibration did not hold up under testing.",
};

const REACHABILITY_TEXT: Record<string, string> = {
  REACHABLE_BOTH_DIRECTIONS: "BUY and SELL setup construction verified.",
  REACHABLE_BUY_ONLY: "BUY setup construction verified. SELL is not yet reachable.",
  REACHABLE_SELL_ONLY: "SELL setup construction verified. BUY is not yet reachable.",
  NOT_REACHABLE: "Setup construction has not yet been verified.",
};

/**
 * Phase 6 Part 7: the exact required Workspace text distinguishing
 * STRATEGY STATUS / VALIDATION / REASON / REACHABILITY / TRADING ELIGIBILITY
 * for any strategy that is not both historically validated and actionable.
 * Never shown for an actionable (validated) strategy -- there is nothing to
 * disclaim there.
 */
export function StrategyValidationPanel({ decision }: { decision: NormalizedDecision }) {
  const evidence = decision.strategy_evidence;
  const actionability = decision.product_actionability;
  if (!evidence || !actionability || actionability.actionable) return null;
  const validation = evidence.historical_edge_proven
    ? "Historically validated"
    : evidence.validation_verdict
      ? "Rejected after formal walk-forward validation"
      : "Formal historical validation not yet completed";
  const reason = evidence.validation_verdict
    ? VALIDATION_REASON_TEXT[evidence.validation_verdict] ?? evidence.evidence_summary
    : "No historical validation has been completed for this strategy yet.";
  const reachability = REACHABILITY_TEXT[evidence.reachability_status] ?? evidence.reachability_status;
  return (
    <section className="mt-3 space-y-2 rounded border border-white/[.07] bg-white/[.02] p-3 text-[11px] leading-5">
      <div>
        <p className="label">Strategy status</p>
        <p className="text-zinc-300">{evidence.research_only ? "Research only" : "Production"}</p>
      </div>
      <div>
        <p className="label">Validation</p>
        <p className="text-zinc-300">{validation}</p>
      </div>
      <div>
        <p className="label">Reason</p>
        <p className="text-zinc-400">{reason}</p>
      </div>
      <div>
        <p className="label">Reachability</p>
        <p className="text-zinc-300">{reachability}</p>
      </div>
      <div>
        <p className="label">Trading eligibility</p>
        <p className="text-zinc-400">Auto: {actionability.auto_allowed ? "Enabled" : "Disabled"}</p>
        <p className="text-zinc-400">Paper signals: {actionability.paper_allowed ? "Enabled" : "Disabled"}</p>
        <p className="text-zinc-400">Live execution: {actionability.live_allowed ? "Enabled" : "Disabled"}</p>
        <p className="text-zinc-400">ML filtering: Disabled</p>
      </div>
    </section>
  );
}
export function DevelopingSetup({
  decision,
}: {
  decision: NormalizedDecision;
}) {
  return (
    <section className="space-y-3 border-b border-white/[.07] p-4">
      <p className="label">Developing setup</p>
      <h3 className="text-sm font-medium">
        {titleCase(decision.setup.setup_type || "No active setup")}
      </h3>
      <p className="text-xs leading-5 text-zinc-400">
        {decision.setup.context_summary}
      </p>
      <dl className="detail-grid">
        {decision.setup.jump_mode && (
          <><dt>Jump mode</dt><dd>{decision.setup.jump_mode}</dd></>
        )}
        <dt>Stage</dt>
        <dd>{titleCase(decision.decision.stage)}</dd>
        <dt>Blocker</dt>
        <dd>{titleCase(decision.decision.first_blocking_gate) || "None"}</dd>
        <dt>Waiting for</dt>
        <dd>{decision.setup.next_required_condition}</dd>
      </dl>
    </section>
  );
}
export function TradeReadyPlan({ decision }: { decision: NormalizedDecision }) {
  const active = decision.active_setup as
    | (NormalizedDecision["setup"] & Record<string, unknown>)
    | null
    | undefined;
  if (
    !active ||
    !decision.decision.trade_ready ||
    decision.trade_plan?.available !== true
  )
    return null;
  // Engine TRADE_READY is preserved and fully displayed below regardless of
  // validation status (Part 13: never delete analysis) -- only the label
  // changes, so an unvalidated/rejected strategy is never presented as a
  // trading recommendation. Absent product_actionability (a decision that
  // predates Phase 6) preserves the original label rather than inventing a
  // downgrade the backend never actually claimed.
  const actionable = decision.product_actionability ? decision.product_actionability.actionable : true;
  return (
    <section className="space-y-3 border-b border-white/[.07] p-4">
      <p className="label">{actionable ? "Trade plan · paper only" : "Research plan · not actionable"}</p>
      <dl className="detail-grid financial">
        <dt>Setup ID</dt>
        <dd className="break-all text-[10px]">{active.setup_id}</dd>
        <dt>Emitted</dt>
        <dd>{new Date(decision.meta.emitted_time || decision.meta.analysis_time).toISOString()}</dd>
        <dt>Direction</dt>
        <dd>{titleCase(active.direction)}</dd>
        <dt>H1 structure</dt>
        <dd>{titleCase(decision.market.external_structure)}</dd>
        <dt>M15 condition</dt>
        <dd>{titleCase(decision.market.internal_structure)}</dd>
        <dt>M5 confirmation</dt>
        <dd>{active.m5_confirmation_status || "Passed"}</dd>
        <dt>Entry</dt>
        <dd>{formatPrice(active.entry, decision.precision)}</dd>
        <dt>Stop</dt>
        <dd>{formatPrice(active.stop, decision.precision)}</dd>
        {active.targets.map((target) => (
          <>
            <dt key={`${target.name}-dt`}>{target.name}</dt>
            <dd key={`${target.name}-dd`}>
              {formatPrice(target.price, decision.precision)}
              {target.risk_reward ? ` · ${target.risk_reward.toFixed(2)}R` : ""}
            </dd>
          </>
        ))}
        <dt>Target source</dt>
        <dd>
          {titleCase(active.target_source)} ·{" "}
          {active.target_timeframe}
        </dd>
        <dt>R:R</dt>
        <dd>{active.rr == null ? "—" : `${active.rr.toFixed(2)}R`}</dd>
      </dl>
    </section>
  );
}
export const NoOpportunityState = ({
  onAction = () => {},
}: {
  onAction?: () => void;
}) => (
  <EmptyState
    icon={BarChart3}
    title="No market opportunity"
    description="Structure is valid, but no complete SMC setup currently passes every gate."
    action="Refresh analysis"
    onAction={onAction}
  />
);
export const DataLoadingState = () => (
  <div className="grid min-h-52 place-items-center">
    <div className="text-center text-xs text-zinc-500">
      <LoaderCircle className="mx-auto mb-3 animate-spin" size={20} />
      Loading completed market context…
    </div>
  </div>
);
export const ProviderErrorState = ({
  retry = () => {},
  symbol = "—",
}: {
  retry?: () => void;
  symbol?: string;
}) => (
  <div className="p-5">
    <AlertTriangle className="mb-3 text-red-300" size={20} />
    <h2 className="text-sm font-semibold">MARKET DATA UNAVAILABLE</h2>
    <dl className="detail-grid mt-4">
      <dt>Failed stage</dt>
      <dd>Completed-candle history</dd>
      <dt>Provider</dt>
      <dd>Deriv</dd>
      <dt>Symbol</dt>
      <dd>{symbol}</dd>
    </dl>
    <p className="mt-4 text-xs leading-5 text-zinc-500">
      Live analysis is paused. A failed or empty provider response never
      replaces the last known-good cache.
    </p>
    <Button className="mt-4" onClick={retry}>
      Retry connection
    </Button>
    <details className="mt-4 text-[10px] text-zinc-600">
      <summary>Technical details</summary>
      <p className="mt-2">
        Open Research → Diagnostics or `/api/system/data-pipeline` for the
        failed stage and provider error code.
      </p>
    </details>
  </div>
);
export const StaleConnectionState = ({ through }: { through?: string | number | null }) => (
  <div className="flex items-center gap-3 border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200">
    <WifiOff size={15} />
    <span>STALE MARKET DATA · Showing cached candles{through ? ` through ${new Date(typeof through === "number" ? through * 1000 : through).toISOString().slice(11, 16)} UTC` : ""}. Live analysis is paused until the provider reconnects.</span>
  </div>
);
export const ContradictionState = () => (
  <div className="flex items-start gap-3 border border-red-400/20 bg-red-400/5 p-3 text-xs text-red-200">
    <ShieldAlert size={15} />
    <div>
      <b>State contradiction</b>
      <p className="mt-1 text-red-200/70">
        Actionable overlays were removed and paper registration was blocked.
      </p>
    </div>
  </div>
);
export function ReplayProgress({ progress = 42 }: { progress?: number }) {
  return (
    <div className="w-72 space-y-2">
      <div className="flex justify-between text-xs">
        <span>Replay progress</span>
        <span className="font-mono">{progress}%</span>
      </div>
      <div className="h-1 overflow-hidden bg-zinc-800">
        <div className="h-full bg-blue-500" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
export const EmptyEvidence = ({
  openReplay = () => {},
}: {
  openReplay?: () => void;
}) => (
  <EmptyState
    icon={Database}
    title="No evidence yet"
    description="Performance appears after valid paper or replay trades resolve."
    action="Open Replay"
    onAction={openReplay}
  />
);
export function ScannerRowPreview() {
  return (
    <div className="grid w-[760px] grid-cols-[1.2fr_.8fr_.8fr_1fr_1fr] items-center border-y border-white/[.07] bg-[#0b0e14] px-3 py-2 text-xs">
      <b>Volatility 50</b>
      <span>VOLATILITY</span>
      <span className="font-mono">86.1889</span>
      <StatusBadge tone="developing">Developing</StatusBadge>
      <span className="text-zinc-500">Waiting for MSS</span>
    </div>
  );
}
export function SymbolSelectorPreview() {
  return (
    <Button className="w-56 justify-between">
      <span>Volatility 50 Index</span>
      <span className="font-mono text-zinc-500">R_50</span>
    </Button>
  );
}
