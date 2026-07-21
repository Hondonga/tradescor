import { describe, expect, it } from "vitest";
import { applySetupFocus } from "./setupFocus";
import type { NormalizedDecision, Overlay } from "@/types";

function overlay(overrides: Partial<Overlay> & { overlay_id: string }): Overlay {
  return {
    decision_owner_id: "owner",
    strategy_id: "strategy",
    setup_id: "setup-1",
    symbol_id: "deriv:R_75",
    provider_symbol: "R_75",
    market_type: "derived",
    timeframe: "M5",
    category: "context",
    type: "generic",
    label: "Generic",
    source: "backend",
    price: null,
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
    actionable: false,
    priority: 50,
    display_group: "context",
    metadata: {},
    ...overrides,
  };
}

function decision(overrides: Partial<NormalizedDecision> = {}): NormalizedDecision {
  return {
    decision_id: "d",
    overlay_mode: "LIVE",
    precision: { symbol_id: "deriv:R_75", price_decimals: 2, pip_size: null, tick_size: 0.01, quantity_decimals: null },
    meta: { symbol: "R_75", display_symbol: "Volatility 75 Index", timeframe: "M5", analysis_time: "2026-07-20T12:00:00Z", live: true, market_schedule: "24_7", analysis_clock: "UTC", market_source: "deriv", market_type: "derived" },
    ownership: { selected_model_id: "s", decision_owner_id: "owner", overlay_owner_id: "owner" },
    readiness: { state: "ready" },
    market: { current_price: 51500 },
    trade_plan: { available: false, status: "UNAVAILABLE", entry: null, stop: null, targets: [] },
    decision: { status: "MARKET CONTEXT", direction: null, stage: "NO_DIRECTIONAL_CONTEXT", trade_ready: false },
    setup: { setup_id: null, trade_ready: false, targets: [] },
    active_setup: null,
    previous_setup: null,
    diagnostics: {},
    overlays: [],
    ...overrides,
  } as NormalizedDecision;
}

describe("applySetupFocus", () => {
  it("returns overlays unchanged when there is no decision yet", () => {
    const overlays = [overlay({ overlay_id: "a" })];
    expect(applySetupFocus(overlays, undefined)).toBe(overlays);
  });

  describe("no active setup", () => {
    const d = decision({ active_setup: null, decision: { status: "MARKET CONTEXT", direction: null, stage: "NO_DIRECTIONAL_CONTEXT", headline: "Market context", summary: "", next_action: "Wait", trade_ready: false } });

    it("keeps current price and context-category overlays", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "ctx", category: "context", price: 51900 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).toContain("cp");
      expect(result).toContain("ctx");
    });

    it("drops diagnostic-tier overlays not in the context category", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "diag", category: "developing", price: 51600 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).not.toContain("diag");
    });

    it("keeps every context-tier overlay (external high/low, range, liquidity) -- nothing more specific exists to narrow to yet", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "external-high", category: "context", price: 51600 }),
        overlay({ overlay_id: "external-low", category: "context", price: 51000 }),
        overlay({ overlay_id: "liquidity-above", category: "context", price: 52000 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).toEqual(expect.arrayContaining(["cp", "external-high", "external-low", "liquidity-above"]));
    });
  });

  describe("developing (not trade-ready) active setup", () => {
    const d = decision({
      active_setup: { setup_id: "setup-1", lifecycle: "WAITING_FOR_DISPLACEMENT" },
      decision: { status: "WAITING", direction: "sell", stage: "WAITING_FOR_DISPLACEMENT", headline: "Waiting", summary: "", next_action: "Wait", trade_ready: false },
    });

    it("keeps the setup zone, confirmation, invalidation and objective", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "zone", category: "developing", type: "m15_pullback_area", low: 51300, high: 51600 }),
        overlay({ overlay_id: "confirm", category: "developing", type: "confirmation", price: 51420 }),
        overlay({ overlay_id: "invalid", category: "developing", type: "setup_invalidation", price: 51700 }),
        overlay({ overlay_id: "objective", category: "developing", type: "potential_objective", price: 51100 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).toEqual(expect.arrayContaining(["cp", "zone", "confirm", "invalid", "objective"]));
    });

    it("drops developing-category overlays that are not zone/confirmation/invalidation/objective", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "other", category: "developing", type: "internal_swing", price: 51550 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).not.toContain("other");
    });

    it("never surfaces actionable levels before TRADE_READY", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "entry", category: "actionable", actionable: true, type: "entry", price: 51500 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).not.toContain("entry");
    });

    it("narrows external structure context to the nearest reference above and below current price", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "near-above", category: "context", price: 51600 }),
        overlay({ overlay_id: "far-above", category: "context", price: 52000 }),
        overlay({ overlay_id: "near-below", category: "context", price: 51400 }),
        overlay({ overlay_id: "far-below", category: "context", price: 51000 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).toContain("near-above");
      expect(result).toContain("near-below");
      expect(result).not.toContain("far-above");
      expect(result).not.toContain("far-below");
    });
  });

  describe("trade-ready setup", () => {
    const d = decision({
      active_setup: { setup_id: "setup-1", lifecycle: "TRADE_READY" },
      decision: { status: "READY TO BUY", direction: "buy", stage: "READY_TO_BUY", headline: "Ready", summary: "", next_action: "Paper only", trade_ready: true },
    });

    it("keeps every actionable overlay (entry, stop, TP1, TP2)", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "entry", category: "actionable", actionable: true, type: "entry", price: 51500 }),
        overlay({ overlay_id: "stop", category: "actionable", actionable: true, type: "stop", price: 51350 }),
        overlay({ overlay_id: "tp1", category: "actionable", actionable: true, type: "tp1", price: 51850 }),
        overlay({ overlay_id: "tp2", category: "actionable", actionable: true, type: "tp2", price: 52100 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).toEqual(expect.arrayContaining(["cp", "entry", "stop", "tp1", "tp2"]));
    });

    it("keeps the setup zone only when it is still a real zone (has low/high)", () => {
      const overlays = [
        overlay({ overlay_id: "cp", type: "current_price", price: 51500 }),
        overlay({ overlay_id: "zone", category: "developing", type: "m15_pullback_area", low: 51300, high: 51600 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).toContain("zone");
    });

    it("preserves the original overlay order (priority-sorted) rather than reordering by branch", () => {
      const overlays = [
        overlay({ overlay_id: "entry", category: "actionable", actionable: true, type: "entry", price: 51500, priority: 100 }),
        overlay({ overlay_id: "cp", type: "current_price", price: 51500, priority: 110 }),
        overlay({ overlay_id: "stop", category: "actionable", actionable: true, type: "stop", price: 51350, priority: 100 }),
      ];
      const result = applySetupFocus(overlays, d).map((o) => o.overlay_id);
      expect(result).toEqual(["entry", "cp", "stop"]);
    });
  });
});
