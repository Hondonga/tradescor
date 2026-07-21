import { describe, expect, it } from "vitest";
import { priorityLevelOf, priorityLevelLabel, priorityRank, PRIORITY_LEVELS } from "./overlayPriority";
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
    timeframe: "M5",
    category: "context",
    type: "generic",
    label: "Generic",
    source: "backend",
    price: 100,
    low: null,
    high: null,
    start_time: null,
    end_time: null,
    created_at: null,
    confirmed_at: null,
    expires_at: null,
    invalidated_at: null,
    active: true,
    historical: false,
    actionable: false,
    priority: 50,
    display_group: "context",
    metadata: {},
    ...overrides,
  };
}

describe("priorityLevelOf", () => {
  it("classifies any actionable overlay as ACTIONABLE regardless of type", () => {
    expect(priorityLevelOf(overlay({ actionable: true, type: "entry" }))).toBe("ACTIONABLE");
    expect(priorityLevelOf(overlay({ actionable: true, type: "tp2" }))).toBe("ACTIONABLE");
  });

  it("classifies pullback area / confirmation / invalidation / objective as ACTIVE_SETUP", () => {
    expect(priorityLevelOf(overlay({ category: "developing", type: "m15_pullback_area" }))).toBe("ACTIVE_SETUP");
    expect(priorityLevelOf(overlay({ category: "developing", type: "confirmation" }))).toBe("ACTIVE_SETUP");
    expect(priorityLevelOf(overlay({ category: "developing", type: "setup_invalidation" }))).toBe("ACTIVE_SETUP");
  });

  it("classifies high-priority context (external structure) as PRIMARY_STRUCTURE", () => {
    expect(priorityLevelOf(overlay({ category: "context", type: "h1_context", priority: 80 }))).toBe("PRIMARY_STRUCTURE");
  });

  it("classifies current price as CURRENT_CONTEXT", () => {
    expect(priorityLevelOf(overlay({ category: "context", type: "current_price", priority: 110 }))).toBe("CURRENT_CONTEXT");
  });

  it("classifies advanced-SMC diagnostic evidence as DIAGNOSTIC", () => {
    expect(priorityLevelOf(overlay({ type: "swing_high", display_group: "advanced_smc" }))).toBe("DIAGNOSTIC");
    expect(priorityLevelOf(overlay({ type: "equal_high", display_group: "advanced_smc" }))).toBe("DIAGNOSTIC");
  });

  it("classifies any historical overlay as HISTORICAL regardless of type", () => {
    expect(priorityLevelOf(overlay({ historical: true, type: "historical_entry" }))).toBe("HISTORICAL");
  });

  it("actionable takes precedence over historical when both are somehow set", () => {
    expect(priorityLevelOf(overlay({ actionable: true, historical: true, type: "entry" }))).toBe("ACTIONABLE");
  });
});

describe("priorityLevelLabel / priorityRank", () => {
  it("has a human label for every level", () => {
    for (const level of PRIORITY_LEVELS) {
      expect(priorityLevelLabel(level)).toBeTruthy();
    }
  });

  it("ranks ACTIONABLE strictly above DIAGNOSTIC", () => {
    expect(priorityRank("ACTIONABLE")).toBeLessThan(priorityRank("DIAGNOSTIC"));
  });

  it("preserves the exact seven required levels in priority order", () => {
    expect(PRIORITY_LEVELS).toEqual([
      "ACTIONABLE",
      "ACTIVE_SETUP",
      "PRIMARY_STRUCTURE",
      "CURRENT_CONTEXT",
      "SUPPORTING_EVIDENCE",
      "HISTORICAL",
      "DIAGNOSTIC",
    ]);
  });
});
