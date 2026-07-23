import type { NormalizedDecision, StrategyEvidence } from "@/types";
import type { StatusTone } from "@/components/ui/status-badge";

/**
 * Single source of truth for user-facing status wording. The backend keeps
 * its own richer status/stage vocabulary (READY TO BUY, WAITING_FOR_MSS,
 * TOO_LATE, STATE CONTRADICTION, ...) for logic and diagnostics -- this
 * module only maps that vocabulary down to the three statuses users see:
 * TRADE READY, WATCHLIST, AVOID. It never changes `decision.decision.*`
 * itself, so nothing that keys off the raw fields (filtering, overlays,
 * request logic) is affected.
 */
export type CanonicalStatus = "TRADE READY" | "WATCHLIST" | "AVOID";

const AVOID_MARKERS = [
  "TOO LATE",
  "TOO_LATE",
  "EXPIRED",
  "INVALIDATED",
  "INVALID",
  "CONTRADICTION",
  "NO TRADE",
  "REJECTED",
  "MISSED",
  "NO VALID RE-ENTRY",
];

/** decision.decision.trade_ready is the one authoritative "is this really
 * tradeable right now" signal -- everything else is presentation. */
export function canonicalStatus(decision: NormalizedDecision): CanonicalStatus {
  if (decision.decision.trade_ready) return "TRADE READY";
  const status = String(decision.decision.status || "").toUpperCase();
  const stage = String(decision.decision.stage || "").toUpperCase();
  const timingStatus = String(decision.entry_timing?.status || "").toLowerCase();
  if (
    AVOID_MARKERS.some((marker) => status.includes(marker) || stage.includes(marker)) ||
    timingStatus === "too_late" ||
    timingStatus === "missed" ||
    timingStatus === "invalid"
  ) {
    return "AVOID";
  }
  return "WATCHLIST";
}

/**
 * Phase 6: the product-facing status. `canonicalStatus` above answers "what
 * did the engine reach" (ENGINE TRADE_READY, purely technical); this answers
 * "what may the product tell the user to do" (PRODUCT ACTIONABILITY). A
 * strategy that is engine TRADE_READY but has never been historically
 * validated is a RESEARCH PLAN, never a user-facing TRADE READY -- engine
 * readiness can never override validation eligibility.
 *
 * `strategyEvidence`/`decision.product_actionability` are backend-authoritative
 * (analysis/strategy_quarantine_registry.py + analysis/global_overlay_contract.py).
 * This function never invents eligibility itself; when the backend has not
 * attached `product_actionability` (older/cached decisions) it falls back to
 * treating the strategy as unvalidated, the conservative default.
 */
export type ProductStatus =
  | "TRADE_READY"
  | "RESEARCH_PLAN"
  | "WATCHLIST"
  | "RESEARCH_WATCH"
  | "AVOID"
  | "MARKET_CONTEXT"
  | "NO_VALIDATED_STRATEGY";

export function resolveProductStatus(
  decision: NormalizedDecision,
  strategyEvidence?: StrategyEvidence | null,
): ProductStatus {
  const status = String(decision.decision?.status || "").toUpperCase();
  const stage = String(decision.decision?.stage || "").toUpperCase();
  const timingStatus = String(decision.entry_timing?.status || "").toLowerCase();

  if (status.includes("NO_VALIDATED_STRATEGY") || stage.includes("NO_VALIDATED_STRATEGY")) {
    return "NO_VALIDATED_STRATEGY";
  }
  const avoid =
    AVOID_MARKERS.some((marker) => status.includes(marker) || stage.includes(marker)) ||
    timingStatus === "too_late" ||
    timingStatus === "missed" ||
    timingStatus === "invalid";
  if (avoid) return "AVOID";

  const actionability = decision.product_actionability;
  if (actionability) {
    if (actionability.status === "TRADE_READY") return "TRADE_READY";
    if (actionability.status === "RESEARCH_PLAN") return "RESEARCH_PLAN";
    if (actionability.status === "RESEARCH_WATCH") return "RESEARCH_WATCH";
    if (actionability.status === "MARKET_CONTEXT") return "MARKET_CONTEXT";
  }

  // Defensive fallback only -- every live decision carries product_actionability
  // once it passes through normalize_global_decision, so this only fires for
  // decisions that predate Phase 6 (old cached/replayed JSON, or fixtures
  // that don't model strategy evidence). When evidence is genuinely absent,
  // preserve the pre-Phase-6 3-state behavior rather than inventing a new
  // downgrade this decision never actually claimed; when evidence IS present
  // but shows the strategy unvalidated, never treat trade_ready as enough.
  const evidence = strategyEvidence ?? decision.strategy_evidence;
  const engineTradeReady = Boolean(decision.decision?.trade_ready);
  if (!evidence) {
    if (engineTradeReady) return "TRADE_READY";
    return "WATCHLIST";
  }
  const validated = Boolean(evidence.historical_edge_proven && !evidence.research_only);
  if (engineTradeReady) return validated ? "TRADE_READY" : "RESEARCH_PLAN";
  if (stage && stage !== "NO_CONTEXT" && stage !== "") return validated ? "WATCHLIST" : "RESEARCH_WATCH";
  return "MARKET_CONTEXT";
}

export function productStatusTone(status: ProductStatus): StatusTone {
  if (status === "TRADE_READY") return "ready";
  if (status === "AVOID") return "error";
  return "waiting";
}

export function productStatusLabel(status: ProductStatus): string {
  return {
    TRADE_READY: "TRADE READY",
    RESEARCH_PLAN: "RESEARCH PLAN",
    WATCHLIST: "WATCHLIST",
    RESEARCH_WATCH: "RESEARCH WATCH",
    AVOID: "AVOID",
    MARKET_CONTEXT: "MARKET CONTEXT",
    NO_VALIDATED_STRATEGY: "NO VALIDATED STRATEGY",
  }[status];
}

export function productStatusSubtitle(status: ProductStatus): string {
  return {
    TRADE_READY: "Historically validated trade plan available.",
    RESEARCH_PLAN: "Complete plan construction verified. Historical edge not proven -- research only.",
    WATCHLIST: "Setup forming. Waiting for confirmation.",
    RESEARCH_WATCH: "Developing setup. Research only -- historical edge not proven.",
    AVOID: "Too late to enter. Do not chase.",
    MARKET_CONTEXT: "Market context only. No setup yet.",
    NO_VALIDATED_STRATEGY: "No strategy for this market has passed the required historical validation.",
  }[status];
}

export function canonicalStatusTone(status: CanonicalStatus): StatusTone {
  if (status === "TRADE READY") return "ready";
  if (status === "AVOID") return "error";
  return "waiting";
}

export function canonicalStatusSubtitle(status: CanonicalStatus): string {
  if (status === "TRADE READY") return "Valid trade plan available.";
  if (status === "AVOID") return "Too late to enter. Do not chase.";
  return "Setup forming. Waiting for confirmation.";
}

/** Section 6: BUY setup / SELL setup / Neutral, for the "Looking for" line. */
export function directionLabel(direction?: string | null): string {
  const normalized = String(direction || "").toLowerCase();
  if (normalized === "buy") return "BUY setup";
  if (normalized === "sell") return "SELL setup";
  return "Neutral";
}

export interface EntryTimingCopy {
  label: "AT ENTRY" | "NEAR ENTRY" | "EXTENDED" | "TOO LATE" | "MISSED" | "INVALID";
  message: string;
}

const ENTRY_TIMING_COPY: Record<string, EntryTimingCopy> = {
  at_entry: {
    label: "AT ENTRY",
    message: "Price is inside the entry zone. Confirm risk before entering.",
  },
  near_entry: {
    label: "NEAR ENTRY",
    message: "Price is near the entry zone. Entry may still be valid if risk/reward holds.",
  },
  extended: {
    label: "EXTENDED",
    message: "Price has moved away from entry. Do not chase. Wait for a pullback.",
  },
  too_late: {
    label: "TOO LATE",
    message: "Too late to enter now. Price is too far from entry and reward is reduced.",
  },
  missed: {
    label: "MISSED",
    message: "Setup already moved to target area. Wait for the next setup.",
  },
  invalid: {
    label: "INVALID",
    message: "Setup is invalidated. Do not enter.",
  },
};

/** Looks up the exact required entry-timing label/message for a backend
 * entry_timing_status value (case-insensitive). Returns null when there is
 * no entry-timing classification to show. */
export function entryTimingCopy(status?: string | null): EntryTimingCopy | null {
  if (!status) return null;
  return ENTRY_TIMING_COPY[status.toLowerCase()] ?? null;
}

/** True when entry timing has already moved past a chaseable state -- the
 * single condition both the chart and the rail check before either one
 * renders a "too late"-style warning, so only one of them ever does. */
export function isLateEntryTiming(status?: string | null): boolean {
  const normalized = String(status || "").toLowerCase();
  return normalized === "too_late" || normalized === "extended" || normalized === "missed" || normalized === "invalid";
}
