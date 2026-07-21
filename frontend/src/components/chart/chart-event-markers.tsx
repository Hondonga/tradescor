import { hexToRgbTriplet, styleForOverlay } from "@/lib/overlay-style-registry";
import type { Overlay } from "@/types";

const MARKER_TEXT: Record<string, string> = {
  m5_displacement: "DISP",
  displacement: "DISP",
  sweep: "SWEEP",
  liquidity_sweep: "SWEEP",
  confirmed_sweep: "SWEEP",
  bos: "BOS",
  mss: "MSS",
  rejection: "REJ",
  confirmation: "CONF",
};

export interface ChartEventMarkersProps {
  overlays: Overlay[];
  priceToY: (price: number) => number | null;
  timeToX: (time: string) => number | null;
  chartWidth: number;
  selectedOverlayId: string;
  onSelect: (id: string) => void;
}

/**
 * Compact candle markers for completed-evidence events (Milestone: chart
 * redesign, §10) — a small tag near the event's price/time, never a
 * full-width horizontal line. Bullish-leaning events sit above their price,
 * bearish-leaning ones below; direction comes only from backend metadata.
 */
export function ChartEventMarkers({
  overlays,
  priceToY,
  timeToX,
  chartWidth,
  selectedOverlayId,
  onSelect,
}: ChartEventMarkersProps) {
  return (
    <>
      {overlays.map((overlay) => {
        if (overlay.price == null) return null;
        const y = priceToY(overlay.price);
        if (y == null) return null;
        const time = overlay.confirmed_at || overlay.created_at;
        const x = time ? timeToX(time) : null;
        const left = x != null ? Math.min(Math.max(x, 4), chartWidth - 40) : chartWidth - 44;
        const direction = String(overlay.metadata.direction || "").toLowerCase();
        const above = direction !== "bearish" && direction !== "sell" && direction !== "down";
        const style = styleForOverlay(overlay);
        const rgb = hexToRgbTriplet(style.color);
        const text = MARKER_TEXT[overlay.type.toLowerCase()] || overlay.type.slice(0, 4).toUpperCase();
        const selected = overlay.overlay_id === selectedOverlayId;

        return (
          <button
            key={overlay.overlay_id}
            type="button"
            onClick={() => onSelect(overlay.overlay_id)}
            className="pointer-events-auto absolute z-30 rounded-sm border px-1 font-mono text-[8px] font-medium leading-3"
            style={{
              left,
              top: above ? y - 20 : y + 6,
              borderColor: `rgba(${rgb}, .4)`,
              background: selected ? `rgba(${rgb}, .25)` : `rgba(${rgb}, .1)`,
              color: `rgba(${rgb}, .9)`,
            }}
          >
            {text}
          </button>
        );
      })}
    </>
  );
}
