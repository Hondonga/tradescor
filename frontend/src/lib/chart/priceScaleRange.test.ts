import { describe, expect, it } from "vitest";
import { actionablePriceRange } from "./priceScaleRange";
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
    category: "actionable",
    type: "entry",
    label: "Entry",
    source: "backend",
    price: 51500,
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
    actionable: true,
    priority: 100,
    display_group: "trade_plan",
    metadata: {},
    ...overrides,
  };
}

describe("actionablePriceRange", () => {
  it("returns null when nothing actionable is present", () => {
    expect(actionablePriceRange([overlay({ actionable: false })])).toBeNull();
  });

  it("returns null for an empty overlay list", () => {
    expect(actionablePriceRange([])).toBeNull();
  });

  it("spans the min/max of every actionable price, including targets far beyond recent candle action", () => {
    const overlays = [
      overlay({ overlay_id: "entry", type: "entry", price: 51500 }),
      overlay({ overlay_id: "stop", type: "stop", price: 51350 }),
      overlay({ overlay_id: "tp1", type: "tp1", price: 51850 }),
      overlay({ overlay_id: "tp2", type: "tp2", price: 52100 }),
    ];
    expect(actionablePriceRange(overlays)).toEqual({ minValue: 51350, maxValue: 52100 });
  });

  it("ignores non-actionable overlays even when they carry a price far outside the actionable range", () => {
    const overlays = [
      overlay({ overlay_id: "entry", price: 51500 }),
      overlay({ overlay_id: "stop", type: "stop", price: 51350 }),
      overlay({ overlay_id: "diagnostic", actionable: false, price: 60000 }),
    ];
    expect(actionablePriceRange(overlays)).toEqual({ minValue: 51350, maxValue: 51500 });
  });

  it("ignores actionable overlays with a null price (zones, not price lines)", () => {
    const overlays = [
      overlay({ overlay_id: "zone", price: null, low: 100, high: 200 }),
    ];
    expect(actionablePriceRange(overlays)).toBeNull();
  });
});
