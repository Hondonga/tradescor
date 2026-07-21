import { describe, expect, it } from "vitest";
import { computeZoneRect, isOversizedZone } from "./overlay-layout";
import type { Overlay } from "@/types";

function overlay(overrides: Partial<Overlay> = {}): Overlay {
  return {
    overlay_id: "zone",
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
    low: 50303,
    high: 53000,
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

describe("computeZoneRect", () => {
  it("returns null for a price-only overlay (not a zone)", () => {
    expect(computeZoneRect(overlay({ low: null, high: null, price: 100 }), {
      chartWidth: 800,
      priceToY: () => 0,
      timeToX: () => 0,
    })).toBeNull();
  });

  it("uses the left-margin fallback when start_time is missing", () => {
    const rect = computeZoneRect(overlay(), {
      chartWidth: 1000,
      priceToY: (price) => (price === 50303 ? 300 : 100),
      timeToX: () => null,
    });
    expect(rect).not.toBeNull();
    expect(rect!.left).toBe(80); // 1000 * 0.08 default margin
    expect(rect!.top).toBe(100);
    expect(rect!.height).toBe(200);
  });

  it("uses start_time/end_time coordinates when available", () => {
    const rect = computeZoneRect(overlay({ start_time: "t1", end_time: "t2" }), {
      chartWidth: 1000,
      priceToY: (price) => (price === 50303 ? 300 : 100),
      timeToX: (t) => (t === "t1" ? 400 : 600),
    });
    expect(rect!.left).toBe(400);
    expect(rect!.width).toBe(200);
  });

  it("never lets the zone extend into the right-edge price-scale gutter", () => {
    const rect = computeZoneRect(overlay({ end_time: "t2" }), {
      chartWidth: 500,
      priceToY: () => 100,
      timeToX: () => 490, // past the 64px gutter
    });
    expect(rect!.left + rect!.width).toBeLessThanOrEqual(500 - 64);
  });
});

describe("isOversizedZone", () => {
  it("flags a zone that dominates the visible price range", () => {
    const rect = { overlayId: "z", top: 0, height: 500, left: 0, width: 100 };
    expect(isOversizedZone(rect, 600)).toBe(true);
  });

  it("does not flag a modestly sized zone", () => {
    const rect = { overlayId: "z", top: 0, height: 100, left: 0, width: 100 };
    expect(isOversizedZone(rect, 600)).toBe(false);
  });
});
