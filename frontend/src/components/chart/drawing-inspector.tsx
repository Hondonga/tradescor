import { ChevronDown } from "lucide-react";
import { stripStatusPrefix } from "@/lib/overlay-labels";
import { tierLabel, tierOf } from "@/lib/overlay-style-registry";
import { priorityLevelLabel, priorityLevelOf } from "@/lib/chart/overlayPriority";
import { formatPrice, titleCase } from "@/lib/utils";
import type { InstrumentPrecision, Overlay } from "@/types";

export interface DrawingInspectorProps {
  overlay: Overlay;
  close: () => void;
  precision?: InstrumentPrecision;
}

function priceOrZoneText(overlay: Overlay, precision?: InstrumentPrecision): string {
  if (overlay.low != null && overlay.high != null) {
    return `${formatPrice(overlay.low, precision)} – ${formatPrice(overlay.high, precision)}`;
  }
  if (overlay.price != null) return formatPrice(overlay.price, precision) || "—";
  return "—";
}

function mitigationStatusText(overlay: Overlay): string {
  const state = overlay.metadata.state;
  if (typeof state === "string" && state.toLowerCase().includes("mitigat")) return titleCase(state);
  const mitigated = overlay.metadata.mitigated;
  if (typeof mitigated === "boolean") return mitigated ? "Mitigated" : "Unmitigated";
  const pct = overlay.metadata.mitigation_percentage;
  if (typeof pct === "number") return pct >= 1 ? "Fully mitigated" : pct > 0 ? "Partially mitigated" : "Unmitigated";
  return "Not applicable";
}

/**
 * Drawing inspector (Milestone: chart redesign, §14; extended Phase 3 §14).
 * Structured fields by default; raw metadata is available but collapsed,
 * never shown up front. Never mutates backend/analysis state -- purely a
 * read-only metadata viewer for whatever overlay is currently selected.
 */
export function DrawingInspector({ overlay, close, precision }: DrawingInspectorProps) {
  const invalidation = overlay.metadata.invalidation_condition;
  const reason = overlay.metadata.visibility_reason;
  const sourceTimeframe = overlay.metadata.source_timeframe;

  return (
    <aside className="pointer-events-auto absolute bottom-8 left-3 z-30 w-72 border border-white/10 bg-[#0b0e14]/95 p-3 shadow-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold text-zinc-200">
            {stripStatusPrefix(overlay.label)}
          </p>
          <p className="mt-1 font-mono text-[9px] text-zinc-500">
            {tierLabel(tierOf(overlay))} · {typeof sourceTimeframe === "string" ? sourceTimeframe : overlay.timeframe}
          </p>
        </div>
        <button aria-label="Close drawing metadata" className="text-xs text-zinc-500" onClick={close}>
          ×
        </button>
      </div>
      <dl className="detail-grid mt-3 text-[9px]">
        <dt>Category</dt>
        <dd>{titleCase(overlay.category)}</dd>
        <dt>Priority</dt>
        <dd>{priorityLevelLabel(priorityLevelOf(overlay))}</dd>
        <dt>Timeframe</dt>
        <dd>{typeof sourceTimeframe === "string" ? sourceTimeframe : overlay.timeframe}</dd>
        <dt>Price / zone</dt>
        <dd className="tabular-nums">{priceOrZoneText(overlay, precision)}</dd>
        <dt>Source</dt>
        <dd>{overlay.source}</dd>
        <dt>Setup</dt>
        <dd className="break-all">{overlay.setup_id || "Market context"}</dd>
        <dt>Status</dt>
        <dd>{overlay.historical ? "Historical" : overlay.active ? "Active" : "Inactive"}</dd>
        <dt>Mitigation</dt>
        <dd>{mitigationStatusText(overlay)}</dd>
        <dt>Created</dt>
        <dd>{overlay.created_at || "—"}</dd>
        <dt>Invalidated</dt>
        <dd>{overlay.invalidated_at || "—"}</dd>
        <dt>Invalidates when</dt>
        <dd>{typeof invalidation === "string" ? invalidation : "Superseded by backend context"}</dd>
        <dt>Actionable</dt>
        <dd>{overlay.actionable ? "Yes" : "No"}</dd>
        <dt>Visibility reason</dt>
        <dd>{typeof reason === "string" ? reason : titleCase(overlay.display_group)}</dd>
        <dt>Hidden reason</dt>
        <dd>{overlay.active ? "Currently visible" : "—"}</dd>
      </dl>
      <details className="mt-3 border-t border-white/[.07] pt-2">
        <summary className="flex cursor-pointer list-none items-center justify-between text-[9px] text-zinc-500">
          View raw metadata
          <ChevronDown size={11} />
        </summary>
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[9px] text-zinc-500">
          {JSON.stringify(overlay, null, 2)}
        </pre>
      </details>
    </aside>
  );
}
