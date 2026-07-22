import type { NormalizedDecision } from "@/types";
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
