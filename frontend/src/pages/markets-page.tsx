import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Search, Star } from "lucide-react";
import { useRouter } from "@tanstack/react-router";
import { analyze, listSymbols } from "@/lib/api";
import { useTerminalStore } from "@/store/terminal-store";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatPrice, titleCase } from "@/lib/utils";
import {
  canonicalStatus,
  canonicalStatusTone,
  directionLabel,
  isLateEntryTiming,
} from "@/lib/status-labels";
import type { MarketRow } from "@/types";
const helper = createColumnHelper<MarketRow>();
function segment(row: MarketRow) {
  const d = row.decision;
  if (row.symbol.analysis_supported === false) return "Unsupported Model";
  if (row.error || d?.readiness.state === "insufficient")
    return "Data Problems";
  if (d?.decision.trade_ready) return "Trade Ready";
  if (d?.decision.direction && d.decision.stage.includes("WAIT"))
    return "Developing";
  if (d?.decision.stage) return "Waiting";
  return "No Opportunity";
}
export function MarketsPage() {
  const store = useTerminalStore(),
    router = useRouter(),
    [search, setSearch] = useState(""),
    [marketType, setMarketType] = useState("all"),
    [family, setFamily] = useState("ALL"),
    [support, setSupport] = useState("SUPPORTED"),
    [scanScope, setScanScope] = useState("favorites"),
    [scanning, setScanning] = useState(false);
  const symbols = useQuery({ queryKey: ["symbols"], queryFn: listSymbols });
  useEffect(() => {
    if (!symbols.data || store.markets.length) return;
    store.setMarkets(symbols.data.map((symbol) => ({ symbol, decision: symbol.cached_analysis?.decision, price: symbol.cached_analysis?.decision?.market.current_price, lastAnalysis: symbol.cached_analysis?.last_analysis, analysisDepth: symbol.cached_analysis?.analysis_depth === "full" ? "Full" : symbol.cached_analysis ? "Lightweight" : undefined, lastFullAnalysis: symbol.cached_analysis?.analysis_depth === "full" ? symbol.cached_analysis.last_analysis : undefined, dataFreshness: symbol.cached_analysis?.data_freshness })));
  }, [symbols.data, store]);
  const scan = async () => {
    if (!symbols.data) return;
    setScanning(true);
    const universe = symbols.data
        .filter((symbol) => marketType === "all" || symbol.market_type === marketType)
        .filter((symbol) => symbol.analysis_supported !== false)
        .filter((symbol) => scanScope === "all" || scanScope === "family" ? scanScope === "all" || family === "ALL" || symbol.family === family : store.watchlist.includes(symbol.provider_symbol));
    const rows: MarketRow[] = [];
    for (let index = 0; index < universe.length; index += 2) {
      rows.push(...await Promise.all(universe.slice(index, index + 2).map(async (symbol) => {
          try {
            const model = symbol.available_models.some(
              (item) => item.id === store.model,
            )
              ? store.model
              : symbol.available_models[0]?.id || "auto";
            const payload = await analyze(symbol, store.timeframe, model, undefined, { analysisDepth: "lightweight", priority: scanScope === "favorites" ? "PRIORITY_2_WATCHLIST" : "PRIORITY_3_RESEARCH_SCAN" });
            return {
              symbol,
              decision: payload.decision,
              price: payload.decision?.market.current_price,
              lastAnalysis: payload.decision?.meta.analysis_time,
              watching: store.watchlist.includes(symbol.provider_symbol),
              analysisDepth: "Lightweight",
              dataFreshness: payload.decision?.readiness.state,
            } as MarketRow;
          } catch (error) {
            return { symbol, error: (error as Error).message } as MarketRow;
          }
        })));
    }
    const unsupported = symbols.data
      .filter(
        (symbol) => marketType === "all" || symbol.market_type === marketType,
      )
      .filter((symbol) => symbol.analysis_supported === false)
      .map((symbol) => ({ symbol, error: "UNSUPPORTED_MODEL" }) as MarketRow);
    const updated = new Map(store.markets.map((row) => [row.symbol.symbol_id, row]));[...rows, ...unsupported].forEach((row) => updated.set(row.symbol.symbol_id, row));store.setMarkets([...updated.values()]);
    setScanning(false);
  };
  const data = useMemo(
    () =>
      store.markets.filter(
        (row) =>
          (marketType === "all" || row.symbol.market_type === marketType) &&
          (family === "ALL" || row.symbol.family === family) &&
          (support === "ALL" || row.symbol.analysis_supported !== false) &&
          (row.symbol.display_name
            .toLowerCase()
            .includes(search.toLowerCase()) ||
            row.symbol.provider_symbol
              .toLowerCase()
              .includes(search.toLowerCase())),
      ),
    [store.markets, marketType, family, support, search],
  );
  const columns = useMemo(
    () => [
      helper.display({
        id: "watch",
        header: "",
        cell: (info) => (
          <button
            aria-label="Toggle watchlist"
            onClick={(event) => {
              event.stopPropagation();
              store.toggleWatch(info.row.original.symbol.provider_symbol);
            }}
          >
            <Star
              size={13}
              className={
                store.watchlist.includes(
                  info.row.original.symbol.provider_symbol,
                )
                  ? "fill-blue-400 text-blue-400"
                  : "text-zinc-700"
              }
            />
          </button>
        ),
      }),
      helper.accessor((x) => x.symbol.display_name, {
        id: "symbol",
        header: "Symbol",
        cell: (i) => (
          <div>
            <b>{i.getValue()}</b>
            <small>{i.row.original.symbol.provider_symbol}</small>
          </div>
        ),
      }),
      helper.accessor(
        (x) => x.symbol.family_display || titleCase(x.symbol.family),
        {
          id: "family",
          header: "Family",
        },
      ),
      helper.accessor("price", {
        header: "Price",
        cell: (i) => (
          <span className="financial">
            {formatPrice(i.getValue(), i.row.original.decision?.precision)}
          </span>
        ),
      }),
      helper.accessor((x) => x.decision?.market.external_structure, {
        id: "external",
        header: "External",
      }),
      helper.accessor((x) => x.decision?.market.internal_structure, {
        id: "internal",
        header: "Internal",
      }),
      helper.accessor((x) => x.decision?.setup.setup_type, {
        id: "setup",
        header: "Active SMC setup",
        cell: (i) => titleCase(i.getValue()) || "—",
      }),
      helper.accessor((x) => x.decision?.decision.direction, {
        id: "direction",
        header: "Looking for",
        cell: (i) => (i.row.original.decision ? directionLabel(i.getValue()) : "—"),
      }),
      helper.accessor((x) => x.decision?.decision.stage, {
        id: "stage",
        header: "Status",
        cell: (i) => {
          const decision = i.row.original.decision;
          if (i.row.original.symbol.analysis_supported === false)
            return <StatusBadge tone="neutral">Unsupported model</StatusBadge>;
          if (!decision) return <StatusBadge tone="neutral">Unanalyzed</StatusBadge>;
          const status = canonicalStatus(decision);
          return <StatusBadge tone={canonicalStatusTone(status)}>{status}</StatusBadge>;
        },
      }),
      helper.accessor((x) => x.decision?.entry_timing?.status, {
        id: "entryTiming",
        header: "Entry timing",
        cell: (i) => {
          const status = i.getValue();
          return status ? status.replace(/_/g, " ").toUpperCase() : "—";
        },
      }),
      helper.accessor(
        (x) => {
          const timing = x.decision?.entry_timing;
          return timing && isLateEntryTiming(timing.status)
            ? timing.next_action
            : x.decision?.decision.next_action;
        },
        {
          id: "nextAction",
          header: "Next action",
          cell: (i) => i.getValue() || "—",
        },
      ),
      helper.accessor((x) => x.decision?.setup.setup_quality_score, {
        id: "quality",
        header: "Trade score",
        cell: (i) => <span className="financial">{i.getValue() ?? "—"}</span>,
      }),
      helper.accessor((x) => x.decision?.setup.quality_grade, {
        id: "confidence",
        header: "Confidence",
        cell: (i) => i.getValue() || "—",
      }),
      helper.accessor((x) => x.decision?.decision.first_blocking_gate, {
        id: "why",
        header: "Why",
        cell: (i) => titleCase(i.getValue()) || "—",
      }),
      helper.accessor((x) => x.decision?.readiness.state, {
        id: "data",
        header: "Data",
      }),
      helper.accessor("analysisDepth", { header: "Analysis depth", cell: (i) => i.getValue() || "—" }),
      helper.accessor("lastFullAnalysis", { header: "Last full analysis", cell: (i) => i.getValue() ? new Date(i.getValue()!).toISOString().slice(11,19) : "—" }),
      helper.accessor("dataFreshness", { header: "Data freshness", cell: (i) => titleCase(i.getValue()) || "—" }),
      helper.accessor("lastAnalysis", {
        header: "Last analysis",
        cell: (i) =>
          i.getValue()
            ? new Date(i.getValue()!).toISOString().slice(11, 19)
            : "—",
      }),
    ],
    [store.watchlist],
  );
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });
  const open = (row: MarketRow) => {
    store.selectMarket(row);
    store.setRoute("workspace");
    router.navigate({ to: "/workspace" });
  };
  return (
    <div className="page markets-page">
      <header className="page-title">
        <div>
          <p>Multi-symbol scanner</p>
          <h1>Markets</h1>
        </div>
        <Button variant="primary" onClick={scan} disabled={scanning}>
          {scanning ? "Scanning completed candles…" : "Scan markets"}
        </Button>
      </header>
      <div className="filter-bar">
        <div className="market-tabs" role="tablist" aria-label="Market type">
          {[["all", "All"], ["derived", "Derived"], ["forex", "Forex"], ["crypto", "Crypto"], ["index", "Indices"]].map(([value, label]) => (
            <button key={value} role="tab" aria-selected={marketType === value} className={marketType === value ? "active" : ""} onClick={() => { setMarketType(value); setFamily("ALL"); }}>
              {label}
            </button>
          ))}
        </div>
        <label>
          <Search size={13} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search symbols"
          />
        </label>
        <select value={family} onChange={(e) => setFamily(e.target.value)}>
          <option>ALL</option>
          {[...new Set(symbols.data?.map((x) => x.family) || [])].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
        <select value={support} onChange={(e) => setSupport(e.target.value)}>
          <option value="SUPPORTED">Supported only</option>
          <option value="ALL">All support states</option>
        </select>
        <select aria-label="Scan scope" value={scanScope} onChange={(e) => setScanScope(e.target.value)}>
          <option value="favorites">Favorites</option><option value="family">Current family</option><option value="all">All supported symbols</option>
        </select>
        <span>
          {data.length} markets · {store.timeframe} · {titleCase(store.model)}
        </span>
      </div>
      {!store.markets.length ? (
        <EmptyState
          icon={Search}
          title="No analysis yet"
          description="Run the selected market models across the current universe to populate structure, lifecycle, and blockers."
          action="Scan markets"
          onAction={scan}
        />
      ) : (
        <div className="market-table-wrap">
          <table className="market-table">
            <thead>
              {table.getHeaderGroups().map((group) => (
                <tr key={group.id}>
                  {group.headers.map((header) => (
                    <th key={header.id}>
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {[
                "Trade Ready",
                "Developing",
                "Waiting",
                "No Opportunity",
                "Data Problems",
                "Unsupported Model",
              ].map((group) => (
                <FragmentRows
                  key={group}
                  label={group}
                  rows={table
                    .getRowModel()
                    .rows.filter((row) => segment(row.original) === group)}
                  open={open}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
function FragmentRows({
  label,
  rows,
  open,
}: {
  label: string;
  rows: ReturnType<
    ReturnType<typeof useReactTable<MarketRow>>["getRowModel"]
  >["rows"];
  open: (row: MarketRow) => void;
}) {
  if (!rows.length) return null;
  return (
    <>
      <tr className="segment-row">
        <td colSpan={19}>
          {label}
          <span>{rows.length}</span>
        </td>
      </tr>
      {rows.map((row) => (
        <tr
          key={row.id}
          tabIndex={0}
          onClick={() => open(row.original)}
          onKeyDown={(e) => {
            if (e.key === "Enter") open(row.original);
          }}
        >
          {row.getVisibleCells().map((cell) => (
            <td key={cell.id}>
              {flexRender(cell.column.columnDef.cell, cell.getContext())}
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
