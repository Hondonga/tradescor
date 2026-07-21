import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  ChartCandlestick,
  Copy,
  RefreshCw,
  Search,
  SlidersHorizontal,
  TestTube2,
} from "lucide-react";
import { useRouter } from "@tanstack/react-router";
import { useTerminalStore } from "@/store/terminal-store";
import { useAnalysis } from "@/hooks/use-analysis";
const commands = [
  { label: "Open Markets", to: "/markets", Icon: BarChart3 },
  { label: "Open Workspace", to: "/workspace", Icon: ChartCandlestick },
  { label: "Open Research", to: "/research", Icon: TestTube2 },
];
export function CommandMenu() {
  const store = useTerminalStore(),
    router = useRouter(),
    analysis = useAnalysis(),
    [query, setQuery] = useState("");
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        store.setCommandOpen(!store.commandOpen);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [store.commandOpen]);
  const rows = useMemo(
    () =>
      commands.filter((x) =>
        x.label.toLowerCase().includes(query.toLowerCase()),
      ),
    [query],
  );
  if (!store.commandOpen) return null;
  const run = (action: () => void) => {
    action();
    store.setCommandOpen(false);
  };
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-start bg-black/60 pt-[14vh] backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Command menu"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) store.setCommandOpen(false);
      }}
    >
      <div className="w-[520px] overflow-hidden rounded-lg border border-white/10 bg-[#10141c] shadow-2xl">
        <label className="flex h-12 items-center gap-3 border-b border-white/[.07] px-4">
          <Search size={15} className="text-zinc-500" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
            placeholder="Search commands or symbols…"
          />
          <kbd>Esc</kbd>
        </label>
        <div className="max-h-80 p-2">
          {rows.map(({ label, to, Icon }) => (
            <button
              key={to}
              className="command-row"
              onClick={() => run(() => router.navigate({ to }))}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
          <button
            className="command-row"
            onClick={() => run(() => analysis.mutate())}
          >
            <RefreshCw size={14} />
            Run SMC analysis <kbd>↵</kbd>
          </button>
          <button
            className="command-row"
            onClick={() => run(() => store.toggleOverlay("trade_plan"))}
          >
            <SlidersHorizontal size={14} />
            Toggle Trade Plan overlays
          </button>
          <button
            className="command-row"
            onClick={() =>
              run(() =>
                navigator.clipboard.writeText(
                  store.decision?.decision.summary || "No active setup",
                ),
              )
            }
          >
            <Copy size={14} />
            Copy setup summary
          </button>
        </div>
      </div>
    </div>
  );
}
