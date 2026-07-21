import type { Overlay } from "@/types";

/**
 * lightweight-charts' default autoscale only considers OHLC bar data, not
 * price lines. Without this, an actionable level placed beyond recent price
 * action (e.g. a TP well above the visible candle range) produces a
 * null/off-screen coordinate and its permanent right-edge tag silently
 * vanishes (Phase 2 checkpoint 16 observation). Every actionable price must
 * always be inside the chart's visible price range, so this computes the
 * min/max of every currently-actionable overlay to merge into the chart's
 * autoscaleInfoProvider.
 */
export function actionablePriceRange(overlays: Overlay[]): { minValue: number; maxValue: number } | null {
  const prices = overlays
    .filter((overlay) => overlay.actionable && overlay.price != null)
    .map((overlay) => overlay.price as number);
  if (!prices.length) return null;
  return { minValue: Math.min(...prices), maxValue: Math.max(...prices) };
}
