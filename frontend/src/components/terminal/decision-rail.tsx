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
  const planVisible = Boolean(
    activeSetup &&
      decision.trade_plan?.available === true &&
      decision.decision.trade_ready,
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

      <section className="border-b border-white/[.07] p-4">
        <p className="label">Current market</p>
        <dl className="detail-grid mt-3">
          <dt>External structure</dt>
          <dd>{titleCase(currentMarket.external_structure) || "—"}</dd>
          <dt>Condition</dt>
          <dd>
            {titleCase(
              text(currentMarket.condition) || currentMarket.internal_structure,
            ) || "—"}
          </dd>
          <dt>Direction</dt>
          <dd>
            {titleCase(
              text(currentMarket.direction) ||
                decision.decision.direction ||
                "neutral",
            )}
          </dd>
          <dt>Current price</dt>
          <dd className="font-mono">
            {formatPrice(currentMarket.current_price, decision.precision)}
          </dd>
          <dt>Data state</dt>
          <dd>{titleCase(decision.readiness.state)}</dd>
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

      {activeSetup ? (
        <section className="border-b border-white/[.07] p-4">
          <p className="label">Active setup</p>
          <h3 className="mt-2 text-sm font-medium">
            {titleCase(activeSetup.setup_type || "Active setup")}
          </h3>
          <dl className="detail-grid mt-3">
            <dt>Stage</dt>
            <dd>
              {titleCase(
                text(activeSetup.lifecycle) ||
                  text(activeSetup.state) ||
                  activeSetup.stage,
              )}
            </dd>
            <dt>Blocker</dt>
            <dd>
              {activeSetup.first_blocking_gate ||
                decision.decision.first_blocking_gate ||
                "None"}
            </dd>
            <dt>Waiting for</dt>
            <dd>{activeSetup.next_required_condition || "—"}</dd>
            <dt>Idea invalidation</dt>
            <dd>
              {formatPrice(activeSetup.invalidation?.price, decision.precision)}
            </dd>
          </dl>
          {activeSetup.invalidation?.condition && (
            <p className="mt-3 text-[11px] leading-4 text-zinc-500">
              {activeSetup.invalidation.condition}
            </p>
          )}
          <details className="mt-3">
            <summary className="cursor-pointer text-[9px] text-zinc-600">Setup ID</summary>
            <p className="mt-1 break-all font-mono text-[9px] text-zinc-600">
              {activeSetup.setup_id}
            </p>
          </details>
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
            <dt>Plan blocker</dt>
            <dd>{decision.setup.plan_blocker || "Trade plan unavailable"}</dd>
          </dl>
        </section>
      )}

      {planVisible && <TradeReadyPlan decision={decision} />}

      <section className="border-b border-white/[.07] p-4">
        <p className="label">Next action</p>
        <p className="mt-2 text-xs leading-5 text-zinc-300">
          {decision.decision.next_action}
        </p>
      </section>

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

      {[
        ["Evidence", activeSetup || currentMarket],
        ["SMC entities", activeSetup || currentMarket],
        ["Diagnostics", decision.diagnostics],
      ].map(([label, value]) => (
        <details key={label as string} className="border-b border-white/[.07] p-4">
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
