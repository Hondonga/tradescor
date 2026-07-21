// Presentation-only label composition for chart drawings. The backend
// already sends a normalized, semantic base label per overlay (including a
// mode-aware current-price label — "Current" / "Decision-time Current" /
// "Replay Current" / "Previous setup price"); this module only decides how
// much of that label to show and how to shorten it for a compact right-edge
// tag. It never invents or overrides wording the backend didn't send, with
// one narrow exception: the current-price tag's short form (Phase 3 §17 —
// "CURRENT" / "DECISION TIME" / "REPLAY PRICE") is derived directly from the
// overlay's own backend-sent `overlay_mode` enum, not guessed by the
// frontend, so it can never disagree with what the backend normalized.
import type { Overlay } from "@/types";
import { overlayRole } from "./overlays";

const STATUS_PREFIXES = ["DEVELOPING · ", "DEVELOPING: ", "DEVELOPING - "];

/** Removes any (possibly repeated) lifecycle-status prefix from a label. */
export function stripStatusPrefix(label: string): string {
  let text = String(label || "").trim();
  let changed = true;
  while (changed) {
    changed = false;
    for (const prefix of STATUS_PREFIXES) {
      if (text.toUpperCase().startsWith(prefix)) {
        text = text.slice(prefix.length);
        changed = true;
      }
    }
  }
  return text;
}

/**
 * The on-chart zone/line label. The decision rail already communicates
 * lifecycle state (SETUP DEVELOPING, PLAN VALIDATION, ...), so the chart
 * label should read as a plain semantic name — "M15 PULLBACK AREA", never
 * "DEVELOPING · DEVELOPING · M15 Pullback Area".
 */
export function chartLabel(overlay: Overlay): string {
  return stripStatusPrefix(overlay.label).toUpperCase();
}

const TAG_TEXT: Record<string, string> = {
  entry: "ENTRY",
  trade_entry: "ENTRY",
  preferred_entry: "ENTRY",
  stop: "STOP",
  stop_loss: "STOP",
  trade_stop: "STOP",
  tp1: "TP1",
  target_1: "TP1",
  tp2: "TP2",
  target_2: "TP2",
  final_invalidation: "INVALID",
  invalidation: "INVALID",
  setup_invalidation: "INVALID",
};

// Phase 3 §17 — the current-price tag's text must reflect Workspace mode
// (LIVE/HISTORICAL_INSPECTION/REPLAY), keyed off the overlay's own
// overlay_mode metadata rather than any frontend-side mode tracking, so it
// can never drift from what the backend actually normalized this decision
// as. PREVIOUS_SETUP intentionally falls through to "" here — per §17,
// previous-setup pricing must never replace/relabel the current-price tag;
// it renders through its own separate historical overlay rows instead.
const CURRENT_PRICE_TAG_TEXT: Record<string, string> = {
  LIVE: "CURRENT",
  HISTORICAL_INSPECTION: "DECISION TIME",
  REPLAY: "REPLAY PRICE",
};

/** Short (<=6 char) right-edge tag text, distinct from the full chart label. */
export function tagText(overlay: Overlay): string {
  if (overlay.type === "current_price") {
    const mode = String(overlay.metadata.overlay_mode || "");
    return CURRENT_PRICE_TAG_TEXT[mode] || "";
  }
  const role = String(overlay.metadata.plan_role || overlay.type || "").toLowerCase();
  if (role in TAG_TEXT) return TAG_TEXT[role];
  const words = chartLabel(overlay).split(/\s+/).filter(Boolean);
  if (!words.length) return "";
  if (words.length === 1) return words[0].slice(0, 8);
  return words.slice(0, 2).join(" ");
}

// Right-edge tag priority (Milestone: chart redesign, §7) — a fixed display
// hierarchy distinct from the backend's overlay.priority, used only to
// decide which tags stay visible when vertical space is tight.
const TAG_RANK: Record<string, number> = {
  current_price: 100,
  entry: 95,
  stop: 90,
  tp1: 85,
  tp2: 80,
  invalidation: 75,
  confirmation: 70,
  entry_zone: 65,
  potential_objective: 60,
};

export function tagPriority(overlay: Overlay): number {
  if (overlay.type === "current_price") return TAG_RANK.current_price;
  const role = overlayRole(overlay);
  if (role && role in TAG_RANK) return TAG_RANK[role];
  const type = overlay.type.toLowerCase();
  if (type.includes("confirmation")) return TAG_RANK.confirmation;
  if (type.includes("objective")) return TAG_RANK.potential_objective;
  return 50; // structural references and everything else
}
