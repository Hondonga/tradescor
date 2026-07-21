// Presentation-only visual tier and style lookup for normalized backend
// overlays. This module never invents structure, prices, or ownership — it
// only decides how an already-normalized overlay should look on the chart.
import type { Overlay } from "@/types";
import { SEMANTIC_COLORS } from "./chart/semanticColors";

export type OverlayTier = 1 | 2 | 3 | 4;
export type LineStyleToken = "solid" | "dashed" | "dotted";
export type RenderAs = "line" | "zone" | "marker";

export interface OverlayStyle {
  tier: OverlayTier;
  color: string;
  lineStyle: LineStyleToken;
  lineWidth: 1 | 2;
  /** 0..1 fill opacity for zone rectangles. */
  zoneFillOpacity: number;
  /** 0..1 border opacity for zone rectangles. */
  zoneBorderOpacity: number;
  renderAs: RenderAs;
}

// Chart-role aliases onto the single centralized semantic palette
// (lib/chart/semanticColors.ts) — kept as named roles here because a chart
// role (e.g. "confirmation") and a generic UI category (e.g. "warning")
// aren't always the same word, but they must always resolve to the same
// underlying color value. Never add a literal hex value below; alias an
// existing SEMANTIC_COLORS entry instead.
const PALETTE = {
  entry: SEMANTIC_COLORS.actionable,
  stop: SEMANTIC_COLORS.bearish,
  target: SEMANTIC_COLORS.bullish,
  invalidation: SEMANTIC_COLORS.bearish,
  confirmation: SEMANTIC_COLORS.warning,
  potentialObjective: SEMANTIC_COLORS.neutral,
  structure: SEMANTIC_COLORS.historical,
  diagnostic: SEMANTIC_COLORS.disabled,
  currentPrice: SEMANTIC_COLORS.neutral,
};

/**
 * Setup-area zones (tier 2, e.g. an M15 pullback area) previously always
 * rendered in the same blue regardless of trade direction, so a developing
 * BUY setup and a developing SELL setup looked identical on the chart. When
 * the overlay carries direction metadata, color it bullish/bearish like the
 * rest of the terminal already does for direction-aware UI; otherwise fall
 * back to the neutral "entry" tone unchanged.
 */
function directionAwareZoneColor(overlay: Overlay): string {
  const direction = String(overlay.metadata.direction || "").toLowerCase();
  if (direction === "buy" || direction === "bullish") return SEMANTIC_COLORS.bullish;
  if (direction === "sell" || direction === "bearish") return SEMANTIC_COLORS.bearish;
  return PALETTE.entry;
}

/** Event-evidence kinds that render as compact candle markers, never full-width lines. */
const EVENT_MARKER_TYPES = new Set([
  "m5_displacement",
  "displacement",
  "sweep",
  "liquidity_sweep",
  "confirmed_sweep",
  "bos",
  "mss",
  "rejection",
  "confirmation",
  // Phase 3 §9/§1 -- swings and equal highs/lows are RESEARCH-mode
  // diagnostic evidence, never a permanent full-width line ("do not render
  // every swing as a full-width line").
  "swing_high",
  "swing_low",
  "equal_high",
  "equal_low",
]);

function normalizedRole(overlay: Overlay) {
  const token = String(overlay.metadata.plan_role || overlay.type || "").toLowerCase();
  return token;
}

/**
 * Tier mirrors the backend's global overlay priority bands (Milestone 2
 * section 8): 100 actionable · 90 setup area/invalidation · 80 structure ·
 * 70 potential objective · 50 confirmation/displacement evidence · 20
 * diagnostic. Recomputed here purely for STYLING, not for visibility gating
 * (that stays governed by overlayVisibility / density mode).
 */
export function tierOf(overlay: Overlay): OverlayTier {
  if (overlay.category === "actionable") return 1;
  if (overlay.category === "developing") return 2;
  if (overlay.category === "context" && overlay.priority >= 70) return 3;
  return 4;
}

export function styleForOverlay(overlay: Overlay): OverlayStyle {
  const tier = tierOf(overlay);
  const role = normalizedRole(overlay);
  const type = overlay.type.toLowerCase();
  const isEvent = EVENT_MARKER_TYPES.has(type);

  if (tier === 1) {
    const isStop = role.includes("stop") || type.includes("stop") || role.includes("invalidation");
    const isTarget = role.includes("tp") || type.includes("target") || role === "tp1" || role === "tp2";
    return {
      tier,
      color: isStop ? PALETTE.stop : isTarget ? PALETTE.target : PALETTE.entry,
      lineStyle: "solid",
      lineWidth: 2,
      zoneFillOpacity: 0.12,
      zoneBorderOpacity: 0.65,
      renderAs: "line",
    };
  }

  if (tier === 2) {
    const isInvalidation = type.includes("invalidation") || type === "setup_invalidation";
    const isConfirmation = type.includes("confirmation");
    const isObjective = type.includes("objective");
    return {
      tier,
      color: isInvalidation
        ? PALETTE.invalidation
        : isConfirmation
          ? PALETTE.confirmation
          : isObjective
            ? PALETTE.potentialObjective
            : directionAwareZoneColor(overlay),
      lineStyle: isInvalidation ? "solid" : isConfirmation ? "dashed" : "dotted",
      lineWidth: 1,
      zoneFillOpacity: 0.1,
      zoneBorderOpacity: 0.5,
      renderAs: overlay.low != null && overlay.high != null ? "zone" : "line",
    };
  }

  if (tier === 3) {
    return {
      tier,
      color: type === "current_price" ? PALETTE.currentPrice : PALETTE.structure,
      lineStyle: type === "current_price" ? "dotted" : "dashed",
      lineWidth: 1,
      zoneFillOpacity: 0.05,
      zoneBorderOpacity: 0.3,
      renderAs: overlay.low != null && overlay.high != null ? "zone" : "line",
    };
  }

  return {
    tier: 4,
    color: PALETTE.diagnostic,
    lineStyle: "dotted",
    lineWidth: 1,
    zoneFillOpacity: 0.04,
    zoneBorderOpacity: 0.22,
    renderAs: isEvent ? "marker" : overlay.low != null && overlay.high != null ? "zone" : "line",
  };
}

export function tierLabel(tier: OverlayTier) {
  return { 1: "Actionable", 2: "Developing setup", 3: "Market structure", 4: "Diagnostic" }[tier];
}

/** #rrggbb -> "r, g, b" for building rgba() strings. */
export function hexToRgbTriplet(hex: string): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return `${r}, ${g}, ${b}`;
}
