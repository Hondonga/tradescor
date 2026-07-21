import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { OpportunityQueue } from "./opportunity-queue";
import type { MarketRow, NormalizedDecision, SymbolInfo } from "@/types";

function symbolFor(name: string): SymbolInfo {
  return {
    symbol_id: `deriv:${name}`,
    provider_symbol: name,
    display_name: name,
    family: "VOLATILITY",
    market_source: "deriv",
    market_type: "derived",
    market_schedule: "24_7",
    analysis_engine: "derived_smc",
    supported: true,
    available_models: [{ id: "auto", label: "Auto" }],
  };
}

function decisionFor(overrides: Partial<NormalizedDecision> = {}): NormalizedDecision {
  return {
    decision_id: "d",
    overlay_mode: "LIVE",
    precision: { symbol_id: "deriv:R_75", price_decimals: 2, pip_size: null, tick_size: 0.01, quantity_decimals: null },
    meta: { symbol: "R_75", display_symbol: "Volatility 75 Index", timeframe: "M5", analysis_time: "2026-07-20T12:00:00Z", live: true, market_schedule: "24_7", analysis_clock: "UTC", market_source: "deriv", market_type: "derived" },
    ownership: { selected_model_id: "volatility_structure_pullback", selected_strategy_id: "volatility_structure_pullback", decision_owner_id: "owner", overlay_owner_id: "owner" },
    readiness: { state: "ready" },
    market: { current_price: 51500 },
    trade_plan: { available: false, status: "UNAVAILABLE", entry: null, stop: null, targets: [] },
    decision: { status: "SELL SETUP DEVELOPING", direction: "sell", stage: "WAITING_FOR_DISPLACEMENT", headline: "", summary: "", next_action: "", trade_ready: false, first_blocking_gate: "Waiting for a completed M5 displacement." },
    setup: { setup_id: "s1", trade_ready: false, targets: [], quality_score: null, quality_grade: null, next_required_condition: "Wait for structure.", context_summary: "" } as any,
    active_setup: { setup_id: "s1", lifecycle: "WAITING_FOR_DISPLACEMENT" },
    previous_setup: null,
    diagnostics: {},
    overlays: [],
    ...overrides,
  } as NormalizedDecision;
}

function row(name: string, decision?: NormalizedDecision): MarketRow {
  return { symbol: symbolFor(name), decision };
}

describe("OpportunityQueue", () => {
  it("shows a production-supported developing setup with market/timeframe/strategy/direction/lifecycle/missing-requirement", () => {
    render(
      <OpportunityQueue
        rows={[row("R_75", decisionFor())]}
        onSelect={() => {}}
        dataReadiness="ready"
        onAnalyzeNow={() => {}}
        analyzePending={false}
      />,
    );
    expect(screen.getByText("R_75")).toBeInTheDocument();
    expect(screen.getByText("M5")).toBeInTheDocument();
    expect(screen.getByText(/Volatility Structure Pullback/)).toBeInTheDocument();
    expect(screen.getByText(/Sell/)).toBeInTheDocument();
    expect(screen.getByText(/Waiting for a completed M5 displacement\./)).toBeInTheDocument();
  });

  it("never shows a row without a valid active setup", () => {
    render(
      <OpportunityQueue
        rows={[row("R_75", decisionFor({ active_setup: null }))]}
        onSelect={() => {}}
        dataReadiness="ready"
        onAnalyzeNow={() => {}}
        analyzePending={false}
      />,
    );
    expect(screen.queryByText("R_75")).not.toBeInTheDocument();
  });

  it("never shows an unanalyzed row (no decision at all)", () => {
    render(
      <OpportunityQueue
        rows={[row("R_75")]}
        onSelect={() => {}}
        dataReadiness="ready"
        onAnalyzeNow={() => {}}
        analyzePending={false}
      />,
    );
    expect(screen.queryByText("R_75")).not.toBeInTheDocument();
  });

  it("hides research-only candidates by default, and reveals them only via the explicit Show Research toggle", () => {
    render(
      <OpportunityQueue
        rows={[row("JD10", decisionFor({ setup: { setup_id: "s1", trade_ready: false, targets: [], quality_score: null, quality_grade: null, next_required_condition: "", context_summary: "", research_only: true } as any }))]}
        onSelect={() => {}}
        dataReadiness="ready"
        onAnalyzeNow={() => {}}
        analyzePending={false}
      />,
    );
    expect(screen.queryByText("JD10")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/Show Research/));
    expect(screen.getByText("JD10")).toBeInTheDocument();
    expect(screen.getByText("RESEARCH")).toBeInTheDocument();
  });

  it("never shows a research-only row as a plain, unlabeled opportunity once revealed", () => {
    render(
      <OpportunityQueue
        rows={[row("JD10", decisionFor({ setup: { setup_id: "s1", trade_ready: false, targets: [], quality_score: null, quality_grade: null, next_required_condition: "", context_summary: "", research_only: true } as any }))]}
        onSelect={() => {}}
        dataReadiness="ready"
        onAnalyzeNow={() => {}}
        analyzePending={false}
      />,
    );
    fireEvent.click(screen.getByText(/Show Research/));
    expect(screen.getByText("RESEARCH")).toBeInTheDocument();
  });

  it("calls onSelect with the row when a card is clicked", () => {
    const onSelect = vi.fn();
    const r = row("R_75", decisionFor());
    render(<OpportunityQueue rows={[r]} onSelect={onSelect} dataReadiness="ready" onAnalyzeNow={() => {}} analyzePending={false} />);
    fireEvent.click(screen.getByText("R_75"));
    expect(onSelect).toHaveBeenCalledWith(r);
  });

  it("shows the paused message when data readiness is in error, and the default empty message otherwise", () => {
    const { rerender } = render(
      <OpportunityQueue rows={[]} onSelect={() => {}} dataReadiness="error" onAnalyzeNow={() => {}} analyzePending={false} />,
    );
    expect(screen.getByText("OPPORTUNITY QUEUE PAUSED")).toBeInTheDocument();
    rerender(<OpportunityQueue rows={[]} onSelect={() => {}} dataReadiness="ready" onAnalyzeNow={() => {}} analyzePending={false} />);
    expect(screen.getByText("Star symbols in Markets to build the queue.")).toBeInTheDocument();
  });

  it("never shows 'waiting for target' language for a neutral-direction row, even in the defensive edge case where one somehow carries an active setup", () => {
    render(
      <OpportunityQueue
        rows={[row("R_75", decisionFor({ decision: { status: "MARKET CONTEXT", direction: null, stage: "NO_DIRECTIONAL_CONTEXT", headline: "", summary: "", next_action: "", trade_ready: false } }))]}
        onSelect={() => {}}
        dataReadiness="ready"
        onAnalyzeNow={() => {}}
        analyzePending={false}
      />,
    );
    expect(screen.getByText(/Neutral/)).toBeInTheDocument();
    expect(screen.queryByText(/WAITING FOR TARGET/i)).not.toBeInTheDocument();
  });

  it("calls onAnalyzeNow when the Analyze now button is clicked", () => {
    const onAnalyzeNow = vi.fn();
    render(<OpportunityQueue rows={[]} onSelect={() => {}} dataReadiness="ready" onAnalyzeNow={onAnalyzeNow} analyzePending={false} />);
    fireEvent.click(screen.getByText("Analyze now"));
    expect(onAnalyzeNow).toHaveBeenCalled();
  });
});
