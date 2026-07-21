import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { OverlayTooltip } from "./overlay-tooltip";
import type { Overlay } from "@/types";

function overlay(overrides: Partial<Overlay> = {}): Overlay {
  return {
    overlay_id: "internal-db-id-123",
    decision_owner_id: "owner",
    strategy_id: "strategy",
    setup_id: "setup-1",
    symbol_id: "deriv:R_75",
    provider_symbol: "R_75",
    market_type: "derived",
    timeframe: "M15",
    category: "developing",
    type: "m15_pullback_area",
    label: "DEVELOPING · M15 Pullback Area",
    source: "m15_structural_pullback",
    price: null,
    low: 51350,
    high: 51650,
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
    metadata: { visibility_reason: "Active setup location" },
    ...overrides,
  };
}

describe("OverlayTooltip", () => {
  it("shows a clean semantic name, price/zone range, timeframe, status, source, and the reason it's shown", () => {
    render(<OverlayTooltip overlay={overlay()} x={0} y={0} />);
    expect(screen.getByText("M15 Pullback Area")).toBeInTheDocument();
    expect(screen.getByText("51350 – 51650")).toBeInTheDocument();
    expect(screen.getByText("M15")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("m15_structural_pullback")).toBeInTheDocument();
    expect(screen.getByText("Active setup location")).toBeInTheDocument();
  });

  it("shows an exact price for a line overlay instead of a range", () => {
    render(<OverlayTooltip overlay={overlay({ low: null, high: null, price: 51500 })} x={0} y={0} />);
    expect(screen.getByText("51500")).toBeInTheDocument();
  });

  it("never shows the internal overlay ID unless Diagnostics is enabled", () => {
    const { rerender } = render(<OverlayTooltip overlay={overlay()} x={0} y={0} />);
    expect(screen.queryByText("internal-db-id-123")).not.toBeInTheDocument();
    rerender(<OverlayTooltip overlay={overlay()} x={0} y={0} diagnosticsVisible />);
    expect(screen.getByText("internal-db-id-123")).toBeInTheDocument();
  });

  it("marks a historical overlay's status as Historical, not Active", () => {
    render(<OverlayTooltip overlay={overlay({ historical: true, active: false })} x={0} y={0} />);
    expect(screen.getByText("Historical")).toBeInTheDocument();
  });
});
