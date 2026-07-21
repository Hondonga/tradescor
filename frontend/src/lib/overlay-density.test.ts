import { describe, expect, it } from "vitest";
import { applyDensity, hiddenEvidenceCount } from "./overlay-density";
import type { Overlay } from "@/types";

function overlay(overrides: Partial<Overlay> = {}): Overlay {
  return {
    overlay_id: overrides.overlay_id || "o",
    decision_owner_id: "owner",
    strategy_id: "strategy",
    setup_id: "setup-1",
    symbol_id: "deriv:R_75",
    provider_symbol: "R_75",
    market_type: "derived",
    timeframe: "M15",
    category: "context",
    type: "structural_reference",
    label: "STRUCTURAL REFERENCE",
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
    priority: 20,
    display_group: "context",
    metadata: {},
    ...overrides,
  };
}

const currentPrice = overlay({ overlay_id: "current", type: "current_price", priority: 110 });
const entry = overlay({ overlay_id: "entry", category: "actionable", actionable: true, type: "entry", priority: 100 });
const pullbackZone = overlay({ overlay_id: "zone", category: "developing", type: "m15_pullback_area", low: 1, high: 2, priority: 90 });
const confirmation = overlay({ overlay_id: "confirm", category: "developing", type: "confirmation", priority: 50 });
const structureHigh = overlay({ overlay_id: "structure-high", category: "context", type: "h1_context", priority: 80 });
const structureLow = overlay({ overlay_id: "structure-low", category: "context", type: "structural_range", priority: 75 });
const displacement = overlay({ overlay_id: "displacement", category: "context", type: "m5_displacement", priority: 50 });
const internalSwing = overlay({ overlay_id: "swing", category: "context", type: "swing_high", priority: 40 });
const oldFvg = overlay({ overlay_id: "old-fvg", category: "context", type: "fvg", priority: 30, historical: true });
const mitigatedFvg = overlay({ overlay_id: "mitigated-fvg", category: "context", type: "fvg", priority: 35, metadata: { state: "fully_mitigated" } });

const all = [currentPrice, entry, pullbackZone, confirmation, structureHigh, structureLow, displacement, internalSwing];
const allWithFvgs = [...all, oldFvg, mitigatedFvg];

describe("applyDensity", () => {
  it("CLEAN keeps current price, actionable, developing, and only the single strongest structure reference", () => {
    const result = applyDensity(all, "clean");
    const ids = result.map((r) => r.overlay_id);
    expect(ids).toContain("current");
    expect(ids).toContain("entry");
    expect(ids).toContain("zone");
    expect(ids).toContain("confirm");
    expect(ids).toContain("structure-high"); // highest priority tier-3 row
    expect(ids).not.toContain("structure-low");
    expect(ids).not.toContain("displacement");
    expect(ids).not.toContain("swing");
  });

  it("STANDARD adds every market-structure row on top of CLEAN", () => {
    const result = applyDensity(all, "standard");
    const ids = result.map((r) => r.overlay_id);
    expect(ids).toContain("structure-high");
    expect(ids).toContain("structure-low");
    expect(ids).not.toContain("displacement");
    expect(ids).not.toContain("swing");
  });

  it("RESEARCH returns every overlay, including diagnostic tier", () => {
    const result = applyDensity(all, "research");
    expect(result).toHaveLength(all.length);
  });

  it("keeps old/mitigated FVGs hidden in CLEAN mode (Phase 3 §1/§10)", () => {
    const result = applyDensity(allWithFvgs, "clean");
    const ids = result.map((r) => r.overlay_id);
    expect(ids).not.toContain("old-fvg");
    expect(ids).not.toContain("mitigated-fvg");
  });

  it("still surfaces old/mitigated FVGs in RESEARCH mode -- density hides evidence by default, it never deletes it", () => {
    const result = applyDensity(allWithFvgs, "research");
    const ids = result.map((r) => r.overlay_id);
    expect(ids).toContain("old-fvg");
    expect(ids).toContain("mitigated-fvg");
  });

  it("never mutates the input overlay array or its objects (Phase 3 §24: density mode cannot change backend decision data)", () => {
    const snapshot = JSON.parse(JSON.stringify(all));
    applyDensity(all, "clean");
    applyDensity(all, "standard");
    applyDensity(all, "research");
    expect(JSON.parse(JSON.stringify(all))).toEqual(snapshot);
  });

  it("hiddenEvidenceCount reports how many rows CLEAN/STANDARD are hiding", () => {
    expect(hiddenEvidenceCount(all, "clean")).toBe(all.length - applyDensity(all, "clean").length);
    expect(hiddenEvidenceCount(all, "research")).toBe(0);
  });
});
