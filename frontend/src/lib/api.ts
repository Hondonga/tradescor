import type { AnalyzePayload, HistoricalInspection, HistoricalSearchProgress, SymbolInfo } from "@/types";

async function json<T>(response: Response): Promise<T> {
  const body = await response.json();
  if (!response.ok)
    throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}
export async function listSymbols(): Promise<SymbolInfo[]> {
  const payload = await json<any>(await fetch("/api/markets/registry"));
  const rows = Array.isArray(payload) ? payload : payload.markets || [];
  return rows
    .map((row: any) => ({
      symbol_id: row.symbol_id,
      provider_symbol: row.provider_symbol || row.symbol,
      display_name: row.display_name || row.name || row.provider_symbol,
      family: row.family || "OTHER_DERIVED",
      family_display: row.family_display,
      variant: row.variant,
      market_source: row.market_source,
      market_type: row.market_type,
      market_schedule: row.market_schedule,
      analysis_engine: row.analysis_engine,
      supported: row.supported,
      available_models: row.available_models || [],
      default_model: row.default_model,
      auto_adapter: row.auto_adapter,
      production_supported: row.production_supported,
      research_supported: row.research_supported,
      cached_analysis: row.cached_analysis,
      market: row.market,
      submarket: row.submarket,
      pip_size: row.pip_size ?? row.instrument_precision?.pip_size,
      price_decimals:
        row.price_decimals ??
        row.instrument_precision?.price_decimals ??
        row.precision?.price_decimals,
      quantity_decimals:
        row.quantity_decimals ??
        row.instrument_precision?.quantity_decimals ??
        row.precision?.quantity_decimals,
      tick_size: row.tick_size ?? row.instrument_precision?.tick_size,
      precision: row.instrument_precision ?? row.precision,
      market_open: row.market_open,
      smc_adapter: row.smc_adapter,
      analysis_supported: row.supported,
      analysis_support_status: row.analysis_support_status || (row.supported ? "SUPPORTED" : "UNSUPPORTED_MODEL"),
    }))
    .filter((row: SymbolInfo) => row.provider_symbol);
}
export async function analyze(
  symbol: SymbolInfo,
  timeframe: string,
  model: string,
  signal?: AbortSignal,
  options?: { analysisDepth?: "lightweight" | "full"; priority?: string },
): Promise<AnalyzePayload> {
  // Keep the explicit Derived route visible while traditional markets use their registry type.
  const derivedRoute = { asset_class: "derived_index" };
  const query = new URLSearchParams({
    symbol: symbol.provider_symbol,
    display_name: symbol.display_name,
    timeframe,
    strategy: model,
    provider: symbol.market_source || "twelve_data",
    asset_class:
      symbol.market_type === "derived"
        ? derivedRoute.asset_class
        : symbol.market_type,
    manual: "1",
    bars: "300",
    multi_timeframe: "1",
    context_depth: "balanced",
    analysis_depth: options?.analysisDepth || "full",
    priority: options?.priority || "PRIORITY_1_WORKSPACE",
  });
  if (symbol.pip_size != null) query.set("pip_size", String(symbol.pip_size));
  if (symbol.tick_size != null) query.set("tick_size", String(symbol.tick_size));
  if (symbol.price_decimals != null)
    query.set("price_decimals", String(symbol.price_decimals));
  if (symbol.quantity_decimals != null)
    query.set("quantity_decimals", String(symbol.quantity_decimals));
  return json<AnalyzePayload>(await fetch(`/api/analyze?${query}`, { signal }));
}
export const paperRecords = async () =>
  json<any>(await fetch("/api/paper/setups"));
export const paperEvidence = async () =>
  json<any>(await fetch("/api/paper/performance"));
export const replayRuns = async () =>
  json<any>(await fetch("/api/replay/runs"));
export const startLatestSetupSearch = async (periodDays: 30|90) => json<HistoricalSearchProgress>(await fetch("/api/workspace/latest-valid-setup", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({period_days:periodDays})}));
export const latestSetupSearch = async (jobId:string) => json<{progress:HistoricalSearchProgress;result:HistoricalInspection|null}>(await fetch(`/api/workspace/latest-valid-setup/${jobId}`));
export const cancelLatestSetupSearch = async (jobId:string) => json<HistoricalSearchProgress>(await fetch(`/api/workspace/latest-valid-setup/${jobId}/cancel`,{method:"POST"}));
export const revealHistoricalOutcome = async (jobId:string) => json<any>(await fetch(`/api/workspace/latest-valid-setup/${jobId}/reveal-outcome`,{method:"POST"}));
export const mlDatasets = async () => json<any>(await fetch("/api/ml/datasets"));
export const buildMlDataset = async () => json<any>(await fetch("/api/ml/datasets/build",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({period_days:90,snapshot_policy:"every_stage_transition"})}));
export const mlDatasetProgress = async (id:string) => json<any>(await fetch(`/api/ml/datasets/${id}/progress`));
export const mlDatasetAction = async (id:string,action:"pause"|"resume"|"cancel") => json<any>(await fetch(`/api/ml/datasets/${id}/${action}`,{method:"POST"}));
export const validateMlDataset = async (id:string) => json<any>(await fetch(`/api/ml/datasets/${id}/validate`,{method:"POST"}));
export const mlTrainingRuns = async () => json<any>(await fetch("/api/ml/training/runs"));
export const startMlTraining = async (datasetId:string) => json<any>(await fetch("/api/ml/training/runs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({dataset_id:datasetId})}));
export const mlTrainingProgress = async (id:string) => json<any>(await fetch(`/api/ml/training/runs/${id}/progress`));
export const cancelMlTraining = async (id:string) => json<any>(await fetch(`/api/ml/training/runs/${id}/cancel`,{method:"POST"}));
