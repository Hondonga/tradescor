import { chartLabel } from "@/lib/overlay-labels";
import { isOversizedZone, type ZoneRect } from "@/lib/overlay-layout";
import { hexToRgbTriplet, styleForOverlay } from "@/lib/overlay-style-registry";
import type { Overlay } from "@/types";

export interface ChartZoneLayerProps {
  /** Precomputed geometry — market-chart.tsx owns the single reconciliation
   * pass; this component only renders what it's given. */
  zones: Array<{ rect: ZoneRect; overlay: Overlay }>;
  chartHeight: number;
  selectedOverlayId: string;
  onSelect: (id: string) => void;
  secondaryLine?: (overlay: Overlay) => string | null;
}

/**
 * Zone rectangles (Milestone: chart redesign, §4). Transparent interior,
 * border carries more visual weight than fill, label sits in the upper-left
 * interior and never repeats the lifecycle prefix. A zone that dominates the
 * visible price range renders as boundary lines instead of a filled block.
 */
export function ChartZoneLayer({
  zones,
  chartHeight,
  selectedOverlayId,
  onSelect,
  secondaryLine,
}: ChartZoneLayerProps) {
  return (
    <>
      {zones.map(({ rect, overlay }) => {
        const style = styleForOverlay(overlay);
        const rgb = hexToRgbTriplet(style.color);
        const oversized = isOversizedZone(rect, chartHeight);
        const selected = overlay.overlay_id === selectedOverlayId;
        const zIndex = Math.max(1, Math.min(10, Math.round(overlay.priority / 10)));

        return (
          <div
            key={overlay.overlay_id}
            className="pointer-events-none absolute"
            style={{ top: rect.top, height: rect.height, left: rect.left, width: rect.width, zIndex }}
          >
            {oversized ? (
              <>
                <div
                  className="absolute inset-x-0 top-0 h-px"
                  style={{ background: `rgba(${rgb}, ${style.zoneBorderOpacity})` }}
                />
                <div
                  className="absolute inset-x-0 bottom-0 h-px"
                  style={{ background: `rgba(${rgb}, ${style.zoneBorderOpacity})` }}
                />
              </>
            ) : (
              <div
                className="absolute inset-0 border"
                style={{
                  background: `rgba(${rgb}, ${style.zoneFillOpacity})`,
                  borderColor: `rgba(${rgb}, ${style.zoneBorderOpacity})`,
                  outline: selected ? "1px solid rgba(255,255,255,.35)" : undefined,
                }}
              />
            )}
            <div className="pointer-events-auto absolute left-1.5 top-1.5 max-w-[85%]">
              <button
                type="button"
                onClick={() => onSelect(overlay.overlay_id)}
                className="block truncate text-left font-mono text-[9px] font-medium tracking-wide"
                style={{ color: `rgba(${rgb}, .95)` }}
              >
                {chartLabel(overlay)}
              </button>
              {secondaryLine?.(overlay) && (
                <p className="mt-0.5 truncate text-[9px] text-zinc-500">
                  {secondaryLine(overlay)}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </>
  );
}
