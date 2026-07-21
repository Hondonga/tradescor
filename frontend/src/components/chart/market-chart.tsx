import { useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  createChart,
  LineStyle,
  type AutoscaleInfo,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useQuery } from "@tanstack/react-query";
import { useTerminalStore } from "@/store/terminal-store";
import { chartPriceFormat, formatPrice } from "@/lib/utils";
import { selectVisibleOverlays } from "@/lib/overlays";
import { applyDensity, hiddenEvidenceCount } from "@/lib/overlay-density";
import { styleForOverlay, type LineStyleToken } from "@/lib/overlay-style-registry";
import { computeZoneRect, type ZoneRect } from "@/lib/overlay-layout";
import { actionablePriceRange } from "@/lib/chart/priceScaleRange";
import { applySetupFocus } from "@/lib/chart/setupFocus";
import { ChartToolbar } from "./chart-toolbar";
import { ChartZoneLayer } from "./chart-zone-layer";
import { ChartPriceTags } from "./chart-price-tags";
import { ChartEventMarkers } from "./chart-event-markers";
import { ChartSetupSummary } from "./chart-setup-summary";
import { DrawingInspector } from "./drawing-inspector";
import type { Overlay } from "@/types";

async function loadCandles(
  symbol: string,
  displayName: string,
  timeframe: string,
  provider: string,
  marketType: string,
) {
  const q = new URLSearchParams({
    symbol,
    display_name: displayName,
    timeframe,
    provider,
    asset_class: marketType === "derived" ? "derived_index" : marketType,
    bars: "600",
  });
  const response = await fetch(`/api/candles?${q}`);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Chart data unavailable");
  return (body.candles || body.data || body).map((row: any) => ({
    time: toTimestamp(row.time),
    open: +row.open,
    high: +row.high,
    low: +row.low,
    close: +row.close,
  }));
}

const LINE_STYLE: Record<LineStyleToken, LineStyle> = {
  solid: LineStyle.Solid,
  dashed: LineStyle.Dashed,
  dotted: LineStyle.Dotted,
};

interface ChartLayout {
  zones: Array<{ rect: ZoneRect; overlay: Overlay }>;
  lineOverlays: Overlay[];
  markerOverlays: Overlay[];
  chartHeight: number;
}

export function MarketChart() {
  const root = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [layout, setLayout] = useState<ChartLayout>({
    zones: [],
    lineOverlays: [],
    markerOverlays: [],
    chartHeight: 0,
  });
  const [selectedOverlayId, setSelectedOverlayId] = useState("");
  const store = useTerminalStore();
  const query = useQuery({
    queryKey: [
      "candles",
      store.marketSource,
      store.symbol.provider_symbol,
      store.timeframe,
    ],
    queryFn: () =>
      loadCandles(
        store.symbol.provider_symbol,
        store.symbol.display_name,
        store.timeframe,
        store.marketSource,
        store.marketType,
      ),
    enabled: store.workspaceMode === "live",
    refetchInterval:
      store.workspaceMode === "live" && store.connection === "connected"
        ? 15_000
        : false,
  });

  const permittedOverlays = useMemo(
    () =>
      selectVisibleOverlays({
        decision: store.decision,
        symbol: store.symbol,
        timeframe: store.timeframe,
        workspaceMode: store.workspaceMode,
        connection: store.connection,
        visibility: store.overlayVisibility,
      }),
    [
      store.connection,
      store.decision,
      store.overlayVisibility,
      store.symbol,
      store.timeframe,
      store.workspaceMode,
    ],
  );

  // Density is a further default-view refinement on top of the toggle-based
  // permission list above — it never widens what's already been filtered
  // out by ownership/lifecycle/toggle rules. Setup Focus (Phase 3 §5) is a
  // further narrowing on top of that, enabled by default specifically in
  // CLEAN mode — switching density mode away from CLEAN is how a trader
  // turns it off.
  const visibleOverlays = useMemo(() => {
    const densityFiltered = applyDensity(permittedOverlays, store.densityMode);
    return store.densityMode === "clean"
      ? applySetupFocus(densityFiltered, store.decision)
      : densityFiltered;
  }, [permittedOverlays, store.densityMode, store.decision]);
  const hiddenByDensity = useMemo(
    () => hiddenEvidenceCount(permittedOverlays, store.densityMode),
    [permittedOverlays, store.densityMode],
  );
  const previousSetupCount = useMemo(
    () => (permittedOverlays.some((o) => o.category === "historical") ? 1 : 0),
    [permittedOverlays],
  );

  const selectedOverlay = visibleOverlays.find(
    (overlay) => overlay.overlay_id === selectedOverlayId,
  );

  useEffect(() => {
    if (!root.current) return;
    const chart = createChart(root.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#080b10" },
        textColor: "#748196",
        fontFamily: "Geist Mono",
      },
      grid: {
        vertLines: { color: "#111722" },
        horzLines: { color: "#111722" },
      },
      rightPriceScale: { borderColor: "#1a2230" },
      timeScale: {
        borderColor: "#1a2230",
        timeVisible: true,
        secondsVisible: false,
      },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#2fad79",
      downColor: "#e25858",
      borderVisible: false,
      wickUpColor: "#2fad79",
      wickDownColor: "#e25858",
      // The normalized current-price overlay owns this visual globally, and
      // the custom right-edge tag system (ChartPriceTags) owns every other
      // overlay's axis label. Hiding the library defaults prevents doubled
      // labels at the same tick.
      priceLineVisible: false,
      lastValueVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    const resize = () => chart.timeScale().fitContent();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const rows =
      store.workspaceMode === "live"
        ? query.data || []
        : store.historicalCandles.map((row) => ({
            ...row,
            time: toTimestamp(row.time),
          }));
    if (!seriesRef.current) return;
    seriesRef.current.setData(rows as any);
    if (rows.length) chartRef.current?.timeScale().fitContent();
  }, [query.data, store.historicalCandles, store.workspaceMode]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    const priceFormat = chartPriceFormat(store.decision?.precision);
    if (priceFormat) series.applyOptions({ priceFormat });
  }, [store.decision?.precision]);

  // Single reconciliation pass for every overlay-driven visual: native price
  // lines (used for their horizontal line only — axis labels are disabled
  // in favor of the custom tag layer), zone rectangles, and the layout data
  // ChartPriceTags/ChartZoneLayer/ChartEventMarkers need to position
  // themselves. All price lines are torn down and recreated together so
  // there is never a leaked or duplicate line for a stale symbol/overlay.
  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series) return;
    series.applyOptions({
      autoscaleInfoProvider: (original: () => AutoscaleInfo | null) => {
        const base = original();
        const range = actionablePriceRange(visibleOverlays);
        if (!range) return base;
        const priceRange = base?.priceRange
          ? {
              minValue: Math.min(base.priceRange.minValue, range.minValue),
              maxValue: Math.max(base.priceRange.maxValue, range.maxValue),
            }
          : range;
        return { priceRange, margins: base?.margins };
      },
    });
    series.priceScale().applyOptions({ autoScale: true });

    const zoneOverlays = visibleOverlays.filter((o) => o.low != null && o.high != null);
    const priceOverlays = visibleOverlays.filter((o) => o.price != null);
    const markerOverlays = priceOverlays.filter((o) => styleForOverlay(o).renderAs === "marker");
    const lineOverlays = priceOverlays.filter((o) => styleForOverlay(o).renderAs !== "marker");

    const priceLines = lineOverlays.map((overlay) => {
      const style = styleForOverlay(overlay);
      return series.createPriceLine({
        price: overlay.price!,
        color: style.color,
        lineWidth: style.lineWidth,
        lineStyle: LINE_STYLE[style.lineStyle],
        axisLabelVisible: false,
        title: "",
      });
    });

    const recompute = () => {
      const chartWidth = root.current?.clientWidth || 0;
      const chartHeight = root.current?.clientHeight || 0;
      const zones = zoneOverlays.flatMap((overlay) => {
        const rect = computeZoneRect(overlay, {
          chartWidth,
          priceToY: (price) => series.priceToCoordinate(price),
          timeToX: (time) => chart.timeScale().timeToCoordinate(toTimestamp(time)),
        });
        return rect ? [{ rect, overlay }] : [];
      });
      setLayout({ zones, lineOverlays, markerOverlays, chartHeight });
    };
    recompute();
    chart.timeScale().subscribeVisibleLogicalRangeChange(recompute);
    return () => {
      priceLines.forEach((line) => series.removePriceLine(line));
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(recompute);
      setLayout({ zones: [], lineOverlays: [], markerOverlays: [], chartHeight: 0 });
    };
  }, [visibleOverlays]);

  useEffect(() => {
    if (
      selectedOverlayId &&
      !visibleOverlays.some(
        (overlay) => overlay.overlay_id === selectedOverlayId,
      )
    )
      setSelectedOverlayId("");
  }, [selectedOverlayId, visibleOverlays]);

  const [chartWidth, setChartWidth] = useState(0);
  useEffect(() => {
    if (!root.current) return;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width || 0;
      setChartWidth(width);
    });
    observer.observe(root.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="flex h-full min-h-0 flex-1 flex-col bg-[#080b10]">
      <header className="flex h-12 items-center justify-between border-b border-white/[.07] px-3">
        <div>
          <b className="text-sm">
            {store.symbol.display_name} · {store.timeframe}
          </b>
          <span className="ml-2 font-mono text-[10px] text-zinc-500">
            {workspaceLabel(store.workspaceMode, store.marketType, store.symbol.family, store.connection)}
          </span>
        </div>
        <div className="font-mono text-sm tabular-nums">
          {formatPrice(
            store.decision?.market.current_price,
            store.decision?.precision,
          )}
        </div>
      </header>
      <ChartToolbar
        visibility={store.overlayVisibility}
        onToggle={store.toggleOverlay}
        previousSetupCount={previousSetupCount}
        hiddenEvidenceCount={hiddenByDensity}
        overlays={visibleOverlays}
        selectedOverlayId={selectedOverlayId}
        onSelectOverlay={setSelectedOverlayId}
      />
      <div className="relative min-h-0 flex-1">
        <div ref={root} className="absolute inset-0" />
        <ChartZoneLayer
          zones={layout.zones}
          chartHeight={layout.chartHeight}
          selectedOverlayId={selectedOverlayId}
          onSelect={setSelectedOverlayId}
        />
        <ChartPriceTags
          overlays={layout.lineOverlays}
          chartHeight={layout.chartHeight}
          priceToY={(price) => seriesRef.current?.priceToCoordinate(price) ?? null}
          precision={store.decision?.precision}
          selectedOverlayId={selectedOverlayId}
          onSelect={setSelectedOverlayId}
        />
        <ChartEventMarkers
          overlays={layout.markerOverlays}
          priceToY={(price) => seriesRef.current?.priceToCoordinate(price) ?? null}
          timeToX={(time) => chartRef.current?.timeScale().timeToCoordinate(toTimestamp(time)) ?? null}
          chartWidth={root.current?.clientWidth || 0}
          selectedOverlayId={selectedOverlayId}
          onSelect={setSelectedOverlayId}
        />
        <ChartSetupSummary
          decision={store.decision}
          visible={store.overlayVisibility.trade_plan && chartWidth >= 420}
        />
        {selectedOverlay && (
          <DrawingInspector
            overlay={selectedOverlay}
            close={() => setSelectedOverlayId("")}
            precision={store.decision?.precision}
          />
        )}
        {store.workspaceMode === "live" && query.isError && (
          <div className="absolute inset-0 grid place-items-center text-xs text-zinc-500">
            Completed chart candles are unavailable.
          </div>
        )}
      </div>
    </section>
  );
}

function workspaceLabel(
  mode: "live" | "historical" | "replay",
  marketType: string,
  family: string,
  connection: string,
) {
  if (mode === "historical") return "HISTORICAL · FROZEN AT DECISION TIME";
  if (mode === "replay") return "REPLAY · DECISION-TIME OBJECTS ONLY";
  return `${marketType.toUpperCase()} · ${family} · ${connection.toUpperCase()}`;
}

function toTimestamp(value: string | number): UTCTimestamp {
  return (typeof value === "number" ? value : Date.parse(value) / 1000) as UTCTimestamp;
}
