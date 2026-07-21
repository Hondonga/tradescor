import { stripStatusPrefix } from "@/lib/overlay-labels";
import { formatPrice } from "@/lib/utils";
import type { InstrumentPrecision, Overlay } from "@/types";

export interface OverlayTooltipProps {
  overlay: Overlay;
  x: number;
  y: number;
  precision?: InstrumentPrecision;
  diagnosticsVisible?: boolean;
}

/**
 * Compact hover tooltip (Phase 3 §15). Shows the same semantic fields as
 * the Drawing Inspector, condensed for a quick glance: name, exact price/
 * zone, timeframe, status, source, ownership, and why it's displayed.
 * Internal database IDs (setup_id, overlay_id) are only shown once
 * Diagnostics is toggled on -- everyone else gets ownership described in
 * plain terms instead.
 */
export function OverlayTooltip({ overlay, x, y, precision, diagnosticsVisible = false }: OverlayTooltipProps) {
  const priceText =
    overlay.low != null && overlay.high != null
      ? `${formatPrice(overlay.low, precision)} – ${formatPrice(overlay.high, precision)}`
      : overlay.price != null
        ? formatPrice(overlay.price, precision)
        : "—";
  const status = overlay.historical ? "Historical" : overlay.active ? "Active" : "Inactive";
  const reason = overlay.metadata.visibility_reason;

  return (
    <div
      role="tooltip"
      className="tooltip pointer-events-none absolute z-40 w-56"
      style={{ left: x + 10, top: y - 8 }}
    >
      <p className="font-semibold text-[10px] text-zinc-100">{stripStatusPrefix(overlay.label)}</p>
      <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[9px]">
        <dt className="text-zinc-500">Price</dt>
        <dd className="tabular-nums text-zinc-300">{priceText}</dd>
        <dt className="text-zinc-500">Timeframe</dt>
        <dd className="text-zinc-300">{overlay.timeframe}</dd>
        <dt className="text-zinc-500">Status</dt>
        <dd className="text-zinc-300">{status}</dd>
        <dt className="text-zinc-500">Source</dt>
        <dd className="text-zinc-300">{overlay.source}</dd>
        <dt className="text-zinc-500">Setup</dt>
        <dd className="text-zinc-300">{overlay.setup_id ? "This setup" : "Market context"}</dd>
        {typeof reason === "string" && (
          <>
            <dt className="text-zinc-500">Shown because</dt>
            <dd className="text-zinc-300">{reason}</dd>
          </>
        )}
        {diagnosticsVisible && (
          <>
            <dt className="text-zinc-500">Overlay ID</dt>
            <dd className="break-all font-mono text-zinc-500">{overlay.overlay_id}</dd>
          </>
        )}
      </dl>
    </div>
  );
}
