import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartZoneLayer } from "./chart-zone-layer";
import type { Overlay } from "@/types";
import type { ZoneRect } from "@/lib/overlay-layout";

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
    label: "DEVELOPING · DEVELOPING · M15 Pullback Area",
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

describe("ChartZoneLayer", () => {
  it("strips a duplicated DEVELOPING prefix from the on-chart label", () => {
    const rect: ZoneRect = { overlayId: "zone", top: 100, height: 150, left: 40, width: 300 };
    render(
      <ChartZoneLayer
        zones={[{ rect, overlay: overlay() }]}
        chartHeight={600}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("M15 PULLBACK AREA")).toBeInTheDocument();
    expect(screen.queryByText(/DEVELOPING/)).not.toBeInTheDocument();
  });

  it("keeps zone fill opacity within the spec limit (8-14%)", () => {
    const rect: ZoneRect = { overlayId: "zone", top: 100, height: 150, left: 40, width: 300 };
    const { container } = render(
      <ChartZoneLayer
        zones={[{ rect, overlay: overlay() }]}
        chartHeight={600}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    const fill = container.querySelector(".border") as HTMLElement;
    const match = fill.style.background.match(/rgba\([\d, ]+, ([\d.]+)\)/);
    const opacity = Number(match?.[1]);
    expect(opacity).toBeGreaterThanOrEqual(0.08);
    expect(opacity).toBeLessThanOrEqual(0.14);
  });

  it("renders an oversized zone as boundary lines instead of a filled rectangle", () => {
    const rect: ZoneRect = { overlayId: "zone", top: 0, height: 500, left: 40, width: 300 }; // 500/600 > 45%
    const { container } = render(
      <ChartZoneLayer
        zones={[{ rect, overlay: overlay() }]}
        chartHeight={600}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(container.querySelector(".border")).toBeNull();
    expect(container.querySelectorAll(".h-px")).toHaveLength(2);
  });
});
