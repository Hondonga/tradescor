import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { Search, X } from "lucide-react";
import { useState } from "react";
import { useTerminalStore } from "@/store/terminal-store";
import { useAnalysis } from "@/hooks/use-analysis";
import { MarketChart } from "@/components/chart/market-chart";
import { DecisionRail } from "@/components/terminal/decision-rail";
import { OpportunityQueue } from "@/components/terminal/opportunity-queue";
import { Button } from "@/components/ui/button";
import { cancelLatestSetupSearch, startLatestSetupSearch } from "@/lib/api";
import { useHistorySearchPolling } from "@/hooks/use-history-search-polling";
export function WorkspacePage() {
  const store = useTerminalStore(),
    analysis = useAnalysis();
  const [period,setPeriod]=useState<30|90>(30);
  useHistorySearchPolling();
  const findLatest=async()=>store.setHistoricalSearch(await startLatestSetupSearch(period));
  const watch = store.markets.filter((x) =>
    store.watchlist.includes(x.symbol.provider_symbol),
  );
  return (
    <div className="workspace-page">
      <div className="flex h-10 items-center gap-2 border-b border-white/[.07] bg-[#0b0e14] px-3 text-[11px]">
        <Button className="h-7" variant={store.workspaceMode==="live"?"secondary":"ghost"} onClick={()=>store.returnLive()}>LIVE ANALYSIS</Button>
        <Button className="h-7" variant={store.workspaceMode==="historical"?"secondary":"ghost"} disabled={!store.historicalJobId} onClick={()=>{}}>HISTORICAL INSPECTION</Button>
        <span className="ml-2 text-zinc-500">No strategy for this market has passed the required historical validation, so Auto is unavailable. Use Research to review complete plans manually.</span>
        <select className="ml-auto rounded border border-white/10 bg-black px-2 py-1" value={period} onChange={e=>setPeriod(+e.target.value as 30|90)}><option value={30}>30 days</option><option value={90}>90 days</option></select>
        <Button className="h-7" onClick={findLatest} disabled={["queued","running"].includes(store.historicalSearch?.state || "")}><Search size={12}/> Find latest valid setup</Button>
        {["queued","running"].includes(store.historicalSearch?.state || "") && <><span className="font-mono text-blue-300">{store.historicalSearch?.processed_candles}/{store.historicalSearch?.total_candles || "…"} · {store.historicalSearch?.trade_ready_found} ready</span><Button className="h-7" variant="ghost" onClick={async()=>store.setHistoricalSearch(await cancelLatestSetupSearch(store.historicalSearch!.job_id))}><X size={12}/> Cancel</Button></>}
      </div>
      <PanelGroup
        direction="horizontal"
        onLayout={(sizes) => store.setPanels(sizes[0], sizes[2])}
      >
        <Panel
          defaultSize={store.leftPanel}
          minSize={12}
          collapsible
          collapsedSize={0}
          order={1}
        >
          <OpportunityQueue
            rows={watch}
            onSelect={(row) => store.selectMarket(row)}
            dataReadiness={store.dataReadiness}
            onAnalyzeNow={() => analysis.mutate()}
            analyzePending={analysis.isPending}
          />
        </Panel>
        <PanelResizeHandle className="resize-handle" />
        <Panel defaultSize={58} minSize={40} order={2}>
          <MarketChart />
        </Panel>
        <PanelResizeHandle className="resize-handle" />
        <Panel
          defaultSize={store.rightPanel}
          minSize={18}
          collapsible
          collapsedSize={0}
          order={3}
        >
          <DecisionRail />
        </Panel>
      </PanelGroup>
    </div>
  );
}
