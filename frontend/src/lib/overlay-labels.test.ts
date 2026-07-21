import { describe, expect, it } from "vitest";
import { chartLabel, stripStatusPrefix, tagText } from "./overlay-labels";
import type { Overlay } from "@/types";

function overlay(overrides: Partial<Overlay> = {}): Overlay {
  return {
    overlay_id: "o1",
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

describe("stripStatusPrefix", () => {
  it("removes a single lifecycle prefix", () => {
    expect(stripStatusPrefix("DEVELOPING · M15 Pullback Area")).toBe("M15 Pullback Area");
  });

  it("removes a duplicated lifecycle prefix", () => {
    expect(stripStatusPrefix("DEVELOPING · DEVELOPING · M15 Pullback Area")).toBe("M15 Pullback Area");
  });

  it("leaves a label with no prefix untouched", () => {
    expect(stripStatusPrefix("IDEA INVALIDATION")).toBe("IDEA INVALIDATION");
  });
});

describe("chartLabel", () => {
  it("produces a clean on-chart label with no lifecycle prefix", () => {
    expect(chartLabel(overlay())).toBe("M15 PULLBACK AREA");
  });

  it("never produces a duplicated DEVELOPING prefix even if the backend label has one", () => {
    const doubled = overlay({ label: "DEVELOPING · DEVELOPING · M15 Pullback Area" });
    expect(chartLabel(doubled)).not.toContain("DEVELOPING");
    expect(chartLabel(doubled)).toBe("M15 PULLBACK AREA");
  });

  it("does not repeat the lifecycle word inside labels that never had one", () => {
    expect(chartLabel(overlay({ label: "IDEA INVALIDATION" }))).toBe("IDEA INVALIDATION");
  });
});

describe("tagText", () => {
  it("uses short trading-role names for actionable rows", () => {
    expect(tagText(overlay({ type: "entry", metadata: { plan_role: "entry" } }))).toBe("ENTRY");
    expect(tagText(overlay({ type: "stop", metadata: { plan_role: "stop" } }))).toBe("STOP");
    expect(tagText(overlay({ type: "tp1", metadata: { plan_role: "tp1" } }))).toBe("TP1");
    expect(tagText(overlay({ type: "tp2", metadata: { plan_role: "tp2" } }))).toBe("TP2");
  });

  it("falls back to a short form of the chart label for everything else", () => {
    expect(tagText(overlay({ label: "H1 Bearish Context", type: "h1_context" }))).toBe("H1 BEARISH");
  });

  it("labels the current-price tag CURRENT in live mode (Phase 3 §17)", () => {
    expect(tagText(overlay({ type: "current_price", metadata: { overlay_mode: "LIVE" } }))).toBe("CURRENT");
  });

  it("labels the current-price tag DECISION TIME in historical inspection, never 'Decision-time Current'", () => {
    const text = tagText(overlay({ type: "current_price", metadata: { overlay_mode: "HISTORICAL_INSPECTION" } }));
    expect(text).toBe("DECISION TIME");
    expect(text).not.toContain("Decision-time Current");
  });

  it("labels the current-price tag REPLAY PRICE in replay mode", () => {
    expect(tagText(overlay({ type: "current_price", metadata: { overlay_mode: "REPLAY" } }))).toBe("REPLAY PRICE");
  });

  it("does not replace the current-price tag when Previous Setup is the mode", () => {
    expect(tagText(overlay({ type: "current_price", metadata: { overlay_mode: "PREVIOUS_SETUP" } }))).toBe("");
  });
});
