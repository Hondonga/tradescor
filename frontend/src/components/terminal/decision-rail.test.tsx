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

  it("falls through to plan_blocker when first_blocking_gate is absent, so Jump-family plan-level detail is never lost (Phase 3 §25 regression fix)", () => {
    renderRail(
      baseDecision({
        decision: { status: "SELL SETUP DEVELOPING", direction: "sell", stage: "WAITING_FOR_DISPLACEMENT", headline: "", summary: "", next_action: "", trade_ready: false },
        active_setup: {
          setup_id: "vsp-1",
          lifecycle: "WAITING_FOR_DISPLACEMENT",
          setup_type: "structure_pullback",
          direction: "sell",
          plan_blocker: "No valid opposing structural target currently provides acceptable geometry.",
          targets: [],
        },
      }),
    );
    const whatIsMissing = screen.getByText("What is missing").closest("section");
    expect(whatIsMissing?.textContent).toContain("No valid opposing structural target currently provides acceptable geometry.");
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

describe("DecisionRail status wording polish", () => {
  beforeEach(() => {
    useTerminalStore.persist.clearStorage();
  });

  it("shows only TRADE READY / WATCHLIST / AVOID as the primary status, never WAIT or NO TRADE", () => {
    renderRail(baseDecision());
    expect(screen.getByText("WATCHLIST")).toBeInTheDocument();
    expect(screen.queryByText("WAIT")).not.toBeInTheDocument();
    expect(screen.queryByText("NO TRADE")).not.toBeInTheDocument();
    expect(screen.queryByText(/^SELL SETUP DEVELOPING$/)).not.toBeInTheDocument();
  });

  it("shows AVOID for a trade-ready-false decision with a too-late entry timing classification", () => {
    renderRail(
      baseDecision({
        entry_timing: {
          status: "too_late",
          message: "Too late to enter now. Price is too far from entry and reward is reduced.",
          next_action: "Do not chase. Wait for a new setup or a clean pullback.",
          can_enter_now: false,
        },
      } as Partial<NormalizedDecision>),
    );
    expect(screen.getByText("AVOID")).toBeInTheDocument();
    expect(screen.queryByText("WATCHLIST")).not.toBeInTheDocument();
  });

  it("shows TRADE READY for a trade-ready decision", () => {
    renderRail(
      baseDecision({
        decision: { status: "READY TO SELL", direction: "sell", stage: "TRADE_READY", headline: "READY TO SELL", summary: "", next_action: "x", trade_ready: true },
        trade_plan: { available: true, status: "READY TO SELL", entry: 51500, stop: 51650, targets: [{ name: "TP1", price: 51150, risk_reward: 2.3 }] },
      }),
    );
    expect(screen.getByText("TRADE READY")).toBeInTheDocument();
  });

  it('shows "Looking for: SELL setup" for a sell-direction decision', () => {
    renderRail(baseDecision());
    expect(screen.getByText("Looking for: SELL setup")).toBeInTheDocument();
  });

  it('shows "Looking for: Neutral" when there is no direction yet', () => {
    renderRail(baseDecision({ decision: { status: "MARKET CONTEXT", direction: null, stage: "NO_DIRECTIONAL_CONTEXT", headline: "", summary: "", next_action: "x", trade_ready: false }, active_setup: null }));
    expect(screen.getByText("Looking for: Neutral")).toBeInTheDocument();
  });

  it("Phase 6: shows RESEARCH PLAN, not TRADE READY, for a rejected strategy's complete engine TRADE_READY plan, and discloses STRATEGY STATUS/VALIDATION/REASON/REACHABILITY/TRADING ELIGIBILITY", () => {
    renderRail(
      baseDecision({
        decision: { status: "READY TO SELL", direction: "sell", stage: "TRADE_READY", headline: "READY TO SELL", summary: "", next_action: "x", trade_ready: true },
        trade_plan: { available: true, status: "READY TO SELL", entry: 51500, stop: 51650, targets: [{ name: "TP1", price: 51150, risk_reward: 2.3 }] },
        strategy_evidence: {
          reachability_status: "REACHABLE_BOTH_DIRECTIONS",
          validation_status: "REJECTED_NO_EDGE_AFTER_COSTS",
          validation_verdict: "REJECTED_NO_EDGE_AFTER_COSTS",
          historical_edge_proven: false,
          profitability_claim_allowed: false,
          auto_eligible: false,
          paper_signal_allowed: false,
          paper_shadow_eligible: false,
          live_execution_allowed: false,
          research_only: true,
          experiment_id: "phase5-r75-vsp-walkforward-v1",
          evidence_summary: "",
        },
        product_actionability: {
          actionable: false,
          status: "RESEARCH_PLAN",
          blocker: "REJECTED_NO_EDGE_AFTER_COSTS",
          auto_allowed: false,
          paper_allowed: false,
          live_allowed: false,
        },
      } as Partial<NormalizedDecision>),
    );
    expect(screen.getByText("RESEARCH PLAN")).toBeInTheDocument();
    expect(screen.queryByText("TRADE READY")).not.toBeInTheDocument();
    // Appears twice: the header's "Research only" badge and the disclosure
    // panel's "Strategy status" value both legitimately say this.
    expect(screen.getAllByText("Research only").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Rejected after formal walk-forward validation")).toBeInTheDocument();
    expect(screen.getByText("No stable post-cost edge was confirmed.")).toBeInTheDocument();
    expect(screen.getByText("BUY and SELL setup construction verified.")).toBeInTheDocument();
    expect(screen.getByText("Auto: Disabled")).toBeInTheDocument();
    expect(screen.getByText("Paper signals: Disabled")).toBeInTheDocument();
    expect(screen.getByText("Live execution: Disabled")).toBeInTheDocument();
    expect(screen.getByText("ML filtering: Disabled")).toBeInTheDocument();
    // Part 13: the engine's own output is still fully preserved and visible.
    expect(screen.getByText("Research plan · not actionable")).toBeInTheDocument();
    expect(screen.getByText(/51,?500|51500/)).toBeInTheDocument();
  });

  it("uses the too-late entry-timing message and next action in WHAT IS MISSING / NEXT ACTION, and the chart card does not repeat it", () => {
    const decision = baseDecision({
      entry_timing: {
        status: "too_late",
        message: "Too late to enter now. Price is too far from entry and reward is reduced.",
        next_action: "Do not chase. Wait for a new setup or a clean pullback.",
        can_enter_now: false,
      },
    } as Partial<NormalizedDecision>);
    renderRail(decision);
    const whatIsMissing = screen.getByText("What is missing").closest("section");
    expect(whatIsMissing?.textContent).toContain("Too late to enter now. Price is too far from entry and reward is reduced.");
    const nextAction = screen.getByText("Next action").closest("section");
    expect(nextAction?.textContent).toContain("Do not chase. Wait for a new setup or a clean pullback.");

    const { container: chartCard } = render(<ChartSetupSummary decision={decision} visible />);
    // The rail already explains the too-late warning -- the chart card must
    // not repeat or contradict it with its own "Waiting for" text.
    expect(chartCard.textContent).not.toContain("Waiting for");
    expect(chartCard.textContent).not.toContain("Too late to enter now");
  });
});

describe("DecisionRail Forex-specific content (Phase 4 §18)", () => {
  beforeEach(() => {
    useTerminalStore.persist.clearStorage();
  });

  function forexDecision(overrides: Partial<NormalizedDecision> = {}): NormalizedDecision {
    return baseDecision({
      meta: {
        symbol: "GBP/USD",
        display_symbol: "GBP/USD",
        timeframe: "M5",
        analysis_time: "2026-07-20T12:00:00Z",
        live: true,
        market_schedule: "24_5",
        analysis_clock: "UTC",
        market_source: "twelve_data",
        market_type: "forex",
      },
      market: { external_structure: "bullish", internal_structure: "pullback", current_price: 1.271, session: "London Kill Zone" },
      forex: {
        htf_bias: "buy",
        market_structure: "aligned",
        session: "London Kill Zone",
        liquidity_event: { direction: "buy", liquidity_price: 1.262, sweep_price: 1.261, confirmed_at: "2026-07-20T11:30:00Z" },
        displacement: { direction: "buy", confirmed: true, structure_effect: "local_structure_broken" },
        structure_confirmation: { close_confirmed: true, level: 1.274, break_time: "2026-07-20T11:45:00Z" },
        dealing_range: { premium_discount_state: "discount", current_position_pct: 28.4, range_high: 1.29, range_low: 1.26, equilibrium: 1.275, source_timeframe: "H4" },
        scenario_state: "WAITING_FOR_M5_CONFIRMATION",
      },
      ...overrides,
    });
  }

  it("shows session/kill-zone and premium/discount in MARKET STATE for a Forex decision", () => {
    renderRail(forexDecision());
    const marketState = screen.getByText("Market state").closest("section");
    expect(marketState?.textContent).toContain("London Kill Zone");
    expect(marketState?.textContent).toContain("Discount");
    expect(marketState?.textContent).toContain("28%");
  });

  it("shows liquidity sweep, displacement and structure confirmation in ACTIVE SETUP for a Forex decision", () => {
    renderRail(forexDecision());
    const activeSetup = screen.getByText("Active setup").closest("section");
    expect(activeSetup?.textContent).toContain("Buy @");
    expect(activeSetup?.textContent).toContain("Displacement");
    expect(activeSetup?.textContent).toContain("Structure confirmation");
    expect(activeSetup?.textContent).toContain("Confirmed (MSS)");
  });

  it("does not render Forex-only rows for a non-Forex (Derived) decision", () => {
    renderRail(baseDecision());
    const marketState = screen.getByText("Market state").closest("section");
    expect(marketState?.textContent).not.toContain("Session / kill zone");
    expect(marketState?.textContent).not.toContain("Premium / discount");
    const activeSetup = screen.getByText("Active setup").closest("section");
    expect(activeSetup?.textContent).not.toContain("Liquidity sweep");
    expect(activeSetup?.textContent).not.toContain("Structure confirmation");
  });
});
