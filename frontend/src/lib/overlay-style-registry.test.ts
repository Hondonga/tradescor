import { describe, expect, it } from "vitest";
import { styleForOverlay, tierOf } from "./overlay-style-registry";
import { SEMANTIC_COLORS } from "./chart/semanticColors";
import type { Overlay } from "@/types";

function overlay(overrides: Partial<Overlay> = {}): Overlay {
  return {
    overlay_id: "o",
    decision_owner_id: "owner",
    strategy_id: "strategy",
    setup_id: "setup-1",
    symbol_id: "deriv:R_75",
    provider_symbol: "R_75",
    market_type: "derived",
    timeframe: "M15",
    category: "developing",
    type: "m15_pullback_area",
    label: "M15 Pullback Area",
    source: "backend",
    price: null,
    low: 100,
    high: 200,
    start_time: null,
    end_time: null,
    created_at: null,
    confirmed_at: null,
    expires_at: null,
    invalidated_at: null,
    active: true,
    historical: false,
    actionable: false,
    priority: 90,
    display_group: "setup",
    metadata: {},
    ...overrides,
  };
}

describe("styleForOverlay direction-aware zone coloring", () => {
  it("colors a buy-direction developing zone bullish", () => {
    const style = styleForOverlay(overlay({ metadata: { direction: "buy" } }));
    expect(style.color).toBe(SEMANTIC_COLORS.bullish);
  });

  it("colors a bullish-direction developing zone bullish", () => {
    const style = styleForOverlay(overlay({ metadata: { direction: "bullish" } }));
    expect(style.color).toBe(SEMANTIC_COLORS.bullish);
  });

  it("colors a sell-direction developing zone bearish", () => {
    const style = styleForOverlay(overlay({ metadata: { direction: "sell" } }));
    expect(style.color).toBe(SEMANTIC_COLORS.bearish);
  });

  it("colors a bearish-direction developing zone bearish", () => {
    const style = styleForOverlay(overlay({ metadata: { direction: "bearish" } }));
    expect(style.color).toBe(SEMANTIC_COLORS.bearish);
  });

  it("falls back to the neutral actionable tone with no direction metadata", () => {
    const style = styleForOverlay(overlay({ metadata: {} }));
    expect(style.color).toBe(SEMANTIC_COLORS.actionable);
  });

  it("never lets direction override an explicit invalidation/confirmation/objective role", () => {
    const invalidation = styleForOverlay(overlay({ type: "setup_invalidation", metadata: { direction: "buy" } }));
    expect(invalidation.color).toBe(SEMANTIC_COLORS.bearish);
    const confirmation = styleForOverlay(overlay({ type: "confirmation", metadata: { direction: "sell" } }));
    expect(confirmation.color).toBe(SEMANTIC_COLORS.warning);
  });
});

describe("styleForOverlay tier-1 (actionable) colors", () => {
  it("colors a stop bearish", () => {
    const style = styleForOverlay(overlay({ category: "actionable", type: "stop", metadata: { plan_role: "stop" } }));
    expect(style.color).toBe(SEMANTIC_COLORS.bearish);
  });

  it("colors a target bullish", () => {
    const style = styleForOverlay(overlay({ category: "actionable", type: "tp1", metadata: { plan_role: "tp1" } }));
    expect(style.color).toBe(SEMANTIC_COLORS.bullish);
  });

  it("colors an entry with the actionable tone", () => {
    const style = styleForOverlay(overlay({ category: "actionable", type: "entry", metadata: { plan_role: "entry" } }));
    expect(style.color).toBe(SEMANTIC_COLORS.actionable);
  });
});

describe("tierOf", () => {
  it("still assigns tier 1 to actionable overlays after the palette refactor", () => {
    expect(tierOf(overlay({ category: "actionable" }))).toBe(1);
  });
});

describe("styleForOverlay swing/equal-high-low rendering (Phase 3 §1/§9)", () => {
  it("renders swing highs/lows and equal highs/lows as compact markers, never a permanent full-width line", () => {
    for (const type of ["swing_high", "swing_low", "equal_high", "equal_low"]) {
      const style = styleForOverlay(overlay({ category: "diagnostic" as any, display_group: "advanced_smc", type, low: null, high: null }));
      expect(style.renderAs).toBe("marker");
    }
  });
});
