import { cn } from "@/lib/utils";
import type { DensityMode } from "@/lib/overlay-density";
import type { Overlay, OverlayCategory } from "@/types";

const TOGGLES: Array<[OverlayCategory, string]> = [
  ["trade_plan", "Plan"],
  ["market_structure", "Structure"],
  ["context_levels", "Context"],
  ["advanced_smc", "Advanced"],
  ["previous_setup", "Previous"],
];

const DENSITY_OPTIONS: Array<[DensityMode, string]> = [
  ["clean", "Clean"],
  ["standard", "Standard"],
  ["research", "Research"],
];

const MODE_BADGE: Record<"live" | "historical" | "replay", { text: string; className: string }> = {
  live: { text: "LIVE", className: "border-bullish/40 bg-bullish/10 text-bullish" },
  historical: { text: "HISTORICAL", className: "border-neutral/40 bg-neutral/10 text-neutral" },
  replay: { text: "REPLAY", className: "border-research/40 bg-research/10 text-research" },
};

export interface ChartToolbarProps {
  visibility: Record<OverlayCategory, boolean>;
  onToggle: (category: OverlayCategory) => void;
  previousSetupCount?: number;
  hiddenEvidenceCount?: number;
  overlays: Overlay[];
  selectedOverlayId: string;
  onSelectOverlay: (id: string) => void;
  densityMode?: DensityMode;
  onDensityModeChange?: (mode: DensityMode) => void;
  workspaceMode?: "live" | "historical" | "replay";
  connection?: string;
  onAutoFit?: () => void;
  onResetView?: () => void;
  diagnosticsVisible?: boolean;
  onToggleDiagnostics?: () => void;
}

/**
 * Compact, professional toolbar (Phase 3 §4). Three groups on one row:
 * overlay-visibility toggles + drawing inspector (left/existing), density
 * mode + live/historical/replay mode (center), and chart actions (right).
 * Symbol, provider status, timeframe and model/strategy already have a
 * dedicated, prominent home directly above this toolbar (the Workspace
 * command bar) — they are deliberately not duplicated here. Fixed 32px
 * height, single row, no wrapped labels.
 */
export function ChartToolbar({
  visibility,
  onToggle,
  previousSetupCount = 0,
  hiddenEvidenceCount = 0,
  overlays,
  selectedOverlayId,
  onSelectOverlay,
  densityMode,
  onDensityModeChange,
  workspaceMode,
  onAutoFit,
  onResetView,
  diagnosticsVisible = false,
  onToggleDiagnostics,
}: ChartToolbarProps) {
  const modeBadge = workspaceMode ? MODE_BADGE[workspaceMode] : undefined;

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

      {modeBadge && (
        <span
          className={cn(
            "ml-2 hidden shrink-0 rounded border px-1.5 py-0.5 text-[9px] font-semibold leading-none sm:inline-block",
            modeBadge.className,
          )}
        >
          {modeBadge.text}
        </span>
      )}

      {densityMode && onDensityModeChange && (
        <div
          role="group"
          aria-label="Chart density mode"
          className="ml-2 hidden shrink-0 items-center gap-0.5 rounded border border-white/[.08] p-0.5 md:flex"
        >
          {DENSITY_OPTIONS.map(([mode, label]) => (
            <button
              key={mode}
              type="button"
              aria-pressed={densityMode === mode}
              onClick={() => onDensityModeChange(mode)}
              className={cn(
                "h-5 shrink-0 rounded-sm px-1.5 text-[9px] font-medium leading-none transition-colors",
                densityMode === mode
                  ? "bg-white/[.12] text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <div className="ml-auto flex shrink-0 items-center gap-1">
        {onAutoFit && (
          <button
            type="button"
            title="Auto-fit chart to visible candles"
            aria-label="Auto-fit chart"
            onClick={onAutoFit}
            className="hidden h-6 shrink-0 items-center rounded border border-white/[.08] px-2 text-[10px] text-zinc-500 hover:text-zinc-300 lg:inline-flex"
          >
            Auto-fit
          </button>
        )}
        {onResetView && (
          <button
            type="button"
            title="Reset chart view"
            aria-label="Reset chart view"
            onClick={onResetView}
            className="hidden h-6 shrink-0 items-center rounded border border-white/[.08] px-2 text-[10px] text-zinc-500 hover:text-zinc-300 lg:inline-flex"
          >
            Reset
          </button>
        )}
        {onToggleDiagnostics && (
          <button
            type="button"
            aria-pressed={diagnosticsVisible}
            title="Toggle diagnostics"
            aria-label="Toggle diagnostics visibility"
            onClick={onToggleDiagnostics}
            className={cn(
              "hidden h-6 shrink-0 items-center rounded border px-2 text-[10px] transition-colors md:inline-flex",
              diagnosticsVisible
                ? "border-white/[.14] bg-white/[.09] text-zinc-100"
                : "border-white/[.08] text-zinc-500 hover:text-zinc-300",
            )}
          >
            Diagnostics
          </button>
        )}
        {overlays.length > 0 && (
          <select
            aria-label="Inspect chart drawing metadata"
            className="h-6 max-w-48 shrink-0 rounded border border-white/10 bg-black px-2 font-mono text-[9px] text-zinc-400"
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
    </div>
  );
}
