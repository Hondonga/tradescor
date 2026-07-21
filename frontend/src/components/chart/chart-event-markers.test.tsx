import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChartEventMarkers } from "./chart-event-markers";
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
    category: "diagnostic" as any,
    type: "m5_displacement",
    label: "Completed M5 Displacement",
    source: "backend",
    price: 51420,
    low: null,
    high: null,
    start_time: null,
    end_time: null,
    created_at: "2026-07-18T02:00:00Z",
    confirmed_at: "2026-07-18T02:05:00Z",
    expires_at: null,
    invalidated_at: null,
    active: true,
    historical: false,
    actionable: false,
    priority: 50,
    display_group: "advanced_smc",
    metadata: {},
    ...overrides,
  };
}

describe("ChartEventMarkers", () => {
  it("renders a compact marker (not a full-width line) for a completed event", () => {
    render(
      <ChartEventMarkers
        overlays={[overlay()]}
        priceToY={() => 100}
        timeToX={() => 200}
        chartWidth={800}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("DISP")).toBeInTheDocument();
  });

  it("skips an overlay whose price cannot be mapped to a chart coordinate", () => {
    render(
      <ChartEventMarkers
        overlays={[overlay()]}
        priceToY={() => null}
        timeToX={() => 200}
        chartWidth={800}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(screen.queryByText("DISP")).not.toBeInTheDocument();
  });

  it("calls onSelect with the overlay ID when clicked", () => {
    const onSelect = vi.fn();
    render(
      <ChartEventMarkers
        overlays={[overlay({ overlay_id: "evt-1" })]}
        priceToY={() => 100}
        timeToX={() => 200}
        chartWidth={800}
        selectedOverlayId=""
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("DISP"));
    expect(onSelect).toHaveBeenCalledWith("evt-1");
  });

  it("stacks above the chart's internal interaction canvas (z-index 2)", () => {
    render(
      <ChartEventMarkers
        overlays={[overlay()]}
        priceToY={() => 100}
        timeToX={() => 200}
        chartWidth={800}
        selectedOverlayId=""
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("DISP").className).toMatch(/\bz-30\b/);
  });
});
