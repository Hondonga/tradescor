import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartSetupSummary } from "./chart-setup-summary";
import type { NormalizedDecision } from "@/types";

function decision(overrides: Partial<NormalizedDecision> = {}): NormalizedDecision {
  return {
    decision_id: "d",
    overlay_mode: "LIVE",
    precision: { symbol_id: "x", price_decimals: 2, pip_size: null, tick_size: 0.01, quantity_decimals: null },
    meta: {
      symbol: "R_75",
      display_symbol: "Volatility 75 Index",
      timeframe: "M5",
      analysis_time: "t",
      live: true,
      market_schedule: "24_7",
      analysis_clock: "UTC",
    },
    ownership: { selected_model_id: "vsp", decision_owner_id: "vsp", overlay_owner_id: "vsp" },
    readiness: { state: "ready" },
    market: { current_price: 100 },
    decision: {
      status: "PLAN VALIDATION",
      direction: "sell",
      stage: "PLAN_VALIDATION",
      headline: "",
      summary: "",
      next_action: "Wait for a fresh unswept structural objective below the proposed sell entry.",
      trade_ready: false,
    },
    setup: {
      setup_type: "structure_pullback",
      stage: "PLAN_VALIDATION",
      status: "PLAN VALIDATION",
      context_summary: "",
      next_required_condition: "Wait for a valid target.",
      trade_ready: false,
      targets: [],
      quality_score: null,
      quality_grade: null,
    },
    diagnostics: {},
    overlays: [],
    active_setup: {
      setup_id: "vsp-1",
      lifecycle: "PLAN_VALIDATION",
      direction: "sell",
      setup_type: "structure_pullback",
    },
    ...overrides,
  };
}

describe("ChartSetupSummary", () => {
  it("shows direction, setup type, stage, and waiting-for text", () => {
    render(<ChartSetupSummary decision={decision()} visible />);
    expect(screen.getByText("SELL SETUP")).toBeInTheDocument();
    expect(screen.getByText("Structure Pullback")).toBeInTheDocument();
    expect(screen.getByText("Plan Validation")).toBeInTheDocument();
  });

  it("does not render when there is no active setup", () => {
    const { container } = render(<ChartSetupSummary decision={decision({ active_setup: null })} visible />);
    expect(container).toBeEmptyDOMElement();
  });

  it("does not render when the parent marks it not visible (hidden / too narrow)", () => {
    const { container } = render(<ChartSetupSummary decision={decision()} visible={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
