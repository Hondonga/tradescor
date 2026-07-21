// Generic pixel-space collision resolution for right-edge price tags and
// on-chart labels. This is purely a layout concern: it repositions and
// hides DISPLAY elements based on their already-assigned overlay priority.
// It never changes a price, a label's text, or which overlays are allowed
// to be visible (that's overlay-density.ts / selectVisibleOverlays).
export interface CollisionItem {
  id: string;
  /** Natural (unadjusted) vertical center, in px. */
  y: number;
  /** Rendered height, in px. */
  height: number;
  priority: number;
}

export interface ResolvedItem extends CollisionItem {
  /** Final vertical center after collision resolution. */
  resolvedY: number;
  /** resolvedY - y, for drawing a connector line back to the true position. */
  offset: number;
  visible: boolean;
}

export interface ResolveCollisionsOptions {
  /** Minimum vertical gap required between two items' edges, in px. */
  minGap?: number;
  /** Available vertical space; items pushed outside it are hidden (lowest priority first). */
  viewportHeight?: number;
}

/**
 * Resolves vertical overlap among same-column items (e.g. right-edge price
 * tags) by nudging lower-priority items away from higher-priority ones, and
 * hiding whatever still doesn't fit. Deterministic and priority-ordered so
 * the same overlay set always produces the same layout.
 */
export function resolveCollisions(
  items: CollisionItem[],
  options: ResolveCollisionsOptions = {},
): ResolvedItem[] {
  const minGap = options.minGap ?? 2;
  if (!items.length) return [];

  // Highest priority first: higher-priority items claim their natural slot;
  // lower-priority items get pushed away from whatever's already placed.
  const order = [...items].sort((a, b) => b.priority - a.priority || a.y - b.y);
  const placed: ResolvedItem[] = [];

  for (const item of order) {
    let y = item.y;
    let moved = true;
    // Nudge downward until clear of every already-placed item, checking
    // repeatedly since a shift can create a new overlap further down.
    while (moved) {
      moved = false;
      for (const other of placed) {
        const gap = Math.abs(y - other.resolvedY);
        const required = item.height / 2 + other.height / 2 + minGap;
        if (gap < required) {
          y = other.resolvedY + required;
          moved = true;
        }
      }
    }
    placed.push({ ...item, resolvedY: y, offset: y - item.y, visible: true });
  }

  if (options.viewportHeight != null) {
    const limit = options.viewportHeight;
    for (const entry of [...placed].sort((a, b) => a.priority - b.priority)) {
      const top = entry.resolvedY - entry.height / 2;
      const bottom = entry.resolvedY + entry.height / 2;
      if (top < 0 || bottom > limit) entry.visible = false;
    }
  }

  // Return in original input order for stable rendering.
  const byId = new Map(placed.map((entry) => [entry.id, entry]));
  return items.map((item) => byId.get(item.id)!);
}
