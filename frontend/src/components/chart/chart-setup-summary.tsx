import { titleCase } from "@/lib/utils";
import type { NormalizedDecision } from "@/types";

export interface ChartSetupSummaryProps {
  decision?: NormalizedDecision;
  /** false when the parent has hidden Setup Focus or the chart is too narrow. */
  visible: boolean;
}

/**
 * Small chart-side setup card (Milestone: chart redesign, §11). Deliberately
 * thin — three lines, no duplication of the full decision rail.
 */
export function ChartSetupSummary({ decision, visible }: ChartSetupSummaryProps) {
  if (!visible || !decision) return null;
  const activeSetup = decision.active_setup as
    | (NormalizedDecision["setup"] & Record<string, unknown>)
    | null
    | undefined;
  if (!activeSetup) return null;

  const direction = String(activeSetup.direction || decision.decision.direction || "").toLowerCase();
  if (direction !== "buy" && direction !== "sell") return null;

  const setupType = titleCase(String(activeSetup.setup_type || decision.setup.setup_type || ""));
  const stage = titleCase(
    String(activeSetup.lifecycle || activeSetup.state || activeSetup.stage || decision.decision.stage || ""),
  );
  const waitingFor = decision.decision.next_action || activeSetup.next_required_condition;

  return (
    <div className="pointer-events-none absolute left-2 top-2 z-30 w-44 border border-white/[.08] bg-[#0b0e14]/90 p-2 backdrop-blur-sm">
      <p
        className={
          "text-[10px] font-semibold tracking-[.06em] " +
          (direction === "sell" ? "text-red-300" : "text-emerald-300")
        }
      >
        {direction.toUpperCase()} SETUP
      </p>
      {setupType && <p className="text-[9px] text-zinc-500">{setupType}</p>}
      <div className="mt-2 space-y-1.5">
        <div>
          <p className="text-[8px] uppercase tracking-[.08em] text-zinc-600">Stage</p>
          <p className="truncate text-[10px] text-zinc-200">{stage || "—"}</p>
        </div>
        {waitingFor && (
          <div>
            <p className="text-[8px] uppercase tracking-[.08em] text-zinc-600">Waiting for</p>
            <p className="line-clamp-2 text-[10px] text-zinc-300">{waitingFor}</p>
          </div>
        )}
      </div>
    </div>
  );
}
