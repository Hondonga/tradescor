import { cn } from "@/lib/utils";
import type { Overlay, OverlayCategory } from "@/types";

const TOGGLES: Array<[OverlayCategory, string]> = [
  ["trade_plan", "Plan"],
  ["market_structure", "Structure"],
  ["context_levels", "Context"],
  ["advanced_smc", "Advanced"],
  ["previous_setup", "Previous"],
];

export interface ChartToolbarProps {
  visibility: Record<OverlayCategory, boolean>;
  onToggle: (category: OverlayCategory) => void;
  previousSetupCount?: number;
  hiddenEvidenceCount?: number;
  overlays: Overlay[];
  selectedOverlayId: string;
  onSelectOverlay: (id: string) => void;
}

/** Compact segmented toolbar (Milestone: chart redesign, §2). Fixed 32px
 * height, single-row, no wrapped labels. */
export function ChartToolbar({
  visibility,
  onToggle,
  previousSetupCount = 0,
  hiddenEvidenceCount = 0,
  overlays,
  selectedOverlayId,
  onSelectOverlay,
}: ChartToolbarProps) {
  return (
    <div className="flex h-8 shrink-0 items-center gap-1 border-b border-white/[.07] px-2">
      {TOGGLES.map(([category, label]) => {
        const active = visibility[category];
        const disabled = category === "previous_setup" && previousSetupCount === 0;
        const count = category === "previous_setup" ? previousSetupCount : 0;
        const showHiddenDot = category === "advanced_smc" && !active && hiddenEvidenceCount > 0;
        return (
          <button
            key={category}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => onToggle(category)}
            className={cn(
              "inline-flex h-6 shrink-0 items-center gap-1 whitespace-nowrap rounded border px-2 text-[10px] font-medium leading-none transition-colors",
              active
                ? "border-white/[.14] bg-white/[.09] text-zinc-100"
                : "border-white/[.08] bg-transparent text-zinc-500 hover:text-zinc-300",
              disabled && "cursor-not-allowed opacity-35",
            )}
          >
            {label}
            {count > 0 && (
              <span className="rounded-sm bg-white/10 px-1 text-[9px] tabular-nums text-zinc-300">
                {count}
              </span>
            )}
            {showHiddenDot && (
              <span
                aria-label={`${hiddenEvidenceCount} hidden diagnostic overlays`}
                className="h-1.5 w-1.5 rounded-full bg-amber-400/80"
              />
            )}
          </button>
        );
      })}
      {overlays.length > 0 && (
        <select
          aria-label="Inspect chart drawing metadata"
          className="ml-auto h-6 max-w-48 shrink-0 rounded border border-white/10 bg-black px-2 font-mono text-[9px] text-zinc-400"
          value={selectedOverlayId}
          onChange={(event) => onSelectOverlay(event.target.value)}
        >
          <option value="">Inspect drawing…</option>
          {overlays.map((overlay) => (
            <option key={overlay.overlay_id} value={overlay.overlay_id}>
              {overlay.label}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
