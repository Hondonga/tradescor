import type { Overlay } from "@/types";

// Phase 3 §3 — the seven named presentation-priority levels. This is a
// documentation/display taxonomy (surfaced in the Drawing Inspector's
// "priority" field) layered on top of the existing, already-tested
// mechanisms that actually enforce it: overlay-style-registry.ts's
// numeric tier (visual weight -- opacity/line width/render style) and
// overlay-labels.ts's tagPriority (which tag survives a collision).
// Levels are ordered highest-priority first, matching that ordering.
export const PRIORITY_LEVELS = [
  "ACTIONABLE",
  "ACTIVE_SETUP",
  "PRIMARY_STRUCTURE",
  "CURRENT_CONTEXT",
  "SUPPORTING_EVIDENCE",
  "HISTORICAL",
  "DIAGNOSTIC",
] as const;

export type PriorityLevel = (typeof PRIORITY_LEVELS)[number];

const ACTIVE_SETUP_TYPES = new Set([
  "m15_pullback_area",
  "pullback_area",
  "confirmation",
  "setup_invalidation",
  "potential_objective",
  "entry_zone",
]);

const CURRENT_CONTEXT_TYPES = new Set([
  "current_price",
  "equilibrium",
  "liquidity",
  "unfilled_fvg",
  "active_fvg",
  "displacement",
  "m5_displacement",
]);

const DIAGNOSTIC_TYPES = new Set([
  "swing_high",
  "swing_low",
  "equal_high",
  "equal_low",
  "rejected_target",
  "target_candidate",
]);

/**
 * Classifies an already-normalized overlay into one of the seven required
 * priority levels. Presentation-only -- never changes what an overlay IS,
 * only how it is described/ranked when shown (e.g. in the Drawing
 * Inspector).
 */
export function priorityLevelOf(overlay: Overlay): PriorityLevel {
  if (overlay.actionable) return "ACTIONABLE";
  if (overlay.historical) return "HISTORICAL";
  const type = overlay.type.toLowerCase();
  if (overlay.category === "developing" && ACTIVE_SETUP_TYPES.has(type)) return "ACTIVE_SETUP";
  if (CURRENT_CONTEXT_TYPES.has(type)) return "CURRENT_CONTEXT";
  if (overlay.category === "context" && overlay.priority >= 70) return "PRIMARY_STRUCTURE";
  if (DIAGNOSTIC_TYPES.has(type) || overlay.display_group === "advanced_smc") return "DIAGNOSTIC";
  if (overlay.category === "developing") return "SUPPORTING_EVIDENCE";
  return "SUPPORTING_EVIDENCE";
}

export function priorityLevelLabel(level: PriorityLevel): string {
  return {
    ACTIONABLE: "Actionable",
    ACTIVE_SETUP: "Active setup",
    PRIMARY_STRUCTURE: "Primary structure",
    CURRENT_CONTEXT: "Current context",
    SUPPORTING_EVIDENCE: "Supporting evidence",
    HISTORICAL: "Historical",
    DIAGNOSTIC: "Diagnostic",
  }[level];
}

/** Rank of a level for comparisons -- lower number = higher priority. */
export function priorityRank(level: PriorityLevel): number {
  return PRIORITY_LEVELS.indexOf(level);
}
