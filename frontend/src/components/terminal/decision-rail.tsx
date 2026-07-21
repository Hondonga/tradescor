import { ChevronDown } from "lucide-react";
import {
  DecisionHeader,
  TradeReadyPlan,
  DataLoadingState,
  ProviderErrorState,
  StaleConnectionState,
} from "./status-components";
import { useTerminalStore } from "@/store/terminal-store";
import { useAnalysis } from "@/hooks/use-analysis";
import { revealHistoricalOutcome } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { formatPrice, titleCase } from "@/lib/utils";
import type { NormalizedDecision } from "@/types";

// Phase 3 §11 — required top-level section order: MARKET STATE, ACTIVE
// SETUP, WHAT IS MISSING, TRADE PLAN, NEXT ACTION, DETAILS, DIAGNOSTICS.
// Every blocker/next-action string rendered here already arrives
// pre-translated from the backend (analysis/blocker_translations.py, wired
// into first_blocking_gate/next_action at the engine layer) -- this
// component never shows a raw underscored code as primary text; raw codes
// only ever appear inside the collapsed DIAGNOSTICS group.
export function DecisionRail() {
  const store = useTerminalStore();
  const { decision, dataReadiness } = store;
  const analysis = useAnalysis();
  if (dataReadiness === "loading")
    return (
      <aside className="h-full bg-[#0b0e14]">
        <DataLoadingState />
      </aside>
    );
  if (dataReadiness === "error")
    return (
      <aside className="h-full bg-[#0b0e14]">
        <ProviderErrorState
          symbol={store.symbol.provider_symbol}
          retry={() => analysis.mutate()}
        />
      </aside>
    );
  if (!decision)
    return (
      <aside className="grid h-full place-items-center bg-[#0b0e14] p-8 text-center">
        <div>
          <h2 className="text-sm font-semibold">No analysis yet</h2>
          <p className="mt-2 text-xs leading-5 text-zinc-500">
            Run SMC analysis to populate structure, blockers, and the backend
            trade plan.
          </p>
        </div>
      </aside>
    );

  const currentMarket = (decision.current_market ||
    decision.market) as NormalizedDecision["market"] & Record<string, unknown>;
  const activeSetup = decision.active_setup as
    | (NormalizedDecision["setup"] & Record<string, unknown>)
    | null
    | undefined;
  const jumpEvent = (decision.setup.recent_event || {}) as Record<
    string,
    string | null | undefined
  >;
  const jumpLevels = (decision.setup.confirmation_levels || {}) as Record<
    string,
    string | undefined
  >;
  const tradeReady = Boolean(decision.decision.trade_ready);
  const planVisible = Boolean(
    activeSetup && decision.trade_plan?.available === true && tradeReady,
  );
  const primaryBlocker =
    activeSetup?.first_blocking_gate || decision.decision.first_blocking_gate;
  const strategyLabel = titleCase(
    decision.ownership.selected_strategy_id || decision.ownership.selected_model_id,
  );

  return (
    <aside className="h-full overflow-y-auto bg-[#0b0e14]">
      {store.workspaceMode !== "live" && (
        <InspectionBanner mode={store.workspaceMode} />
      )}
      {decision.readiness.state.toLowerCase() === "stale" && (
        <StaleConnectionState through={decision.readiness.last_successful_update} />
      )}
      <DecisionHeader decision={decision} />

      {/* 1. MARKET STATE */}
      <section className="border-b border-white/[.07] p-4">
        <p className="label">Market state</p>
        <dl className="detail-grid mt-3">
          <dt>Direction</dt>
          <dd>
            {titleCase(
              text(currentMarket.direction) ||
                decision.decision.direction ||
                "neutral",
            )}
          </dd>
          <dt>External structure</dt>
          <dd>{titleCase(currentMarket.external_structure) || "—"}</dd>
          <dt>Condition</dt>
          <dd>
            {titleCase(
              text(currentMarket.condition) || currentMarket.internal_structure,
            ) || "—"}
          </dd>
          <dt>Data freshness</dt>
          <dd>{titleCase(decision.readiness.state)}</dd>
          <dt>Strategy</dt>
          <dd>{strategyLabel || "—"}</dd>
          <dt>Current price</dt>
          <dd className="font-mono">
            {formatPrice(currentMarket.current_price, decision.precision)}
          </dd>
        </dl>
      </section>

      {decision.market_analysis?.continuation_context === "bearish_pullback" && (
        <section className="border-b border-white/[.07] p-4">
          <p className="label">Developing scenario</p>
          <h3 className="mt-2 text-sm font-medium">
            {decision.market_analysis.developing_scenario}
          </h3>
          <dl className="detail-grid mt-3">
            <dt>Market structure</dt>
            <dd>{decision.market_analysis.external_structure_display}</dd>
            <dt>M15 condition</dt>
            <dd>{decision.market_analysis.internal_structure_display}</dd>
            <dt>Confirmation required</dt>
            <dd>{decision.market_analysis.next_confirmation}</dd>
          </dl>
        </section>
      )}

      {/* 2. ACTIVE SETUP */}
      {activeSetup ? (
        <section className="border-b border-white/[.07] p-4">
          <p className="label">Active setup</p>
          <h3 className="mt-2 text-sm font-medium">
            {titleCase(activeSetup.setup_type || "Active setup")}
          </h3>
          <dl className="detail-grid mt-3">
            <dt>Direction</dt>
            <dd>{titleCase(text(activeSetup.direction)) || "—"}</dd>
            <dt>Lifecycle</dt>
            <dd>
              {titleCase(
                text(activeSetup.lifecycle) ||
                  text(activeSetup.state) ||
                  activeSetup.stage,
              )}
            </dd>
            <dt>Setup area</dt>
            <dd>
              {decision.setup.entry_area
                ? `${formatPrice(decision.setup.entry_area.low, decision.precision)} – ${formatPrice(decision.setup.entry_area.high, decision.precision)}`
                : "—"}
            </dd>
            <dt>Confirmation</dt>
            <dd>{decision.setup.completed_confirmation ? "Confirmed" : "Pending"}</dd>
            <dt>Invalidation</dt>
            <dd>
              {formatPrice(activeSetup.invalidation?.price, decision.precision)}
            </dd>
          </dl>
          {activeSetup.invalidation?.condition && (
            <p className="mt-3 text-[11px] leading-4 text-zinc-500">
              {activeSetup.invalidation.condition}
            </p>
          )}
        </section>
      ) : (
        <section className="border-b border-white/[.07] p-4">
          <p className="label">Active setup</p>
          <h3 className="mt-2 text-sm">None</h3>
          <p className="mt-2 text-xs leading-5 text-zinc-500">
            Current structure remains available while TradeScor waits for a new
            qualifying setup.
          </p>
        </section>
      )}

      {activeSetup && decision.setup.jump_mode === "JUMP_POST_EVENT_SMC" && (
        <section className="border-b border-white/[.07] p-4">
          <p className="label">Jump post-event research</p>
          <dl className="detail-grid mt-3">
            <dt>Recent event</dt>
            <dd>{jumpEvent.status || "—"}</dd>
            <dt>Future jump direction</dt>
            <dd>{jumpEvent.future_direction || "Unknown"}</dd>
            <dt>Confirmation levels</dt>
            <dd>
              Bullish: {jumpLevels.bullish || "—"}
              <br />
              Bearish: {jumpLevels.bearish || "—"}
            </dd>
          </dl>
        </section>
      )}

      {/* 3. WHAT IS MISSING -- one clear primary blocker, plain translated text */}
      {activeSetup && !tradeReady && (
        <section className="border-b border-white/[.07] p-4">
          <p className="label">What is missing</p>
          <p className="mt-2 text-xs leading-5 text-zinc-300">
            {primaryBlocker || "Waiting for the next completed structural condition."}
          </p>
          {activeSetup.next_required_condition && (
            <p className="mt-2 text-[11px] leading-5 text-zinc-500">
              {activeSetup.next_required_condition}
            </p>
          )}
        </section>
      )}

      {/* 4. TRADE PLAN -- only when available */}
      {planVisible && <TradeReadyPlan decision={decision} />}

      {/* 5. NEXT ACTION -- plain language */}
      <section className="border-b border-white/[.07] p-4">
        <p className="label">Next action</p>
        <p className="mt-2 text-xs leading-5 text-zinc-300">
          {decision.decision.next_action}
        </p>
      </section>

      {/* 6. DETAILS -- target source, structural source, setup ownership, timeframe context */}
      {activeSetup && (
        <details className="border-b border-white/[.07] p-4">
          <summary className="flex cursor-pointer list-none items-center justify-between text-xs text-zinc-400">
            Details
            <ChevronDown size={13} />
          </summary>
          <dl className="detail-grid mt-3">
            <dt>Target source</dt>
            <dd>{titleCase(decision.setup.target_source) || "—"}</dd>
            <dt>Target timeframe</dt>
            <dd>{decision.setup.target_timeframe || "—"}</dd>
            <dt>Structural timeframe</dt>
            <dd>{decision.meta.timeframe}</dd>
            <dt>Setup ownership</dt>
            <dd className="break-all">{decision.ownership.decision_owner_id}</dd>
            <dt>Setup ID</dt>
            <dd className="break-all font-mono">{activeSetup.setup_id}</dd>
          </dl>
        </details>
      )}

      {Boolean(decision.previous_setup) && (
        <details className="border-b border-white/[.07] p-4">
          <summary className="flex cursor-pointer list-none items-center justify-between text-xs text-zinc-400">
            Previous setup
            <ChevronDown size={13} />
          </summary>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap font-mono text-[10px] text-zinc-500">
            {JSON.stringify(decision.previous_setup, null, 2)}
          </pre>
        </details>
      )}

      {store.workspaceMode === "historical" && (
        <section className="border-b border-white/[.07] p-4">
          {!store.historicalOutcome ? (
            <Button
              className="w-full"
              onClick={async () =>
                store.setHistoricalOutcome(
                  await revealHistoricalOutcome(store.historicalJobId!),
                )
              }
            >
              Reveal later outcome
            </Button>
          ) : (
            <>
              <p className="label">Later outcome</p>
              <pre className="mt-3 whitespace-pre-wrap font-mono text-[10px] text-zinc-400">
                {JSON.stringify(store.historicalOutcome, null, 2)}
              </pre>
              <p className="mt-3 text-[10px] text-amber-300">
                This information was unavailable when the setup was generated.
              </p>
            </>
          )}
        </section>
      )}

      {/* 7. DIAGNOSTICS -- collapsed by default; opens only via the
          toolbar's explicit Diagnostics toggle. Raw codes live here, never
          in the sections above. */}
      {[
        ["Evidence", activeSetup || currentMarket],
        ["SMC entities", activeSetup || currentMarket],
        ["Diagnostics", decision.diagnostics],
      ].map(([label, value]) => (
        <details key={label as string} open={store.diagnosticsVisible} className="border-b border-white/[.07] p-4">
          <summary className="flex cursor-pointer list-none items-center justify-between text-xs text-zinc-400">
            {label as string}
            <ChevronDown size={13} />
          </summary>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap font-mono text-[10px] text-zinc-500">
            {JSON.stringify(value, null, 2)}
          </pre>
        </details>
      ))}
    </aside>
  );
}

function InspectionBanner({ mode }: { mode: "historical" | "replay" }) {
  return (
    <section className="border-b border-amber-400/20 bg-amber-400/[.06] p-4">
      <p className="text-[10px] font-semibold tracking-[.16em] text-amber-300">
        {mode === "historical" ? "HISTORICAL INSPECTION" : "REPLAY INSPECTION"}
      </p>
      <h3 className="mt-2 text-sm">FROZEN AT DECISION TIME</h3>
      <p className="mt-1 text-[11px] text-zinc-500">
        These objects are isolated from the current live decision.
      </p>
    </section>
  );
}

function text(value: unknown) {
  return typeof value === "string" ? value : "";
}
