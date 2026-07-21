import { describe, expect, it, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DecisionRail } from "./decision-rail";
import { ChartSetupSummary } from "@/components/chart/chart-setup-summary";
import { useTerminalStore } from "@/store/terminal-store";
import type { NormalizedDecision, SymbolInfo } from "@/types";

const symbol: SymbolInfo = {
  symbol_id: "deriv:R_75",
  provider_symbol: "R_75",
  display_name: "Volatility 75 Index",
  family: "VOLATILITY",
  market_source: "deriv",
  market_type: "derived",
  market_schedule: "24_7",
  analysis_engine: "derived_smc",
  supported: true,
  available_models: [{ id: "auto", label: "SMC Auto" }],
};

function baseDecision(overrides: Partial<NormalizedDecision> = {}): NormalizedDecision {
  return {
    decision_id: "d1",
    overlay_mode: "LIVE",
    precision: { symbol_id: symbol.symbol_id, price_decimals: 2, pip_size: null, tick_size: 0.01, quantity_decimals: null },
    meta: {
      symbol: symbol.provider_symbol,
      display_symbol: symbol.display_name,
      timeframe: "M5",
      analysis_time: "2026-07-20T12:00:00Z",
      emitted_time: "2026-07-20T12:00:00Z",
      live: true,
      market_schedule: "24_7",
      analysis_clock: "UTC",
      market_source: symbol.market_source,
      market_type: symbol.market_type,
    },
    ownership: {
      selected_model_id: "volatility_structure_pullback",
      selected_strategy_id: "volatility_structure_pullback",
      decision_owner_id: "volatility_structure_pullback",
      overlay_owner_id: "volatility_structure_pullback",
    },
    readiness: { state: "ready" },
    market: { external_structure: "bearish", internal_structure: "pullback", current_price: 51500 },
    trade_plan: { available: false, status: "UNAVAILABLE", entry: null, stop: null, targets: [] },
    decision: {
      status: "SELL SETUP DEVELOPING",
      direction: "sell",
      stage: "WAITING_FOR_DISPLACEMENT",
      headline: "SELL SETUP DEVELOPING",
      summary: "",
      next_action: "Wait for a completed bearish displacement.",
      trade_ready: false,
      first_blocking_gate: "Waiting for a completed M5 displacement and structure break.",
    },
    setup: {
      setup_id: "vsp-1",
      setup_type: "structure_pullback",
      direction: "sell",
      stage: "WAITING_FOR_DISPLACEMENT",
      status: "SELL SETUP DEVELOPING",
      context_summary: "H1 bearish, M15 pullback",
      next_required_condition: "Wait for the M5 structure break.",
      trade_ready: false,
      targets: [],
      quality_score: 70,
      quality_grade: "B",
      entry_area: { low: 51350, high: 51650, type: "m5_displacement_retrace" },
      target_source: "m5_structure",
      target_timeframe: "M5",
      completed_confirmation: null,
    },
    active_setup: {
      setup_id: "vsp-1",
      lifecycle: "WAITING_FOR_DISPLACEMENT",
      setup_type: "structure_pullback",
      direction: "sell",
      first_blocking_gate: "Waiting for a completed M5 displacement and structure break.",
      next_required_condition: "Wait for the M5 structure break.",
      invalidation: { price: 51700, condition: "Price closes above the protected M5 high." },
      targets: [],
    },
    previous_setup: null,
    diagnostics: { invariants: { valid: true } },
    overlays: [],
    ...overrides,
  } as NormalizedDecision;
}

function renderRail(decision: NormalizedDecision | undefined, storeOverrides: Record<string, unknown> = {}) {
  useTerminalStore.setState({
    symbol,
    decision,
    dataReadiness: decision ? "ready" : "idle",
    workspaceMode: "live",
    diagnosticsVisible: false,
    ...storeOverrides,
  } as any);
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <DecisionRail />
    </QueryClientProvider>,
  );
}

describe("DecisionRail section order (Phase 3 §11)", () => {
  beforeEach(() => {
    useTerminalStore.persist.clearStorage();
  });

  it("renders MARKET STATE, ACTIVE SETUP, WHAT IS MISSING, NEXT ACTION and DETAILS in the required order for a developing setup", () => {
    renderRail(baseDecision());
    const labels = screen.getAllByText(/^(Market state|Active setup|What is missing|Next action|Details)$/i, { selector: "p.label, summary" }).map((el) => el.textContent);
    expect(labels).toEqual(["Market state", "Active setup", "What is missing", "Next action", "Details"]);
  });

  it("shows the pre-translated blocker text in WHAT IS MISSING, never a raw underscored code in that section specifically", () => {
    renderRail(baseDecision());
    const whatIsMissing = screen.getByText("What is missing").closest("section");
    expect(whatIsMissing?.textContent).toContain("Waiting for a completed M5 displacement and structure break.");
    expect(whatIsMissing?.textContent).not.toMatch(/[A-Z_]{4,}/); // no raw SCREAMING_SNAKE_CASE code
  });

  it("omits WHAT IS MISSING and TRADE PLAN when there is no active setup", () => {
    renderRail(
      baseDecision({
        active_setup: null,
        decision: {
          status: "MARKET CONTEXT",
          direction: null,
          stage: "NO_DIRECTIONAL_CONTEXT",
          headline: "MARKET CONTEXT",
          summary: "",
          next_action: "Wait for a completed H1 structure break.",
          trade_ready: false,
        },
      }),
    );
    expect(screen.queryByText("What is missing")).not.toBeInTheDocument();
    expect(screen.queryByText("Trade plan · paper only")).not.toBeInTheDocument();
    expect(screen.queryByText("Details")).not.toBeInTheDocument();
  });

  it("omits WHAT IS MISSING once TRADE_READY, and shows the trade plan instead", () => {
    renderRail(
      baseDecision({
        trade_plan: { available: true, status: "READY TO SELL", entry: 51500, stop: 51650, targets: [{ name: "TP1", price: 51150, risk_reward: 2.3 }] },
        decision: {
          status: "READY TO SELL",
          direction: "sell",
          stage: "READY_TO_SELL",
          headline: "READY TO SELL",
          summary: "",
          next_action: "Paper-analysis plan is complete.",
          trade_ready: true,
        },
        setup: {
          setup_id: "vsp-1",
          setup_type: "structure_pullback",
          direction: "sell",
          stage: "READY_TO_SELL",
          status: "READY TO SELL",
          context_summary: "",
          next_required_condition: "None",
          trade_ready: true,
          entry: 51500,
          stop: 51650,
          targets: [{ name: "TP1", price: 51150, risk_reward: 2.3 }],
          rr: 2.3,
          quality_score: 90,
          quality_grade: "A",
          target_source: "m5_structure",
          target_timeframe: "M5",
        },
        active_setup: {
          setup_id: "vsp-1",
          lifecycle: "TRADE_READY",
          setup_type: "structure_pullback",
          direction: "sell",
          entry: 51500,
          stop: 51650,
          targets: [{ name: "TP1", price: 51150, risk_reward: 2.3 }],
          rr: 2.3,
          target_source: "m5_structure",
          target_timeframe: "M5",
          m5_confirmation_status: "Passed",
        },
      }),
    );
    expect(screen.queryByText("What is missing")).not.toBeInTheDocument();
    expect(screen.getByText("Trade plan · paper only")).toBeInTheDocument();
  });

  it("shows target source and setup ownership in DETAILS", () => {
    renderRail(baseDecision());
    const details = screen.getByText("Details").closest("details");
    expect(details).not.toBeNull();
    expect(details?.textContent).toContain("M5 Structure");
    expect(details?.textContent).toContain("volatility_structure_pullback");
  });

  it("keeps DIAGNOSTICS collapsed by default", () => {
    renderRail(baseDecision());
    const diag = screen.getByText("Diagnostics").closest("details");
    expect(diag).not.toHaveAttribute("open");
  });

  it("agrees with the chart's Setup Focus card on direction and lifecycle for the same decision (Phase 3 §24)", () => {
    const decision = baseDecision();
    renderRail(decision);
    expect(screen.getAllByText("Sell").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Waiting For Displacement").length).toBe(1); // from the rail, before the chart card mounts
    const { container: chartCard } = render(<ChartSetupSummary decision={decision} visible />);
    expect(chartCard.textContent).toContain("SELL SETUP");
    expect(chartCard.textContent).toContain("Waiting For Displacement");
    // Both components now describe the same setup on screen simultaneously,
    // in agreement -- neither invented a different direction or lifecycle.
    expect(screen.getAllByText("Waiting For Displacement").length).toBe(2);
  });

  it("opens DIAGNOSTICS when the toolbar's diagnostics toggle is on", () => {
    renderRail(baseDecision(), { diagnosticsVisible: true });
    const diag = screen.getByText("Diagnostics").closest("details");
    expect(diag).toHaveAttribute("open");
  });
});
