import type { NormalizedDecision, Overlay } from "@/types";

/**
 * Setup Focus (Phase 3 §5): a further presentation-only reduction on top of
 * density filtering, to the specific handful of levels a trader needs for
 * whatever the setup is doing right now. It never changes which overlays
 * EXIST or are permitted (that stays owned by selectVisibleOverlays /
 * applyDensity) -- it only narrows which of the already-permitted overlays
 * are kept, and it never reorders them.
 *
 * Design note: the milestone describes Setup Focus as "enabled by default
 * in CLEAN mode" rather than as an independently persisted toggle, so it is
 * implemented here as the specific behavior CLEAN mode exhibits (derived
 * from densityMode, not a second stored flag) -- switching density mode
 * away from CLEAN is how a trader turns it off.
 */
export function applySetupFocus(
  overlays: Overlay[],
  decision: NormalizedDecision | undefined,
): Overlay[] {
  if (!decision) return overlays;
  const tradeReady = Boolean(decision.decision?.trade_ready);
  const hasActiveSetup = Boolean(decision.active_setup);
  const currentPrice = overlays.find((o) => o.type === "current_price")?.price ?? null;

  if (tradeReady) {
    const chosen = new Set<string>();
    for (const o of overlays) {
      if (o.type === "current_price") chosen.add(o.overlay_id);
      if (o.actionable) chosen.add(o.overlay_id); // entry, stop, TP1, TP2, actionable invalidation
      if (o.category === "developing" && o.low != null && o.high != null) chosen.add(o.overlay_id); // setup zone, when still useful
    }
    for (const o of nearestStructureReferences(overlays, currentPrice, 1)) chosen.add(o.overlay_id);
    return overlays.filter((o) => chosen.has(o.overlay_id));
  }

  if (hasActiveSetup) {
    const chosen = new Set<string>();
    for (const o of overlays) {
      if (o.type === "current_price") chosen.add(o.overlay_id);
      if (o.category !== "developing") continue;
      const isZone = o.low != null && o.high != null;
      const isConfirmation = o.type.includes("confirmation");
      const isInvalidation = o.type.includes("invalidation");
      const isObjective = o.type.includes("objective");
      if (isZone || isConfirmation || isInvalidation || isObjective) chosen.add(o.overlay_id);
    }
    for (const o of nearestStructureReferences(overlays, currentPrice, 1)) chosen.add(o.overlay_id);
    return overlays.filter((o) => chosen.has(o.overlay_id));
  }

  // No setup: current price + external high/low + active range/market
  // context + nearest liquidity above/below -- all of these already live in
  // the "context" category, and this state has nothing more specific to
  // narrow down to, so every context-tier overlay is kept (unlike the two
  // branches above, which narrow structure references to the nearest one
  // per side).
  const chosen = new Set<string>();
  for (const o of overlays) {
    if (o.type === "current_price") chosen.add(o.overlay_id);
    if (o.category === "context") chosen.add(o.overlay_id);
  }
  return overlays.filter((o) => chosen.has(o.overlay_id));
}

/**
 * Picks the nearest-to-current-price line overlay above and the nearest
 * below, up to `perSide` each -- a type-name-agnostic way to surface "one
 * external structure reference above, one below" without depending on an
 * exhaustive, brittle list of every structure-overlay type name the backend
 * might emit. Restricted to category "context" (where H1/M15 external
 * structure references live, e.g. h1_context/structural_range) so this can
 * never accidentally rescue an internal-swing or diagnostic-tier overlay
 * that CLEAN density filtering is supposed to keep hidden.
 */
function nearestStructureReferences(
  overlays: Overlay[],
  currentPrice: number | null,
  perSide: number,
): Overlay[] {
  const candidates = overlays.filter(
    (o) => o.price != null && o.category === "context" && o.type !== "current_price" && o.low == null && o.high == null,
  );
  if (currentPrice == null) return candidates.slice(0, perSide * 2);
  const above = candidates
    .filter((o) => (o.price as number) > currentPrice)
    .sort((a, b) => (a.price as number) - (b.price as number))
    .slice(0, perSide);
  const below = candidates
    .filter((o) => (o.price as number) < currentPrice)
    .sort((a, b) => (b.price as number) - (a.price as number))
    .slice(0, perSide);
  return [...above, ...below];
}
