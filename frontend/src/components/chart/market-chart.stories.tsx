import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MarketChart } from "./market-chart";
import { useTerminalStore } from "@/store/terminal-store";
import type {
  HistoricalCandle,
  NormalizedDecision,
  Overlay,
  OverlayCategory,
  SymbolInfo,
} from "@/types";

// ---------------------------------------------------------------------------
// Visual regression fixtures (Milestone: chart redesign, §20).
//
// No screenshot-diffing tool (Playwright/Chromatic/loki) is wired into this
// repo, so these stories are the persisted, reviewable fixture surface:
// Storybook renders each scenario against the real MarketChart + overlay
// pipeline (selectVisibleOverlays -> applyDensity -> style registry), not a
// mocked chart, so a regression here is a regression in the real component.
// ---------------------------------------------------------------------------

const SYMBOL: SymbolInfo = {
  symbol_id: "deriv:R_75",
  provider_symbol: "R_75",
  display_name: "Volatility 75 Index",
  family: "VOLATILITY",
  variant: "VOLATILITY_75",
  market_source: "deriv",
  market_type: "derived",
  market_schedule: "24_7",
  analysis_engine: "derived_smc",
  supported: true,
  available_models: [{ id: "auto", label: "SMC Auto" }],
};
const OWNER = "volatility_structure_pullback";
const PRECISION = { symbol_id: SYMBOL.symbol_id, price_decimals: 2, pip_size: null, tick_size: 0.01, quantity_decimals: null };

function candles(bars = 80, base = 51500): HistoricalCandle[] {
  const rows: HistoricalCandle[] = [];
  let price = base;
  for (let i = 0; i < bars; i++) {
    const drift = Math.sin(i / 6) * 40 + (i > bars - 15 ? -(i - (bars - 15)) * 12 : 0);
    const open = price;
    const close = base + drift + (i % 5) * 6;
    const high = Math.max(open, close) + 25;
    const low = Math.min(open, close) - 25;
    rows.push({ time: new Date(2026, 6, 18, 0, i * 5).toISOString(), open, high, low, close });
    price = close;
  }
  return rows;
}

function overlay(overrides: Partial<Overlay> & { type: string }): Overlay {
  return {
    overlay_id: overrides.overlay_id || `${overrides.type}-${Math.random().toString(36).slice(2, 8)}`,
    decision_owner_id: OWNER,
    strategy_id: OWNER,
    setup_id: null,
    symbol_id: SYMBOL.symbol_id,
    provider_symbol: SYMBOL.provider_symbol,
    market_type: SYMBOL.market_type,
    timeframe: "M5",
    category: "context",
    label: overrides.type.replace(/_/g, " ").toUpperCase(),
    source: "backend_analysis",
    price: null,
    low: null,
    high: null,
    start_time: null,
    end_time: null,
    created_at: "2026-07-18T02:00:00Z",
    confirmed_at: null,
    expires_at: null,
    invalidated_at: null,
    active: true,
    historical: false,
    actionable: false,
    priority: 20,
    display_group: "context",
    metadata: { overlay_mode: "HISTORICAL_INSPECTION" },
    ...overrides,
  };
}

interface ScenarioOptions {
  direction?: "buy" | "sell" | null;
  stage: string;
  status: string;
  tradeReady?: boolean;
  entry?: number | null;
  stop?: number | null;
  targets?: Array<{ name: string; price: number; risk_reward?: number }>;
  setupId?: string | null;
  overlays: Overlay[];
  previousSetup?: unknown;
}

function buildDecision(options: ScenarioOptions): NormalizedDecision {
  const ready = Boolean(options.tradeReady);
  const setup = options.setupId
    ? {
        setup_id: options.setupId,
        setup_type: "structure_pullback",
        direction: options.direction,
        stage: options.stage,
        status: options.status,
        context_summary: "H1 bearish · M15 pullback",
        next_required_condition: "Wait for the next completed structural condition.",
        trade_ready: ready,
        entry: ready ? options.entry : null,
        stop: ready ? options.stop : null,
        targets: ready ? options.targets || [] : [],
        rr: ready ? 2 : null,
        invalidation: { price: options.stop ?? undefined, condition: "Price closes beyond the protected M5 structural level." },
        entry_area: { low: (options.entry ?? 51000) - 60, high: (options.entry ?? 51000) + 60, type: "m5_displacement_retrace" },
        quality_score: 70,
        quality_grade: "B",
      }
    : {
        setup_id: undefined,
        stage: options.stage,
        status: options.status,
        context_summary: "No active setup.",
        next_required_condition: "Wait for a new qualifying setup.",
        trade_ready: false,
        targets: [],
        quality_score: null,
        quality_grade: null,
      };
  return {
    decision_id: "story-decision",
    overlay_mode: "HISTORICAL_INSPECTION",
    precision: PRECISION,
    meta: {
      symbol: SYMBOL.provider_symbol,
      display_symbol: SYMBOL.display_name,
      timeframe: "M5",
      analysis_time: "2026-07-18T02:00:00Z",
      live: false,
      market_schedule: "24_7",
      analysis_clock: "UTC",
      market_source: SYMBOL.market_source,
      market_type: SYMBOL.market_type,
    },
    ownership: { selected_model_id: OWNER, selected_strategy_id: OWNER, decision_owner_id: OWNER, overlay_owner_id: OWNER },
    readiness: { state: "ready" },
    market: { external_structure: "bearish", internal_structure: "pullback", current_price: 51500 },
    trade_plan: ready
      ? { available: true, status: options.status, entry: options.entry, stop: options.stop, targets: options.targets || [] }
      : { available: false, status: "UNAVAILABLE", entry: null, stop: null, targets: [], reason: "Unavailable until all production geometry passes." },
    decision: {
      status: options.status,
      direction: options.direction,
      stage: options.stage,
      headline: options.status,
      summary: "",
      next_action: ready ? "Paper-analysis plan is complete." : "Wait for the next completed structural condition.",
      trade_ready: ready,
      first_blocking_gate: ready ? undefined : "No valid structural target currently belongs to this setup.",
    },
    setup: setup as NormalizedDecision["setup"],
    diagnostics: { invariants: { valid: true } },
    overlays: options.overlays,
    active_setup: options.setupId
      ? { ...setup, setup_id: options.setupId, lifecycle: ready ? "TRADE_READY" : options.stage }
      : null,
    previous_setup: options.previousSetup ?? null,
  };
}

function currentPriceOverlay(): Overlay {
  return overlay({ type: "current_price", price: 51500, priority: 110, display_group: "context", metadata: { overlay_mode: "HISTORICAL_INSPECTION" }, label: "Decision-time Current" });
}

function structureOverlays(): Overlay[] {
  return [
    overlay({ type: "h1_context", price: 52200, priority: 80, display_group: "market_structure", label: "H1 Bearish Context" }),
    overlay({ type: "structural_range", price: 50900, priority: 75, display_group: "market_structure", label: "M15 Structural Low" }),
  ];
}

function developingOverlays(setupId: string, direction: "buy" | "sell"): Overlay[] {
  const bias = direction === "sell" ? -1 : 1;
  return [
    overlay({ type: "m15_pullback_area", setup_id: setupId, category: "developing", low: 51350 - bias * 20, high: 51650 - bias * 20, priority: 90, display_group: "setup", label: "M15 Pullback Area" }),
    overlay({ type: "confirmation", setup_id: setupId, category: "developing", price: 51420, priority: 50, display_group: "setup", label: "Confirmation Level" }),
    overlay({ type: "setup_invalidation", setup_id: setupId, category: "developing", price: 51700 + bias * 30, priority: 90, display_group: "setup", label: "Idea Invalidation" }),
    overlay({ type: "potential_objective", setup_id: setupId, category: "developing", price: 51100 - bias * 40, priority: 70, display_group: "setup", label: "Potential Objective" }),
  ];
}

function actionableOverlays(setupId: string, entry: number, stop: number, tp1: number, tp2: number): Overlay[] {
  return [
    overlay({ type: "entry", setup_id: setupId, category: "actionable", actionable: true, price: entry, priority: 100, display_group: "trade_plan", label: "Entry", metadata: { plan_role: "entry", overlay_mode: "HISTORICAL_INSPECTION" } }),
    overlay({ type: "stop", setup_id: setupId, category: "actionable", actionable: true, price: stop, priority: 100, display_group: "trade_plan", label: "Stop", metadata: { plan_role: "stop", overlay_mode: "HISTORICAL_INSPECTION" } }),
    overlay({ type: "tp1", setup_id: setupId, category: "actionable", actionable: true, price: tp1, priority: 100, display_group: "trade_plan", label: "TP1", metadata: { plan_role: "tp1", overlay_mode: "HISTORICAL_INSPECTION" } }),
    overlay({ type: "tp2", setup_id: setupId, category: "actionable", actionable: true, price: tp2, priority: 100, display_group: "trade_plan", label: "TP2", metadata: { plan_role: "tp2", overlay_mode: "HISTORICAL_INSPECTION" } }),
  ];
}

function diagnosticOverlays(setupId: string): Overlay[] {
  return [
    overlay({ type: "m5_displacement", setup_id: null, price: 51420, priority: 50, display_group: "advanced_smc", label: "Completed M5 Displacement" }),
    overlay({ type: "swing_high", setup_id: null, price: 51980, priority: 40, display_group: "advanced_smc", label: "Internal Swing High" }),
    overlay({ type: "swing_low", setup_id: null, price: 51120, priority: 40, display_group: "advanced_smc", label: "Internal Swing Low" }),
    overlay({ type: "equal_high", setup_id: null, price: 52050, priority: 40, display_group: "advanced_smc", label: "Equal High Liquidity" }),
    overlay({ type: "confirmation", setup_id: setupId, category: "developing", price: 51420, priority: 50, display_group: "advanced_smc", label: "M5 Structure Break" }),
  ];
}

// --- ten required scenarios --------------------------------------------

const marketContextOnly = buildDecision({
  direction: null,
  stage: "NO_DIRECTIONAL_CONTEXT",
  status: "NO DIRECTIONAL CONTEXT",
  setupId: null,
  overlays: [currentPriceOverlay(), ...structureOverlays()],
});

const developingBuy = buildDecision({
  direction: "buy",
  stage: "WAITING_FOR_LOCATION",
  status: "BUY SETUP DEVELOPING",
  setupId: "vsp-buy-developing",
  overlays: [currentPriceOverlay(), ...structureOverlays(), ...developingOverlays("vsp-buy-developing", "buy")],
});

const developingSell = buildDecision({
  direction: "sell",
  stage: "WAITING_FOR_LOCATION",
  status: "SELL SETUP DEVELOPING",
  setupId: "vsp-sell-developing",
  overlays: [currentPriceOverlay(), ...structureOverlays(), ...developingOverlays("vsp-sell-developing", "sell")],
});

const planValidation = buildDecision({
  direction: "sell",
  stage: "PLAN_VALIDATION",
  status: "PLAN VALIDATION",
  setupId: "vsp-plan-validation",
  overlays: [currentPriceOverlay(), ...structureOverlays(), ...developingOverlays("vsp-plan-validation", "sell")],
});

const waitingForConfirmation = buildDecision({
  direction: "sell",
  stage: "WAITING_FOR_DISPLACEMENT",
  status: "WAITING FOR BEARISH M5 DISPLACEMENT",
  setupId: "vsp-waiting-confirmation",
  overlays: [
    currentPriceOverlay(),
    ...structureOverlays(),
    overlay({ type: "m15_pullback_area", setup_id: "vsp-waiting-confirmation", category: "developing", low: 51350, high: 51650, priority: 90, display_group: "setup", label: "M15 Pullback Area" }),
  ],
});

const tradeReadyBuy = buildDecision({
  direction: "buy",
  stage: "READY_TO_BUY",
  status: "READY TO BUY",
  setupId: "vsp-ready-buy",
  tradeReady: true,
  entry: 51500,
  stop: 51350,
  targets: [{ name: "TP1", price: 51850, risk_reward: 2.3 }, { name: "TP2", price: 52100, risk_reward: 4 }],
  overlays: [
    currentPriceOverlay(),
    ...structureOverlays(),
    ...actionableOverlays("vsp-ready-buy", 51500, 51350, 51850, 52100),
  ],
});

const tradeReadySell = buildDecision({
  direction: "sell",
  stage: "READY_TO_SELL",
  status: "READY TO SELL",
  setupId: "vsp-ready-sell",
  tradeReady: true,
  entry: 51500,
  stop: 51650,
  targets: [{ name: "TP1", price: 51150, risk_reward: 2.3 }, { name: "TP2", price: 50900, risk_reward: 4 }],
  overlays: [
    currentPriceOverlay(),
    ...structureOverlays(),
    ...actionableOverlays("vsp-ready-sell", 51500, 51650, 51150, 50900),
  ],
});

const expiredSetup = buildDecision({
  direction: null,
  stage: "NO_DIRECTIONAL_CONTEXT",
  status: "SETUP EXPIRED",
  setupId: null,
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  previousSetup: { setup_id: "vsp-expired-1", terminal_status: "EXPIRED", terminal_reason: "Setup expired before entry confirmation." },
});

const invalidatedSetup = buildDecision({
  direction: null,
  stage: "NO_DIRECTIONAL_CONTEXT",
  status: "SETUP INVALIDATED",
  setupId: null,
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  previousSetup: { setup_id: "vsp-invalidated-1", terminal_status: "INVALIDATED", terminal_reason: "Price closed beyond the protected M5 structural level before entry." },
});

const previousSetupOverlays: Overlay[] = [
  overlay({ type: "historical_entry", setup_id: "vsp-expired-1", category: "historical", historical: true, active: false, price: 51600, priority: 20, display_group: "previous_setup", label: "Previous Entry", metadata: { overlay_mode: "HISTORICAL_INSPECTION" } }),
  overlay({ type: "historical_stop", setup_id: "vsp-expired-1", category: "historical", historical: true, active: false, price: 51750, priority: 20, display_group: "previous_setup", label: "Previous Stop", metadata: { overlay_mode: "HISTORICAL_INSPECTION" } }),
];
const previousSetupEnabled = buildDecision({
  direction: null,
  stage: "NO_DIRECTIONAL_CONTEXT",
  status: "SETUP EXPIRED",
  setupId: null,
  overlays: [currentPriceOverlay(), ...structureOverlays(), ...previousSetupOverlays],
  previousSetup: { setup_id: "vsp-expired-1", terminal_status: "EXPIRED", terminal_reason: "Setup expired before entry confirmation." },
});

const advancedSmcEnabled = buildDecision({
  direction: "sell",
  stage: "PLAN_VALIDATION",
  status: "PLAN VALIDATION",
  setupId: "vsp-advanced",
  overlays: [
    currentPriceOverlay(),
    ...structureOverlays(),
    ...developingOverlays("vsp-advanced", "sell"),
    ...diagnosticOverlays("vsp-advanced"),
  ],
});

function renderScenario(
  decision: NormalizedDecision,
  overlayVisibility: Partial<Record<OverlayCategory, boolean>> = {},
  densityMode: "clean" | "standard" | "research" = "clean",
) {
  useTerminalStore.setState({
    symbol: SYMBOL,
    timeframe: "M5",
    marketSource: "deriv",
    marketType: "derived",
    workspaceMode: "historical",
    historicalCandles: candles(),
    historicalJobId: "story-job",
    decision,
    overlayOwner: OWNER,
    connection: "connected",
    dataReadiness: "ready",
    densityMode,
    overlayVisibility: {
      trade_plan: true,
      market_structure: true,
      context_levels: true,
      advanced_smc: false,
      previous_setup: false,
      ...overlayVisibility,
    },
  });
  const client = new QueryClient();
  return (
    <QueryClientProvider client={client}>
      <div style={{ width: 1440, height: 720 }} className="border border-white/10">
        <MarketChart />
      </div>
    </QueryClientProvider>
  );
}

const meta: Meta = {
  title: "Chart/Scenarios",
  parameters: {
    layout: "fullscreen",
    backgrounds: { default: "terminal", values: [{ name: "terminal", value: "#07090d" }] },
  },
};
export default meta;
type Story = StoryObj;

export const MarketContextOnly: Story = { render: () => renderScenario(marketContextOnly) };
export const DevelopingBuySetup: Story = { render: () => renderScenario(developingBuy) };
export const DevelopingSellSetup: Story = { render: () => renderScenario(developingSell) };
export const PlanValidation: Story = { render: () => renderScenario(planValidation) };
export const WaitingForConfirmation: Story = { render: () => renderScenario(waitingForConfirmation) };
export const TradeReadyBuy: Story = { render: () => renderScenario(tradeReadyBuy) };
export const TradeReadySell: Story = { render: () => renderScenario(tradeReadySell) };
export const ExpiredSetup: Story = { render: () => renderScenario(expiredSetup) };
export const InvalidatedSetup: Story = { render: () => renderScenario(invalidatedSetup) };
export const PreviousSetupEnabled: Story = {
  render: () => renderScenario(previousSetupEnabled, { previous_setup: true }),
};
export const AdvancedSmcEnabled: Story = {
  render: () => renderScenario(advancedSmcEnabled, { advanced_smc: true }, "research"),
};

// --- responsive spot-checks (Phase 3 §16 widths) — one illustrative scenario ---

const RESOLUTIONS: Array<[string, number, number]> = [
  ["1920x1080", 1920, 1080],
  ["1536x864", 1536, 864],
  ["1440x900", 1440, 900],
  ["1280x800", 1280, 800],
  ["1024x768", 1024, 768],
];

function renderAtWidth(decision: NormalizedDecision, width: number, height: number) {
  useTerminalStore.setState({
    symbol: SYMBOL,
    timeframe: "M5",
    marketSource: "deriv",
    marketType: "derived",
    workspaceMode: "historical",
    historicalCandles: candles(),
    historicalJobId: "story-job",
    decision,
    overlayOwner: OWNER,
    connection: "connected",
    dataReadiness: "ready",
    densityMode: "clean",
    overlayVisibility: { trade_plan: true, market_structure: true, context_levels: true, advanced_smc: false, previous_setup: false },
  });
  const client = new QueryClient();
  return (
    <QueryClientProvider client={client}>
      <div style={{ width, height }} className="border border-white/10">
        <MarketChart />
      </div>
    </QueryClientProvider>
  );
}

export const TradeReadySell_1920x1080: Story = { render: () => renderAtWidth(tradeReadySell, RESOLUTIONS[0][1], RESOLUTIONS[0][2]) };
export const TradeReadySell_1536x864: Story = { render: () => renderAtWidth(tradeReadySell, RESOLUTIONS[1][1], RESOLUTIONS[1][2]) };
export const TradeReadySell_1440x900: Story = { render: () => renderAtWidth(tradeReadySell, RESOLUTIONS[2][1], RESOLUTIONS[2][2]) };
export const TradeReadySell_1280x800: Story = { render: () => renderAtWidth(tradeReadySell, RESOLUTIONS[3][1], RESOLUTIONS[3][2]) };
export const TradeReadySell_1024x768: Story = { render: () => renderAtWidth(tradeReadySell, RESOLUTIONS[4][1], RESOLUTIONS[4][2]) };
