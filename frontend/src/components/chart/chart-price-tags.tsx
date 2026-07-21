import { tagPriority, tagText } from "@/lib/overlay-labels";
import { resolveCollisions } from "@/lib/overlay-collision";
import { hexToRgbTriplet, styleForOverlay } from "@/lib/overlay-style-registry";
import type { InstrumentPrecision, Overlay } from "@/types";
import { formatPrice } from "@/lib/utils";

const TAG_HEIGHT = 16;
// Phase 2 stabilization §8: a clean default chart never shows more than a
// handful of permanent right-edge tags regardless of available height.
const MAX_DEFAULT_RIGHT_EDGE_TAGS = 7;

export interface ChartPriceTagsProps {
  overlays: Overlay[]; // line-type overlays only (overlay.price != null)
  chartHeight: number;
  priceToY: (price: number) => number | null;
  precision?: InstrumentPrecision;
  selectedOverlayId: string;
  onSelect: (id: string) => void;
  onHover?: (id: string, x: number, y: number) => void;
  onHoverEnd?: () => void;
}

/**
 * Right-edge price tag layout manager (Milestone: chart redesign, §7).
 * Detects vertical overlap, offsets lower-priority tags, draws a connector
 * back to the true price, and hides whatever still doesn't fit.
 */
export function ChartPriceTags({
  overlays,
  chartHeight,
  priceToY,
  precision,
  selectedOverlayId,
  onSelect,
  onHover,
  onHoverEnd,
}: ChartPriceTagsProps) {
  const placed = overlays
    .filter((overlay) => overlay.price != null)
    .map((overlay) => ({ overlay, y: priceToY(overlay.price!) }))
    .filter((row): row is { overlay: Overlay; y: number } => row.y != null);

  const resolved = resolveCollisions(
    placed.map((row) => ({
      id: row.overlay.overlay_id,
      y: row.y,
      height: TAG_HEIGHT,
      priority: tagPriority(row.overlay),
    })),
    { minGap: 3, viewportHeight: chartHeight },
  );
  // Cap permanent tags at MAX_DEFAULT_RIGHT_EDGE_TAGS regardless of how much
  // vertical room resolveCollisions found — lowest priority drops first.
  const visibleCount = resolved.filter((item) => item.visible).length;
  if (visibleCount > MAX_DEFAULT_RIGHT_EDGE_TAGS) {
    const keep = new Set(
      [...resolved]
        .filter((item) => item.visible)
        .sort((a, b) => b.priority - a.priority)
        .slice(0, MAX_DEFAULT_RIGHT_EDGE_TAGS)
        .map((item) => item.id),
    );
    for (const item of resolved) if (!keep.has(item.id)) item.visible = false;
  }

  const byId = new Map(placed.map((row) => [row.overlay.overlay_id, row]));

  return (
    <>
      {resolved.map((item) => {
        if (!item.visible) return null;
        const overlay = byId.get(item.id)!.overlay;
        const style = styleForOverlay(overlay);
        const rgb = hexToRgbTriplet(style.color);
        const text = tagText(overlay);
        const sources = overlay.metadata.supporting_sources;
        const title = Array.isArray(sources) && sources.length
          ? sources.map((s: any) => s?.label || s?.type).filter(Boolean).join("\n")
          : undefined;
        const selected = overlay.overlay_id === selectedOverlayId;

        return (
          <div key={item.id} className="pointer-events-none absolute right-1 z-30" style={{ top: item.resolvedY - TAG_HEIGHT / 2 }}>
            {Math.abs(item.offset) > 1 && (
              <svg className="absolute right-full top-1/2 h-px w-3 -translate-y-1/2 overflow-visible">
                <line
                  x1="0"
                  y1="0"
                  x2="12"
                  y2={item.y - item.resolvedY}
                  stroke={`rgba(${rgb}, .5)`}
                  strokeWidth="1"
                />
              </svg>
            )}
            <button
              type="button"
              title={title}
              onClick={() => onSelect(overlay.overlay_id)}
              onMouseEnter={(event) => onHover?.(overlay.overlay_id, event.clientX, event.clientY)}
              onMouseLeave={() => onHoverEnd?.()}
              onFocus={(event) => onHover?.(overlay.overlay_id, event.currentTarget.getBoundingClientRect().left, event.currentTarget.getBoundingClientRect().top)}
              onBlur={() => onHoverEnd?.()}
              className="pointer-events-auto flex items-center gap-1 whitespace-nowrap rounded-sm border px-1 font-mono text-[9px] leading-4"
              style={{
                borderColor: `rgba(${rgb}, .5)`,
                background: selected ? `rgba(${rgb}, .22)` : `rgba(${rgb}, .12)`,
                color: `rgba(${rgb}, .95)`,
              }}
            >
              {text && <span className="font-semibold">{text}</span>}
              <span className="tabular-nums">{formatPrice(overlay.price, precision)}</span>
            </button>
          </div>
        );
      })}
    </>
  );
}
