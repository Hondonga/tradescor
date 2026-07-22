import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WorkspacePage } from "./workspace-page";
import { useTerminalStore } from "@/store/terminal-store";
import type { HistoricalCandle, NormalizedDecision, Overlay, SymbolInfo } from "@/types";

// ---------------------------------------------------------------------------
// Phase 4 §24 -- GBP/USD full-Workspace acceptance fixtures. Renders the real
// WorkspacePage (OpportunityQueue + MarketChart + DecisionRail), not a
// mocked layout, against hand-built GBP/USD decisions covering the required
// M5 states plus a GBP/USD <-> R_75 symbol switch.
// ---------------------------------------------------------------------------

const GBPUSD: SymbolInfo = {
  symbol_id: "twelve_data:GBP/USD",
  provider_symbol: "GBP/USD",
  display_name: "GBP/USD",
  family: "FOREX",
  market_source: "twelve_data",
  market_type: "forex",
  market_schedule: "24_5",
  analysis_engine: "forex_strategy",
  supported: true,
  available_models: [{ id: "auto", label: "Forex ICT" }],
};
const R75: SymbolInfo = {
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
const OWNER = "ict_2022";
const PRECISION = { symbol_id: GBPUSD.symbol_id, price_decimals: 5, pip_size: 0.0001, tick_size: 0.00001, quantity_decimals: null };

function candles(bars = 80, base = 1.271): HistoricalCandle[] {
  const rows: HistoricalCandle[] = [];
  let price = base;
  for (let i = 0; i < bars; i++) {
    const drift = Math.sin(i / 6) * 0.004 + (i > bars - 15 ? -(i - (bars - 15)) * 0.0012 : 0);
    const open = price;
    const close = base + drift + (i % 5) * 0.0006;
    const high = Math.max(open, close) + 0.0025;
    const low = Math.min(open, close) - 0.0025;
    rows.push({ time: new Date(2026, 6, 20, 8, i * 5).toISOString(), open, high, low, close });
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
    symbol_id: GBPUSD.symbol_id,
    provider_symbol: GBPUSD.provider_symbol,
    market_type: GBPUSD.market_type,
    timeframe: "M5",
    category: "context",
    label: overrides.type.replace(/_/g, " ").toUpperCase(),
    source: "backend_analysis",
    price: null,
    low: null,
    high: null,
    start_time: null,
    end_time: null,
    created_at: "2026-07-20T08:00:00Z",
    confirmed_at: null,
    expires_at: null,
    invalidated_at: null,
    active: true,
    historical: false,
    actionable: false,
    priority: 20,
    display_group: "context",
    metadata: {},
    ...overrides,
  };
}

function currentPriceOverlay(): Overlay {
  return overlay({ type: "current_price", price: 1.271, priority: 110, display_group: "context", label: "Decision-time Current" });
}
function structureOverlays(): Overlay[] {
  return [
    overlay({ type: "h1_context", price: 1.29, priority: 80, display_group: "market_structure", label: "H1 Bullish Context" }),
    overlay({ type: "structural_range", price: 1.268, priority: 75, display_group: "market_structure", label: "M15 Structural Low" }),
  ];
}
function actionableOverlays(setupId: string, entry: number, stop: number, tp1: number, tp2: number): Overlay[] {
  return [
    overlay({ type: "entry", setup_id: setupId, category: "actionable", actionable: true, price: entry, priority: 100, display_group: "trade_plan", label: "Entry", metadata: { plan_role: "entry" } }),
    overlay({ type: "stop", setup_id: setupId, category: "actionable", actionable: true, price: stop, priority: 100, display_group: "trade_plan", label: "Stop", metadata: { plan_role: "stop" } }),
    overlay({ type: "tp1", setup_id: setupId, category: "actionable", actionable: true, price: tp1, priority: 100, display_group: "trade_plan", label: "TP1", metadata: { plan_role: "tp1" } }),
    overlay({ type: "tp2", setup_id: setupId, category: "actionable", actionable: true, price: tp2, priority: 100, display_group: "trade_plan", label: "TP2", metadata: { plan_role: "tp2" } }),
  ];
}

interface GbpScenario {
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
  readiness?: { state: string; last_successful_update?: string };
  forex?: NormalizedDecision["forex"];
  session?: string;
}

function buildGbpDecision(options: GbpScenario): NormalizedDecision {
  const ready = Boolean(options.tradeReady);
  const setup = options.setupId
    ? {
        setup_id: options.setupId,
        setup_type: "ict_2022_v2",
        direction: options.direction,
        stage: options.stage,
        status: options.status,
        context_summary: "H1 bullish · M15 discount",
        next_required_condition: "Wait for the next completed structural condition.",
        trade_ready: ready,
        entry: ready ? options.entry : null,
        stop: ready ? options.stop : null,
        targets: ready ? options.targets || [] : [],
        rr: ready ? 2 : null,
        invalidation: { price: options.stop ?? undefined, condition: "Price closes beyond the sweep extreme." },
        entry_area: { low: (options.entry ?? 1.271) - 0.0005, high: (options.entry ?? 1.271) + 0.0005, type: "fvg" },
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
    decision_id: "gbpusd-story",
    overlay_mode: "HISTORICAL_INSPECTION",
    precision: PRECISION,
    meta: {
      symbol: GBPUSD.provider_symbol,
      display_symbol: GBPUSD.display_name,
      timeframe: "M5",
      analysis_time: "2026-07-20T08:00:00Z",
      live: false,
      market_schedule: "24_5",
      analysis_clock: "UTC",
      market_source: GBPUSD.market_source,
      market_type: GBPUSD.market_type,
    },
    ownership: { selected_model_id: OWNER, selected_strategy_id: OWNER, decision_owner_id: OWNER, overlay_owner_id: OWNER },
    readiness: options.readiness || { state: "ready" },
    market: { external_structure: "bullish", internal_structure: "pullback", current_price: 1.271, session: options.session },
    forex: options.forex,
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
      first_blocking_gate: ready ? undefined : "Waiting for the next completed structural condition.",
    },
    setup: setup as NormalizedDecision["setup"],
    diagnostics: { invariants: { valid: true } },
    overlays: options.overlays,
    active_setup: options.setupId ? { ...setup, setup_id: options.setupId, lifecycle: ready ? "TRADE_READY" : options.stage } : null,
    previous_setup: options.previousSetup ?? null,
  } as NormalizedDecision;
}

const marketClosed = buildGbpDecision({
  direction: null, stage: "NO_CONTEXT", status: "MARKET CLOSED", setupId: null,
  overlays: [currentPriceOverlay()],
  readiness: { state: "market_closed" },
  forex: { htf_bias: "neutral", session: "Market Closed (Weekend)", scenario_state: "NO_CONTEXT" },
});
const marketContext = buildGbpDecision({
  direction: null, stage: "NO_CONTEXT", status: "MARKET CONTEXT", setupId: null,
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  forex: { htf_bias: "buy", session: "London Kill Zone", scenario_state: "NO_CONTEXT" },
});
const waitingForSession = buildGbpDecision({
  direction: null, stage: "NO_CONTEXT", status: "WAITING FOR SESSION", setupId: null,
  overlays: [currentPriceOverlay()],
  forex: { htf_bias: "neutral", session: "Outside Trading Hours", scenario_state: "NO_CONTEXT" },
});
const waitingForSweep = buildGbpDecision({
  direction: "buy", stage: "WAITING_FOR_LIQUIDITY", status: "BUY SETUP DEVELOPING", setupId: "gbp-sweep",
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  forex: { htf_bias: "buy", session: "London Kill Zone", scenario_state: "WAITING_FOR_LIQUIDITY" },
});
const waitingForDisplacement = buildGbpDecision({
  direction: "buy", stage: "WAITING_FOR_DISPLACEMENT", status: "BUY SETUP DEVELOPING", setupId: "gbp-disp",
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  forex: { htf_bias: "buy", session: "London Kill Zone", liquidity_event: { direction: "buy", sweep_price: 1.261 }, scenario_state: "WAITING_FOR_DISPLACEMENT" },
});
const waitingForStructureConfirmation = buildGbpDecision({
  direction: "buy", stage: "MSS_CONFIRMED", status: "BUY SETUP DEVELOPING", setupId: "gbp-mss",
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  forex: { htf_bias: "buy", session: "London Kill Zone", liquidity_event: { direction: "buy", sweep_price: 1.261 }, displacement: { confirmed: true }, scenario_state: "MSS_CONFIRMED" },
});
const waitingForRetrace = buildGbpDecision({
  direction: "buy", stage: "WAITING_FOR_RETRACE", status: "BUY SETUP DEVELOPING", setupId: "gbp-retrace",
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  forex: { htf_bias: "buy", session: "London Kill Zone", liquidity_event: { direction: "buy", sweep_price: 1.261 }, displacement: { confirmed: true }, structure_confirmation: { close_confirmed: true }, scenario_state: "WAITING_FOR_RETRACE" },
});
const planValidation = buildGbpDecision({
  direction: "buy", stage: "WAITING_FOR_M5_CONFIRMATION", status: "PLAN VALIDATION", setupId: "gbp-plan",
  overlays: [currentPriceOverlay(), ...structureOverlays()],
  forex: { htf_bias: "buy", session: "London Kill Zone", dealing_range: { premium_discount_state: "discount", current_position_pct: 28 }, scenario_state: "WAITING_FOR_M5_CONFIRMATION" },
});
const tradeReadyBuy = buildGbpDecision({
  direction: "buy", stage: "TRADE_READY", status: "READY TO BUY", setupId: "gbp-ready-buy", tradeReady: true,
  entry: 1.271, stop: 1.267, targets: [{ name: "TP1", price: 1.28, risk_reward: 2.25 }, { name: "TP2", price: 1.284, risk_reward: 3.25 }],
  overlays: [currentPriceOverlay(), ...structureOverlays(), ...actionableOverlays("gbp-ready-buy", 1.271, 1.267, 1.28, 1.284)],
  forex: { htf_bias: "buy", session: "London Kill Zone", dealing_range: { premium_discount_state: "discount", current_position_pct: 28 }, liquidity_event: { direction: "buy", sweep_price: 1.261 }, displacement: { confirmed: true }, structure_confirmation: { close_confirmed: true }, scenario_state: "TRADE_READY" },
});
const tradeReadySell = buildGbpDecision({
  direction: "sell", stage: "TRADE_READY", status: "READY TO SELL", setupId: "gbp-ready-sell", tradeReady: true,
  entry: 1.271, stop: 1.275, targets: [{ name: "TP1", price: 1.262, risk_reward: 2.25 }, { name: "TP2", price: 1.258, risk_reward: 3.25 }],
  overlays: [currentPriceOverlay(), ...structureOverlays(), ...actionableOverlays("gbp-ready-sell", 1.271, 1.275, 1.262, 1.258)],
  forex: { htf_bias: "sell", session: "New York Kill Zone", dealing_range: { premium_discount_state: "premium", current_position_pct: 74 }, liquidity_event: { direction: "sell", sweep_price: 1.281 }, displacement: { confirmed: true }, structure_confirmation: { close_confirmed: true }, scenario_state: "TRADE_READY" },
});
const tooLate = buildGbpDecision({
  direction: null, stage: "NO_CONTEXT", status: "TOO LATE", setupId: null,
  overlays: [currentPriceOverlay()],
  previousSetup: { setup_id: "gbp-too-late-1", terminal_status: "TOO_LATE", terminal_reason: "Price moved too far beyond the confirmed entry to chase." },
});
const expired = buildGbpDecision({
  direction: null, stage: "NO_CONTEXT", status: "SETUP EXPIRED", setupId: null,
  overlays: [currentPriceOverlay()],
  previousSetup: { setup_id: "gbp-expired-1", terminal_status: "EXPIRED", terminal_reason: "The entry array was excessively mitigated." },
});
const invalidated = buildGbpDecision({
  direction: null, stage: "NO_CONTEXT", status: "SETUP INVALIDATED", setupId: null,
  overlays: [currentPriceOverlay()],
  previousSetup: { setup_id: "gbp-invalidated-1", terminal_status: "INVALIDATED", terminal_reason: "Price closed beyond the sweep extreme before entry." },
});
const stateContradiction: NormalizedDecision = {
  ...buildGbpDecision({ direction: null, stage: "NO_CONTEXT", status: "STATE CONTRADICTION", setupId: null, overlays: [currentPriceOverlay()] }),
  decision: { status: "STATE CONTRADICTION", direction: null, stage: "STATE_CONTRADICTION", headline: "STATE CONTRADICTION", summary: "Conflicting lifecycle or ownership fields were blocked.", next_action: "Do not act. Wait for a new coherent decision.", trade_ready: false },
};
const staleData: NormalizedDecision = {
  ...buildGbpDecision({ direction: "buy", stage: "WAITING_FOR_DISPLACEMENT", status: "BUY SETUP DEVELOPING", setupId: "gbp-stale", overlays: [currentPriceOverlay(), ...structureOverlays()] }),
  readiness: { state: "stale", last_successful_update: "2026-07-20T07:40:00Z" } as any,
};

function renderGbpWorkspace(
  decision: NormalizedDecision,
  storeOverrides: Partial<Parameters<typeof useTerminalStore.setState>[0]> = {},
  width = 1440,
  height = 900,
) {
  useTerminalStore.setState({
    symbol: GBPUSD,
    timeframe: "M5",
    marketSource: "twelve_data",
    marketType: "forex",
    marketSchedule: "24_5",
    workspaceMode: "historical",
    historicalCandles: candles(),
    historicalJobId: "gbp-story-job",
    decision,
    overlayOwner: OWNER,
    connection: "connected",
    dataReadiness: "ready",
    densityMode: "clean",
    diagnosticsVisible: false,
    markets: [],
    watchlist: [],
    overlayVisibility: { trade_plan: true, market_structure: true, context_levels: true, advanced_smc: false, previous_setup: false },
    ...storeOverrides,
  } as any);
  const client = new QueryClient();
  return (
    <QueryClientProvider client={client}>
      <div style={{ width, height }} className="border border-white/10">
        <WorkspacePage />
      </div>
    </QueryClientProvider>
  );
}

const meta: Meta = {
  title: "Workspace/GBPUSD",
  parameters: { layout: "fullscreen", backgrounds: { default: "terminal", values: [{ name: "terminal", value: "#07090d" }] } },
};
export default meta;
type Story = StoryObj;

export const MarketClosed: Story = { render: () => renderGbpWorkspace(marketClosed) };
export const MarketContext: Story = { render: () => renderGbpWorkspace(marketContext) };
export const WaitingForSession: Story = { render: () => renderGbpWorkspace(waitingForSession) };
export const WaitingForLiquiditySweep: Story = { render: () => renderGbpWorkspace(waitingForSweep) };
export const WaitingForDisplacement: Story = { render: () => renderGbpWorkspace(waitingForDisplacement) };
export const WaitingForStructureConfirmation: Story = { render: () => renderGbpWorkspace(waitingForStructureConfirmation) };
export const WaitingForRetrace: Story = { render: () => renderGbpWorkspace(waitingForRetrace) };
export const PlanValidation: Story = { render: () => renderGbpWorkspace(planValidation) };
export const TradeReadyBuy: Story = { render: () => renderGbpWorkspace(tradeReadyBuy) };
export const TradeReadySell: Story = { render: () => renderGbpWorkspace(tradeReadySell) };
export const TooLate: Story = { render: () => renderGbpWorkspace(tooLate) };
export const Expired: Story = { render: () => renderGbpWorkspace(expired) };
export const Invalidated: Story = { render: () => renderGbpWorkspace(invalidated) };
export const StateContradiction: Story = { render: () => renderGbpWorkspace(stateContradiction) };
export const StaleProviderData: Story = { render: () => renderGbpWorkspace(staleData) };
export const ReplayMode: Story = { render: () => renderGbpWorkspace(tradeReadySell, { workspaceMode: "replay" }) };
export const HistoricalMode: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, { workspaceMode: "historical" }) };
export const StandardDensity: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, { densityMode: "standard" }) };
export const ResearchDensity: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, { densityMode: "research", overlayVisibility: { trade_plan: true, market_structure: true, context_levels: true, advanced_smc: true, previous_setup: false } }) };

// --- 5-resolution sweep (Phase 4 §24), one representative state per direction ---

const RESOLUTIONS: Array<[string, number, number]> = [
  ["1920x1080", 1920, 1080], ["1536x864", 1536, 864], ["1440x900", 1440, 900], ["1280x800", 1280, 800], ["1024x768", 1024, 768],
];
export const TradeReadyBuy_1920x1080: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, {}, RESOLUTIONS[0][1], RESOLUTIONS[0][2]) };
export const TradeReadyBuy_1536x864: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, {}, RESOLUTIONS[1][1], RESOLUTIONS[1][2]) };
export const TradeReadyBuy_1440x900: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, {}, RESOLUTIONS[2][1], RESOLUTIONS[2][2]) };
export const TradeReadyBuy_1280x800: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, {}, RESOLUTIONS[3][1], RESOLUTIONS[3][2]) };
export const TradeReadyBuy_1024x768: Story = { render: () => renderGbpWorkspace(tradeReadyBuy, {}, RESOLUTIONS[4][1], RESOLUTIONS[4][2]) };
export const TradeReadySell_1920x1080: Story = { render: () => renderGbpWorkspace(tradeReadySell, {}, RESOLUTIONS[0][1], RESOLUTIONS[0][2]) };
export const TradeReadySell_1536x864: Story = { render: () => renderGbpWorkspace(tradeReadySell, {}, RESOLUTIONS[1][1], RESOLUTIONS[1][2]) };
export const TradeReadySell_1440x900: Story = { render: () => renderGbpWorkspace(tradeReadySell, {}, RESOLUTIONS[2][1], RESOLUTIONS[2][2]) };
export const TradeReadySell_1280x800: Story = { render: () => renderGbpWorkspace(tradeReadySell, {}, RESOLUTIONS[3][1], RESOLUTIONS[3][2]) };
export const TradeReadySell_1024x768: Story = { render: () => renderGbpWorkspace(tradeReadySell, {}, RESOLUTIONS[4][1], RESOLUTIONS[4][2]) };

// --- GBP/USD <-> R_75 switching capture (Phase 4 §19/§24) ---

export const SwitchToR75AfterGbpTradeReady: Story = {
  render: () => renderGbpWorkspace(
    {
      ...tradeReadySell,
      decision_id: "r75-after-switch",
      meta: { symbol: R75.provider_symbol, display_symbol: R75.display_name, timeframe: "M5", analysis_time: "2026-07-20T08:00:00Z", live: false, market_schedule: "24_7", analysis_clock: "UTC", market_source: R75.market_source, market_type: R75.market_type },
      forex: undefined,
      market: { external_structure: "bearish", internal_structure: "pullback", current_price: 51500 },
    } as NormalizedDecision,
    { symbol: R75, marketSource: "deriv", marketType: "derived", marketSchedule: "24_7", overlayOwner: "volatility_structure_pullback" },
  ),
};
