import { useState } from "react";
import { Bell, Star } from "lucide-react";
import { titleCase } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { MarketRow } from "@/types";

export interface OpportunityQueueProps {
  rows: MarketRow[];
  onSelect: (row: MarketRow) => void;
  dataReadiness: string;
  onAnalyzeNow: () => void;
  analyzePending: boolean;
}

/** A research-only candidate can never be presented as an actionable
 * opportunity (Phase 2 quarantine rules, Phase 3 §18/§19). */
function isResearchOnly(row: MarketRow): boolean {
  return Boolean(row.decision?.setup?.research_only);
}

/** The queue only ever shows rows with a real, backend-owned active setup --
 * never a bare "not analyzed" placeholder or a neutral-direction row (which
 * structurally cannot carry an active_setup per the global overlay
 * contract). */
function hasValidActiveSetup(row: MarketRow): boolean {
  return Boolean(row.decision?.active_setup);
}

function queueEligible(row: MarketRow, showResearch: boolean): boolean {
  if (!hasValidActiveSetup(row)) return false;
  if (isResearchOnly(row) && !showResearch) return false;
  return true;
}

function directionText(row: MarketRow): string {
  const direction = row.decision?.decision.direction;
  return direction ? titleCase(direction) : "Neutral";
}

function lifecycleText(row: MarketRow): string {
  const active = row.decision?.active_setup as Record<string, unknown> | null | undefined;
  const lifecycle = active?.lifecycle ?? active?.state ?? row.decision?.decision.stage;
  return typeof lifecycle === "string" && lifecycle ? titleCase(lifecycle) : "—";
}

function strategyText(row: MarketRow): string {
  return titleCase(row.decision?.ownership.selected_strategy_id || row.decision?.ownership.selected_model_id) || "—";
}

/** Always the backend's own pre-translated text (first_blocking_gate /
 * next_required_condition) -- never a raw code, and never invented here. */
function missingRequirementText(row: MarketRow): string {
  const decision = row.decision;
  if (!decision) return "—";
  if (decision.decision.trade_ready) return "Trade-ready";
  const active = decision.active_setup as Record<string, unknown> | null | undefined;
  return (
    (typeof active?.first_blocking_gate === "string" ? active.first_blocking_gate : undefined) ||
    decision.decision.first_blocking_gate ||
    decision.setup.next_required_condition ||
    "—"
  );
}

function freshnessText(row: MarketRow): string {
  return row.dataFreshness || row.lastAnalysis || "—";
}

/**
 * Opportunity queue (Phase 3 §19), extracted from workspace-page.tsx. Shows
 * only production-supported developing/plan-validation/trade-ready setups
 * by default; research-only candidates require the explicit "Show
 * Research" toggle and are always visually muted/labeled RESEARCH.
 */
export function OpportunityQueue({ rows, onSelect, dataReadiness, onAnalyzeNow, analyzePending }: OpportunityQueueProps) {
  const [showResearch, setShowResearch] = useState(false);
  const visible = rows.filter((row) => queueEligible(row, showResearch));
  const researchCount = rows.filter((row) => hasValidActiveSetup(row) && isResearchOnly(row)).length;

  return (
    <aside className="queue-panel">
      <header>
        <b>Opportunity queue</b>
        <div className="flex items-center gap-2">
          {researchCount > 0 && (
            <button
              type="button"
              aria-pressed={showResearch}
              onClick={() => setShowResearch((v) => !v)}
              className="rounded border border-white/10 px-1.5 py-0.5 text-[9px] text-zinc-500 hover:text-zinc-300"
            >
              Show Research {researchCount > 0 && `(${researchCount})`}
            </button>
          )}
          <Bell size={13} />
        </div>
      </header>
      {visible.length ? (
        visible.map((row) => (
          <button key={row.symbol.provider_symbol} onClick={() => onSelect(row)}>
            <Star size={11} />
            <span className="min-w-0 flex-1">
              <b className="flex items-center gap-1.5">
                {row.symbol.display_name}
                <span className="font-mono text-[9px] font-normal text-zinc-500">{row.decision?.meta.timeframe}</span>
                {isResearchOnly(row) && (
                  <span className="rounded-sm border border-research/40 bg-research/10 px-1 text-[8px] font-semibold text-research">
                    RESEARCH
                  </span>
                )}
              </b>
              <small>
                {strategyText(row)} · {directionText(row)} · {lifecycleText(row)}
              </small>
              <small className="block text-zinc-600">
                {missingRequirementText(row)} · {freshnessText(row)}
              </small>
            </span>
          </button>
        ))
      ) : dataReadiness === "error" ? (
        <div className="queue-empty">
          <b>OPPORTUNITY QUEUE PAUSED</b>
          <br />
          Live analysis is unavailable because completed candle data could
          not be loaded.
        </div>
      ) : (
        <div className="queue-empty">
          {rows.length ? "No production-supported opportunities right now." : "Star symbols in Markets to build the queue."}
        </div>
      )}
      <Button className="m-3" onClick={onAnalyzeNow} disabled={analyzePending}>
        Analyze now
      </Button>
    </aside>
  );
}
