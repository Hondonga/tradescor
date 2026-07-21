// Presentation-only visual tier and style lookup for normalized backend
// overlays. This module never invents structure, prices, or ownership — it
// only decides how an already-normalized overlay should look on the chart.
import type { Overlay } from "@/types";

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

const PALETTE = {
  entry: "#5d98f8",
  stop: "#ef6767",
  target: "#36bd80",
  invalidation: "#ef6767",
  confirmation: "#e0b064",
  potentialObjective: "#8fa8c9",
  structure: "#5b6b85",
  diagnostic: "#5b6478",
  currentPrice: "#8b97ab",
};

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
            : PALETTE.entry,
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
