import { Outlet, useRouter, useRouterState } from "@tanstack/react-router";
import { Tooltip } from "@base-ui/react/tooltip";
import {
  BarChart3,
  ChartCandlestick,
  ChevronDown,
  Command,
  RefreshCw,
  Settings,
  TestTube2,
  UserRound,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { listSymbols } from "@/lib/api";
import { useAnalysis } from "@/hooks/use-analysis";
import { useTerminalStore } from "@/store/terminal-store";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { CommandMenu } from "@/components/terminal/command-menu";
import type { RouteId } from "@/types";
import { useEffect, useState } from "react";

const nav = [
  {
    id: "markets" as RouteId,
    to: "/markets",
    label: "Markets",
    Icon: BarChart3,
  },
  {
    id: "workspace" as RouteId,
    to: "/workspace",
    label: "Workspace",
    Icon: ChartCandlestick,
  },
  {
    id: "research" as RouteId,
    to: "/research",
    label: "Research",
    Icon: TestTube2,
  },
];
export function AppShell() {
  const [operatingMode, setOperatingMode] = useState("FOCUSED");
  const store = useTerminalStore(),
    router = useRouter(),
    path = useRouterState({ select: (s) => s.location.pathname }),
    symbols = useQuery({
      queryKey: ["symbols"],
      queryFn: listSymbols,
      staleTime: 300000,
    }),
    analysis = useAnalysis();
  useEffect(() => {
    if (path.startsWith("/workspace")) analysis.mutate();
    // Analyze only the selected symbol when it changes or Workspace opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.providerSymbol, path]);
  useEffect(() => {
    if (!path.startsWith("/workspace")) return;
    let timer:number;
    const schedule=()=>{
      const now=Date.now(),fiveMinutes=300000,next=Math.ceil(now/fiveMinutes)*fiveMinutes+2000;
      timer=window.setTimeout(()=>{analysis.mutate();schedule();},Math.max(1000,next-now));
    };
    schedule();return()=>window.clearTimeout(timer);
    // The timer intentionally follows completed UTC M5 boundaries only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path,store.providerSymbol]);
  const scheduleLabel = store.marketSchedule === "24_7" ? "24/7" : store.marketSchedule === "24_5" ? "24/5" : "Exchange";
  const providerLabel = store.marketSource === "deriv" ? "Deriv" : "Twelve Data";
  return (
    <Tooltip.Provider delay={250}>
      <div className="terminal-shell">
        <aside className="left-rail">
          <button className="brand-mark" aria-label="TradeScor">
            TS
          </button>
          <nav>
            {nav.map(({ id, to, label, Icon }) => (
              <Tooltip.Root key={id}>
                <Tooltip.Trigger
                  render={
                    <button
                      className={path.startsWith(to) ? "active" : ""}
                      onClick={() => {
                        store.setRoute(id);
                        router.navigate({ to });
                      }}
                    />
                  }
                >
                  <Icon size={17} />
                  <span className="sr-only">{label}</span>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Positioner sideOffset={8}>
                    <Tooltip.Popup className="tooltip">{label}</Tooltip.Popup>
                  </Tooltip.Positioner>
                </Tooltip.Portal>
              </Tooltip.Root>
            ))}
          </nav>
          <div className="mt-auto grid place-items-center gap-2 py-3">
            <span className={`connection-dot ${store.connection}`} />
            <span className="sr-only">Connection {store.connection}</span>
          </div>
        </aside>
        <main className="min-w-0">
          <header className="command-bar">
            <div className="command-controls">
              <select
                aria-label="Symbol"
                value={store.symbol.symbol_id}
                onChange={(event) => {
                  const selected = symbols.data?.find(
                    (x) => x.symbol_id === event.target.value,
                  );
                  if (selected) store.setSymbol(selected);
                }}
              >
                <option value={store.symbol.symbol_id}>
                  {store.symbol.display_name}
                </option>
                {symbols.data
                  ?.filter(
                    (x) => x.symbol_id !== store.symbol.symbol_id,
                  )
                  .map((row) => (
                    <option
                      key={row.symbol_id}
                      value={row.symbol_id}
                    >
                      {row.display_name}
                    </option>
                  ))}
              </select>
              {store.modelNotice && <span className="model-notice">{store.modelNotice}</span>}
              <select
                aria-label="Timeframe"
                value={store.timeframe}
                onChange={(e) => store.setTimeframe(e.target.value)}
              >
                {["M5", "M15", "H1", "H4"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
              <select
                aria-label="Model"
                value={store.model}
                onChange={(e) => store.setModel(e.target.value)}
              >
                {store.availableModels.map((model) => (
                  <option key={model.id} value={model.id}>{model.label}</option>
                ))}
              </select>
              <Button
                aria-label="Refresh analysis"
                onClick={() => analysis.mutate()}
                disabled={analysis.isPending}
              >
                <RefreshCw
                  size={13}
                  className={analysis.isPending ? "animate-spin" : ""}
                />
              </Button>
            </div>
            <div className="command-status">
              <StatusBadge
                tone={
                  store.connection === "connected"
                    ? "ready"
                    : store.connection === "provider_error"
                      ? "error"
                      : "neutral"
                }
              >
                {store.connection.replaceAll("_", " ")}
              </StatusBadge>
              <span><small>Provider</small><b>{providerLabel}</b></span>
              <span><small>Market</small><b>{scheduleLabel}</b></span>
              {store.marketType === "forex" && store.decision?.market.session && (
                <span><small>Session</small><b>{store.decision.market.session}</b></span>
              )}
              <span><small>Clock</small><b>UTC</b></span>
              <span>
                <small>Data</small>
                <b>{store.dataReadiness}</b>
              </span>
              <span>
                <small>Last candle</small>
                <b>
                  {store.lastCompletedCandle
                    ? new Date(store.lastCompletedCandle)
                        .toISOString()
                        .slice(11, 19)
                    : "—"}
                </b>
              </span>
              <Button
                className="shortcut"
                onClick={() => store.setCommandOpen(true)}
              >
                <Command size={13} />K
              </Button>
              <div className="relative">
                <Button
                  aria-label="Profile and system menu"
                  onClick={() => store.setSystemMenu(!store.systemMenuOpen)}
                >
                  <UserRound size={13} />
                  <ChevronDown size={11} />
                </Button>
                {store.systemMenuOpen && (
                  <div className="system-menu">
                    <button>
                      <Settings size={13} />
                      System preferences
                    </button>
                    <button>Reconnect data</button>
                    <label className="grid gap-1 px-2 py-1 text-[9px] text-zinc-500">
                      Operating mode
                      <select value={operatingMode} onChange={async (event) => { const mode=event.target.value;setOperatingMode(mode);await fetch("/api/system/analysis-priority",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mode})}); }}>
                        <option>FOCUSED</option><option>BALANCED</option><option>RESEARCH</option>
                      </select>
                    </label>
                    <small>TradeScor · paper research only</small>
                  </div>
                )}
              </div>
            </div>
          </header>
          <AnimatePresence mode="wait">
            <motion.div
              key={path}
              className="route-frame"
              initial={{ opacity: 0, y: 2 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
        <CommandMenu />
      </div>
    </Tooltip.Provider>
  );
}
