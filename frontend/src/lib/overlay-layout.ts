// Pure geometry helpers for placing zone rectangles on the chart. Extracted
// from market-chart.tsx so the placement math is testable without a real
// lightweight-charts instance. Never mutates or reads backend price/time
// values as anything other than plain numeric inputs — layout calculations
// must never change the values they're positioning.
import type { Overlay } from "@/types";

export interface ZoneRect {
  overlayId: string;
  top: number;
  height: number;
  left: number;
  width: number;
}

export interface ZoneLayoutInput {
  chartWidth: number;
  /** Right-edge gutter reserved for the price scale/axis labels, in px. */
  rightGutter?: number;
  /** Left margin used when an overlay has no start_time, as a fraction of chartWidth. */
  leftMarginRatio?: number;
  priceToY: (price: number) => number | null;
  timeToX: (time: string) => number | null;
}

/** Computes one overlay's on-chart rectangle, or null if it can't be placed
 * (missing price coordinates, or the overlay isn't a zone at all). */
export function computeZoneRect(overlay: Overlay, input: ZoneLayoutInput): ZoneRect | null {
  if (overlay.low == null || overlay.high == null) return null;
  const high = input.priceToY(overlay.high);
  const low = input.priceToY(overlay.low);
  if (high == null || low == null) return null;

  const rightGutter = input.rightGutter ?? 64;
  const leftMarginRatio = input.leftMarginRatio ?? 0.08;
  const start = overlay.start_time ? input.timeToX(overlay.start_time) : null;
  const end = overlay.end_time ? input.timeToX(overlay.end_time) : null;
  const left = Math.max(0, start ?? input.chartWidth * leftMarginRatio);
  const right = Math.min(input.chartWidth - rightGutter, end ?? input.chartWidth - rightGutter);

  return {
    overlayId: overlay.overlay_id,
    top: Math.min(high, low),
    height: Math.max(2, Math.abs(low - high)),
    left,
    width: Math.max(2, right - left),
  };
}

/**
 * A zone is "oversized" when it dominates the visible price range — the
 * exact malformed-chart symptom this milestone repairs. Oversized zones
 * should render as boundary lines rather than a filled rectangle (§4).
 */
export function isOversizedZone(rect: ZoneRect, chartHeight: number, maxRatio = 0.45): boolean {
  if (chartHeight <= 0) return false;
  return rect.height / chartHeight > maxRatio;
}
