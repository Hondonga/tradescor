// Chart visual density modes (Milestone: chart redesign, §13). Purely a
// display-layer filter over an already-normalized, already-permission-
// checked overlay list (selectVisibleOverlays / overlayVisibility toggles
// still run first) — this module never changes which overlays exist or
// what they mean, only how many of them are shown by default.
import type { Overlay } from "@/types";
import { tierOf } from "./overlay-style-registry";

export type DensityMode = "clean" | "standard" | "research";

export const DENSITY_MODES: DensityMode[] = ["clean", "standard", "research"];

const CURRENT_PRICE = "current_price";

/**
 * CLEAN (default / "Setup Focus"): current price, the full actionable plan,
 * the full active developing setup (pullback/entry zone, confirmation,
 * invalidation, potential objective), and at most one external structure
 * reference — the highest-priority tier-3 row.
 *
 * STANDARD: CLEAN plus every tier-3 market-structure row (external/internal
 * highs-lows, range boundaries, equilibrium, key liquidity).
 *
 * RESEARCH: everything (tier 1-4) — equivalent to Advanced SMC fully on.
 */
export function applyDensity(overlays: Overlay[], mode: DensityMode): Overlay[] {
  if (mode === "research") return overlays;

  const tier1 = overlays.filter((o) => tierOf(o) === 1);
  const tier2 = overlays.filter((o) => tierOf(o) === 2);
  const tier3 = overlays.filter((o) => tierOf(o) === 3 && o.type !== CURRENT_PRICE);
  const currentPrice = overlays.filter((o) => o.type === CURRENT_PRICE);

  if (mode === "standard") return [...currentPrice, ...tier1, ...tier2, ...tier3];

  const nearestStructure = tier3.length
    ? [tier3.reduce((best, row) => (row.priority > best.priority ? row : best))]
    : [];
  return [...currentPrice, ...tier1, ...tier2, ...nearestStructure];
}

/** How many tier-3/4 rows CLEAN mode is currently hiding, for the toolbar's "hidden evidence" indicator. */
export function hiddenEvidenceCount(overlays: Overlay[], mode: DensityMode): number {
  if (mode === "research") return 0;
  return overlays.length - applyDensity(overlays, mode).length;
}
