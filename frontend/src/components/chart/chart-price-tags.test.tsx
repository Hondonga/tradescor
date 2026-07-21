import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartPriceTags } from "./chart-price-tags";
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
    timeframe: "M5",
    category: "actionable",
    type: "entry",
    label: "Entry",
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
    actionable: true,
    priority: 100,
    display_group: "trade_plan",
    metadata: { plan_role: "entry" },
    ...overrides,
  };
}

describe("ChartPriceTags", () => {
  it("does not overlap tags whose natural positions collide", () => {
    const entry = overlay({ overlay_id: "entry", type: "entry", metadata: { plan_role: "entry" } });
    const stop = overlay({ overlay_id: "stop", type: "stop", metadata: { plan_role: "stop" }, priority: 100 });
    const { container } = render(
      <ChartPriceTags
        overlays={[entry, stop]}
        chartHeight={400}
        priceToY={() => 100} // identical y for both -> forced collision
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    const tags = container.querySelectorAll("button");
    expect(tags).toHaveLength(2);
    const tops = [...tags].map((el) => Number((el.parentElement as HTMLElement).style.top.replace("px", "")));
    expect(Math.abs(tops[0] - tops[1])).toBeGreaterThan(0);
  });

  it("collapses low-priority tags before high-priority ones when space is tight", () => {
    const entry = overlay({ overlay_id: "entry", priority: 100, type: "entry", metadata: { plan_role: "entry" } });
    const structural = overlay({
      overlay_id: "structural",
      category: "context",
      actionable: false,
      priority: 20,
      type: "structural_reference",
      label: "Structural Reference",
      metadata: {},
    });
    render(
      <ChartPriceTags
        overlays={[entry, structural]}
        chartHeight={20} // tiny viewport forces a hide
        priceToY={() => 10}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("ENTRY")).toBeInTheDocument();
    expect(screen.queryByText(/STRUCTURAL/)).not.toBeInTheDocument();
  });

  it("never shows more than 7 permanent tags, even with abundant vertical room", () => {
    const overlays = Array.from({ length: 12 }, (_, i) =>
      overlay({
        overlay_id: `o${i}`,
        category: "context",
        actionable: false,
        type: "structural_reference",
        label: `Structural Reference ${i}`,
        priority: 50 - i, // strictly decreasing priority
        metadata: {},
        price: 100 + i,
      }),
    );
    const { container } = render(
      <ChartPriceTags
        overlays={overlays}
        chartHeight={5000} // plenty of room for all 12
        priceToY={(price) => (price - 100) * 100} // spread far apart, no collisions
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(container.querySelectorAll("button")).toHaveLength(7);
  });

  it("shows the correct backend price on each tag", () => {
    const entry = overlay({ overlay_id: "entry", price: 51500, metadata: { plan_role: "entry" } });
    render(
      <ChartPriceTags
        overlays={[entry]}
        chartHeight={400}
        priceToY={() => 100}
        precision={{ symbol_id: "x", price_decimals: 2, pip_size: null, tick_size: 0.01, quantity_decimals: null }}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("51500.00")).toBeInTheDocument();
  });
});
