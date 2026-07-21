import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  MarketRow,
  HistoricalCandle,
  HistoricalSearchProgress,
  NormalizedDecision,
  OverlayCategory,
  RouteId,
  SymbolInfo,
  WorkspaceMode,
} from "@/types";
import { decisionMatchesWorkspace } from "@/lib/overlays";
import type { DensityMode } from "@/lib/overlay-density";

const defaultSymbol: SymbolInfo = {
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
  available_models: [{ id: "auto", label: "SMC Auto" }, { id: "volatility_smc", label: "Volatility SMC" }],
};
interface TerminalState {
  route: RouteId;
  marketSource: string;
  marketType: SymbolInfo["market_type"];
  marketSchedule: SymbolInfo["market_schedule"];
  providerSymbol: string;
  analysisEngine: string;
  availableModels: SymbolInfo["available_models"];
  modelNotice?: string;
  providerStates: Record<string, { state: string; last_update?: string | null }>;
  symbol: SymbolInfo;
  timeframe: string;
  model: string;
  connection:
    | "disconnected"
    | "connecting"
    | "connected"
    | "stale"
    | "reconnecting"
    | "rate_limited"
    | "provider_error";
  dataReadiness: string;
  lastCompletedCandle?: string;
  decision?: NormalizedDecision;
  liveDecision?: NormalizedDecision;
  workspaceMode: WorkspaceMode;
  historicalCandles: HistoricalCandle[];
  historicalJobId?: string;
  historicalOutcome?: unknown;
  historicalSearch?: HistoricalSearchProgress;
  analysisRequestId?: string;
  analysisStartedAt?: string;
  overlayOwner?: string;
  markets: MarketRow[];
  watchlist: string[];
  overlayVisibility: Record<OverlayCategory, boolean>;
  densityMode: DensityMode;
  leftPanel: number;
  rightPanel: number;
  systemMenuOpen: boolean;
  commandOpen: boolean;
  setRoute: (route: RouteId) => void;
  setSymbol: (symbol: SymbolInfo) => void;
  selectMarket: (row: MarketRow) => void;
  setTimeframe: (value: string) => void;
  setModel: (value: string) => void;
  beginAnalysis: (requestId: string) => void;
  acceptDecision: (requestId: string, decision: NormalizedDecision) => boolean;
  failAnalysis: (requestId: string) => void;
  setConnection: (value: TerminalState["connection"]) => void;
  setMarkets: (rows: MarketRow[]) => void;
  toggleWatch: (symbol: string) => void;
  toggleOverlay: (category: OverlayCategory) => void;
  setDensityMode: (mode: DensityMode) => void;
  setPanels: (left: number, right: number) => void;
  setSystemMenu: (open: boolean) => void;
  setCommandOpen: (open: boolean) => void;
  clearDecision: () => void;
  showHistorical: (jobId:string, decision:NormalizedDecision, candles:HistoricalCandle[]) => void;
  showReplay: (decision:NormalizedDecision, candles:HistoricalCandle[]) => void;
  returnLive: () => void;
  setHistoricalSearch: (progress?:HistoricalSearchProgress) => void;
  setHistoricalOutcome: (outcome:unknown) => void;
}
export const useTerminalStore = create<TerminalState>()(
  persist(
    (set, get) => ({
      route: "markets",
      marketSource: "deriv",
      marketType: "derived",
      marketSchedule: "24_7",
      providerSymbol: "R_75",
      analysisEngine: "derived_smc",
      availableModels: defaultSymbol.available_models,
      providerStates: {deriv:{state:"disconnected"},twelve_data:{state:"disconnected"}},
      symbol: defaultSymbol,
      timeframe: "M5",
      model: "auto",
      connection: "disconnected",
      workspaceMode: "live",
      historicalCandles: [],
      dataReadiness: "idle",
      markets: [],
      watchlist: ["R_50", "R_100", "JD75"],
      overlayVisibility: {
        trade_plan: true,
        market_structure: true,
        context_levels: true,
        advanced_smc: false,
        previous_setup: false,
      },
      densityMode: "clean",
      leftPanel: 18,
      rightPanel: 24,
      systemMenuOpen: false,
      commandOpen: false,
      setRoute: (route) => set({ route }),
      setSymbol: (symbol) =>
        set((state) => {
          const compatible = symbol.available_models.some((item) => item.id === state.model);
          const resolved = compatible ? state.model : symbol.default_model || symbol.available_models[0]?.id || "auto";
          return ({
          symbol,
          marketSource: symbol.market_source || "deriv",
          marketType: symbol.market_type,
          marketSchedule: symbol.market_schedule,
          providerSymbol: symbol.provider_symbol,
          analysisEngine: symbol.analysis_engine,
          availableModels: symbol.available_models,
          model: resolved,
          modelNotice: compatible ? undefined : `Model changed to ${modelLabel(symbol, resolved)} because ${symbol.display_name} does not support ${modelLabel(state.symbol, state.model)}.`,
          connection: connectionFromProvider(
            state.providerStates[symbol.market_source || "deriv"]?.state,
          ),
          decision: undefined,
          liveDecision: undefined,
          overlayOwner: undefined,
          workspaceMode: "live",
          historicalCandles: [],
          historicalJobId: undefined,
          historicalOutcome: undefined,
          dataReadiness: "idle",
          lastCompletedCandle: undefined,
          analysisRequestId: undefined,
          analysisStartedAt: undefined,
        });}),
      selectMarket: (row) => {
        const decision = row.decision;
        const compatible = Boolean(
          decision &&
            decision.overlay_mode === "LIVE" &&
            decisionMatchesWorkspace(decision, row.symbol, get().timeframe),
        );
        set({
          symbol: row.symbol,
          marketSource: row.symbol.market_source || "deriv",
          marketType: row.symbol.market_type,
          marketSchedule: row.symbol.market_schedule,
          providerSymbol: row.symbol.provider_symbol,
          analysisEngine: row.symbol.analysis_engine,
          availableModels: row.symbol.available_models,
          model: row.symbol.available_models.some((item)=>item.id===get().model) ? get().model : row.symbol.default_model || row.symbol.available_models[0]?.id || "auto",
          modelNotice: row.symbol.available_models.some((item)=>item.id===get().model) ? undefined : `Model changed to ${modelLabel(row.symbol,row.symbol.default_model || row.symbol.available_models[0]?.id || "auto")} because ${row.symbol.display_name} does not support ${modelLabel(get().symbol,get().model)}.`,
          decision: compatible ? decision : undefined,
          liveDecision: compatible ? decision : undefined,
          overlayOwner: compatible
            ? decision!.ownership.decision_owner_id
            : undefined,
          workspaceMode: "live",
          historicalCandles: [],
          historicalJobId: undefined,
          historicalOutcome: undefined,
          dataReadiness: compatible ? decision!.readiness.state : "idle",
          lastCompletedCandle: compatible
            ? decision!.meta.analysis_time
            : undefined,
          connection: compatible
            ? decision!.meta.live
              ? "connected"
              : "stale"
            : connectionFromProvider(
                get().providerStates[row.symbol.market_source || "deriv"]?.state,
              ),
          providerStates: compatible ? {...get().providerStates,[row.symbol.market_source || "deriv"]:{state:decision!.meta.live?"ready":"stale",last_update:decision!.meta.analysis_time}} : get().providerStates,
          analysisRequestId: undefined,
          analysisStartedAt: undefined,
        });
      },
      setTimeframe: (timeframe) =>
        set({
          timeframe,
          decision: undefined,
          liveDecision: undefined,
          overlayOwner: undefined,
          workspaceMode: "live",
          historicalCandles: [],
          historicalJobId: undefined,
          historicalOutcome: undefined,
          dataReadiness: "idle",
          analysisRequestId: undefined,
          analysisStartedAt: undefined,
        }),
      setModel: (model) =>
        set({
          model,
          modelNotice: undefined,
          decision: undefined,
          liveDecision: undefined,
          overlayOwner: undefined,
          workspaceMode: "live",
          historicalCandles: [],
          historicalJobId: undefined,
          historicalOutcome: undefined,
          dataReadiness: "idle",
          analysisRequestId: undefined,
          analysisStartedAt: undefined,
        }),
      beginAnalysis: (analysisRequestId) =>
        set((state) => ({
          analysisRequestId,
          analysisStartedAt: new Date().toISOString(),
          dataReadiness:
            state.workspaceMode === "live" ? "loading" : state.dataReadiness,
        })),
      acceptDecision: (requestId, decision) => {
        const state = get();
        if (state.analysisRequestId !== requestId) return false;
        const symbol = state.symbol;
        if (
          decision.overlay_mode !== "LIVE" ||
          !decisionMatchesWorkspace(decision, symbol, state.timeframe) ||
          !requestedModelMatches(decision, state.model) ||
          olderThanCurrentDecision(decision, state.liveDecision)
        ) {
          set({
            analysisRequestId: undefined,
            analysisStartedAt: undefined,
            dataReadiness:
              state.workspaceMode === "live"
                ? state.decision?.readiness.state || "idle"
                : state.dataReadiness,
          });
          return false;
        }
        const viewingLive=state.workspaceMode === "live";
        set({
          liveDecision: decision,
          decision: viewingLive ? decision : state.decision,
          overlayOwner: viewingLive
            ? decision.ownership.decision_owner_id
            : state.overlayOwner,
          dataReadiness: viewingLive
            ? decision.readiness.state
            : state.dataReadiness,
          lastCompletedCandle:
            decision.readiness.timeframes?.M5?.last_completed_time ||
            decision.meta.analysis_time,
          connection: decision.meta.live ? "connected" : "stale",
          providerStates: {...get().providerStates,[symbol.market_source || "deriv"]:{state:decision.meta.live?"ready":"stale",last_update:decision.meta.analysis_time}},
          analysisRequestId: undefined,
          analysisStartedAt: undefined,
          markets: state.markets.map((row) =>
            row.symbol.symbol_id === symbol.symbol_id
              ? { ...row, decision, price: decision.market.current_price, lastAnalysis: decision.meta.analysis_time, analysisDepth: "Full", lastFullAnalysis: decision.meta.analysis_time, dataFreshness: decision.readiness.state }
              : row,
          ),
        });
        return true;
      },
      failAnalysis: (requestId) => {
        const state = get();
        if (state.analysisRequestId === requestId)
          set(state.workspaceMode === "live" ? {
            analysisRequestId: undefined,
            analysisStartedAt: undefined,
            dataReadiness: state.decision ? "stale" : "error",
            connection: state.decision ? "stale" : "provider_error",
          } : {
            analysisRequestId: undefined,
            analysisStartedAt: undefined,
          });
      },
      setConnection: (connection) => set({ connection }),
      setMarkets: (markets) => {
        const latest = markets.find((row) => row.decision)?.decision;
        set({
          markets,
          connection: latest?.meta.live ? "connected" : get().connection,
          dataReadiness: latest ? "ready" : get().dataReadiness,
          lastCompletedCandle:
            latest?.readiness.timeframes?.M5?.last_completed_time ||
            get().lastCompletedCandle,
        });
      },
      toggleWatch: (symbol) =>
        set((state) => ({
          watchlist: state.watchlist.includes(symbol)
            ? state.watchlist.filter((x) => x !== symbol)
            : [...state.watchlist, symbol],
        })),
      toggleOverlay: (category) =>
        set((state) => {
          const next = !state.overlayVisibility[category];
          return {
            overlayVisibility: { ...state.overlayVisibility, [category]: next },
            // Turning Advanced on implies "show diagnostic-tier detail too" —
            // the same thing RESEARCH density means, so keep them in sync.
            densityMode:
              category === "advanced_smc" && next ? "research" : state.densityMode,
          };
        }),
      setDensityMode: (densityMode) => set({ densityMode }),
      setPanels: (leftPanel, rightPanel) => set({ leftPanel, rightPanel }),
      setSystemMenu: (systemMenuOpen) => set({ systemMenuOpen }),
      setCommandOpen: (commandOpen) => set({ commandOpen }),
      clearDecision: () =>
        set({
          decision: undefined,
          liveDecision: undefined,
          overlayOwner: undefined,
          historicalCandles: [],
          historicalJobId: undefined,
          historicalOutcome: undefined,
          workspaceMode: "live",
          dataReadiness: "idle",
        }),
      showHistorical: (historicalJobId,decision,historicalCandles) => {
        if (
          decision.overlay_mode !== "HISTORICAL_INSPECTION" ||
          !decisionMatchesWorkspace(decision, get().symbol, get().timeframe)
        ) return;
        set({workspaceMode:"historical",historicalJobId,historicalCandles,historicalOutcome:undefined,decision,overlayOwner:decision.ownership.decision_owner_id,dataReadiness:decision.readiness.state});
      },
      showReplay: (decision,historicalCandles) => {
        if (
          decision.overlay_mode !== "REPLAY" ||
          !decisionMatchesWorkspace(decision, get().symbol, get().timeframe)
        ) return;
        set({workspaceMode:"replay",historicalJobId:undefined,historicalCandles,historicalOutcome:undefined,decision,overlayOwner:decision.ownership.decision_owner_id,dataReadiness:decision.readiness.state});
      },
      returnLive: () => set((state)=>({workspaceMode:"live",decision:state.liveDecision,overlayOwner:state.liveDecision?.ownership.decision_owner_id,historicalCandles:[],historicalJobId:undefined,historicalOutcome:undefined,dataReadiness:state.liveDecision?.readiness.state || "idle"})),
      setHistoricalSearch: (historicalSearch) => set({historicalSearch}),
      setHistoricalOutcome: (historicalOutcome) => set({historicalOutcome}),
    }),
    {
      name: "tradescor-terminal-v2",
      version: 4,
      migrate: (persisted) => {
        const value = (persisted || {}) as Partial<TerminalState>;
        return {
          ...value,
          overlayVisibility: {
            trade_plan: value.overlayVisibility?.trade_plan ?? true,
            market_structure: value.overlayVisibility?.market_structure ?? true,
            context_levels: value.overlayVisibility?.context_levels ?? true,
            advanced_smc: value.overlayVisibility?.advanced_smc ?? false,
            previous_setup: false,
          },
          densityMode: value.densityMode ?? "clean",
        } as TerminalState;
      },
      partialize: (s) => ({
        symbol: s.symbol,
        timeframe: s.timeframe,
        model: s.model,
        watchlist: s.watchlist,
        overlayVisibility: {
          ...s.overlayVisibility,
          previous_setup: false,
        },
        densityMode: s.densityMode,
        leftPanel: s.leftPanel,
        rightPanel: s.rightPanel,
      }),
    },
  ),
);

function connectionFromProvider(
  state?: string,
): TerminalState["connection"] {
  if (state === "ready" || state === "connected") return "connected";
  if (state === "loading" || state === "connecting") return "connecting";
  if (state === "reconnecting") return "reconnecting";
  if (state === "stale") return "stale";
  if (state === "rate_limited") return "rate_limited";
  if (state === "error" || state === "provider_error") return "provider_error";
  return "disconnected";
}
function modelLabel(symbol: SymbolInfo, model: string) {
  return symbol.available_models.find((item) => item.id === model)?.label || model.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()).replace("Smc", "SMC");
}

function requestedModelMatches(decision: NormalizedDecision, model: string) {
  const requested = decision.ownership.requested_model_id;
  if (!requested) return true;
  const normalizedRequested = requested.toLowerCase();
  const normalizedModel = model.toLowerCase();
  if (["auto", "smc_auto"].includes(normalizedModel))
    return ["auto", "smc_auto"].includes(normalizedRequested);
  return normalizedRequested === normalizedModel;
}

function olderThanCurrentDecision(
  incoming: NormalizedDecision,
  current?: NormalizedDecision,
) {
  if (!current || current.overlay_mode !== "LIVE") return false;
  if (
    incoming.meta.symbol !== current.meta.symbol ||
    incoming.meta.timeframe !== current.meta.timeframe
  ) return false;
  const incomingAt = Date.parse(incoming.meta.analysis_time);
  const currentAt = Date.parse(current.meta.analysis_time);
  return Number.isFinite(incomingAt) && Number.isFinite(currentAt) && incomingAt < currentAt;
}
