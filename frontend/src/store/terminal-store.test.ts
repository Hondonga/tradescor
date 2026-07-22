import { beforeEach, describe, expect, it } from "vitest";
import { useTerminalStore } from "./terminal-store";
import type { NormalizedDecision, SymbolInfo } from "@/types";

const symbol: SymbolInfo = {
  symbol_id: "deriv:R_100",
  provider_symbol: "R_100",
  display_name: "Volatility 100 Index",
  family: "VOLATILITY",
  market_source: "deriv",
  market_type: "derived",
  market_schedule: "24_7",
  analysis_engine: "derived_smc",
  supported: true,
  available_models: [
    { id: "auto", label: "SMC Auto" },
    { id: "volatility_smc", label: "Volatility SMC" },
  ],
};
const decision = {
  decision_id: "decision-1",
  overlay_mode: "LIVE",
  precision: {
    symbol_id: "deriv:R_100",
    price_decimals: 2,
    pip_size: null,
    tick_size: 0.01,
    quantity_decimals: null,
  },
  meta: {
    symbol: "R_100",
    display_symbol: "Volatility 100 Index",
    timeframe: "M5",
    analysis_time: "2026-07-19T12:00:00Z",
    live: true,
    market_schedule: "24/7",
    analysis_clock: "UTC",
  },
  ownership: {
    selected_model_id: "smc",
    requested_model_id: "auto",
    decision_owner_id: "decision-1",
    overlay_owner_id: "decision-1",
  },
  readiness: { state: "ready" },
  market: { current_price: 100 },
  decision: {
    status: "READY TO SELL",
    direction: "sell",
    stage: "confirmed",
    headline: "Ready",
    summary: "Validated",
    next_action: "Paper test",
    trade_ready: true,
  },
  setup: {
    stage: "confirmed",
    status: "ready",
    context_summary: "Bearish",
    next_required_condition: "none",
    trade_ready: true,
    targets: [],
    quality_score: 90,
    quality_grade: "A",
  },
  diagnostics: {},
  overlays: [],
} satisfies NormalizedDecision;

describe("terminal decision ownership", () => {
  beforeEach(() => {
    useTerminalStore.setState({
      decision: undefined,
      analysisRequestId: undefined,
      overlayOwner: undefined,
      dataReadiness: "idle",
      connection: "disconnected",
      timeframe: "M5",
      workspaceMode: "live",
      historicalCandles: [],
      liveDecision: undefined,
    });
  });
  it("never presents a live refresh as part of historical inspection", () => {
    const historical={...decision,decision_id:"historical-1",overlay_mode:"HISTORICAL_INSPECTION" as const};
    const live={...decision,decision_id:"live-2"};
    useTerminalStore.getState().setSymbol(symbol);
    useTerminalStore.getState().showHistorical("job-1",historical,[{time:"2026-07-19T12:00:00Z",open:100,high:101,low:99,close:100}]);
    const inspectionReadiness = useTerminalStore.getState().dataReadiness;
    useTerminalStore.getState().beginAnalysis("live-request");
    expect(useTerminalStore.getState().dataReadiness).toBe(inspectionReadiness);
    expect(useTerminalStore.getState().acceptDecision("live-request",live)).toBe(true);
    expect(useTerminalStore.getState().decision?.decision_id).toBe("historical-1");
    expect(useTerminalStore.getState().overlayOwner).toBe(
      historical.ownership.decision_owner_id,
    );
    useTerminalStore.getState().returnLive();
    expect(useTerminalStore.getState().decision?.decision_id).toBe("live-2");
    expect(useTerminalStore.getState().historicalCandles).toEqual([]);
  });
  it("keeps a scanned decision when opening its workspace", () => {
    useTerminalStore.getState().selectMarket({ symbol, decision });
    const state = useTerminalStore.getState();
    expect(state.symbol).toEqual(symbol);
    expect(state.decision?.decision_id).toBe("decision-1");
    expect(state.overlayOwner).toBe("decision-1");
  });

  it("rejects a stale asynchronous response", () => {
    const store = useTerminalStore.getState();
    store.setSymbol(symbol);
    store.beginAnalysis("new-request");
    expect(store.acceptDecision("old-request", decision)).toBe(false);
    expect(useTerminalStore.getState().decision).toBeUndefined();
  });

  it("clears ownership when the symbol context changes", () => {
    useTerminalStore.getState().selectMarket({ symbol, decision });
    useTerminalStore.getState().setSymbol({
      symbol_id: "deriv:JD75",
      provider_symbol: "JD75",
      display_name: "Jump 75 Index",
      family: "JUMP",
      market_source: "deriv",
      market_type: "derived",
      market_schedule: "24_7",
      analysis_engine: "derived_smc",
      supported: true,
      available_models: [{ id: "auto", label: "SMC Auto" }],
    });
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().overlayOwner).toBeUndefined();
  });

  it("switches providers and clears incompatible ownership atomically", () => {
    useTerminalStore.getState().selectMarket({ symbol, decision });
    useTerminalStore.getState().setSymbol({
      symbol_id: "twelve_data:EUR/USD",
      provider_symbol: "EUR/USD",
      display_name: "EUR/USD",
      family: "FOREX",
      market_source: "twelve_data",
      market_type: "forex",
      market_schedule: "24_5",
      analysis_engine: "forex_strategy",
      supported: true,
      available_models: [
        { id: "auto", label: "Structure Context" },
        { id: "ict_2022", label: "ICT Precision" },
      ],
    });
    const state = useTerminalStore.getState();
    expect(state.marketSource).toBe("twelve_data");
    expect(state.marketSchedule).toBe("24_5");
    expect(state.analysisEngine).toBe("forex_strategy");
    expect(state.availableModels.map((item) => item.id)).not.toContain(
      "volatility_smc",
    );
    expect(state.decision).toBeUndefined();
    expect(state.overlayOwner).toBeUndefined();
  });

  it("cannot apply a Forex response after switching back to Derived", () => {
    const forex = {
      ...symbol,
      symbol_id: "twelve_data:EUR/USD",
      provider_symbol: "EUR/USD",
      display_name: "EUR/USD",
      family: "FOREX",
      market_source: "twelve_data",
      market_type: "forex" as const,
      market_schedule: "24_5" as const,
      analysis_engine: "forex_strategy",
      available_models: [{ id: "auto", label: "Structure Context" }],
    };
    const forexDecision = {
      ...decision,
      meta: { ...decision.meta, symbol: "EUR/USD", market_source: "twelve_data", market_type: "forex" },
      market: { ...decision.market, session: "London" },
    } satisfies NormalizedDecision;
    const store = useTerminalStore.getState();
    store.setSymbol(forex);
    store.beginAnalysis("forex-request");
    store.setSymbol(symbol);
    expect(store.acceptDecision("forex-request", forexDecision)).toBe(false);
    const state = useTerminalStore.getState();
    expect(state.marketSource).toBe("deriv");
    expect(state.marketSchedule).toBe("24_7");
    expect(state.decision?.market.session).toBeUndefined();
  });

  it("corrects an incompatible family model and clears overlays", () => {
    useTerminalStore.setState({ model: "step_smc", decision, overlayOwner: "decision-1" });
    useTerminalStore.getState().setSymbol({
      ...symbol,
      symbol_id: "deriv:CRASH50",
      provider_symbol: "CRASH50",
      display_name: "Crash 50 Index",
      family: "CRASH",
      default_model: "boom_crash_spike_state",
      available_models: [
        { id: "auto", label: "SMC Auto" },
        { id: "boom_crash_spike_state", label: "Boom/Crash Spike-State" },
      ],
    });
    const state = useTerminalStore.getState();
    expect(state.model).toBe("boom_crash_spike_state");
    expect(state.modelNotice).toContain("does not support Step SMC");
    expect(state.decision).toBeUndefined();
    expect(state.overlayOwner).toBeUndefined();
  });

  it("cannot resurrect a prior live decision after timeframe or model changes", () => {
    useTerminalStore.getState().selectMarket({ symbol, decision });
    useTerminalStore.getState().setTimeframe("M15");
    useTerminalStore.getState().returnLive();
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().liveDecision).toBeUndefined();

    useTerminalStore.getState().setTimeframe("M5");
    useTerminalStore.getState().selectMarket({ symbol, decision });
    useTerminalStore.getState().setModel("volatility_smc");
    useTerminalStore.getState().returnLive();
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().overlayOwner).toBeUndefined();
  });

  it("rejects an older analysis timestamp even with the current request ID", () => {
    useTerminalStore.getState().selectMarket({ symbol, decision });
    useTerminalStore.getState().beginAnalysis("refresh");
    const older = {
      ...decision,
      decision_id: "older",
      meta: { ...decision.meta, analysis_time: "2026-07-19T11:55:00Z" },
    } satisfies NormalizedDecision;
    expect(
      useTerminalStore.getState().acceptDecision("refresh", older),
    ).toBe(false);
    expect(useTerminalStore.getState().decision?.decision_id).toBe(
      "decision-1",
    );
    expect(useTerminalStore.getState().analysisRequestId).toBeUndefined();
  });

  it("isolates replay drawings and clears them when returning live", () => {
    useTerminalStore.getState().selectMarket({ symbol, decision });
    const replay = {
      ...decision,
      decision_id: "replay-1",
      overlay_mode: "REPLAY" as const,
    };
    useTerminalStore
      .getState()
      .showReplay(replay, [
        { time: "2026-07-19T11:00:00Z", open: 99, high: 101, low: 98, close: 100 },
      ]);
    expect(useTerminalStore.getState().workspaceMode).toBe("replay");
    expect(useTerminalStore.getState().decision?.decision_id).toBe("replay-1");
    useTerminalStore.getState().returnLive();
    expect(useTerminalStore.getState().workspaceMode).toBe("live");
    expect(useTerminalStore.getState().decision?.decision_id).toBe("decision-1");
    expect(useTerminalStore.getState().historicalCandles).toEqual([]);
  });

  it("refuses an inspection decision tagged for a different overlay mode", () => {
    useTerminalStore.getState().selectMarket({ symbol, decision });
    useTerminalStore
      .getState()
      .showHistorical("job", decision, [
        { time: 1, open: 1, high: 1, low: 1, close: 1 },
      ]);
    expect(useTerminalStore.getState().workspaceMode).toBe("live");
    expect(useTerminalStore.getState().decision?.decision_id).toBe("decision-1");
  });

  it("leaves no stale state after rapid R_75 M5 -> other symbol -> R_75 M15 -> R_75 M5 switching (Phase 2 checkpoint 10)", () => {
    const r75: SymbolInfo = { ...symbol, symbol_id: "deriv:R_75", provider_symbol: "R_75", display_name: "Volatility 75 Index" };
    const r75Decision = {
      ...decision,
      decision_id: "r75-m5-1",
      precision: { ...decision.precision, symbol_id: "deriv:R_75" },
      meta: { ...decision.meta, symbol: "R_75", timeframe: "M5" },
    } satisfies NormalizedDecision;
    const other: SymbolInfo = { ...symbol, symbol_id: "deriv:R_50", provider_symbol: "R_50", display_name: "Volatility 50 Index" };

    // R_75 M5 with a live decision, candles, and an owner.
    useTerminalStore.setState({ model: "auto" }); // avoid leaking `model` from an earlier test in this file
    useTerminalStore.getState().selectMarket({ symbol: r75, decision: r75Decision });
    useTerminalStore.setState({ historicalCandles: [{ time: "2026-07-19T12:00:00Z", open: 1, high: 1, low: 1, close: 1 }] });
    expect(useTerminalStore.getState().decision?.decision_id).toBe("r75-m5-1");

    // -> another symbol: R_75 decision/candles/owner must not survive.
    useTerminalStore.getState().setSymbol(other);
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().overlayOwner).toBeUndefined();
    expect(useTerminalStore.getState().historicalCandles).toEqual([]);

    // -> back to R_75, but M15: still no stale decision from the earlier M5 session.
    useTerminalStore.getState().setSymbol(r75);
    useTerminalStore.getState().setTimeframe("M15");
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().timeframe).toBe("M15");

    // -> back to R_75 M5: a stale M15-tagged response must not be accepted as current.
    useTerminalStore.getState().setTimeframe("M5");
    useTerminalStore.getState().beginAnalysis("late-m15");
    const staleM15Decision = { ...r75Decision, decision_id: "stale-m15", meta: { ...r75Decision.meta, timeframe: "M15" } } satisfies NormalizedDecision;
    expect(useTerminalStore.getState().acceptDecision("late-m15", staleM15Decision)).toBe(false);
    expect(useTerminalStore.getState().decision).toBeUndefined();

    // A correctly-tagged fresh R_75 M5 response is still accepted normally.
    useTerminalStore.getState().beginAnalysis("fresh-m5");
    const freshDecision = { ...r75Decision, decision_id: "fresh-m5-1" } satisfies NormalizedDecision;
    expect(useTerminalStore.getState().acceptDecision("fresh-m5", freshDecision)).toBe(true);
    expect(useTerminalStore.getState().decision?.decision_id).toBe("fresh-m5-1");
  });

  it("leaves no stale state and rejects late responses across GBP/USD M5 -> GBP/USD M15 -> R_75 M5 -> GBP/USD M5 (Phase 4 checkpoint 19)", () => {
    const gbpusd: SymbolInfo = {
      ...symbol,
      symbol_id: "twelve_data:GBP/USD",
      provider_symbol: "GBP/USD",
      display_name: "GBP/USD",
      family: "FOREX",
      market_source: "twelve_data",
      market_type: "forex",
      market_schedule: "24_5",
      analysis_engine: "forex_strategy",
      available_models: [{ id: "auto", label: "Forex ICT" }],
    };
    const r75: SymbolInfo = { ...symbol, symbol_id: "deriv:R_75", provider_symbol: "R_75", display_name: "Volatility 75 Index" };
    const gbpM5 = {
      ...decision,
      decision_id: "gbpusd-m5-1",
      precision: { ...decision.precision, symbol_id: "twelve_data:GBP/USD" },
      meta: { ...decision.meta, symbol: "GBP/USD", timeframe: "M5", market_source: "twelve_data", market_type: "forex" },
      market: { ...decision.market, session: "London Kill Zone" },
    } satisfies NormalizedDecision;

    useTerminalStore.setState({ model: "auto" });
    useTerminalStore.getState().selectMarket({ symbol: gbpusd, decision: gbpM5 });
    expect(useTerminalStore.getState().decision?.decision_id).toBe("gbpusd-m5-1");
    expect(useTerminalStore.getState().marketSource).toBe("twelve_data");

    // -> GBP/USD M15: the M5 decision must not survive the timeframe switch,
    // and a late-arriving M5-tagged response (from before the switch) must
    // be rejected, not silently applied to the M15 view.
    useTerminalStore.getState().beginAnalysis("late-gbp-m5");
    useTerminalStore.getState().setTimeframe("M15");
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().acceptDecision("late-gbp-m5", gbpM5)).toBe(false);
    expect(useTerminalStore.getState().decision).toBeUndefined();

    // -> R_75 M5 (provider switch: Twelve Data -> Deriv). No Forex state,
    // owner, or session data may leak into the Deriv workspace.
    useTerminalStore.getState().setSymbol(r75);
    useTerminalStore.getState().setTimeframe("M5");
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().marketSource).toBe("deriv");
    expect(useTerminalStore.getState().marketSchedule).toBe("24_7");
    const r75Decision = {
      ...decision,
      decision_id: "r75-m5-1",
      precision: { ...decision.precision, symbol_id: "deriv:R_75" },
      meta: { ...decision.meta, symbol: "R_75", timeframe: "M5", market_source: "deriv", market_type: "derived" },
    } satisfies NormalizedDecision;
    useTerminalStore.getState().beginAnalysis("r75-request");
    expect(useTerminalStore.getState().acceptDecision("r75-request", r75Decision)).toBe(true);
    expect(useTerminalStore.getState().decision?.market.session).toBeUndefined();

    // -> back to GBP/USD M5 (provider switch: Deriv -> Twelve Data). The
    // R_75 decision/owner must not survive, and a late Deriv response tagged
    // for R_75 must be rejected once we are back on Forex.
    useTerminalStore.getState().beginAnalysis("late-r75");
    useTerminalStore.getState().setSymbol(gbpusd);
    expect(useTerminalStore.getState().decision).toBeUndefined();
    expect(useTerminalStore.getState().marketSource).toBe("twelve_data");
    expect(useTerminalStore.getState().acceptDecision("late-r75", r75Decision)).toBe(false);
    expect(useTerminalStore.getState().decision).toBeUndefined();

    // A correctly-tagged fresh GBP/USD M5 response is still accepted normally.
    useTerminalStore.getState().beginAnalysis("fresh-gbp-m5");
    const freshGbp = { ...gbpM5, decision_id: "gbpusd-m5-2" } satisfies NormalizedDecision;
    expect(useTerminalStore.getState().acceptDecision("fresh-gbp-m5", freshGbp)).toBe(true);
    expect(useTerminalStore.getState().decision?.decision_id).toBe("gbpusd-m5-2");
    expect(useTerminalStore.getState().decision?.market.session).toBe("London Kill Zone");
  });
});
