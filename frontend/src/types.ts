export type RouteId = "markets" | "workspace" | "research";
export type OverlayCategory =
  | "trade_plan"
  | "market_structure"
  | "context_levels"
  | "advanced_smc"
  | "previous_setup";
export type OverlayDataCategory =
  | "context"
  | "developing"
  | "actionable"
  | "historical";
export type OverlayMode =
  | "LIVE"
  | "HISTORICAL_INSPECTION"
  | "REPLAY"
  | "PREVIOUS_SETUP";
export type WorkspaceMode = "live" | "historical" | "replay";
export interface InstrumentPrecision {
  symbol_id: string;
  price_decimals: number;
  pip_size: number | null;
  tick_size: number | null;
  quantity_decimals: number | null;
}
export interface SymbolInfo {
  symbol_id: string;
  provider_symbol: string;
  display_name: string;
  family: string;
  family_display?: string;
  variant?: string;
  market_source?: string;
  market_type: "derived" | "forex" | "crypto" | "index";
  market_schedule: "24_7" | "24_5" | "exchange";
  analysis_engine: string;
  supported: boolean;
  available_models: Array<{ id: string; label: string }>;
  default_model?: string;
  auto_adapter?: string;
  production_supported?: boolean;
  research_supported?: boolean;
  cached_analysis?: {
    decision?: NormalizedDecision;
    analysis_depth?: "lightweight" | "full";
    last_analysis?: string;
    data_freshness?: string;
  };
  market?: string;
  submarket?: string;
  pip_size?: number;
  tick_size?: number;
  price_decimals?: number;
  quantity_decimals?: number;
  precision?: InstrumentPrecision;
  market_open?: boolean;
  smc_adapter?: string;
  analysis_supported?: boolean;
  analysis_support_status?: string;
}
export interface Overlay {
  overlay_id: string;
  decision_owner_id: string;
  strategy_id: string;
  setup_id: string | null;
  symbol_id: string;
  provider_symbol: string;
  market_type: string;
  timeframe: string;
  category: OverlayDataCategory;
  type: string;
  label: string;
  source: string;
  price: number | null;
  low: number | null;
  high: number | null;
  start_time: string | null;
  end_time: string | null;
  created_at: string | null;
  confirmed_at: string | null;
  expires_at: string | null;
  invalidated_at: string | null;
  active: boolean;
  historical: boolean;
  actionable: boolean;
  priority: number;
  display_group: string;
  metadata: Record<string, unknown>;
}
export interface HistoricalCandle { time: string | number; open: number; high: number; low: number; close: number }
export interface HistoricalSearchProgress { job_id: string; symbol: string; strategy: string; period_days: number; processed_candles: number; total_candles: number; trade_ready_found: number; state: "queued"|"running"|"completed"|"cancelled"|"error"; error?: string; result_available?: boolean }
export interface HistoricalInspection { mode: "historical"; label: string; decision?: NormalizedDecision; candles: HistoricalCandle[]; report: Record<string, unknown> }
export interface NormalizedDecision {
  decision_id: string;
  overlay_mode: OverlayMode;
  precision: InstrumentPrecision;
  meta: {
    symbol: string;
    display_symbol: string;
    timeframe: string;
    family?: string;
    variant?: string;
    analysis_time: string;
    live: boolean;
    market_schedule: string;
    analysis_clock: string;
    emitted_time?: string;
    source_timeframe?: string;
    market_source?: string;
    market_type?: string;
  };
  ownership: {
    selected_model_id: string;
    selected_strategy_id?: string;
    requested_model_id?: string;
    decision_owner_id: string;
    overlay_owner_id: string;
    model_corrected?: boolean;
    model_correction_reason?: string;
  };
  readiness: {
    state: string;
    last_successful_update?: string | number | null;
    analysis_paused?: boolean;
    timeframes?: Record<
      string,
      {
        available: number;
        required: number;
        passed: boolean;
        last_completed_time?: string | null;
      }
    >;
  };
  market: {
    external_structure?: string;
    internal_structure?: string;
    current_price?: number;
    event_state?: string;
    session?: string;
  };
  // Forex-only ICT context (analysis/forex_decision_normalizer.py); absent
  // for other market families.
  forex?: {
    htf_bias?: string;
    market_structure?: string;
    session?: string;
    liquidity_event?: { direction?: string; liquidity_price?: number; sweep_price?: number; confirmed_at?: string | null } | null;
    displacement?: { direction?: string; confirmed?: boolean; structure_effect?: string } | null;
    structure_confirmation?: { close_confirmed?: boolean; level?: number; break_time?: string | null } | null;
    dealing_range?: { premium_discount_state?: string; current_position_pct?: number; range_high?: number; range_low?: number; equilibrium?: number; source_timeframe?: string } | null;
    scenario_state?: string;
  };
  analysis_depth?: "lightweight" | "full";
  market_analysis?: {
    available: boolean;
    regime?: string;
    external_structure?: string;
    internal_structure?: string;
    directional_bias?: string | null;
    recent_bos?: unknown;
    recent_mss?: unknown;
    recent_sweep?: unknown;
    price_location?: string;
    developing_scenario?: string;
    invalidation?: string;
    next_confirmation?: string;
    setup_blocker?: string;
    recent_event?: {
      status?: string;
      event_id?: string;
      event_time?: string;
      completed_direction?: string;
      future_direction?: string | null;
    };
    confirmation_levels?: {
      bullish?: string;
      bearish?: string;
    };
    continuation_context?: "bearish_pullback";
    external_structure_display?: string;
    internal_structure_display?: string;
  };
  trade_plan?: {
    available: boolean;
    status: string;
    entry?: number | null;
    stop?: number | null;
    targets: Array<{ name: string; price: number; risk_reward?: number }>;
    reason?: string | null;
    confirmation_present?: boolean;
    entry_geometry_valid?: boolean;
    target_candidates_checked?: unknown[];
    target_rejections?: unknown[];
    entry_zone?: { low: number; high: number } | null;
    invalidation?: number | null;
  };
  decision: {
    status: string;
    direction?: "buy" | "sell" | null;
    setup_type?: string;
    stage: string;
    headline: string;
    summary: string;
    next_action: string;
    first_blocking_gate?: string;
    first_blocking_code?: string;
    trade_ready: boolean;
  };
  setup: {
    setup_id?: string;
    setup_type?: string;
    direction?: string;
    stage: string;
    status: string;
    context_summary: string;
    next_required_condition: string;
    first_blocking_gate?: string;
    trade_ready: boolean;
    entry?: number | null;
    stop?: number | null;
    targets: Array<{
      name: string;
      price: number;
      risk_reward?: number;
      source?: string;
      timeframe?: string;
    }>;
    rr?: number | null;
    invalidation?: { price?: number; condition: string };
    entry_area?: { low: number; high: number; type: string };
    market_quality_score?: number | null;
    setup_quality_score?: number | null;
    quality_score: number | null;
    quality_grade: string | null;
    research_only?: boolean;
    jump_mode?: string;
    setup_blocker?: string;
    plan_blocker?: string;
    recent_event?: unknown;
    confirmation_levels?: unknown;
    target_scope?: string;
    target_timeframe?: string;
    target_source?: string;
    m5_confirmation_status?: string;
    completed_confirmation?: unknown;
  };
  diagnostics: {
    gate_funnel?: unknown;
    invariants?: {
      valid: boolean;
      violations?: Array<{ code: string; message: string }>;
    };
    target_trace?: unknown;
    target_source_audit?: unknown;
    history_depth_audit?: unknown;
    shadow_candidate?: unknown;
  };
  overlays: Overlay[];
  current_market?: Record<string, unknown>;
  active_setup?: ({ setup_id: string; lifecycle?: string; state?: string } & Record<string, unknown>) | null;
  previous_setup?: unknown;
}
export interface AnalyzePayload {
  decision?: NormalizedDecision;
  candles?: Array<{
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
  }>;
  error?: string;
}
export interface MarketRow {
  symbol: SymbolInfo;
  decision?: NormalizedDecision;
  price?: number;
  lastAnalysis?: string;
  error?: string;
  watching?: boolean;
  analysisDepth?: "Lightweight" | "Full";
  lastFullAnalysis?: string;
  dataFreshness?: string;
}
