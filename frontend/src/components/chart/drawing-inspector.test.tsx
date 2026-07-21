import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DrawingInspector } from "./drawing-inspector";
import type { Overlay } from "@/types";

function overlay(overrides: Partial<Overlay> = {}): Overlay {
  return {
    overlay_id: "o",
    decision_owner_id: "owner",
    strategy_id: "strategy",
    setup_id: "vsp-setup-1",
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
    created_at: "2026-07-18T02:00:00Z",
    confirmed_at: null,
    expires_at: null,
    invalidated_at: null,
    active: true,
    historical: false,
    actionable: false,
    priority: 90,
    display_group: "setup",
    metadata: {
      invalidation_condition: "Price closes above the protected M5 high.",
      visibility_reason: "Active setup location",
    },
    ...overrides,
  };
}

describe("DrawingInspector", () => {
  it("shows a clean title without the lifecycle prefix", () => {
    render(<DrawingInspector overlay={overlay()} close={() => {}} />);
    expect(screen.getByText("M15 Pullback Area")).toBeInTheDocument();
  });

  it("shows structured fields as the primary, always-visible content", () => {
    render(<DrawingInspector overlay={overlay()} close={() => {}} />);
    expect(screen.getByText("Price closes above the protected M5 high.")).toBeInTheDocument();
    expect(screen.getByText("Active setup location")).toBeInTheDocument();
  });

  it("keeps raw metadata collapsed behind an explicit disclosure", () => {
    render(<DrawingInspector overlay={overlay()} close={() => {}} />);
    const details = screen.getByText("View raw metadata").closest("details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");
  });
});
