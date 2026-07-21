import { describe, expect, it } from "vitest";
import {
  isNormalizedOverlay,
  selectVisibleOverlays,
  toggleForOverlay,
} from "./overlays";
import { chartPriceFormat, formatPrice } from "./utils";
import type {
  NormalizedDecision,
  Overlay,
  OverlayCategory,
  SymbolInfo,
} from "@/types";

const symbol: SymbolInfo = {
  symbol_id: "twelve_data:USD/JPY",
  provider_symbol: "USD/JPY",
  display_name: "USD/JPY",
  family: "FOREX",
  market_source: "twelve_data",
  market_type: "forex",
  market_schedule: "24_5",
  analysis_engine: "forex",
  supported: true,
  available_models: [{ id: "auto", label: "Auto" }],
};

const visibility: Record<OverlayCategory, boolean> = {
  trade_plan: true,
  market_structure: true,
  context_levels: true,
  advanced_smc: false,
  previous_setup: false,
};

function overlay(overrides: Partial<Overlay> = {}): Overlay {
  return {
    overlay_id: "current",
    decision_owner_id: "owner-1",
    strategy_id: "strategy-1",
    setup_id: null,
    symbol_id: symbol.symbol_id,
    provider_symbol: symbol.provider_symbol,
    market_type: symbol.market_type,
    timeframe: "M5",
    category: "context",
    type: "current_price",
    label: "Current price",
    source: "completed_m5_close",
    price: 161.234,
    high: null,
    low: null,
    start_time: null,
    end_time: null,
    created_at: "2026-07-20T12:00:00Z",
    confirmed_at: "2026-07-20T12:00:00Z",
    expires_at: null,
    invalidated_at: null,
    active: true,
    historical: false,
    actionable: false,
    priority: 80,
    display_group: "context",
    metadata: { visibility_reason: "Latest completed close", overlay_mode: "LIVE" },
    ...overrides,
  };
}

function decision(overrides: Partial<NormalizedDecision> = {}): NormalizedDecision {
  const base: NormalizedDecision = {
    decision_id: "decision-1",
    overlay_mode: "LIVE",
    precision: {
      symbol_id: symbol.symbol_id,
      price_decimals: 3,
      pip_size: 0.01,
      tick_size: 0.001,
      quantity_decimals: null,
    },
    meta: {
      symbol: symbol.provider_symbol,
      display_symbol: symbol.display_name,
      timeframe: "M5",
      analysis_time: "2026-07-20T12:00:00Z",
      live: true,
      market_schedule: "24_5",
      analysis_clock: "UTC",
      market_source: symbol.market_source,
      market_type: symbol.market_type,
    },
    ownership: {
      selected_model_id: "strategy-1",
      selected_strategy_id: "strategy-1",
      requested_model_id: "auto",
      decision_owner_id: "owner-1",
      overlay_owner_id: "owner-1",
    },
    readiness: { state: "READY" },
    market: { current_price: 161.234 },
    trade_plan: {
      available: true,
      status: "VALID",
      entry: 161.2,
      stop: 161.5,
      targets: [{ name: "TP1", price: 160.6 }],
      entry_zone: { low: 161.18, high: 161.22 },
      invalidation: 161.5,
    },
    decision: {
      status: "READY TO SELL",
      direction: "sell",
      stage: "TRADE_READY",
      headline: "Ready",
      summary: "Validated",
      next_action: "Paper only",
      trade_ready: true,
    },
    setup: {
      setup_id: "setup-1",
      setup_type: "structure_pullback",
      direction: "sell",
      stage: "TRADE_READY",
      status: "READY TO SELL",
      context_summary: "Bearish",
      next_required_condition: "None",
      trade_ready: true,
      entry: 161.2,
      stop: 161.5,
      targets: [{ name: "TP1", price: 160.6 }],
      quality_score: 90,
      quality_grade: "A",
    },
    active_setup: { setup_id: "setup-1", lifecycle: "TRADE_READY" },
    previous_setup: { setup_id: "setup-old", state: "EXPIRED" },
    diagnostics: { invariants: { valid: true } },
    overlays: [],
  };
  return { ...base, ...overrides };
}

function select(
  value: NormalizedDecision,
  options: {
    visibility?: Record<OverlayCategory, boolean>;
    workspaceMode?: "live" | "historical" | "replay";
    connection?: string;
  } = {},
) {
  return selectVisibleOverlays({
    decision: value,
    symbol,
    timeframe: "M5",
    workspaceMode: options.workspaceMode || "live",
    connection: options.connection || "connected",
    visibility: options.visibility || visibility,
  });
}

describe("normalized chart overlay policy", () => {
  it("rejects legacy and unexplained chart rows", () => {
    const legacy = {
      overlay_id: "legacy",
      owner_id: "owner-1",
      visibility_category: "trade_plan",
      type: "target",
      price: 160,
    };
    expect(isNormalizedOverlay(legacy)).toBe(false);
    expect(select(decision({ overlays: [legacy as unknown as Overlay] }))).toEqual([]);
    expect(isNormalizedOverlay(overlay({ label: "" }))).toBe(false);
    expect(isNormalizedOverlay(overlay({ source: "" }))).toBe(false);
  });

  it("maps toggles from normalized category, display group, and priority", () => {
    expect(toggleForOverlay(overlay({ category: "actionable" }))).toBe("trade_plan");
    expect(toggleForOverlay(overlay({ display_group: "market_structure" }))).toBe("market_structure");
    expect(toggleForOverlay(overlay({ display_group: "context" }))).toBe("context_levels");
    expect(toggleForOverlay(overlay({ display_group: "market_structure", priority: 40 }))).toBe("advanced_smc");
    expect(toggleForOverlay(overlay({ category: "historical" }))).toBe("previous_setup");
  });

  it("keeps backend current price visible independently of optional toggles", () => {
    const rows = select(decision({ overlays: [overlay()] }), {
      visibility: {
        trade_plan: false,
        market_structure: false,
        context_levels: false,
        advanced_smc: false,
        previous_setup: false,
      },
    });
    expect(rows.map((row) => row.type)).toEqual(["current_price"]);
  });

  it("makes Trade Plan actionable-only while a developing area remains context", () => {
    const actionable = overlay({
      overlay_id: "entry",
      category: "actionable",
      actionable: true,
      setup_id: "setup-1",
      type: "entry",
      label: "Entry",
      price: 161.2,
      display_group: "trade_plan",
      priority: 100,
      metadata: { plan_role: "entry", overlay_mode: "LIVE" },
    });
    const developing = overlay({
      overlay_id: "developing",
      category: "developing",
      setup_id: "setup-1",
      type: "setup_area",
      label: "DEVELOPING · NOT AN ENTRY",
      price: null,
      low: 161.18,
      high: 161.22,
      display_group: "trade_plan",
      priority: 90,
    });
    const rows = select(
      decision({ overlays: [actionable, developing] }),
      {
        visibility: {
          ...visibility,
          context_levels: false,
        },
      },
    );
    expect(rows.map((row) => row.overlay_id)).toEqual(["entry"]);
  });

  it("hides archived overlays by default and reveals only the previous setup", () => {
    const historical = overlay({
      overlay_id: "old-entry",
      category: "historical",
      setup_id: "setup-old",
      type: "entry",
      label: "Previous entry",
      active: false,
      historical: true,
      priority: 20,
      display_group: "previous_setup",
      metadata: { overlay_mode: "LIVE" },
    });
    const current = overlay();
    const value = decision({ overlays: [historical, current] });
    expect(select(value).map((row) => row.overlay_id)).toEqual(["current"]);
    const revealed = select(value, {
      visibility: { ...visibility, previous_setup: true },
    });
    expect(revealed.map((row) => row.overlay_id)).toEqual([
      "current",
      "old-entry",
    ]);
  });

  it("rejects owner, symbol, market, and timeframe mismatches", () => {
    const rows = [
      overlay({ overlay_id: "owner", decision_owner_id: "other" }),
      overlay({ overlay_id: "symbol", symbol_id: "other" }),
      overlay({ overlay_id: "provider", provider_symbol: "EUR/USD" }),
      overlay({ overlay_id: "market", market_type: "derived" }),
      overlay({ overlay_id: "timeframe", timeframe: "M15" }),
      overlay({ overlay_id: "strategy", strategy_id: "other" }),
    ];
    expect(select(decision({ overlays: rows }))).toEqual([]);
  });

  it("allows a family adapter to own a selected strategy without conflating their IDs", () => {
    const adapted = decision({
      ownership: {
        ...decision().ownership,
        selected_model_id: "jump_post_event_smc",
        selected_strategy_id: "jump_post_event_smc",
        decision_owner_id: "jump_smc_adapter",
        overlay_owner_id: "jump_smc_adapter",
      },
      overlays: [
        overlay({
          decision_owner_id: "jump_smc_adapter",
          strategy_id: "jump_post_event_smc",
        }),
      ],
    });
    expect(select(adapted)).toHaveLength(1);
  });

  it("never mixes live, historical-inspection, or replay decisions", () => {
    const live = decision({ overlays: [overlay()] });
    expect(select(live, { workspaceMode: "historical" })).toEqual([]);
    const historical = decision({
      overlay_mode: "HISTORICAL_INSPECTION",
      overlays: [overlay({ metadata: { overlay_mode: "HISTORICAL_INSPECTION" } })],
    });
    expect(select(historical, { workspaceMode: "live" })).toEqual([]);
    expect(select(historical, { workspaceMode: "historical" })).toHaveLength(1);
    const replay = decision({
      overlay_mode: "REPLAY",
      overlays: [overlay({ metadata: { overlay_mode: "REPLAY" } })],
    });
    expect(select(replay, { workspaceMode: "historical" })).toEqual([]);
    expect(select(replay, { workspaceMode: "replay" })).toHaveLength(1);
  });

  it("keeps context but suspends actionable rows when live data is stale", () => {
    const entry = overlay({
      overlay_id: "entry",
      category: "actionable",
      actionable: true,
      setup_id: "setup-1",
      type: "entry",
      label: "Entry",
      price: 161.2,
      priority: 100,
      display_group: "trade_plan",
      metadata: { plan_role: "entry", overlay_mode: "LIVE" },
    });
    const rows = select(decision({ overlays: [entry, overlay()] }), {
      connection: "stale",
    });
    expect(rows.map((row) => row.overlay_id)).toEqual(["current"]);
  });

  it("requires a complete backend plan before any actionable overlay", () => {
    const entry = overlay({
      overlay_id: "entry",
      category: "actionable",
      actionable: true,
      setup_id: "setup-1",
      type: "entry",
      label: "Entry",
      price: 161.2,
      priority: 100,
      display_group: "trade_plan",
      metadata: { plan_role: "entry", overlay_mode: "LIVE" },
    });
    const missingEntry = decision({
      trade_plan: { ...decision().trade_plan!, entry: null },
      overlays: [entry],
    });
    const missingStop = decision({
      trade_plan: { ...decision().trade_plan!, stop: null },
      overlays: [entry],
    });
    const notReady = decision({
      decision: { ...decision().decision, trade_ready: false, stage: "WAITING_FOR_CONFIRMATION" },
      overlays: [entry],
    });
    expect(select(missingEntry)).toEqual([]);
    expect(select(missingStop)).toEqual([]);
    expect(select(notReady)).toEqual([]);
  });

  it("requires actionable prices to equal the backend trade plan", () => {
    const wrongTarget = overlay({
      overlay_id: "tp1",
      category: "actionable",
      actionable: true,
      setup_id: "setup-1",
      type: "tp1",
      label: "TP1",
      price: 160.61,
      priority: 100,
      display_group: "trade_plan",
      metadata: { plan_role: "tp1", overlay_mode: "LIVE" },
    });
    expect(select(decision({ overlays: [wrongTarget] }))).toEqual([]);
  });

  it("removes setup-specific drawings when there is no active setup", () => {
    const developing = overlay({
      overlay_id: "objective",
      category: "developing",
      setup_id: "setup-1",
      type: "structural_objective",
      label: "POTENTIAL OBJECTIVE",
      price: 160.6,
      priority: 70,
    });
    const value = decision({
      active_setup: null,
      overlays: [developing, overlay()],
    });
    expect(select(value).map((row) => row.overlay_id)).toEqual(["current"]);
  });

  it("rejects premature TP and entry wording on developing overlays", () => {
    const premature = overlay({
      overlay_id: "premature",
      category: "developing",
      setup_id: "setup-1",
      type: "structural_objective",
      label: "TP1",
      price: 160.6,
      priority: 70,
    });
    expect(select(decision({ overlays: [premature] }))).toEqual([]);
  });
});

describe("instrument-owned precision", () => {
  it("formats JPY and non-JPY values from metadata without chart hardcoding", () => {
    const jpy = decision().precision;
    const nonJpy = { ...jpy, symbol_id: "twelve_data:EUR/USD", price_decimals: 5, tick_size: 0.00001 };
    expect(formatPrice(161.2, jpy)).toBe("161.200");
    expect(formatPrice(1.1, nonJpy)).toBe("1.10000");
    expect(chartPriceFormat(jpy)).toEqual({ type: "price", precision: 3, minMove: 0.001 });
  });
});
