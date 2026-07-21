import type {
  NormalizedDecision,
  Overlay,
  OverlayCategory,
  OverlayMode,
  SymbolInfo,
  WorkspaceMode,
} from "@/types";

const TERMINAL_STATES = new Set([
  "EXPIRED",
  "INVALIDATED",
  "CANCELLED",
  "TOO_LATE",
  "CLOSED",
  "REPLACED",
  "EVENT_CANCELLED",
  "STATE_CONTRADICTION",
]);

const REQUIRED_OVERLAY_KEYS: Array<keyof Overlay> = [
  "overlay_id",
  "decision_owner_id",
  "strategy_id",
  "setup_id",
  "symbol_id",
  "provider_symbol",
  "market_type",
  "timeframe",
  "category",
  "type",
  "label",
  "source",
  "price",
  "high",
  "low",
  "start_time",
  "end_time",
  "created_at",
  "confirmed_at",
  "expires_at",
  "invalidated_at",
  "active",
  "historical",
  "actionable",
  "priority",
  "display_group",
  "metadata",
];

const MODE_BY_WORKSPACE: Record<WorkspaceMode, OverlayMode> = {
  live: "LIVE",
  historical: "HISTORICAL_INSPECTION",
  replay: "REPLAY",
};

export interface OverlaySelectionContext {
  decision?: NormalizedDecision;
  symbol: SymbolInfo;
  timeframe: string;
  workspaceMode: WorkspaceMode;
  connection: string;
  visibility: Record<OverlayCategory, boolean>;
}

export function selectVisibleOverlays({
  decision,
  symbol,
  timeframe,
  workspaceMode,
  connection,
  visibility,
}: OverlaySelectionContext): Overlay[] {
  if (!decision || decision.overlay_mode !== MODE_BY_WORKSPACE[workspaceMode])
    return [];
  if (!decisionMatchesWorkspace(decision, symbol, timeframe)) return [];

  const activeSetupId = currentSetupId(decision);
  const previousSetupIds = archivedSetupIds(decision.previous_setup);
  const actionablePlan = actionablePlanIsValid(
    decision,
    activeSetupId,
    workspaceMode,
    connection,
  );
  const seen = new Set<string>();

  return decision.overlays
    .filter((overlay): overlay is Overlay => isNormalizedOverlay(overlay))
    .filter((overlay) => {
      if (seen.has(overlay.overlay_id)) return false;
      seen.add(overlay.overlay_id);
      if (
        overlay.decision_owner_id !== decision.ownership.decision_owner_id ||
        overlay.strategy_id !== selectedStrategyId(decision) ||
        overlay.symbol_id !== symbol.symbol_id ||
        overlay.provider_symbol !== symbol.provider_symbol ||
        overlay.market_type !== symbol.market_type ||
        normalizedTimeframe(overlay.timeframe) !== normalizedTimeframe(timeframe)
      )
        return false;

      const rowMode = overlay.metadata.overlay_mode;
      if (typeof rowMode === "string" && rowMode !== decision.overlay_mode)
        return false;

      if (overlay.category === "historical") {
        if (overlay.active || !overlay.historical || overlay.actionable)
          return false;
        if (!overlay.setup_id || !previousSetupIds.has(overlay.setup_id))
          return false;
      } else {
        if (!overlay.active || overlay.historical) return false;
        if (overlay.actionable !== (overlay.category === "actionable"))
          return false;
        if (
          overlay.setup_id &&
          (!activeSetupId || overlay.setup_id !== activeSetupId)
        )
          return false;
      }

      if (overlay.category === "developing") {
        if (!activeSetupId || overlay.setup_id !== activeSetupId) return false;
        if (!isDevelopingLabel(overlay.label)) return false;
      }
      if (overlay.category === "actionable") {
        if (
          !actionablePlan ||
          !activeSetupId ||
          overlay.setup_id !== activeSetupId ||
          !actionableOverlayMatchesPlan(overlay, decision)
        )
          return false;
      }

      if (overlay.category === "context" && overlay.type === "current_price")
        return true;
      return visibility[toggleForOverlay(overlay)];
    })
    .sort((left, right) => right.priority - left.priority);
}

export function toggleForOverlay(overlay: Overlay): OverlayCategory {
  if (overlay.category === "historical") return "previous_setup";
  if (overlay.category === "actionable") return "trade_plan";

  const group = normalizedToken(overlay.display_group);
  const advanced =
    overlay.metadata.default_visible === false ||
    overlay.priority < 50 ||
    group === "advanced_smc" ||
    group === "diagnostic" ||
    overlay.metadata.advanced === true;
  if (advanced) return "advanced_smc";
  if (
    group === "structure" ||
    group === "market_structure" ||
    group === "structural_context"
  )
    return "market_structure";
  return "context_levels";
}

export function isNormalizedOverlay(value: unknown): value is Overlay {
  if (!isRecord(value)) return false;
  if (!REQUIRED_OVERLAY_KEYS.every((key) => hasOwn(value, key))) return false;
  if (
    !nonEmptyString(value.overlay_id) ||
    !nonEmptyString(value.decision_owner_id) ||
    !nonEmptyString(value.strategy_id) ||
    !(value.setup_id === null || nonEmptyString(value.setup_id)) ||
    !nonEmptyString(value.symbol_id) ||
    !nonEmptyString(value.provider_symbol) ||
    !nonEmptyString(value.market_type) ||
    !nonEmptyString(value.timeframe) ||
    !["context", "developing", "actionable", "historical"].includes(
      String(value.category),
    ) ||
    !nonEmptyString(value.type) ||
    !nonEmptyString(value.label) ||
    !nonEmptyString(value.source) ||
    !nullableNumber(value.price) ||
    !nullableNumber(value.low) ||
    !nullableNumber(value.high) ||
    !nullableTime(value.start_time) ||
    !nullableTime(value.end_time) ||
    !nullableTime(value.created_at) ||
    !nullableTime(value.confirmed_at) ||
    !nullableTime(value.expires_at) ||
    !nullableTime(value.invalidated_at) ||
    typeof value.active !== "boolean" ||
    typeof value.historical !== "boolean" ||
    typeof value.actionable !== "boolean" ||
    typeof value.priority !== "number" ||
    !Number.isFinite(value.priority) ||
    !nonEmptyString(value.display_group) ||
    !isRecord(value.metadata)
  )
    return false;

  const hasPrice = typeof value.price === "number";
  const hasZone = typeof value.low === "number" && typeof value.high === "number";
  const brokenZone = (value.low === null) !== (value.high === null);
  return !brokenZone && (hasPrice || hasZone);
}

export function decisionMatchesWorkspace(
  decision: NormalizedDecision,
  symbol: SymbolInfo,
  timeframe: string,
): boolean {
  return (
    decision.meta.symbol === symbol.provider_symbol &&
    normalizedTimeframe(decision.meta.timeframe) ===
      normalizedTimeframe(timeframe) &&
    (!decision.meta.market_source ||
      decision.meta.market_source === symbol.market_source) &&
    (!decision.meta.market_type ||
      decision.meta.market_type === symbol.market_type) &&
    decision.precision?.symbol_id === symbol.symbol_id
  );
}

export function currentSetupId(decision: NormalizedDecision): string | null {
  if (hasOwn(decision as unknown as Record<string, unknown>, "active_setup"))
    return decision.active_setup?.setup_id || null;
  const state = normalizedToken(
    decision.decision.stage || decision.setup.stage || decision.setup.status,
  ).toUpperCase();
  return TERMINAL_STATES.has(state) ? null : decision.setup.setup_id || null;
}

function actionablePlanIsValid(
  decision: NormalizedDecision,
  activeSetupId: string | null,
  workspaceMode: WorkspaceMode,
  connection: string,
) {
  const plan = decision.trade_plan;
  const activeLifecycle = normalizedToken(
    decision.active_setup?.lifecycle ||
      decision.active_setup?.state ||
      decision.decision.stage,
  ).toUpperCase();
  const readyData = normalizedToken(decision.readiness.state).toUpperCase() === "READY";
  const liveFresh =
    workspaceMode !== "live" ||
    (connection === "connected" && decision.meta.live === true);
  return Boolean(
    activeSetupId &&
      activeLifecycle === "TRADE_READY" &&
      decision.decision.trade_ready === true &&
      plan?.available === true &&
      finite(plan.entry) &&
      finite(plan.stop) &&
      finite(plan.targets?.[0]?.price) &&
      readyData &&
      liveFresh &&
      decision.diagnostics.invariants?.valid !== false,
  );
}

function actionableOverlayMatchesPlan(
  overlay: Overlay,
  decision: NormalizedDecision,
) {
  const plan = decision.trade_plan!;
  const role = overlayRole(overlay);
  if (role === "entry") return overlay.price === plan.entry;
  if (role === "stop") return overlay.price === plan.stop;
  if (role === "entry_zone")
    return (() => {
      const active = decision.active_setup as Record<string, any> | null | undefined;
      const zone = plan.entry_zone || active?.entry_area;
      return Boolean(
        zone && overlay.low === zone.low && overlay.high === zone.high,
      );
    })();
  if (role === "invalidation") {
    const raw = plan.invalidation;
    const invalidation = isRecord(raw) ? raw.price : raw;
    return overlay.price === (invalidation ?? plan.stop);
  }
  if (role === "tp1" || role === "tp2") {
    const index = role === "tp1" ? 0 : 1;
    return overlay.price === plan.targets?.[index]?.price;
  }
  return false;
}

export function overlayRole(overlay: Overlay) {
  const metadataRole = overlay.metadata.plan_role;
  const token = normalizedToken(
    typeof metadataRole === "string" ? metadataRole : overlay.type,
  );
  if (["entry", "trade_entry", "preferred_entry"].includes(token))
    return "entry";
  if (["entry_zone", "trade_ready_entry_zone", "setup_area"].includes(token))
    return "entry_zone";
  if (["stop", "stop_loss", "trade_stop"].includes(token)) return "stop";
  if (["invalidation", "final_invalidation", "plan_invalidation"].includes(token))
    return "invalidation";
  if (["tp1", "target_1"].includes(token)) return "tp1";
  if (["tp2", "target_2"].includes(token)) return "tp2";
  if (token === "target") {
    const label = normalizedToken(overlay.label);
    if (label.startsWith("tp1")) return "tp1";
    if (label.startsWith("tp2")) return "tp2";
  }
  return "";
}

function isDevelopingLabel(label: string) {
  const normalized = label.toUpperCase();
  if (/^(ENTRY|STOP(?: LOSS)?|TP1|TP2)(?:\b|\s|·)/.test(normalized))
    return false;
  return [
    "DEVELOPING",
    "MONITORING LEVEL",
    "NOT AN ENTRY",
    "POTENTIAL OBJECTIVE",
  ].some((token) => normalized.includes(token)) ||
    (normalized.includes("POTENTIAL") && normalized.includes("OBJECTIVE"));
}

function archivedSetupIds(value: unknown, result = new Set<string>()): Set<string> {
  if (Array.isArray(value)) {
    value.forEach((item) => archivedSetupIds(item, result));
    return result;
  }
  if (!isRecord(value)) return result;
  if (nonEmptyString(value.setup_id)) result.add(value.setup_id);
  for (const key of ["setup", "setups", "previous", "archive", "items"])
    if (hasOwn(value, key)) archivedSetupIds(value[key], result);
  return result;
}

function selectedStrategyId(decision: NormalizedDecision) {
  return (
    decision.ownership.selected_strategy_id ||
    decision.ownership.selected_model_id
  );
}

function normalizedTimeframe(value: string) {
  return String(value || "").trim().toUpperCase();
}

function normalizedToken(value: unknown) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function nullableNumber(value: unknown) {
  return value === null || finite(value);
}

function nullableTime(value: unknown) {
  return value === null || typeof value === "string";
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOwn(value: Record<string, unknown>, key: PropertyKey) {
  return Object.prototype.hasOwnProperty.call(value, key);
}
