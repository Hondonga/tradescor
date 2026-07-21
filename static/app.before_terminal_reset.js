// Dashboard logic for the ICT 2022 Flask Scanner.
// Credit-saving rule: no market API request runs until Load Chart is clicked.

const chartElement = document.getElementById("chart");
const chartOverlayLayer = document.getElementById("chart-overlay-layer");
const emptyState = document.getElementById("chart-empty-state");
const loadButton = document.getElementById("load-chart");
const statusText = document.getElementById("status-text");
const refreshText = document.getElementById("refresh-text");
const chartTitle = document.getElementById("chart-title");
const chartDecisionStatus = document.getElementById("chart-decision-status");
const chartDirection = document.getElementById("chart-direction");
const analysisModeBadge = document.getElementById("analysis-mode-badge");
const clock = document.getElementById("clock");
const lastLoaded = document.getElementById("last-loaded");
const topSymbol = document.getElementById("top-symbol");
const topTimeframe = document.getElementById("top-timeframe");
const topStrategy = document.getElementById("top-strategy");
const scannerView = document.getElementById("scanner-view");
const scannerPlaceholder = document.getElementById("scanner-placeholder");
const scannerPlaceholderMarket = document.getElementById("scanner-placeholder-market");
const scannerResult = document.getElementById("scanner-result");
const scannerMarket = document.getElementById("scanner-market");
const scannerAction = document.getElementById("scanner-action");
const scannerState = document.getElementById("scanner-state");
const scannerScore = document.getElementById("scanner-score");
const scannerScoreLabel = document.getElementById("scanner-score-label");
const scannerScoreFill = document.getElementById("scanner-score-fill");
const scannerDirection = document.getElementById("scanner-direction");
const scannerConfidence = document.getElementById("scanner-confidence");
const scannerPlanTitle = document.getElementById("scanner-plan-title");
const scannerTrigger = document.getElementById("scanner-trigger");
const scannerStop = document.getElementById("scanner-stop");
const scannerRisk = document.getElementById("scanner-risk");
const scannerTp1 = document.getElementById("scanner-tp1");
const scannerTp1Distance = document.getElementById("scanner-tp1-distance");
const scannerRr1 = document.getElementById("scanner-rr1");
const scannerTp2 = document.getElementById("scanner-tp2");
const scannerTp2Distance = document.getElementById("scanner-tp2-distance");
const scannerRr2 = document.getElementById("scanner-rr2");
const scannerPlanWarning = document.getElementById("scanner-plan-warning");
const scannerReasons = document.getElementById("scanner-reasons");
const scannerNextAction = document.getElementById("scanner-next-action");
const scannerEntryTimingCard = document.getElementById("scanner-entry-timing-card");
const scannerEntryTimingStatus = document.getElementById("scanner-entry-timing-status");
const scannerEntryTimingMessage = document.getElementById("scanner-entry-timing-message");
const scannerEntryTimingMetrics = document.getElementById("scanner-entry-timing-metrics");
const decisionStatus = document.getElementById("decision-status");
const decisionDirection = document.getElementById("decision-direction");
const decisionScore = document.getElementById("decision-score");
const decisionConfidence = document.getElementById("decision-confidence");
const decisionEntryTimingStatus = document.getElementById("decision-entry-timing-status");
const decisionEntryTimingMessage = document.getElementById("decision-entry-timing-message");
const decisionLifecycleCard = document.getElementById("decision-lifecycle-card");
const decisionLifecycleStatus = document.getElementById("decision-lifecycle-status");
const decisionLifecycleMessage = document.getElementById("decision-lifecycle-message");
const decisionNewsRisk = document.getElementById("decision-news-risk");
const decisionNewsSource = document.getElementById("decision-news-source");
const decisionNewsMessage = document.getElementById("decision-news-message");
const decisionDxyStatus = document.getElementById("decision-dxy-status");
const decisionDxyMessage = document.getElementById("decision-dxy-message");
const decisionSessionStatus = document.getElementById("decision-session-status");
const decisionEntry = document.getElementById("decision-entry");
const decisionStop = document.getElementById("decision-stop");
const decisionTp1 = document.getElementById("decision-tp1");
const decisionTp2 = document.getElementById("decision-tp2");
const decisionRisk = document.getElementById("decision-risk");
const decisionRr = document.getElementById("decision-rr");
const chartEntryTiming = document.getElementById("chart-entry-timing");
const chartEntryTimingStatus = document.getElementById("chart-entry-timing-status");
const chartEntryTimingMessage = document.getElementById("chart-entry-timing-message");
const tradePlanToggle = document.getElementById("toggle-trade-plan");
const contextZonesToggle = document.getElementById("toggle-context-zones");
const advancedLabelsToggle = document.getElementById("toggle-advanced-labels");
const appViewButtons = [...document.querySelectorAll("[data-app-view]")];
const openViewButtons = [...document.querySelectorAll("[data-open-view]")];
const homeSymbol = document.getElementById("home-symbol");
const homeTimeframe = document.getElementById("home-timeframe");
const homeAnalyze = document.getElementById("home-analyze");
const homeDecisionEmpty = document.getElementById("home-decision-empty");
const homeDecisionResult = document.getElementById("home-decision-result");
const homeDecisionMarket = document.getElementById("home-decision-market");
const homeDecisionStatus = document.getElementById("home-decision-status");
const homeDecisionDirection = document.getElementById("home-decision-direction");
const homeDecisionScore = document.getElementById("home-decision-score");
const homeDecisionNext = document.getElementById("home-decision-next");
const homeNyTime = document.getElementById("home-ny-time");
const homeMarketOpen = document.getElementById("home-market-open");
const homeSessionName = document.getElementById("home-session-name");
const homeKillZone = document.getElementById("home-kill-zone");
const homeNextSession = document.getElementById("home-next-session");
const homeRecentMarkets = document.getElementById("home-recent-markets");
const dashboardNyTime = document.getElementById("dashboard-ny-time");
const dashboardMarketOpen = document.getElementById("dashboard-market-open");
const dashboardSessionName = document.getElementById("dashboard-session-name");
const dashboardKillZone = document.getElementById("dashboard-kill-zone");
const dashboardNextSession = document.getElementById("dashboard-next-session");
const dashboardNewsStatus = document.getElementById("dashboard-news-status");
const dashboardNewsDetail = document.getElementById("dashboard-news-detail");
const dashboardLabStatus = document.getElementById("dashboard-lab-status");
const dashboardLabSummary = document.getElementById("dashboard-lab-summary");
const settingsDefaultSymbol = document.getElementById("settings-default-symbol");
const settingsDefaultTimeframe = document.getElementById("settings-default-timeframe");
const settingsDefaultStrategy = document.getElementById("settings-default-strategy");
const settingsStrategyMode = document.getElementById("settings-strategy-mode");
const settingsManualStrategyField = document.getElementById("settings-manual-strategy-field");
const settingsTradePlan = document.getElementById("settings-trade-plan");
const settingsContextZones = document.getElementById("settings-context-zones");
const settingsAdvancedLabels = document.getElementById("settings-advanced-labels");
const settingsShowSession = document.getElementById("settings-show-session");
const settingsNyTime = document.getElementById("settings-ny-time");
const settingsAutoRefresh = document.getElementById("settings-auto-refresh");
const settingsRefreshInterval = document.getElementById("settings-refresh-interval");
const settingsDataMode = document.getElementById("settings-data-mode");
const settingsMarketauxEnabled = document.getElementById("settings-marketaux-enabled");
const settingsNewsRisk = document.getElementById("settings-news-risk");
const settingsDxyConfirmation = document.getElementById("settings-dxy-confirmation");
const settingsMarketauxStatus = document.getElementById("settings-marketaux-status");
const settingsSaveStatus = document.getElementById("settings-save-status");
const answerMarket = document.getElementById("answer-market");
const answerNow = document.getElementById("answer-now");
const answerPriceLocation = document.getElementById("answer-price-location");
const answerMarketIntent = document.getElementById("answer-market-intent");
const answerZone = document.getElementById("answer-zone");
const answerConfirmation = document.getElementById("answer-confirmation");
const answerInvalidation = document.getElementById("answer-invalidation");
const answerTopdown = document.getElementById("answer-topdown");
const answerTopdownSummary = document.getElementById("answer-topdown-summary");
const marketClarity = document.getElementById("market-clarity");
const tradeReadiness = document.getElementById("trade-readiness");
const marketStoryTimeline = document.getElementById("market-story-timeline");
const macroSummary = document.getElementById("macro-summary");
const macroAlignment = document.getElementById("macro-alignment");
const macroNewsWarning = document.getElementById("macro-news-warning");
const macroSessionName = document.getElementById("macro-session-name");
const macroSessionDetail = document.getElementById("macro-session-detail");
const macroTopdownList = document.getElementById("macro-topdown-list");
const macroDxyTrend = document.getElementById("macro-dxy-trend");
const macroDxyStatus = document.getElementById("macro-dxy-status");
const macroNewsStatus = document.getElementById("macro-news-status");
const macroNewsDetail = document.getElementById("macro-news-detail");
const macroPhaseName = document.getElementById("macro-phase-name");
const macroPhaseDetail = document.getElementById("macro-phase-detail");
const headerSessionName = document.getElementById("header-session-name");
const headerSessionStatus = document.getElementById("header-session-status");
const headerProgressLabel = document.getElementById("header-progress-label");
const headerProgressPercent = document.getElementById("header-progress-percent");
const headerProgressFill = document.getElementById("header-progress-fill");
const headerSessionStart = document.getElementById("header-session-start");
const headerSessionNow = document.getElementById("header-session-now");
const headerSessionEnd = document.getElementById("header-session-end");
const headerSessionRemaining = document.getElementById("header-session-remaining");
const headerNextSession = document.getElementById("header-next-session");
const headerEntryAllowed = document.getElementById("header-entry-allowed");
const headerSessionTimeline = document.getElementById("header-session-timeline");
const autoRefreshToggle = document.getElementById("auto-refresh");
const autoRefreshState = document.getElementById("auto-refresh-state");
const refreshIntervalSelect = document.getElementById("refresh-interval");
const dataModeSelect = document.getElementById("data-mode");
const contextTimeframeSwitcher = document.getElementById("context-timeframe-switcher");
const replayPlay = document.getElementById("replay-play");
const replayPause = document.getElementById("replay-pause");
const replayBack = document.getElementById("replay-back");
const replayStep = document.getElementById("replay-step");
const replayReset = document.getElementById("replay-reset");
const replaySpeed = document.getElementById("replay-speed");
const replayStatus = document.getElementById("replay-status");
const detailState = document.getElementById("detail-state");
const setupStatusLabel = document.getElementById("setup-status-label");
const setupDirection = document.getElementById("setup-direction");
const setupBias = document.getElementById("setup-bias");
const answerHtfBias = document.getElementById("answer-htf-bias");
const executionTrendLabel = document.getElementById("execution-trend-label");
const storyPhase = document.getElementById("story-phase");
const setupState = document.getElementById("setup-state");
const setupReadiness = document.getElementById("setup-readiness");
const nextConfirmation = document.getElementById("next-confirmation");
const suggestedAction = document.getElementById("suggested-action");
const setupScore = document.getElementById("setup-score");
const setupQuality = document.getElementById("setup-quality");
const tradeQuality = document.getElementById("trade-quality");
const setupChecklist = document.getElementById("setup-checklist");
const technicalChecklist = document.getElementById("technical-checklist");
const whyList = document.getElementById("why-list");
const setupSummary = document.getElementById("setup-summary");
const topdownAlignment = document.getElementById("topdown-alignment");
const topdownList = document.getElementById("topdown-list");
const sessionEntry = document.getElementById("session-entry");
const sessionCurrent = document.getElementById("session-current");
const sessionStatus = document.getElementById("session-status");
const sessionPhase = document.getElementById("session-phase");
const sessionNext = document.getElementById("session-next");
const sessionRemaining = document.getElementById("session-remaining");
const sessionAllowed = document.getElementById("session-allowed");
const sessionBehavior = document.getElementById("session-behavior");
const contextCount = document.getElementById("context-count");
const marketContextList = document.getElementById("market-context-list");
const liquidityMapList = document.getElementById("liquidity-map-list");
const structureCount = document.getElementById("structure-count");
const structureList = document.getElementById("structure-list");
const explanationStatus = document.getElementById("explanation-status");
const setupExplanation = document.getElementById("setup-explanation");
const timelineList = document.getElementById("timeline-list");
const rawAnalysis = document.getElementById("raw-analysis");
const levelList = document.getElementById("level-list");
const levelEntry = document.getElementById("level-entry");
const levelStop = document.getElementById("level-stop");
const levelTp1 = document.getElementById("level-tp1");
const levelTp2 = document.getElementById("level-tp2");
const levelRr1 = document.getElementById("level-rr1");
const levelRr2 = document.getElementById("level-rr2");
const levelNote = document.getElementById("level-note");
const objectivePrimary = document.getElementById("objective-primary");
const objectivePrimaryReason = document.getElementById("objective-primary-reason");
const objectiveSecondary = document.getElementById("objective-secondary");
const objectiveSecondaryReason = document.getElementById("objective-secondary-reason");
const objectiveSecondaryCard = document.getElementById("objective-secondary-card");
const answerQaValidation = document.getElementById("answer-qa-validation");
const answerQaSnapshotCount = document.getElementById("answer-qa-snapshot-count");
const answerQaCurrent = document.getElementById("answer-qa-current");
const answerQaSource = document.getElementById("answer-qa-source");
const answerQaConditions = document.getElementById("answer-qa-conditions");
const answerQaWarnings = document.getElementById("answer-qa-warnings");
const answerQaClarity = document.getElementById("answer-qa-clarity");
const answerQaChangeReason = document.getElementById("answer-qa-change-reason");
const answerQaReplayLog = document.getElementById("answer-qa-replay-log");
const chartCurrentPrice = document.getElementById("chart-current-price");
const chartPriceChange = document.getElementById("chart-price-change");
const chartHigh = document.getElementById("chart-high");
const chartLow = document.getElementById("chart-low");
const chartSpread = document.getElementById("chart-spread");
const assistantTrendExplanation = document.getElementById("assistant-trend-explanation");
const assistantLocationExplanation = document.getElementById("assistant-location-explanation");
const assistantIntentExplanation = document.getElementById("assistant-intent-explanation");
const assistantStatusExplanation = document.getElementById("assistant-status-explanation");
const assistantNextOutcome = document.getElementById("assistant-next-outcome");
const storyInstruction = document.getElementById("story-instruction");
const htfContextTable = document.getElementById("htf-context-table");
const keyNextTarget = document.getElementById("key-next-target");
const keyBias = document.getElementById("key-bias");
const keyRiskReward = document.getElementById("key-risk-reward");
const settingsToggle = document.getElementById("settings-toggle");
const dataSettings = document.getElementById("data-settings");
const moreDetails = document.querySelector(".more-details");
const ictDetailsPanel = document.getElementById("ict-details-panel");
const ictStateLabel = document.getElementById("ict-state-label");
const ictChecklist = document.getElementById("ict-checklist");
const ictKillZone = document.getElementById("ict-kill-zone");
const ictLiquiditySweep = document.getElementById("ict-liquidity-sweep");
const ictChoch = document.getElementById("ict-choch");
const ictFvg = document.getElementById("ict-fvg");
const ictIfvg = document.getElementById("ict-ifvg");
const ictOte = document.getElementById("ict-ote");
const ictOrderBlock = document.getElementById("ict-order-block");
const ictAmdPhase = document.getElementById("ict-amd-phase");
const ictDxy = document.getElementById("ict-dxy");
const ictNews = document.getElementById("ict-news");
const supplyDemandDetailsPanel = document.getElementById("supply-demand-details-panel");
const sdActiveZone = document.getElementById("sd-active-zone");
const sdZoneQuality = document.getElementById("sd-zone-quality");
const sdImpulse = document.getElementById("sd-impulse");
const sdMitigation = document.getElementById("sd-mitigation");
const sdReaction = document.getElementById("sd-reaction");
const sdTrigger = document.getElementById("sd-trigger");
const sdState = document.getElementById("sd-state");
const breakoutDetailsPanel = document.getElementById("breakout-details-panel");
const breakoutRange = document.getElementById("breakout-range");
const breakoutDirection = document.getElementById("breakout-direction");
const breakoutLevel = document.getElementById("breakout-level");
const breakoutRetest = document.getElementById("breakout-retest");
const breakoutRejection = document.getElementById("breakout-rejection");
const breakoutMeasuredMove = document.getElementById("breakout-measured-move");
const breakoutState = document.getElementById("breakout-state");

let chart;
let candleSeries;
let priceLines = [];
let drawnPriceLabelCoordinates = [];
let refreshTimer;
let lastLoadedParams = null;
let replayCandles = [];
let replayIndex = 0;
let replayStartIndex = 0;
let replayTimer = null;
let replayAnalyzing = false;
let isReplayMode = false;
let latestAnalysis = null;
let loadedContextCandles = {};
let recentMarkets = [];

const SETTINGS_STORAGE_KEY = "tradescor.settings.v1";
const RECENT_MARKETS_STORAGE_KEY = "tradescor.recent-markets.v1";
let loadedCacheStatus = {};
let analysisTimelineEvents = [];
let analysisTimelineKeys = new Set();
let answerQaSnapshots = new Map();
let answerQaChanges = [];

const MIN_REPLAY_CANDLES = 30;
const CONTEXT_SWITCHER_TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];
const CONTEXT_TIMEFRAME_ORDER = {
    M1: 1,
    M5: 2,
    M15: 3,
    M30: 4,
    H1: 5,
    H2: 6,
    H4: 7,
    D1: 8,
};

const SESSION_DEFINITIONS = [
    {
        name: "Asian Session",
        start: 20 * 60,
        end: 24 * 60,
        entryAllowed: false,
        phase: "Range Formation",
        expectedBehavior: "Identify Asia range high, range low, and resting liquidity pools.",
    },
    {
        name: "London Kill Zone",
        start: 2 * 60,
        end: 5 * 60,
        entryAllowed: true,
        phase: "Manipulation",
        expectedBehavior: "Looking for manipulation, liquidity sweep, and CHOCH.",
    },
    {
        name: "New York Kill Zone",
        start: 7 * 60,
        end: 10 * 60,
        entryAllowed: true,
        phase: "Distribution",
        expectedBehavior: "Looking for continuation, distribution, and entry confirmation.",
    },
    {
        name: "London Close",
        start: 10 * 60,
        end: 12 * 60,
        entryAllowed: false,
        phase: "Profit Taking",
        expectedBehavior: "Looking for continuation and profit-taking behavior.",
    },
];

function createChartIfNeeded() {
    if (chart) {
        return;
    }

    if (!window.LightweightCharts) {
        throw new Error("Lightweight Charts did not load. Check your internet connection and refresh the page.");
    }

    chart = LightweightCharts.createChart(chartElement, {
        layout: {
            background: { color: "#07100C" },
            textColor: "#F3FFF7",
        },
        grid: {
            vertLines: { color: "rgba(59, 130, 246, 0.08)" },
            horzLines: { color: "rgba(59, 130, 246, 0.08)" },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: "rgba(59, 130, 246, 0.16)",
            scaleMargins: {
                top: 0.12,
                bottom: 0.12,
            },
        },
        timeScale: {
            borderColor: "rgba(59, 130, 246, 0.16)",
            timeVisible: true,
            secondsVisible: false,
            rightOffset: 8,
            barSpacing: 8,
        },
        width: Math.max(chartElement.clientWidth, 320),
        height: Math.max(chartElement.clientHeight, 360),
    });

    candleSeries = chart.addCandlestickSeries({
        upColor: "#22c55e",
        borderUpColor: "#22c55e",
        wickUpColor: "#86efac",
        downColor: "#ef4444",
        borderDownColor: "#ef4444",
        wickDownColor: "#fca5a5",
        priceLineVisible: false,
        lastValueVisible: false,
    });

    chart.timeScale().subscribeVisibleTimeRangeChange(() => {
        redrawChartOverlays();
    });
}

function getFormParams() {
    const symbol = document.getElementById("symbol").value.trim() || "EUR/USD";
    const timeframe = document.getElementById("timeframe").value || "M5";
    const strategy = document.getElementById("strategy").value || "auto";
    const dataMode = dataModeSelect.value || "single";
    const multi_timeframe = dataMode === "single" ? "0" : "1";
    const context_depth = dataMode === "full" ? "full" : "balanced";
    const bars = document.getElementById("bars").value || "300";
    const saved = readSavedSettings();
    const marketaux_enabled = saved.marketauxEnabled ? "1" : "0";
    const news_risk = saved.newsRisk ? "1" : "0";
    const dxy_confirmation = saved.dxyConfirmation ? "1" : "0";

    return { symbol, timeframe, strategy, multi_timeframe, context_depth, bars, marketaux_enabled, news_risk, dxy_confirmation };
}

const buttonSelectConfigs = [
    { id: "timeframe", className: "timeframe-option-buttons", visibleValues: ["M5", "M15", "H1", "H4", "D1"] },
];

function enhanceSelectAsButtons(select, className = "", visibleValues = null) {
    if (!select || select.dataset.buttonOptionsReady === "1") return;

    const group = document.createElement("div");
    group.className = `button-option-group ${className}`.trim();
    group.dataset.optionSource = select.id;
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", select.previousElementSibling?.textContent?.trim() || select.id);

    const allowedValues = Array.isArray(visibleValues) ? new Set(visibleValues) : null;
    for (const option of select.querySelectorAll("option")) {
        if (allowedValues && !allowedValues.has(option.value)) continue;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "button-option";
        button.dataset.value = option.value;
        button.textContent = option.textContent.trim();
        button.title = option.parentElement?.tagName === "OPTGROUP"
            ? `${option.parentElement.label}: ${option.textContent.trim()}`
            : option.textContent.trim();
        button.setAttribute("aria-pressed", "false");
        button.addEventListener("click", () => {
            if (select.value === option.value) return;
            select.value = option.value;
            select.dispatchEvent(new Event("change", { bubbles: true }));
            updateButtonOptions(select);
        });
        group.appendChild(button);
    }

    select.classList.add("select-button-source");
    select.dataset.buttonOptionsReady = "1";
    select.insertAdjacentElement("afterend", group);
    select.addEventListener("change", () => updateButtonOptions(select));
    updateButtonOptions(select);
}

function setupButtonOptions() {
    for (const config of buttonSelectConfigs) {
        enhanceSelectAsButtons(document.getElementById(config.id), config.className, config.visibleValues);
    }
}

function updateButtonOptions(select) {
    if (!select) return;
    const group = select.parentElement?.querySelector(`.button-option-group[data-option-source="${select.id}"]`);
    if (!group) return;

    for (const button of group.querySelectorAll(".button-option")) {
        const active = button.dataset.value === select.value;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
    }
}

function updateAllButtonOptions() {
    for (const config of buttonSelectConfigs) {
        updateButtonOptions(document.getElementById(config.id));
    }
}

function setAppView(view) {
    const normalized = ["home", "scanner", "chart", "lab", "settings"].includes(view) ? view : "scanner";
    document.body.classList.toggle("view-home", normalized === "home");
    document.body.classList.toggle("view-scanner", normalized === "scanner");
    document.body.classList.toggle("view-chart", normalized === "chart");
    document.body.classList.toggle("view-lab", normalized === "lab");
    document.body.classList.toggle("view-settings", normalized === "settings");

    for (const button of appViewButtons) {
        const active = button.dataset.appView === normalized;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
    }

    const pageTitle = document.getElementById("current-page-title");
    if (pageTitle) {
        pageTitle.textContent = normalized === "lab" ? "Strategy Lab" : normalized[0].toUpperCase() + normalized.slice(1);
    }

    if (normalized === "lab") {
        const panel = document.getElementById("strategy-lab-panel");
        if (panel) panel.open = true;
    }

    if (normalized === "settings") {
        syncSettingsControls();
    }

    if (normalized === "chart") {
        requestAnimationFrame(() => {
            resizeChartToContainer();
            if (chart && candleSeries) {
                chart.timeScale().fitContent();
                redrawChartOverlays();
            }
        });
    }
}

function syncHomeControlsFromMain() {
    if (!homeSymbol) return;
    homeSymbol.value = document.getElementById("symbol").value;
    homeTimeframe.value = document.getElementById("timeframe").value;
    updateAllButtonOptions();
}

function syncMainControlsFromHome() {
    document.getElementById("symbol").value = homeSymbol.value;
    document.getElementById("timeframe").value = homeTimeframe.value;
    document.getElementById("strategy").value = "auto";
    updateAllButtonOptions();
    updateTopSelection();
    contextZonesToggle.checked = true;
}

function renderHomeDecisionFromScanner() {
    if (!homeDecisionEmpty || !homeDecisionResult) return;
    homeDecisionEmpty.hidden = true;
    homeDecisionResult.hidden = false;
    homeDecisionMarket.textContent = scannerMarket.textContent;
    homeDecisionStatus.textContent = scannerAction.textContent;
    homeDecisionStatus.className = scannerAction.className;
    homeDecisionDirection.textContent = `Looking for: ${scannerDirection.textContent}`;
    homeDecisionScore.textContent = `${scannerScore.textContent}/100`;
    homeDecisionNext.textContent = scannerNextAction.textContent;
}

function resetHomeDecision(message = "Run an analysis to see your latest result.") {
    if (!homeDecisionEmpty || !homeDecisionResult) return;
    homeDecisionResult.hidden = true;
    homeDecisionEmpty.hidden = false;
    const copy = homeDecisionEmpty.querySelector("p");
    if (copy) copy.textContent = message;
}

function loadRecentMarkets() {
    try {
        const stored = JSON.parse(localStorage.getItem(RECENT_MARKETS_STORAGE_KEY) || "[]");
        recentMarkets = Array.isArray(stored) ? stored.slice(0, 5) : [];
    } catch (_error) {
        recentMarkets = [];
    }
    renderRecentMarkets();
}

function rememberRecentMarket() {
    const item = {
        symbol: scannerMarket.textContent.split(" · ")[0] || getFormParams().symbol,
        timeframe: scannerMarket.textContent.split(" · ")[1] || getFormParams().timeframe,
        status: scannerAction.textContent || "NO CLEAN ENTRY",
        direction: scannerDirection.textContent || "Neutral",
        analyzedAt: new Date().toISOString(),
    };
    recentMarkets = [item, ...recentMarkets.filter((entry) => (
        entry.symbol !== item.symbol || entry.timeframe !== item.timeframe
    ))].slice(0, 5);
    localStorage.setItem(RECENT_MARKETS_STORAGE_KEY, JSON.stringify(recentMarkets));
    renderRecentMarkets();
}

function renderRecentMarkets() {
    if (!homeRecentMarkets) return;
    homeRecentMarkets.innerHTML = "";
    if (!recentMarkets.length) {
        const item = document.createElement("li");
        item.innerHTML = "<span>No analyzed markets yet.</span><small>Results stay on this device.</small>";
        homeRecentMarkets.appendChild(item);
        return;
    }
    for (const market of recentMarkets) {
        const item = document.createElement("li");
        const identity = document.createElement("span");
        identity.textContent = `${market.symbol} · ${market.timeframe}`;
        const outcome = document.createElement("strong");
        const displayStatus = storedDisplayStatus(market.status, market.direction);
        outcome.textContent = displayStatus;
        outcome.className = statusToneClass(displayStatus);
        const direction = document.createElement("small");
        direction.textContent = market.direction;
        item.append(identity, outcome, direction);
        homeRecentMarkets.appendChild(item);
    }
}

function readSavedSettings() {
    const defaults = {
        symbol: "EUR/USD",
        timeframe: "M5",
        strategyMode: "auto",
        strategy: "ict_2022",
        tradePlan: true,
        contextZones: true,
        advancedLabels: false,
        showSession: true,
        autoRefresh: false,
        refreshInterval: "60",
        dataMode: "single",
        marketauxEnabled: true,
        newsRisk: true,
        dxyConfirmation: false,
    };
    try {
        return { ...defaults, ...JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}") };
    } catch (_error) {
        return defaults;
    }
}

function applySavedSettings() {
    const saved = readSavedSettings();
    document.getElementById("symbol").value = saved.symbol;
    document.getElementById("timeframe").value = saved.timeframe;
    document.getElementById("strategy").value = saved.strategyMode === "manual" ? saved.strategy : "auto";
    tradePlanToggle.checked = Boolean(saved.tradePlan);
    contextZonesToggle.checked = Boolean(saved.contextZones);
    advancedLabelsToggle.checked = Boolean(saved.advancedLabels);
    autoRefreshToggle.checked = Boolean(saved.autoRefresh);
    refreshIntervalSelect.value = String(saved.refreshInterval);
    dataModeSelect.value = saved.dataMode;
    document.body.classList.toggle("hide-session-status", !saved.showSession);
    syncHomeControlsFromMain();
    syncSettingsControls();
    updateAllButtonOptions();
}

function syncSettingsControls() {
    if (!settingsDefaultSymbol) return;
    settingsDefaultSymbol.value = document.getElementById("symbol").value;
    settingsDefaultTimeframe.value = document.getElementById("timeframe").value;
    const selectedStrategy = document.getElementById("strategy").value;
    settingsStrategyMode.value = selectedStrategy === "auto" ? "auto" : "manual";
    if (selectedStrategy !== "auto") settingsDefaultStrategy.value = selectedStrategy;
    settingsManualStrategyField.hidden = settingsStrategyMode.value !== "manual";
    settingsTradePlan.checked = tradePlanToggle.checked;
    settingsContextZones.checked = contextZonesToggle.checked;
    settingsAdvancedLabels.checked = advancedLabelsToggle.checked;
    settingsShowSession.checked = !document.body.classList.contains("hide-session-status");
    settingsAutoRefresh.checked = autoRefreshToggle.checked;
    settingsRefreshInterval.value = refreshIntervalSelect.value;
    settingsDataMode.value = dataModeSelect.value;
    settingsMarketauxEnabled.checked = Boolean(readSavedSettings().marketauxEnabled);
    settingsNewsRisk.checked = Boolean(readSavedSettings().newsRisk);
    settingsDxyConfirmation.checked = Boolean(readSavedSettings().dxyConfirmation);
    if (settingsMarketauxStatus) {
        settingsMarketauxStatus.textContent = settingsMarketauxEnabled.checked
            ? "Marketaux API token is read from the backend .env file."
            : "Marketaux provider is disabled in this browser.";
    }
}

function saveSettingsFromPanel() {
    const saved = {
        symbol: settingsDefaultSymbol.value,
        timeframe: settingsDefaultTimeframe.value,
        strategyMode: settingsStrategyMode.value,
        strategy: settingsDefaultStrategy.value,
        tradePlan: settingsTradePlan.checked,
        contextZones: settingsContextZones.checked,
        advancedLabels: settingsAdvancedLabels.checked,
        showSession: settingsShowSession.checked,
        autoRefresh: settingsAutoRefresh.checked,
        refreshInterval: settingsRefreshInterval.value,
        dataMode: settingsDataMode.value,
        marketauxEnabled: settingsMarketauxEnabled.checked,
        newsRisk: settingsNewsRisk.checked,
        dxyConfirmation: settingsDxyConfirmation.checked,
    };
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(saved));
    document.getElementById("symbol").value = saved.symbol;
    document.getElementById("timeframe").value = saved.timeframe;
    document.getElementById("strategy").value = saved.strategyMode === "manual" ? saved.strategy : "auto";
    tradePlanToggle.checked = saved.tradePlan;
    contextZonesToggle.checked = saved.contextZones;
    advancedLabelsToggle.checked = saved.advancedLabels;
    autoRefreshToggle.checked = saved.autoRefresh;
    refreshIntervalSelect.value = saved.refreshInterval;
    dataModeSelect.value = saved.dataMode;
    if (settingsMarketauxStatus) {
        settingsMarketauxStatus.textContent = saved.marketauxEnabled
            ? "Marketaux API token is read from the backend .env file."
            : "Marketaux provider is disabled in this browser.";
    }
    document.body.classList.toggle("hide-session-status", !saved.showSession);
    settingsManualStrategyField.hidden = saved.strategyMode !== "manual";
    syncHomeControlsFromMain();
    updateAllButtonOptions();
    updateTopSelection();
    updateAutoRefreshControls();
    if (latestAnalysis) drawAnalysisOverlays(latestAnalysis);
    settingsSaveStatus.textContent = "Preferences saved.";
    window.setTimeout(() => {
        settingsSaveStatus.textContent = "Preferences save automatically.";
    }, 1600);
}

function setScannerLoading(params) {
    if (!scannerPlaceholder || !scannerResult) return;
    scannerResult.hidden = true;
    scannerPlaceholder.hidden = false;
    scannerPlaceholderMarket.textContent = `${params.symbol} · ${params.timeframe}`;
    scannerPlaceholder.querySelector("strong").textContent = "Analyzing market";
}

function userFacingStatus({
    tradeStatus = "",
    state = "",
    tradeDecision = "PENDING",
    timingStatus = "",
    timingAvailable = false,
    levelsMode = "hidden",
    direction = "",
} = {}) {
    const normalizedTradeStatus = String(tradeStatus).toUpperCase().replaceAll("_", " ");
    const normalizedState = String(state).toUpperCase().replaceAll(" ", "_");
    const normalizedDecision = String(tradeDecision).toUpperCase();
    const normalizedTiming = String(timingStatus).toLowerCase();
    const normalizedDirection = tradeDirection(direction);

    if (timingAvailable && ["too_late", "missed", "invalid"].includes(normalizedTiming)) return "NO CLEAN ENTRY";
    if (
        String(levelsMode).toLowerCase() === "final"
        && normalizedDecision === "ACCEPT"
        && ["ENTRY READY", "TRADE ACTIVE"].includes(normalizedTradeStatus)
    ) {
        if (normalizedDirection === "BUY") return "READY TO BUY";
        if (normalizedDirection === "SELL") return "READY TO SELL";
        return "NO CLEAN ENTRY";
    }
    if (
        normalizedDecision === "REJECT"
        || normalizedTradeStatus.includes("NO TRADE")
        || normalizedTradeStatus.includes("INVALID")
        || normalizedState.includes("NO_TRADE")
        || normalizedState.includes("INVALID")
        || normalizedState.includes("FAILED")
    ) return "NO CLEAN ENTRY";
    if (normalizedDirection === "BUY") return "BUY SETUP FORMING";
    if (normalizedDirection === "SELL") return "SELL SETUP FORMING";
    return "NO CLEAN ENTRY";
}

function tradePlanQuality(analysis = {}) {
    const result = analysis?.strategy_result || {};
    const metrics = analysis?.trade_metrics || result.trade_metrics || {};
    const warnings = Array.isArray(metrics.warnings) ? metrics.warnings.map(String) : [];
    const tp1Rr = Number(metrics.tp1?.risk_reward);
    const tp2Rr = Number(metrics.tp2?.risk_reward);
    const hasWeakRewardWarning = warnings.some((warning) => /weak reward|reward is too weak/i.test(warning));
    const tp1Weak = Number.isFinite(tp1Rr) && tp1Rr < 1.0;
    const noUsableTarget = (!Number.isFinite(tp1Rr) || tp1Rr < 1.0) && (!Number.isFinite(tp2Rr) || tp2Rr < 1.0);

    if (hasWeakRewardWarning || tp1Weak) {
        return {
            valid: false,
            reason: noUsableTarget ? "no_acceptable_target" : "weak_reward",
            message: noUsableTarget
                ? "No clean trade plan — no acceptable target is available."
                : "No clean trade plan — reward is too weak.",
            scannerWarning: noUsableTarget
                ? "No acceptable target is available yet."
                : "TP1 reward is too weak.",
        };
    }

    const decision = String(result.trade_decision || analysis.trade_decision || "PENDING").toUpperCase();
    const mode = String(metrics.plan_mode || result.levels_mode || analysis.levels_mode || "hidden").toLowerCase();
    if (decision === "REJECT") {
        return {
            valid: false,
            reason: "rejected",
            message: "No clean trade plan.",
            scannerWarning: "Trade quality is not clean enough yet.",
        };
    }

    return {
        valid: true,
        reason: "",
        message: mode === "final" ? "Trade plan valid." : "Setup forming. Waiting for confirmation.",
        scannerWarning: "",
    };
}

function tradeDirection(value) {
    const normalized = String(value || "").trim().toUpperCase();
    if (["BUY", "BULLISH", "LONG"].includes(normalized)) return "BUY";
    if (["SELL", "BEARISH", "SHORT"].includes(normalized)) return "SELL";
    return "NEUTRAL";
}

function isReadyAction(status) {
    return status === "READY TO BUY" || status === "READY TO SELL";
}

function isFormingAction(status) {
    return status === "BUY SETUP FORMING" || status === "SELL SETUP FORMING";
}

function directionLabel(direction) {
    if (direction === "Buy") return "BUY setup";
    if (direction === "Sell") return "SELL setup";
    return "No clear direction yet";
}

function statusToneClass(status) {
    if (isReadyAction(status) || status === "TRADE READY") return "trade-ready";
    if (isFormingAction(status) || status === "WATCHLIST") return "watchlist";
    return "avoid";
}

function storedDisplayStatus(status, direction) {
    const normalized = String(status || "").toUpperCase();
    if (isReadyAction(normalized) || isFormingAction(normalized) || normalized === "NO CLEAN ENTRY") {
        return normalized;
    }
    if (normalized === "TRADE READY") {
        return userFacingStatus({
            tradeStatus: "Entry Ready",
            tradeDecision: "ACCEPT",
            levelsMode: "final",
            direction,
        });
    }
    if (normalized === "WATCHLIST") return userFacingStatus({ direction });
    return "NO CLEAN ENTRY";
}

function analysisDecisionStatus(analysis) {
    const result = analysis?.strategy_result || {};
    const answers = analysis?.trader_answers || {};
    const timing = analysis?.entry_timing || result.entry_timing || {};
    const quality = tradePlanQuality(analysis);
    const backendStatus = analysis?.user_status
        || result.user_status
        || analysis?.direction_debug?.user_status
        || result.direction_debug?.user_status;
    if ([
        "READY TO BUY",
        "READY TO SELL",
        "BUY SETUP FORMING",
        "SELL SETUP FORMING",
        "NO CLEAN ENTRY",
    ].includes(backendStatus)) {
        return !quality.valid && isReadyAction(backendStatus) ? "NO CLEAN ENTRY" : backendStatus;
    }
    const derivedStatus = userFacingStatus({
        tradeStatus: answers.trade_status || result.trade_status,
        state: result.state || analysis?.setup_status,
        tradeDecision: result.trade_decision || analysis?.trade_decision,
        timingStatus: timing.entry_timing_status,
        timingAvailable: Boolean(timing.available),
        levelsMode: result.levels_mode || analysis?.levels_mode,
        direction: result.bias || answers.higher_timeframe_bias || answers.trend || analysis?.bias,
    });
    return !quality.valid && !isFormingAction(derivedStatus) ? "NO CLEAN ENTRY" : derivedStatus;
}

function renderScannerAnalysis(analysis, answers, strategyResult, formattedReasons) {
    if (!scannerPlaceholder || !scannerResult) return;

    const tradeStatus = String(answers.trade_status || "No Trade");
    const levelsMode = String(strategyResult.levels_mode || analysis.levels_mode || "hidden");
    const directionDebug = analysis.direction_debug || strategyResult.direction_debug || {};
    const rawDirection = String(directionDebug.final_direction || strategyResult.bias || "Neutral");
    const normalizedDirection = tradeDirection(rawDirection);
    let direction = normalizedDirection === "BUY" ? "Buy" : normalizedDirection === "SELL" ? "Sell" : "Neutral";
    const entryTiming = analysis.entry_timing || strategyResult.entry_timing || {};
    const planQuality = tradePlanQuality(analysis);
    let action = analysisDecisionStatus(analysis);
    if (!planQuality.valid && isReadyAction(action)) {
        action = "NO CLEAN ENTRY";
    }
    if (action === "BUY SETUP FORMING" || action === "READY TO BUY") direction = "Buy";
    if (action === "SELL SETUP FORMING" || action === "READY TO SELL") direction = "Sell";
    const levels = analysis.levels || strategyResult.levels || {};
    const overlays = getOverlays(analysis);
    const tradeMetrics = analysis.trade_metrics || strategyResult.trade_metrics || {};
    const rawScore = Number(analysis.trade_score ?? strategyResult.trade_score ?? analysis.score ?? strategyResult.score ?? 0);
    const score = Math.max(0, Math.min(100, Math.round(Number.isFinite(rawScore) ? rawScore : 0)));
    const confidence = tradeScoreConfidence(score);

    scannerPlaceholder.hidden = true;
    scannerResult.hidden = false;
    scannerMarket.textContent = `${analysis.display_symbol || analysis.symbol || getFormParams().symbol} · ${analysis.timeframe || getFormParams().timeframe}`;
    scannerAction.textContent = action;
    scannerAction.className = statusToneClass(action);
    scannerResult.dataset.action = statusToneClass(action);
    scannerState.textContent = decisionSubtitle(action, entryTiming, planQuality);
    scannerScore.textContent = String(score);
    scannerScoreFill.style.width = `${score}%`;
    scannerScoreLabel.textContent = scannerScoreLabelText(score, action);
    scannerDirection.textContent = direction === "Neutral" && !planQuality.valid
        ? "No clean trade plan"
        : directionLabel(direction);
    scannerDirection.className = isReadyAction(action) ? direction.toLowerCase() : direction === "Neutral" ? "neutral" : "looking";
    scannerConfidence.textContent = confidence;
    scannerConfidence.className = confidence.toLowerCase();
    scannerPlanTitle.textContent = isFormingAction(action)
        ? "Projected Plan if Confirmed"
        : isReadyAction(action)
            ? "Confirmed Trade Plan"
            : "No Valid Trade Plan";

    const triggerLevel = levels.trigger_level;
    scannerTrigger.textContent = Number.isFinite(Number(triggerLevel))
        ? `${direction === "Buy" ? "Buy above" : direction === "Sell" ? "Sell below" : "Watch"} ${formatPrice(triggerLevel, analysis)}`
        : "No valid entry trigger yet";
    const stopPrice = levels.stop_loss ?? tradeMetrics.stop_loss;
    scannerStop.textContent = Number.isFinite(Number(stopPrice))
        ? formatPrice(stopPrice, analysis)
        : "No valid stop loss yet";
    scannerRisk.textContent = tradeMetrics.risk?.display
        ? `Risk: ${tradeMetrics.risk.display}`
        : "Risk unavailable";
    renderScannerTarget(
        scannerTp1,
        scannerTp1Distance,
        scannerRr1,
        tradeMetrics.tp1,
        analysis,
    );
    renderScannerTarget(
        scannerTp2,
        scannerTp2Distance,
        scannerRr2,
        tradeMetrics.tp2,
        analysis,
    );
    const planWarnings = Array.isArray(tradeMetrics.warnings) ? tradeMetrics.warnings : [];
    scannerPlanWarning.textContent = isFormingAction(action) && !planQuality.valid
        ? "No clean trade plan yet until confirmation."
        : planQuality.scannerWarning || planWarnings[0] || "";
    scannerPlanWarning.hidden = !(planQuality.scannerWarning || planWarnings.length);
    if (isFormingAction(action) && !planQuality.valid) {
        scannerPlanWarning.hidden = false;
    }

    const reasons = [...new Set((formattedReasons || [])
        .map((reason) => scannerReasonText(reason, action))
        .filter(Boolean))]
        .slice(0, 3);
    if (!reasons.length) {
        reasons.push(plainEnglishAnalysisText(answers.market_story || "The market has not confirmed a trade."));
    }
    renderScannerReasons(reasons);
    scannerNextAction.textContent = decisionNextAction({
        status: action,
        direction,
        triggerLevel,
        timing: entryTiming,
        analysis,
        planQuality,
        fallback: answers.next_action,
    });
    const lifecycle = evaluateTradeLifecycle(analysis, action, direction);
    analysis.trade_lifecycle = lifecycle;
    renderEntryTiming(entryTiming, analysis, planQuality, action);
    syncDecisionPanelFromScanner(action);
    renderTradeLifecycle(lifecycle);
    renderHomeDecisionFromScanner();
}

function syncDecisionPanelFromScanner(action) {
    if (!decisionStatus) return;

    decisionStatus.textContent = action;
    decisionStatus.className = statusToneClass(action);
    decisionDirection.textContent = scannerDirection.textContent;
    decisionDirection.className = scannerDirection.className;
    decisionScore.textContent = `${scannerScore.textContent}/100`;
    decisionConfidence.textContent = scannerConfidence.textContent;
    decisionConfidence.className = scannerConfidence.className;
    decisionEntry.textContent = isReadyAction(action) || isFormingAction(action)
        ? scannerTrigger.textContent
        : "No clean trade plan yet.";
    decisionStop.textContent = isReadyAction(action) || isFormingAction(action)
        ? scannerStop.textContent
        : "--";
    decisionTp1.textContent = scannerTp1.textContent;
    decisionTp2.textContent = scannerTp2.textContent;
    decisionRisk.textContent = scannerRisk.textContent.replace(/^Risk:\s*/i, "") || "Unavailable";
    decisionRr.textContent = [scannerRr1.textContent, scannerRr2.textContent]
        .filter((value) => value && value !== "R:R unavailable")
        .join(" / ") || "Unavailable";
}

function scannerScoreLabelText(score, action) {
    if (action === "NO CLEAN ENTRY" || score <= 39) return "No clean entry";
    if (!isReadyAction(action) || score <= 79) return "Setup forming";
    return "Trade plan confirmed";
}

function tradeScoreConfidence(score) {
    if (score >= 80) return "High";
    if (score >= 55) return "Medium";
    if (score >= 30) return "Low";
    return "Low";
}

function decisionSubtitle(status, timing = {}, planQuality = { valid: true }) {
    const timingStatus = String(timing?.entry_timing_status || "").toLowerCase();
    if (isFormingAction(status)) return "Setup is forming, but entry is not confirmed.";
    if (!planQuality.valid) {
        return planQuality.reason === "weak_reward" || planQuality.reason === "no_acceptable_target"
            ? "Reward is too small compared to risk."
            : "No clean trade plan is available.";
    }
    if (timingStatus === "too_late") return "Price already moved away from the entry area.";
    if (isReadyAction(status)) return "Entry, stop, and target are aligned.";
    return "No confirmed entry is available at the current price.";
}

function evaluateTradeLifecycle(analysis, action, direction) {
    const metrics = analysis.trade_metrics || {};
    const levels = analysis.levels || {};
    const candles = Array.isArray(analysis.candles) ? analysis.candles : [];
    const normalizedDirection = tradeDirection(direction);
    const entry = Number(metrics.entry_price ?? levels.trigger_level);
    const stop = Number(metrics.stop_loss ?? levels.stop_loss);
    const tp1 = Number(metrics.tp1?.price ?? levels.tp1);
    const tp2 = Number(metrics.tp2?.price ?? levels.tp2);
    const planIsFinal = String(metrics.plan_mode || analysis.levels_mode || "").toLowerCase() === "final";

    if (!isReadyAction(action) || !planIsFinal) {
        return {
            status: "NO ACTIVE POSITION",
            tone: "pending",
            message: "A confirmed position is not active yet. Track TP or SL only after activation.",
        };
    }

    if (!candles.length || !Number.isFinite(entry) || !Number.isFinite(stop) || normalizedDirection === "NEUTRAL") {
        return {
            status: "LIFECYCLE UNAVAILABLE",
            tone: "pending",
            message: "Trade levels are confirmed, but there is not enough candle data to verify activation.",
        };
    }

    const startIndex = lifecycleStartIndex(analysis, candles);
    const activeCandles = candles.slice(startIndex);
    const entryIndexOffset = activeCandles.findIndex((candle) => levelTouched(candle, entry, normalizedDirection === "BUY" ? "above" : "below"));
    if (entryIndexOffset < 0) {
        return {
            status: "READY, NOT ACTIVATED",
            tone: "pending",
            message: `The trade plan is ready, but price has not touched ${formatPrice(entry, analysis)} on the tracked candles.`,
        };
    }

    const entryIndex = startIndex + entryIndexOffset;
    const afterEntry = candles.slice(entryIndex);
    for (const candle of afterEntry) {
        const stopHit = levelTouched(candle, stop, normalizedDirection === "BUY" ? "below" : "above");
        const tp2Hit = Number.isFinite(tp2) && levelTouched(candle, tp2, normalizedDirection === "BUY" ? "above" : "below");
        const tp1Hit = Number.isFinite(tp1) && levelTouched(candle, tp1, normalizedDirection === "BUY" ? "above" : "below");
        const targetHit = tp2Hit || tp1Hit;
        if (stopHit && targetHit) {
            return {
                status: "OUTCOME UNCLEAR",
                tone: "warning",
                message: "Entry activated, but TP and SL were both touched inside one candle. Use a lower timeframe or replay to confirm which hit first.",
            };
        }
        if (stopHit) {
            return {
                status: "STOP LOSS HIT",
                tone: "loss",
                message: `Entry activated and stop loss was touched at ${formatPrice(stop, analysis)}.`,
            };
        }
        if (tp2Hit) {
            return {
                status: "TP2 HIT",
                tone: "win",
                message: `Entry activated and TP2 was touched at ${formatPrice(tp2, analysis)}.`,
            };
        }
        if (tp1Hit) {
            return {
                status: "TP1 HIT",
                tone: "win",
                message: `Entry activated and TP1 was touched at ${formatPrice(tp1, analysis)}.`,
            };
        }
    }

    return {
        status: "TRADE ACTIVATED",
        tone: "active",
        message: `Entry has been touched at ${formatPrice(entry, analysis)}. No TP or SL touch is visible on the tracked candles yet.`,
    };
}

function lifecycleStartIndex(analysis, candles) {
    const overlays = getOverlays(analysis);
    const candidateTimes = [
        overlays.entry_zone?.start_time,
        overlays.confirmation_level?.time,
        overlays.trigger_level?.time,
        overlays.mss_level?.time,
        analysis.active_zone?.start_time,
    ].map(normalizeLifecycleTime).filter(Number.isFinite);
    const startTime = candidateTimes.length ? Math.max(...candidateTimes) : null;
    if (startTime) {
        const index = candles.findIndex((candle) => normalizeLifecycleTime(candle.time) >= startTime);
        if (index >= 0) return index;
    }
    return Math.max(0, candles.length - 80);
}

function normalizeLifecycleTime(value) {
    if (value === null || value === undefined || value === "") return NaN;
    if (typeof value === "number") return value > 100000000000 ? Math.floor(value / 1000) : value;
    const numeric = Number(value);
    if (Number.isFinite(numeric)) return numeric > 100000000000 ? Math.floor(numeric / 1000) : numeric;
    const parsed = Date.parse(String(value));
    return Number.isFinite(parsed) ? Math.floor(parsed / 1000) : NaN;
}

function levelTouched(candle, price, side) {
    const high = Number(candle.high);
    const low = Number(candle.low);
    if (!Number.isFinite(high) || !Number.isFinite(low) || !Number.isFinite(price)) return false;
    return side === "above" ? high >= price : low <= price;
}

function renderTradeLifecycle(lifecycle) {
    if (!decisionLifecycleCard || !decisionLifecycleStatus || !decisionLifecycleMessage) return;
    decisionLifecycleCard.dataset.lifecycle = lifecycle.tone || "pending";
    decisionLifecycleStatus.textContent = lifecycle.status || "NO ACTIVE POSITION";
    decisionLifecycleMessage.textContent = lifecycle.message || "A confirmed trade plan has not activated yet.";
}

function decisionNextAction({ status, direction, triggerLevel, timing, analysis, planQuality = { valid: true }, fallback }) {
    const timingStatus = String(timing?.entry_timing_status || "").toLowerCase();
    if (timingStatus === "too_late") {
        return "Do not chase. Look for a fresh entry or a clean pullback.";
    }
    if (isReadyAction(status)) return "Use the trade plan below.";
    if (status === "NO CLEAN ENTRY" && direction === "Neutral") {
        return "Stand aside until direction and entry confirmation are clear.";
    }
    if (isFormingAction(status)) {
        const trigger = Number(triggerLevel);
        if (Number.isFinite(trigger)) {
            const relation = direction === "Buy" ? "above" : "below";
            return `Watch for a candle close ${relation} ${formatPrice(trigger, analysis)}.`;
        }
        return `Watch for clear ${String(direction).toLowerCase()} confirmation before entering.`;
    }
    if (!planQuality.valid) {
        return "Do not force this setup. Wait for a cleaner structure or better target.";
    }
    if (["missed", "invalid"].includes(timingStatus) && timing?.next_action) {
        return plainEnglishAnalysisText(oneSentenceAction(timing.next_action));
    }
    const cleanedFallback = plainEnglishAnalysisText(oneSentenceAction(fallback || ""));
    return cleanedFallback && !/\bwait\b/i.test(cleanedFallback)
        ? cleanedFallback
        : "Look for a cleaner setup before entering.";
}

function renderEntryTiming(timing, analysis, planQuality = tradePlanQuality(analysis || {}), action = analysisDecisionStatus(analysis || {})) {
    const available = Boolean(timing?.available);
    let status = String(timing?.entry_timing_status || "unavailable").toLowerCase();
    let message = timing?.message || "Entry timing will appear when a valid plan exists.";
    const finalDirection = tradeDirection(analysis?.direction_debug?.final_direction || analysis?.strategy_result?.direction_debug?.final_direction || analysis?.trade_direction);
    const directionIsUnclear = finalDirection === "NEUTRAL";
    if (isFormingAction(action) && ["at_entry", "near_entry", "extended"].includes(status)) {
        status = "setup_forming";
        message = "Setup is forming, but entry is not confirmed. Wait for the trigger close.";
    } else if (directionIsUnclear && ["at_entry", "near_entry", "extended"].includes(status)) {
        status = "unavailable";
        message = "Direction is not clear enough to evaluate entry timing.";
    } else if (!planQuality.valid) {
        status = planQuality.reason === "weak_reward" || planQuality.reason === "no_acceptable_target"
            ? "poor_reward"
            : "unavailable";
        message = planQuality.reason === "weak_reward" || planQuality.reason === "no_acceptable_target"
            ? "Price may be near the entry area, but reward is too small to justify entry."
            : "Entry timing is unavailable because the trade plan is not clean.";
    }
    const labels = {
        at_entry: "AT ENTRY",
        near_entry: "NEAR ENTRY",
        setup_forming: "SETUP FORMING",
        extended: "EXTENDED",
        poor_reward: "POOR REWARD",
        too_late: "NO CLEAN ENTRY",
        missed: "NO CLEAN ENTRY",
        invalid: available ? "NO CLEAN ENTRY" : "PENDING",
        unavailable: "PENDING",
    };
    const label = labels[status] || titleCase(status.replaceAll("_", " "));
    const distance = Number(timing?.distance_from_entry_pips);
    const rr = Number(timing?.remaining_rr_to_tp1);
    const unit = timing?.distance_unit || analysis?.trade_metrics?.unit || "points";
    const metricParts = [];
    if (planQuality.valid && Number.isFinite(distance)) metricParts.push(`${distance.toFixed(1)} ${unit} from planned entry`);
    if (planQuality.valid && Number.isFinite(rr)) metricParts.push(`${rr.toFixed(2)}R remaining to TP1`);

    scannerEntryTimingCard.dataset.status = status;
    scannerEntryTimingStatus.textContent = label;
    scannerEntryTimingMessage.textContent = message;
    scannerEntryTimingMetrics.textContent = metricParts.join(" · ") || "Current-price risk and reward unavailable.";
    chartEntryTiming.dataset.status = status;
    chartEntryTimingStatus.textContent = label;
    chartEntryTimingMessage.textContent = message;
    if (decisionEntryTimingStatus) {
        decisionEntryTimingStatus.textContent = label;
        decisionEntryTimingMessage.textContent = message;
    }
}

function scannerReasonText(value, action) {
    const original = String(value || "");
    if (isFormingAction(action) && /(?:directional )?liquidity has been swept/i.test(original)) {
        return "Liquidity sweep is present, but confirmation is still missing.";
    }
    return plainEnglishAnalysisText(original);
}

function renderScannerTarget(priceElement, distanceElement, rrElement, target, analysis) {
    if (!target || !Number.isFinite(Number(target.price))) {
        priceElement.textContent = "No valid TP yet";
        distanceElement.textContent = "Expected TP unavailable";
        rrElement.textContent = "R:R unavailable";
        return;
    }

    const rr = Number(target.risk_reward);
    if (Number.isFinite(rr) && rr < 1.0) {
        priceElement.textContent = "No valid TP yet";
        distanceElement.textContent = "TP reward is too weak";
        rrElement.textContent = `R:R ${rr.toFixed(2)}R`;
        return;
    }

    priceElement.textContent = formatPrice(target.price, analysis);
    distanceElement.textContent = target.distance?.display
        ? `Expected TP: ${target.distance.display}`
        : "Expected TP unavailable";
    rrElement.textContent = Number.isFinite(rr)
        ? `R:R ${rr.toFixed(Number.isInteger(rr) ? 1 : 2)}R`
        : "R:R unavailable";
}

function renderScannerReasons(reasons) {
    scannerReasons.innerHTML = "";
    for (const reason of reasons.slice(0, 3)) {
        const item = document.createElement("li");
        item.textContent = reason;
        scannerReasons.appendChild(item);
    }
}

function plainEnglishAnalysisText(value) {
    return userFacingText(String(value || ""))
        .replace(/higher-timeframe/gi, "higher timeframe")
        .replace(/directional liquidity has not been swept yet/gi, "the liquidity sweep is still missing")
        .replace(/directional liquidity has been swept/gi, "a liquidity sweep is present")
        .replace(/liquidity has not been swept yet/gi, "the liquidity sweep is still missing")
        .replace(/liquidity has been swept/gi, "a liquidity sweep is present")
        .replace(/\bIFVG\b/gi, "confirmed price area")
        .replace(/\bFVG\b/gi, "price imbalance area")
        .replace(/\bOTE\b/gi, "preferred pullback area")
        .replace(/\bCHoCH\b|\bMSS\b/gi, "structure confirmation")
        .replace(/order block/gi, "institutional price area")
        .replace(/kill zone/gi, "active trading session")
        .replace(/liquidity sweep/gi, "move through a prior high or low")
        .replace(/directional liquidity/gi, "a prior directional high or low")
        .trim();
}

function userFacingText(value) {
    return String(value || "")
        .replace(/\bNO[_ ]TRADE\b/gi, "NO CLEAN ENTRY")
        .replace(/\bENTRY[_ ]READY\b/gi, "confirmed entry")
        .replace(/\bWAITING[_ ]FOR[_ ]RETEST\b/gi, "retest is still pending")
        .replace(/\bWAITING[_ ]FOR[_ ]CONFIRMATION\b/gi, "confirmation is still pending");
}

function oneSentenceAction(value) {
    const text = userFacingText(value).trim();
    if (text === "Do not chase. Look for a fresh entry or a clean pullback.") return text;
    const parts = text.match(/[^.!?]+[.!?]?/g) || [];
    if (parts.length <= 1) return text;
    return `${parts.slice(0, 2).map((part) => part.trim().replace(/[.!?]+$/, "")).join("; ")}.`;
}

function showScannerError(message) {
    if (!scannerPlaceholder || !scannerResult) return;
    scannerPlaceholder.hidden = true;
    scannerResult.hidden = false;
    scannerMarket.textContent = `${getFormParams().symbol} · ${getFormParams().timeframe}`;
    scannerAction.textContent = "NO CLEAN ENTRY";
    scannerAction.className = "avoid";
    scannerResult.dataset.action = "avoid";
    scannerState.textContent = "Analysis could not be completed.";
    scannerScore.textContent = "0";
    scannerScoreFill.style.width = "0%";
    scannerScoreLabel.textContent = "No clean entry";
    scannerDirection.textContent = "Neutral";
    scannerDirection.className = "neutral";
    scannerConfidence.textContent = "Low";
    scannerConfidence.className = "low";
    scannerPlanTitle.textContent = "No Valid Trade Plan";
    scannerTrigger.textContent = "No valid entry trigger yet";
    scannerStop.textContent = "No valid stop loss yet";
    scannerRisk.textContent = "Risk unavailable";
    scannerPlanWarning.textContent = "";
    scannerPlanWarning.hidden = true;
    renderScannerTarget(scannerTp1, scannerTp1Distance, scannerRr1, null, null);
    renderScannerTarget(scannerTp2, scannerTp2Distance, scannerRr2, null, null);
    renderScannerReasons([message]);
    scannerNextAction.textContent = "Resolve the data error, then analyze the market again.";
    renderEntryTiming({}, null);
    resetHomeDecision("Analysis could not be completed. Try again when data is available.");
}

function markScannerSelectionChanged() {
    if (!lastLoadedParams || !scannerPlaceholder || !scannerResult) return;
    const current = getFormParams();
    const changed = current.symbol !== lastLoadedParams.symbol
        || current.timeframe !== lastLoadedParams.timeframe
        || current.strategy !== lastLoadedParams.strategy;
    if (!changed) return;

    scannerResult.hidden = true;
    scannerPlaceholder.hidden = false;
    scannerPlaceholderMarket.textContent = `${current.symbol} · ${current.timeframe}`;
    scannerPlaceholder.querySelector("strong").textContent = "Waiting for new analysis";
}

function updateTopSelection() {
    const params = getFormParams();
    topSymbol.textContent = params.symbol;
    topTimeframe.textContent = params.timeframe;
    topStrategy.textContent = strategyLabel(params.strategy);
    if (params.multi_timeframe !== "1" && contextTimeframeSwitcher) {
        contextTimeframeSwitcher.hidden = true;
    } else {
        renderContextTimeframeSwitcher(params.timeframe);
    }
    answerMarket.textContent = `${params.symbol} · ${params.timeframe}`;
    if (scannerPlaceholderMarket) {
        scannerPlaceholderMarket.textContent = `${params.symbol} · ${params.timeframe}`;
    }
    if (ictDetailsPanel) {
        ictDetailsPanel.hidden = params.strategy !== "ict_2022";
    }
    if (supplyDemandDetailsPanel) {
        supplyDemandDetailsPanel.hidden = params.strategy !== "supply_demand";
    }
    if (breakoutDetailsPanel) {
        breakoutDetailsPanel.hidden = params.strategy !== "breakout_retest";
    }
}

function buildQuery(params) {
    return new URLSearchParams({ ...params, manual: "1" }).toString();
}

async function fetchJson(url) {
    const response = await fetch(url);
    let data;

    try {
        data = await response.json();
    } catch (error) {
        throw new Error("The server returned a response that was not JSON.");
    }

    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });
    let data;

    try {
        data = await response.json();
    } catch (error) {
        throw new Error("The server returned a response that was not JSON.");
    }

    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

async function loadChart(params = getFormParams(), options = { fromTimer: false }) {
    try {
        if (!options.fromTimer) {
            setScannerLoading(params);
        }
        createChartIfNeeded();
        stopReplay();
        setAnalysisMode("live");

        const query = buildQuery(params);

        loadButton.disabled = true;
        setStatus(`Loading ${params.symbol.toUpperCase()} ${params.timeframe}...`, "Working");
        if (!options.fromTimer) {
            clearLoadedContext();
        }

        const payload = await fetchJson(`/api/analyze?${query}`);
        const analysis = normalizeStrategyAnalysis(payload.analysis || payload);
        const candles = prepareCandlesForChart(payload.candles || analysis.candles);
        analysis.candles = candles;
        lastLoadedParams = { ...params };
        latestAnalysis = analysis;
        storeMultiTimeframeContext(payload);

        resizeChartToContainer();
        applyChartPriceFormat(analysis);
        candleSeries.setData(candles);
        chart.timeScale().fitContent();
        emptyState.hidden = true;

        drawAnalysisOverlays(analysis);
        requestAnimationFrame(() => {
            chart.timeScale().fitContent();
            drawAnalysisOverlays(analysis);
        });
        if (!options.fromTimer) {
            resetAnalysisTimeline();
        }
        renderAnalysis(analysis);
        if (!options.fromTimer) {
            rememberRecentMarket();
        }
        resetReplay(candles);

        const now = new Date().toLocaleTimeString();
        chartTitle.textContent = `${analysis.display_symbol || analysis.symbol || params.symbol} · ${analysis.timeframe || params.timeframe}`;
        lastLoaded.textContent = `Last updated: ${now}`;
        setStatus(
            chartDecisionSubtitle(analysisDecisionStatus(analysis), analysis.entry_timing || {}),
            analysisDecisionStatus(analysis),
        );
        _updateMismatchWarning();
    } catch (error) {
        showError(error.message);
    } finally {
        loadButton.disabled = false;
        if (!options.fromTimer) {
            configureAutoRefresh();
        }
    }
}

function setStatus(message, state) {
    statusText.textContent = message;
    detailState.textContent = state;
}

function resizeChartToContainer() {
    if (!chart) {
        return;
    }

    chart.applyOptions({
        width: Math.max(chartElement.clientWidth, 320),
        height: Math.max(chartElement.clientHeight, 360),
    });
}

function prepareCandlesForChart(candles) {
    if (!Array.isArray(candles) || candles.length === 0) {
        throw new Error("No candle data was returned. Try another symbol, timeframe, or bar count.");
    }

    const cleaned = [];
    const byTime = new Map();

    for (const candle of candles) {
        const time = Number(candle.time);
        const open = Number(candle.open);
        const high = Number(candle.high);
        const low = Number(candle.low);
        const close = Number(candle.close);

        if (![time, open, high, low, close].every(Number.isFinite)) {
            continue;
        }

        byTime.set(time, { time, open, high, low, close });
    }

    for (const candle of byTime.values()) {
        cleaned.push(candle);
    }

    cleaned.sort((a, b) => a.time - b.time);

    if (cleaned.length === 0) {
        throw new Error("Candle data was returned, but none of the candles were valid for the chart.");
    }

    return cleaned;
}

function storeMultiTimeframeContext(payload) {
    const multiTimeframe = payload.multi_timeframe || payload.analysis?.multi_timeframe || {};
    const context = multiTimeframe.context || {};
    const selectedTimeframe = String(
        payload.selected_timeframe
        || payload.timeframe
        || payload.analysis?.selected_timeframe
        || payload.analysis?.timeframe
        || getFormParams().timeframe
    ).toUpperCase();
    const selectedCandles = payload.candles || multiTimeframe.selected?.candles || payload.analysis?.candles;

    loadedContextCandles = {};
    loadedCacheStatus = multiTimeframe.cache || payload.cache || payload.analysis?.cache || {};

    for (const [timeframe, candles] of Object.entries(context)) {
        try {
            if (Array.isArray(candles) && candles.length) {
                loadedContextCandles[String(timeframe).toUpperCase()] = prepareCandlesForChart(candles);
            }
        } catch (error) {
            console.warn(`Skipping invalid ${timeframe} context candles:`, error.message);
        }
    }

    if (Array.isArray(selectedCandles) && selectedCandles.length) {
        loadedContextCandles[selectedTimeframe] = prepareCandlesForChart(selectedCandles);
    }

    renderContextTimeframeSwitcher(selectedTimeframe);
}

function clearLoadedContext() {
    loadedContextCandles = {};
    loadedCacheStatus = {};

    if (contextTimeframeSwitcher) {
        contextTimeframeSwitcher.innerHTML = "";
        contextTimeframeSwitcher.hidden = true;
    }
}

function renderContextTimeframeSwitcher(selectedTimeframe) {
    if (!contextTimeframeSwitcher) {
        return;
    }

    const loadedTimeframes = Object.keys(loadedContextCandles);

    if (getFormParams().multi_timeframe !== "1" || loadedTimeframes.length <= 1) {
        contextTimeframeSwitcher.hidden = true;
        contextTimeframeSwitcher.innerHTML = "";
        return;
    }

    const normalizedSelected = String(selectedTimeframe || getFormParams().timeframe).toUpperCase();
    const labels = [...CONTEXT_SWITCHER_TIMEFRAMES];

    if (loadedTimeframes.includes("H2") && !labels.includes("H2")) {
        labels.splice(labels.indexOf("H4"), 0, "H2");
    }

    for (const timeframe of loadedTimeframes.sort(sortTimeframes)) {
        if (!labels.includes(timeframe)) {
            labels.push(timeframe);
        }
    }

    contextTimeframeSwitcher.innerHTML = "";

    const caption = document.createElement("span");
    caption.textContent = "Loaded context";
    contextTimeframeSwitcher.appendChild(caption);

    for (const timeframe of labels) {
        const button = document.createElement("button");
        const hasCandles = Array.isArray(loadedContextCandles[timeframe]) && loadedContextCandles[timeframe].length > 0;

        button.type = "button";
        button.textContent = timeframe;
        button.disabled = !hasCandles;
        button.classList.toggle("active", timeframe === normalizedSelected);
        button.title = hasCandles
            ? `${timeframe} loaded from ${loadedCacheStatus[timeframe] || "context cache"}`
            : `${timeframe} was not loaded for this context depth`;
        button.addEventListener("click", () => switchLoadedTimeframe(timeframe));
        contextTimeframeSwitcher.appendChild(button);
    }

    contextTimeframeSwitcher.hidden = false;
}

function sortTimeframes(first, second) {
    return (CONTEXT_TIMEFRAME_ORDER[first] || 99) - (CONTEXT_TIMEFRAME_ORDER[second] || 99);
}

async function switchLoadedTimeframe(timeframe) {
    const normalizedTimeframe = String(timeframe || "").toUpperCase();
    const candles = loadedContextCandles[normalizedTimeframe];

    if (!Array.isArray(candles) || candles.length === 0) {
        setStatus(`${normalizedTimeframe} context is not loaded.`, "Waiting");
        return;
    }

    try {
        createChartIfNeeded();
        stopReplay();
        setAnalysisMode("live");
        resetAnalysisTimeline();

        const timeframeSelect = document.getElementById("timeframe");
        if (timeframeSelect && [...timeframeSelect.options].some((option) => option.value === normalizedTimeframe)) {
            timeframeSelect.value = normalizedTimeframe;
            updateAllButtonOptions();
        }

        const currentParams = getFormParams();
        lastLoadedParams = {
            ...(lastLoadedParams || currentParams),
            timeframe: normalizedTimeframe,
            strategy: currentParams.strategy,
            multi_timeframe: currentParams.multi_timeframe,
            context_depth: currentParams.context_depth,
        };

        loadButton.disabled = true;
        setStatus(`Switching to loaded ${normalizedTimeframe} context...`, "Working");

        resizeChartToContainer();
        applyChartPriceFormat({
            display_symbol: lastLoadedParams.symbol,
            asset_type: latestAnalysis?.asset_type,
        });
        candleSeries.setData(candles);
        chart.timeScale().fitContent();
        emptyState.hidden = true;

        const payload = await postJson("/api/analyze-replay", {
            symbol: lastLoadedParams.symbol || currentParams.symbol,
            timeframe: normalizedTimeframe,
            strategy: lastLoadedParams.strategy || currentParams.strategy,
            multi_timeframe: Object.keys(loadedContextCandles).length > 1,
            context_depth: lastLoadedParams.context_depth || currentParams.context_depth,
            candles,
            context_candles: loadedContextCandles,
        });
        const analysis = normalizeStrategyAnalysis(payload.analysis || payload);
        const analyzedCandles = prepareCandlesForChart(payload.candles || candles);

        analysis.candles = analyzedCandles;
        latestAnalysis = analysis;
        applyChartPriceFormat(analysis);
        candleSeries.setData(analyzedCandles);
        chart.timeScale().fitContent();
        drawAnalysisOverlays(analysis);
        renderAnalysis(analysis);
        resetReplay(analyzedCandles);
        renderContextTimeframeSwitcher(normalizedTimeframe);

        chartTitle.textContent = `${analysis.display_symbol || analysis.symbol || lastLoadedParams.symbol || "Chart"} · ${normalizedTimeframe}`;
        setStatus(
            chartDecisionSubtitle(analysisDecisionStatus(analysis), analysis.entry_timing || {}),
            analysisDecisionStatus(analysis),
        );
    } catch (error) {
        showError(error.message);
    } finally {
        loadButton.disabled = false;
        configureAutoRefresh();
    }
}

function showError(message) {
    showScannerError(message);
    statusText.textContent = message;
    chartDecisionStatus.textContent = "NO CLEAN ENTRY";
    chartDecisionStatus.className = "avoid";
    chartDirection.textContent = "Looking for: No clear direction yet";
    detailState.textContent = "NO CLEAN ENTRY";
    setupStatusLabel.textContent = "NO CLEAN ENTRY";
    setupDirection.textContent = "NO CLEAN ENTRY";
    setupBias.textContent = "Neutral";
    answerPriceLocation.textContent = "No clear level";
    answerMarketIntent.textContent = "Ranging / undecided";
    answerMarket.textContent = "Not loaded";
    answerNow.textContent = message;
    answerZone.textContent = "Not enough data yet.";
    answerConfirmation.textContent = "No confirmation level yet.";
    answerInvalidation.textContent = "No invalidation level yet.";
    answerTopdown.textContent = "Not loaded";
    answerTopdownSummary.textContent = message;
    assistantTrendExplanation.textContent = message;
    assistantLocationExplanation.textContent = message;
    assistantIntentExplanation.textContent = message;
    assistantStatusExplanation.textContent = "Not Ready. Analysis could not be completed.";
    assistantNextOutcome.textContent = "Fix the error, then load the chart again.";
    storyInstruction.textContent = "No market conclusion was produced.";
    chartCurrentPrice.textContent = "--";
    chartPriceChange.textContent = "--";
    chartPriceChange.className = "";
    chartHigh.textContent = "--";
    chartLow.textContent = "--";
    chartSpread.textContent = "--";
    renderTradeLifecycle({
        status: "NO ACTIVE POSITION",
        tone: "pending",
        message: "A confirmed trade plan has not activated yet.",
    });
    keyNextTarget.textContent = "No trade yet";
    keyBias.textContent = "Unclear";
    keyRiskReward.textContent = "No trade yet";
    renderHtfContext({});
    storyPhase.textContent = "Waiting";
    setupState.textContent = "Error";
    setupReadiness.textContent = "Not Ready";
    marketClarity.textContent = "--";
    marketClarity.className = "";
    tradeReadiness.textContent = "Not Ready";
    tradeReadiness.className = "not-ready";
    nextConfirmation.textContent = message;
    suggestedAction.textContent = "Fix the error, then click Load Chart again.";
    setupScore.textContent = "0";
    setupQuality.textContent = "--";
    tradeQuality.textContent = "--";
    tradeQuality.classList.remove("accepted", "rejected");
    setupSummary.textContent = message;
    macroSummary.textContent = message;
    macroAlignment.textContent = "Error";
    macroNewsWarning.hidden = true;
    macroSessionName.textContent = "--";
    macroSessionDetail.textContent = message;
    macroTopdownList.textContent = message;
    macroDxyTrend.textContent = "--";
    macroDxyStatus.textContent = message;
    macroNewsStatus.textContent = "--";
    macroNewsDetail.textContent = message;
    macroPhaseName.textContent = "--";
    macroPhaseDetail.textContent = message;
    renderMarketFilters({
        news_risk: {
            risk_level: "unavailable",
            message: "Marketaux news unavailable.",
        },
        dxy_confirmation: {
            available: false,
            message: "DXY unavailable — not included in analysis.",
        },
    });
    levelList.classList.add("levels-locked");
    levelNote.textContent = "No valid trade levels yet.";
    renderObjectivePlan({ decision: "PENDING", reason: message });
    renderMarketStoryTimeline(["Analysis stopped because the chart could not be loaded."]);
    topdownAlignment.textContent = "Error";
    topdownList.textContent = message;
    sessionEntry.textContent = "Error";
    sessionCurrent.textContent = "--";
    sessionStatus.textContent = "--";
    sessionPhase.textContent = "--";
    sessionNext.textContent = "--";
    sessionRemaining.textContent = "--";
    sessionAllowed.textContent = "--";
    sessionBehavior.textContent = "--";
    contextCount.textContent = "Error";
    marketContextList.textContent = message;
    liquidityMapList.textContent = message;
    structureCount.textContent = "Error";
    structureList.textContent = message;
    explanationStatus.textContent = "Error";
    setupExplanation.textContent = message;
    renderWhy([{ status: "waiting", text: message }]);
    renderProgress([]);
    timelineList.textContent = message;
    rawAnalysis.textContent = message;
    answerQaValidation.textContent = "Error";
    answerQaValidation.className = "warning";
    answerQaCurrent.textContent = message;
    answerQaSource.textContent = "No strategy result loaded.";
    answerQaConditions.textContent = message;
    answerQaWarnings.textContent = message;
    answerQaClarity.textContent = message;
    disableReplay();
    resetAnalysisTimeline();
    setAnalysisMode("live");
    clearLoadedContext();
    clearPriceLines();
    clearZoneRectangles();
}

function clearPriceLines() {
    if (!candleSeries) {
        return;
    }

    for (const line of priceLines) {
        candleSeries.removePriceLine(line);
    }

    priceLines = [];
    drawnPriceLabelCoordinates = [];
}

function clearZoneRectangles() {
    if (!chartOverlayLayer) {
        return;
    }

    chartOverlayLayer.innerHTML = "";
}

function drawAnalysisOverlays(analysis) {
    latestAnalysis = analysis;
    clearPriceLines();
    clearZoneRectangles();

    const overlays = getOverlays(analysis);
    const levels = analysis.levels || {};
    const candles = analysis.candles || [];
    const currentPrice = overlays.current_price?.price
        ?? (candles.length ? candles[candles.length - 1].close : null);
    const confirmationPrice = levels.trigger_level
        ?? overlays.confirmation_level?.price
        ?? overlays.mss_level?.level;
    const tradeMetrics = analysis.trade_metrics || {};
    const stopPrice = levels.stop_loss ?? tradeMetrics.stop_loss;
    const tp1Price = levels.tp1 ?? tradeMetrics.tp1?.price;
    const tp2Price = levels.tp2 ?? tradeMetrics.tp2?.price;
    const invalidationPrice = levels.invalidation
        ?? overlays.invalidation_level?.price
        ?? overlays.invalidation_level
        ?? overlays.invalid_level
        ?? analysis.invalidation_level;

    const planMode = chartPlanMode(analysis);
    const labels = planMode === "active"
        ? { entry: "Entry Zone", stop: "Stop Loss Zone", tp1: "TP1 Zone", tp2: "TP2 Zone" }
        : planMode === "prior"
            ? { entry: "Prior Entry Zone", stop: "Prior Stop Zone", tp1: "Prior Target Zone", tp2: "Prior Target Zone" }
            : { entry: "Entry Trigger", stop: "Invalidation", tp1: "Target Liquidity", tp2: "Target Liquidity" };
    const shouldDrawFullPlan = tradePlanToggle.checked && planMode === "active";
    const shouldDrawTrigger = tradePlanToggle.checked && planMode === "forming";
    const shouldDrawPrior = tradePlanToggle.checked && planMode === "prior";
    drawLevelLine("Current Price", currentPrice, "#60a5fa", LightweightCharts.LineStyle.Dashed, { priority: 1 });
    if (shouldDrawFullPlan) {
        drawLevelLine(labels.entry, confirmationPrice, "#38bdf8", LightweightCharts.LineStyle.Dashed, { priority: 2 });
        drawLevelLine(labels.stop, stopPrice, "#ef4444", LightweightCharts.LineStyle.Dashed, { priority: 3 });
        drawLevelLine(labels.tp1, tp1Price, "#22c55e", LightweightCharts.LineStyle.Dashed, { priority: 4 });
        drawLevelLine(labels.tp2, tp2Price, "#22c55e", LightweightCharts.LineStyle.Dotted, { priority: 5 });
    } else if (shouldDrawTrigger) {
        drawLevelLine(labels.entry, confirmationPrice, "#38bdf8", LightweightCharts.LineStyle.Dashed, { priority: 2 });
        drawLevelLine(labels.stop, invalidationPrice, "#ef4444", LightweightCharts.LineStyle.Dotted, { priority: 3 });
        drawLevelLine(labels.tp1, tp1Price, "#22c55e", LightweightCharts.LineStyle.Dotted, { priority: 4 });
        drawLevelLine(labels.tp2, tp2Price, "#22c55e", LightweightCharts.LineStyle.Dotted, { priority: 5 });
    } else if (shouldDrawPrior) {
        drawLevelLine(labels.entry, confirmationPrice, "rgba(148, 163, 184, 0.72)", LightweightCharts.LineStyle.Dotted, { priority: 6 });
    }

    const stopNumber = Number(stopPrice);
    const invalidationNumber = Number(invalidationPrice);
    if (shouldDrawFullPlan && Number.isFinite(invalidationNumber) && (!Number.isFinite(stopNumber) || Math.abs(invalidationNumber - stopNumber) > 1e-10)) {
        drawLevelLine("Invalidation", invalidationPrice, "#ef4444", LightweightCharts.LineStyle.Dashed, { priority: 3 });
    }
    redrawChartOverlays();
}

function redrawChartOverlays() {
    clearZoneRectangles();
    if (!latestAnalysis || !chart || !candleSeries) {
        return;
    }

    if (contextZonesToggle.checked) {
        drawContextZones(latestAnalysis);
    }
    if (tradePlanToggle.checked && chartPlanMode(latestAnalysis) === "active") {
        drawRiskRewardOverlay(latestAnalysis);
    }
    drawChartStateMessage(latestAnalysis);
}

function drawRiskRewardOverlay(analysis) {
    if (chartPlanMode(analysis) !== "active") {
        return;
    }
    const metrics = analysis.trade_metrics || {};
    const levels = analysis.levels || {};

    const entry = Number(metrics.entry_price ?? levels.trigger_level);
    const stop = Number(metrics.stop_loss ?? levels.stop_loss);
    const targetMetrics = metrics.tp2 || metrics.tp1;
    const target = Number(targetMetrics?.price ?? levels.tp2 ?? levels.tp1);
    if (![entry, stop, target].every(Number.isFinite)) {
        return;
    }

    if ((target - entry) * (stop - entry) >= 0) {
        return;
    }

    const entryY = candleSeries.priceToCoordinate(entry);
    const stopY = candleSeries.priceToCoordinate(stop);
    const targetY = candleSeries.priceToCoordinate(target);
    if ([entryY, stopY, targetY].some((value) => value === null || value === undefined)) {
        return;
    }

    const chartWidth = chartElement.clientWidth;
    const left = Math.round(chartWidth * (chartWidth < 700 ? 0.42 : 0.62));
    const width = Math.max(110, chartWidth - left - 82);
    const planMode = chartPlanMode(analysis);
    const projected = planMode !== "active";
    const labelPrefix = planMode === "prior" ? "Prior " : projected ? "Projected " : "";
    const targetName = metrics.tp2 ? "TP2" : "TP1";
    const rewardText = targetMetrics?.distance?.display || "Reward";
    const riskText = metrics.risk?.display || "Risk";
    const rr = Number(targetMetrics?.risk_reward);

    drawRiskRewardArea({
        type: "reward",
        left,
        width,
        firstY: entryY,
        secondY: targetY,
        label: `${labelPrefix}${targetName} · +${rewardText}${Number.isFinite(rr) ? ` · ${rr.toFixed(2)}R` : ""}`,
        projected,
        showLabel: advancedLabelsToggle.checked,
    });
    drawRiskRewardArea({
        type: "risk",
        left,
        width,
        firstY: entryY,
        secondY: stopY,
        label: `${labelPrefix}Stop · -${riskText} · 1.00R`,
        projected,
        showLabel: advancedLabelsToggle.checked,
    });

    const entryZone = document.createElement("div");
    entryZone.className = `rr-entry-zone${projected ? " projected" : ""}`;
    entryZone.style.left = `${left}px`;
    entryZone.style.top = `${Math.round(entryY) - 6}px`;
    entryZone.style.width = `${width}px`;
    if (advancedLabelsToggle.checked && width >= 150) {
        const entryLabel = document.createElement("span");
        entryLabel.textContent = `${labelPrefix}Entry · ${formatPrice(entry, analysis)}`;
        entryZone.appendChild(entryLabel);
    }
    chartOverlayLayer.appendChild(entryZone);
}

function drawRiskRewardArea({ type, left, width, firstY, secondY, label, projected, showLabel }) {
    const top = Math.max(0, Math.min(firstY, secondY));
    const bottom = Math.min(chartElement.clientHeight, Math.max(firstY, secondY));
    if (bottom <= 0 || top >= chartElement.clientHeight) {
        return;
    }
    if (Math.abs(bottom - top) < 10) {
        return;
    }

    const area = document.createElement("div");
    area.className = `rr-area rr-${type}${projected ? " projected" : ""}`;
    area.style.left = `${left}px`;
    area.style.top = `${top}px`;
    area.style.width = `${width}px`;
    area.style.height = `${Math.max(bottom - top, 4)}px`;
    if (showLabel && bottom - top >= 26 && width >= 150) {
        const areaLabel = document.createElement("span");
        areaLabel.textContent = label;
        area.appendChild(areaLabel);
    }
    chartOverlayLayer.appendChild(area);
}

function isProjectedPlan(analysis, metrics) {
    return chartPlanMode(analysis) !== "active" || metrics.plan_mode === "projected";
}

function chartPlanMode(analysis) {
    const status = analysisDecisionStatus(analysis);
    const quality = tradePlanQuality(analysis);
    const timingStatus = String((analysis?.entry_timing || analysis?.strategy_result?.entry_timing || {}).entry_timing_status || "").toLowerCase();
    if (isReadyAction(status) && quality.valid) return "active";
    if (isFormingAction(status)) return "forming";
    if (timingStatus === "too_late" && advancedLabelsToggle.checked) return "prior";
    if (status === "NO CLEAN ENTRY" && advancedLabelsToggle.checked && quality.valid) return "prior";
    return "hidden";
}

function drawChartStateMessage(analysis) {
    if (!chartOverlayLayer) return;
    const mode = chartPlanMode(analysis);
    const quality = tradePlanQuality(analysis);
    let message = "";
    if (mode === "forming" && !quality.valid) {
        message = "No clean trade plan yet until confirmation.";
    } else if (!quality.valid) {
        message = quality.message || "No clean trade plan.";
    } else if (mode === "forming") {
        message = "Setup forming. Waiting for confirmation.";
    } else if (mode === "prior") {
        message = "Too late — do not chase.";
    } else if (mode === "hidden") {
        message = "No clean trade plan.";
    }
    if (!message) return;
    const note = document.createElement("div");
    note.className = "chart-plan-note";
    note.textContent = message;
    chartOverlayLayer.appendChild(note);
}

function drawContextZones(analysis) {
    const overlays = getOverlays(analysis);
    const seen = new Set();
    const candidates = [
        [overlays.active_fvg || overlays.fvg_zone, "fvg"],
        [overlays.ifvg_zone, "ifvg"],
    ];
    for (const [zone, kind] of candidates) {
        if (!zone) continue;
        const key = `${kind}|${zone.start_time}|${zone.top ?? zone.top_price}|${zone.bottom ?? zone.bottom_price}`;
        if (seen.has(key)) continue;
        seen.add(key);
        drawContextZone(zone, kind, analysis);
    }
}

function drawContextZone(zone, kind, analysis) {
    const topPrice = Number(zone.top ?? zone.top_price);
    const bottomPrice = Number(zone.bottom ?? zone.bottom_price);
    const startTime = zoneTimestamp(zone.start_time);
    const candles = analysis.candles || [];
    const lastTime = candles.length ? candles[candles.length - 1].time : zone.start_time;
    const endTime = zoneTimestamp(zone.end_time ?? zone.rectangle_end_time ?? lastTime);
    if (![topPrice, bottomPrice, startTime, endTime].every(Number.isFinite) || topPrice <= bottomPrice) return;

    const startX = chart.timeScale().timeToCoordinate(startTime);
    const endX = chart.timeScale().timeToCoordinate(endTime);
    const topY = candleSeries.priceToCoordinate(topPrice);
    const bottomY = candleSeries.priceToCoordinate(bottomPrice);
    if ([startX, endX, topY, bottomY].some((value) => value === null || value === undefined)) return;

    const left = Math.max(0, Math.min(startX, endX));
    const right = Math.min(chartElement.clientWidth - 72, Math.max(startX, endX));
    const rectangle = document.createElement("div");
    rectangle.className = `context-zone context-${kind}`;
    rectangle.style.left = `${left}px`;
    rectangle.style.top = `${Math.max(0, Math.min(topY, bottomY))}px`;
    rectangle.style.width = `${Math.max(right - left, 36)}px`;
    rectangle.style.height = `${Math.max(Math.abs(bottomY - topY), 4)}px`;
    const label = document.createElement("span");
    label.textContent = advancedLabelsToggle.checked
        ? `${kind.toUpperCase()} · ${formatPrice(bottomPrice, analysis)} - ${formatPrice(topPrice, analysis)}`
        : kind.toUpperCase();
    rectangle.appendChild(label);
    chartOverlayLayer.appendChild(rectangle);
}

function zoneTimestamp(value) {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) return numeric > 1e12 ? Math.floor(numeric / 1000) : Math.floor(numeric);
    const milliseconds = Date.parse(String(value || ""));
    return Number.isFinite(milliseconds) ? Math.floor(milliseconds / 1000) : NaN;
}

function getOverlays(analysis) {
    return analysis.overlays || analysis.chart_overlays || {};
}

function normalizeStrategyAnalysis(analysis) {
    const result = analysis.strategy_result;

    if (!result) {
        return analysis;
    }

    const normalized = { ...analysis };
    const score = Number(result.trade_score ?? analysis.trade_score ?? analysis.score ?? result.score ?? 0);
    const state = result.state || analysis.setup_status || "NO_SETUP";

    normalized.bias = strategyBiasToLegacy(result.bias);
    normalized.setup_status = state.replaceAll("_", " ");
    normalized.status = normalized.setup_status;
    normalized.score = Number.isFinite(score) ? score : 0;
    normalized.setup_quality = Number(result.setup_quality ?? analysis.setup_quality ?? normalized.score);
    normalized.trade_quality = Number(result.trade_quality ?? analysis.trade_quality ?? 0);
    normalized.trade_score = Number(result.trade_score ?? analysis.trade_score ?? normalized.score);
    normalized.trade_decision = result.trade_decision || analysis.trade_decision || "PENDING";
    normalized.objective_plan = result.objective_plan || analysis.objective_plan || {};
    normalized.readiness = normalized.score;
    normalized.readiness_level = {
        ...(analysis.readiness_level || {}),
        percent: normalized.score,
        label: state,
    };
    normalized.levels_mode = result.levels_mode || analysis.levels_mode || "hidden";
    normalized.levels = result.levels || analysis.levels || {};
    normalized.overlays = result.overlays || analysis.overlays || analysis.chart_overlays || {};
    normalized.chart_overlays = normalized.overlays;
    normalized.market_narrative = result.market_story || analysis.market_narrative || analysis.summary;
    normalized.summary = result.market_story || analysis.summary;
    normalized.missing_confirmation = result.next_trigger || analysis.missing_confirmation;
    normalized.suggested_action = result.next_trigger || analysis.suggested_action;
    normalized.next_required_confirmation = result.next_trigger || analysis.next_required_confirmation;
    normalized.direction = result.levels_mode === "final"
        ? `${String(result.bias || "Neutral").toUpperCase()} SETUP`
        : `${String(result.bias || "Neutral").toUpperCase()} BIAS`;
    normalized.mentor = buildStrategyMentor(result, normalized);

    return normalized;
}

function strategyBiasToLegacy(bias) {
    if (bias === "Bullish") {
        return "LONG";
    }
    if (bias === "Bearish") {
        return "SHORT";
    }
    return "NEUTRAL";
}

function buildStrategyMentor(result, analysis) {
    const progress = result.progress || [];
    const currentStage = progress.find((step) => step.is_current) || progress[0] || {
        label: result.state || "Waiting",
        status: "current",
    };
    const tradeDecision = result.trade_decision || analysis.trade_decision || "PENDING";
    const objectivePlan = result.objective_plan || analysis.objective_plan || {};
    const tradeStatus = strategyTradeStatus(result.state, result.levels_mode, tradeDecision);

    return {
        market_bias: result.bias || readableBias(analysis.bias),
        market_phase: analysis.macro_dashboard?.market_phase?.current_phase || analysis.session?.phase || "Waiting",
        trade_status: tradeStatus,
        trade_confidence: result.setup_quality ?? analysis.setup_quality ?? result.score ?? analysis.score ?? 0,
        setup_quality: result.setup_quality ?? analysis.setup_quality ?? result.score ?? analysis.score ?? 0,
        trade_quality: result.trade_quality ?? analysis.trade_quality ?? 0,
        trade_decision: tradeDecision,
        objective_plan: objectivePlan,
        current_stage: currentStage,
        setup_journey: progress,
        story_steps: result.why || [],
        why: result.why || [],
        next_trigger: result.next_trigger || analysis.next_required_confirmation || "Wait for the next confirmation.",
        if_this_happens: strategyIfThisHappens(result.state, result.levels_mode, tradeDecision),
        what_next: result.next_trigger || analysis.suggested_action || "Wait for the next confirmation.",
        progression: progress,
        trade_opportunity: {
            status: result.levels_mode === "final" && tradeDecision === "ACCEPT" ? "Entry Ready" : "No Trade",
            message: result.levels_mode === "final" && tradeDecision === "ACCEPT" ? "Entry-ready levels are available." : objectivePlan.reason || result.next_trigger || "No valid trade levels yet.",
            levels_mode: result.levels_mode || "hidden",
            levels: result.levels || {},
            objective_plan: objectivePlan,
        },
        narrative: result.market_story || analysis.market_narrative || analysis.summary || "Load a chart to read the market story.",
    };
}

function strategyTradeStatus(state, levelsMode, tradeDecision = "PENDING") {
    if (state === "ENTRY_READY" && tradeDecision === "REJECT") {
        return "No Trade";
    }
    if (state === "ENTRY_READY" && tradeDecision === "PENDING") {
        return "Building Setup";
    }
    if (levelsMode === "final" && tradeDecision === "ACCEPT") {
        return "Entry Ready";
    }
    if (["PULLBACK_ACTIVE", "AT_IMPORTANT_ZONE", "WAITING_FOR_CONFIRMATION", "WAITING_FOR_PULLBACK", "WAITING_FOR_ZONE", "WAITING_FOR_ENTRY", "CONFIRMED_WAITING_FOR_ENTRY"].includes(state)) {
        return "Building Setup";
    }
    if (state === "INVALIDATED") {
        return "Invalidated";
    }
    return "Watching";
}

function strategyIfThisHappens(state, levelsMode, tradeDecision = "PENDING") {
    if (state === "ENTRY_READY" && tradeDecision === "REJECT") {
        return "Wait for a fresh setup with at least 1.50R to a meaningful objective.";
    }
    if (levelsMode === "final" && tradeDecision === "ACCEPT") {
        return "If price trades into the active zone, the setup can move into trade management.";
    }
    if (["PULLBACK_ACTIVE", "AT_IMPORTANT_ZONE", "WAITING_FOR_CONFIRMATION"].includes(state)) {
        return "If confirmation closes beyond the trigger level, final trade levels will appear.";
    }
    if (["WAITING_FOR_ENTRY", "CONFIRMED_WAITING_FOR_ENTRY"].includes(state)) {
        return "If price returns to the active zone, TradeScor will reassess entry readiness.";
    }
    return "If the next condition forms, TradeScor will advance the selected strategy state.";
}

function drawLiquidityLine(zone) {
    if (!zone || zone.swept_level === undefined) {
        return;
    }

    const color = zone.direction === "bullish" ? "#22c55e" : "#ef4444";
    const tag = zone.side === "sell-side" ? "SSL" : "BSL";
    drawLevelLine(tag, zone.swept_level, color, LightweightCharts.LineStyle.Dashed);
}

function drawLevelLine(label, price, color, style, options = {}) {
    if (!candleSeries) {
        return;
    }

    if (price === null || price === undefined || Number.isNaN(Number(price))) {
        return;
    }

    const priceNumber = Number(price);
    const y = candleSeries.priceToCoordinate(priceNumber);
    const priority = Number(options.priority || 9);
    const forceLabel = Boolean(options.forceLabel);
    const overlaps = Number.isFinite(y)
        && drawnPriceLabelCoordinates.some((item) => Math.abs(item.y - y) < 20 && item.priority <= priority);
    const axisLabelVisible = forceLabel || !overlaps;
    if (axisLabelVisible && Number.isFinite(y)) {
        drawnPriceLabelCoordinates.push({ y, priority, label });
    }

    priceLines.push(
        candleSeries.createPriceLine({
            price: priceNumber,
            color,
            lineWidth: 1,
            lineStyle: style,
            axisLabelVisible,
            title: label,
        })
    );
}

function renderAnalysis(analysis) {
    const mentor = analysis.mentor || buildMentorFallback(analysis);
    const strategyResult = analysis.strategy_result || {};
    const overlays = getOverlays(analysis);
    const answers = analysis.trader_answers || buildTraderAnswersFallback(analysis, mentor, strategyResult);
    const marketLabel = marketAnswerLabel(analysis);
    const tradeStatus = answers.trade_status;
    const marketStory = formatMarketText(answers.market_story, analysis);
    const reasons = (answers.why || []).map((reason) => formatMarketText(reason, analysis));
    const selectedStrategyKey = strategyResult.selected_strategy_key
        || analysis.selected_strategy_key
        || getFormParams().strategy;
    const mainStatus = analysisDecisionStatus(analysis);

    if (getFormParams().strategy === "auto") {
        contextZonesToggle.checked = selectedStrategyKey === "ict_2022";
    }

    renderScannerAnalysis(analysis, answers, strategyResult, reasons);
    const nextTrigger = scannerNextAction.textContent;

    chartDecisionStatus.textContent = mainStatus;
    chartDecisionStatus.className = statusToneClass(mainStatus);
    chartDirection.textContent = `Looking for: ${scannerDirection.textContent}`;
    statusText.textContent = analysis.trade_lifecycle?.status && analysis.trade_lifecycle.status !== "NO ACTIVE POSITION"
        ? analysis.trade_lifecycle.status
        : chartDecisionSubtitle(mainStatus, analysis.entry_timing || strategyResult.entry_timing || {});
    setupStatusLabel.textContent = mainStatus;
    setupDirection.textContent = mainStatus;
    setupDirection.className = `setup-status ${mentorStatusClass(mainStatus, analysis.bias, analysis.setup_status)}`;
    setupBias.textContent = answers.trend;
    answerHtfBias.textContent = answers.higher_timeframe_bias || "Unclear";
    setupBias.className = biasClass(answers.trend);
    answerHtfBias.className = biasClass(answers.higher_timeframe_bias);
    executionTrendLabel.textContent = `${answers.execution_timeframe || analysis.timeframe || "Execution"} Trend`;
    answerPriceLocation.textContent = answers.price_location;
    answerMarketIntent.textContent = answers.market_intent;
    answerMarket.textContent = marketLabel;
    topSymbol.textContent = analysis.display_symbol || analysis.symbol || getFormParams().symbol;
    topTimeframe.textContent = analysis.timeframe || getFormParams().timeframe;
    topStrategy.textContent = strategyResult.strategy_name || strategyLabel(getFormParams().strategy);
    answerNow.textContent = marketStory;
    answerZone.textContent = importantZoneText(overlays);
    answerConfirmation.textContent = confirmationText(overlays, analysis);
    answerInvalidation.textContent = invalidationText(analysis, overlays);
    answerTopdown.textContent = answers.higher_timeframe_bias && answers.higher_timeframe_bias !== "Neutral"
        ? `${answers.higher_timeframe_bias} HTF bias`
        : "Mixed HTF context";
    answerTopdownSummary.textContent = answers.top_down_summary;
    assistantTrendExplanation.textContent = answers.alignment_summary || assistantEvidence(
        reasons,
        ["higher-timeframe", "trend", "bias"],
        answers.top_down_summary
    );
    assistantLocationExplanation.textContent = assistantEvidence(
        reasons,
        ["price", "zone", "support", "resistance", "liquidity", "ote"],
        `Price is currently classified as ${String(answers.price_location || "unclear").toLowerCase()}.`
    );
    assistantIntentExplanation.textContent = assistantEvidence(
        reasons,
        ["structure", "momentum", "sweep", "choch", "confirmation"],
        `Current behavior is ${String(answers.market_intent || "still developing").toLowerCase()}.`
    );
    assistantStatusExplanation.textContent = tradeStatusExplanation(mainStatus);
    assistantNextOutcome.textContent = nextOutcomeText(mainStatus);
    storyInstruction.textContent = storyInstructionText(mainStatus);
    renderAssistantTones(answers, mainStatus);
    storyPhase.textContent = mentor.market_phase || "--";
    setupState.textContent = mainStatus;
    setupReadiness.textContent = answers.trade_readiness;
    marketClarity.textContent = answers.market_clarity;
    marketClarity.className = String(answers.market_clarity || "Low").toLowerCase();
    tradeReadiness.textContent = answers.trade_readiness;
    tradeReadiness.className = readinessClass(answers.trade_readiness);
    nextConfirmation.textContent = nextTrigger;
    suggestedAction.textContent = nextTrigger;
    setupScore.textContent = mentor.trade_confidence ?? analysis.trade_score ?? analysis.score ?? 0;
    setupQuality.textContent = `${Math.round(Number(analysis.setup_quality ?? mentor.setup_quality ?? analysis.score ?? 0))}/100`;
    tradeQuality.textContent = `${Math.round(Number(analysis.trade_quality ?? mentor.trade_quality ?? 0))}/100`;
    setupSummary.textContent = marketStory;
    renderWhy(reasons.map((text) => ({ status: answerReasonStatus(text), text })));
    renderMarketStoryTimeline(answers.market_timeline || analysis.timeline || []);
    renderProgress(mentor.setup_journey || mentor.progression || []);
    renderMacroDashboard(analysis.macro_dashboard || {});
    renderMarketFilters(analysis.market_filters || {}, analysis.session || analysis.kill_zone || analysis.macro_dashboard?.session || null);
    renderChecklist(analysis.checklist || {});
    renderLevels(
        analysis.levels || {},
        analysis.setup_status,
        analysis.levels_mode || getOverlays(analysis).levels_mode || "hidden",
        analysis.invalidation_reason,
        mentor.trade_opportunity || null,
        mainStatus
    );
    renderObjectivePlan(analysis.objective_plan || strategyResult.objective_plan || mentor.objective_plan || {});
    renderTopDown(analysis.top_down_context || analysis.top_down_analysis || {});
    renderHtfContext(analysis.top_down_context || analysis.top_down_analysis || {});
    renderChartMetrics(analysis.candles || [], analysis);
    renderKeyLevels(analysis, answers, overlays);
    renderContextTimeframeSwitcher(analysis.selected_timeframe || analysis.timeframe || getFormParams().timeframe);
    renderSessionIntelligence(analysis.session || analysis.kill_zone || buildClientSessionContext());
    renderMarketContext(analysis);
    renderRecentStructure(analysis);
    renderSetupExplanation(analysis);
    recordTimelineEvents(analysis.timeline || analysis.analysis_timeline || []);
    renderAnswerQa(analysis);
    renderIctDetails(analysis);
    renderStrategyDetails(analysis);
    renderRawAnalysis(analysis);
}

function assistantEvidence(reasons, keywords, fallback) {
    const match = reasons.find((reason) => {
        const text = String(reason || "").toLowerCase();
        return keywords.some((keyword) => text.includes(keyword));
    });
    return firstSentence(match || fallback);
}

function chartDecisionSubtitle(status, timing) {
    return decisionSubtitle(status, timing);
}

function renderAssistantTones(answers, displayStatus = null) {
    const trendCard = document.querySelector('[data-answer-card="trend"]');
    const locationCard = document.querySelector('[data-answer-card="location"]');
    const intentCard = document.querySelector('[data-answer-card="intent"]');
    const statusCard = document.querySelector('[data-answer-card="status"]');
    const trendTone = biasClass(answers.trend);
    const status = displayStatus || userFacingStatus({ tradeStatus: answers.trade_status });
    const statusTone = isReadyAction(status)
        ? "ready"
        : isFormingAction(status)
            ? "waiting"
            : "invalidated";

    trendCard.className = `assistant-card ${trendTone}`;
    locationCard.className = "assistant-card information";
    intentCard.className = "assistant-card information";
    statusCard.className = `assistant-card trade-status-card ${statusTone}`;
    setupStatusLabel.className = statusTone;
}

function tradeStatusExplanation(status) {
    if (isReadyAction(status)) return "Entry, stop, and target are aligned.";
    if (isFormingAction(status)) return "Setup is forming, but entry is not confirmed.";
    return "No confirmed entry is available at the current price.";
}

function nextOutcomeText(status) {
    if (isReadyAction(status)) {
        return "Use only the confirmed levels shown below. Respect invalidation.";
    }
    if (status === "NO CLEAN ENTRY") {
        return "Remain flat. Look for a fresh setup sequence.";
    }
    return "If it happens, reassess for entry. If it fails, remain flat.";
}

function storyInstructionText(status) {
    if (isReadyAction(status)) {
        return "Confirmation is complete. Follow the confirmed plan, not anticipation.";
    }
    return "Be patient. Let the market confirm.";
}

function answerReasonStatus(reason) {
    const text = String(reason || "").toLowerCase();
    if (["invalid", "conflict", "blocked", "failed"].some((word) => text.includes(word))) {
        return "invalidated";
    }
    if (["not ", "no ", "missing", "waiting", "has not", "yet"].some((word) => text.includes(word))) {
        return "waiting";
    }
    return "completed";
}

function renderChartMetrics(candles, analysis) {
    if (!candles.length) {
        return;
    }
    const current = candles[candles.length - 1];
    const previous = candles.length > 1 ? candles[candles.length - 2] : current;
    const change = Number(current.close) - Number(previous.close);
    const percent = Number(previous.close) ? (change / Number(previous.close)) * 100 : 0;

    chartCurrentPrice.textContent = formatPrice(current.close, analysis);
    chartPriceChange.textContent = `${formatSignedPrice(change, analysis)} (${change >= 0 ? "+" : ""}${percent.toFixed(2)}%)`;
    chartPriceChange.className = change > 0 ? "positive" : change < 0 ? "negative" : "";
    chartHigh.textContent = formatPrice(current.high, analysis);
    chartLow.textContent = formatPrice(current.low, analysis);
    chartSpread.textContent = analysis.spread !== undefined ? formatPrice(analysis.spread, analysis) : "N/A";
}

function renderHtfContext(topDown) {
    const rows = topDownRows(topDown);
    htfContextTable.innerHTML = "";

    const head = document.createElement("div");
    head.className = "htf-table-head";
    for (const label of ["Timeframe", "Bias", "Structure", "Summary"]) {
        const cell = document.createElement("span");
        cell.textContent = label;
        head.appendChild(cell);
    }
    htfContextTable.appendChild(head);

    if (!rows.length) {
        const empty = document.createElement("p");
        empty.textContent = "Higher-timeframe context is unavailable for this load.";
        htfContextTable.appendChild(empty);
        return;
    }

    for (const row of rows.slice(0, 6)) {
        const item = document.createElement("div");
        item.className = `htf-table-row ${biasClass(row.bias)}`;
        for (const value of [row.label, row.bias, row.state || "--", row.summary || row.state || "--"]) {
            const cell = document.createElement("span");
            cell.textContent = value;
            item.appendChild(cell);
        }
        htfContextTable.appendChild(item);
    }
}

function renderKeyLevels(analysis, answers, overlays) {
    const ready = ["Entry Ready", "Trade Active"].includes(answers.trade_status);
    const levels = analysis.levels || {};
    const objective = analysis.objective_plan?.primary_objective || null;

    keyBias.textContent = answers.trend || "Unclear";
    if (!ready) {
        keyNextTarget.textContent = "No trade yet";
        keyRiskReward.textContent = "No trade yet";
        return;
    }

    keyNextTarget.textContent = objective
        ? `${objective.name || "Target"} · ${formatPrice(objective.price, analysis)}`
        : formatPrice(levels.tp1, analysis);
    keyRiskReward.textContent = levels.rr1 !== null && levels.rr1 !== undefined
        ? `${formatRatio(levels.rr1)}R`
        : "Unavailable";
}

function renderIctDetails(analysis) {
    if (!ictDetailsPanel || !ictChecklist) {
        return;
    }

    const strategyResult = analysis.strategy_result || {};
    const isIct = (strategyResult.selected_strategy_key || analysis.selected_strategy_key || getFormParams().strategy) === "ict_2022"
        || ["ICT 2022 Model", "ICT Precision"].includes(strategyResult.strategy_name);
    ictDetailsPanel.hidden = !isIct;
    if (!isIct) {
        return;
    }

    const checklist = strategyResult.ict_checklist || analysis.ict_checklist || {};
    const details = strategyResult.ict_details || analysis.ict_details || {};
    ictStateLabel.textContent = analysisDecisionStatus(analysis);

    for (const item of ictChecklist.querySelectorAll("[data-ict-check]")) {
        const status = String(checklist[item.dataset.ictCheck] || "unknown").toLowerCase();
        item.className = status;
        item.querySelector("strong").textContent = titleCase(status);
    }

    const killZone = details.kill_zone || {};
    const sweep = details.liquidity_sweep || {};
    const sweepEvent = sweep.sweep || {};
    const choch = details.choch || {};
    const fvg = details.fvg || {};
    const ifvg = details.ifvg || {};
    const ote = details.ote || {};
    const orderBlock = details.order_block_quality || {};
    const amd = details.amd_phase || {};
    const dxy = details.dxy || {};
    const news = details.news || {};

    ictKillZone.textContent = `${killZone.name || "Outside Trading Hours"} · ${killZone.status || "Inactive"}`;
    ictLiquiditySweep.textContent = sweep.swept
        ? `${titleCase(sweepEvent.side || sweep.expected_side || "Liquidity")} swept at ${formatPrice(sweepEvent.swept_level, analysis)}`
        : `Waiting for ${sweep.expected_side || "directional liquidity"}`;
    ictChoch.textContent = choch.confirmed
        ? `Confirmed at ${formatPrice(choch.level, analysis)}`
        : choch.level !== null && choch.level !== undefined
            ? `Waiting for close beyond ${formatPrice(choch.level, analysis)}`
            : "Waiting for post-sweep structure";
    ictFvg.textContent = fvg.status || (fvg.present ? "Present" : "Missing");
    ictIfvg.textContent = ifvg.status || (ifvg.present ? `Present · ${formatZone(ifvg.zone)}` : "Missing");
    ictOte.textContent = ote.in_zone
        ? `In zone · ${titleCase(ote.location || "dealing range")}`
        : ote.available
            ? `Waiting · ${titleCase(ote.location || "dealing range")}`
            : "Unavailable";
    ictOrderBlock.textContent = orderBlock.present
        ? `${orderBlock.quality || "Weak"} · ${orderBlock.score || 0}/100`
        : "Missing";
    ictAmdPhase.textContent = amd.phase || "Waiting";
    ictDxy.textContent = dxy.enabled === false
        ? "Not applicable"
        : dxy.dxy_trend === "Unavailable"
            ? "DXY unavailable — not included in analysis."
            : `${dxy.dxy_trend || "Unavailable"} · ${dxy.correlation_status || "Waiting"}`;
    ictNews.textContent = news.restriction_active
        ? "Blocked by high-impact event"
        : news.enabled
            ? news.status || "Clear"
            : "News filter unavailable — no live calendar configured.";
}

function renderStrategyDetails(analysis) {
    const result = analysis.strategy_result || {};
    const selected = result.selected_strategy_key || analysis.selected_strategy_key || getFormParams().strategy;
    const isSupplyDemand = selected === "supply_demand" || result.strategy_name === "Supply & Demand";
    const isBreakout = selected === "breakout_retest" || result.strategy_name === "Breakout & Retest";

    if (supplyDemandDetailsPanel) {
        supplyDemandDetailsPanel.hidden = !isSupplyDemand;
    }
    if (breakoutDetailsPanel) {
        breakoutDetailsPanel.hidden = !isBreakout;
    }

    if (isSupplyDemand) {
        const details = result.supply_demand_details || {};
        const zone = details.zone || {};
        const quality = details.zone_quality || {};
        sdActiveZone.textContent = zone.type
            ? `${titleCase(zone.type)} · ${formatZone(zone)}`
            : "No active zone";
        sdZoneQuality.textContent = quality.grade
            ? `${quality.grade} · ${quality.score || 0}/100`
            : "Unavailable";
        sdImpulse.textContent = quality.strong_impulse
            ? `Strong departure · ${quality.impulse_atr || 0} ATR`
            : `Weak departure · ${quality.impulse_atr || 0} ATR`;
        sdMitigation.textContent = quality.fully_mitigated
            ? "Invalidated"
            : quality.fresh
                ? "Fresh · untested"
                : `Tested · ${quality.touch_count || 0} reaction${Number(quality.touch_count || 0) === 1 ? "" : "s"}`;
        sdReaction.textContent = details.reaction ? "Defended" : "Waiting";
        sdTrigger.textContent = details.trigger?.price !== undefined
            ? formatPrice(details.trigger.price, analysis)
            : "Not available";
        sdState.textContent = analysisDecisionStatus(analysis);
    }

    if (isBreakout) {
        const details = result.breakout_retest_details || {};
        const range = details.range || {};
        const breakout = details.breakout || {};
        const retest = details.retest || {};
        breakoutRange.textContent = range.high !== undefined && range.low !== undefined
            ? `${formatPrice(range.low, analysis)} - ${formatPrice(range.high, analysis)}`
            : "No stable range";
        breakoutDirection.textContent = breakout.direction || "Waiting";
        breakoutLevel.textContent = breakout.level !== undefined
            ? formatPrice(breakout.level, analysis)
            : "Not broken";
        breakoutRetest.textContent = retest.time ? "Active" : "Waiting";
        breakoutRejection.textContent = details.rejection_confirmed ? "Confirmed" : "Waiting";
        breakoutMeasuredMove.textContent = details.measured_move !== undefined
            ? formatPrice(details.measured_move, analysis)
            : "Unavailable";
        breakoutState.textContent = analysisDecisionStatus(analysis);
    }
}

function marketAnswerLabel(analysis) {
    const symbol = analysis.display_symbol || analysis.symbol || getFormParams().symbol || "--";
    const timeframe = analysis.timeframe || getFormParams().timeframe || "--";
    return `${symbol} · ${timeframe}`;
}

function buildTraderAnswersFallback(analysis, mentor, strategyResult) {
    const rawTrend = cleanFallback(strategyResult.bias, mentor.market_bias, readableBias(analysis.bias));
    const trend = ["Bullish", "Bearish", "Range", "Unclear"].includes(rawTrend) ? rawTrend : "Unclear";
    const tradeStatus = traderTradeStatus(strategyResult, mentor, analysis);
    const nextAction = cleanFallback(strategyResult.next_trigger, mentor.next_trigger, analysis.missing_confirmation, "Wait for confirmation.");
    const story = cleanFallback(strategyResult.market_story, mentor.narrative, analysis.market_narrative, analysis.summary, "The market is still developing.");
    const higherBias = cleanFallback(analysis.top_down_context?.overall_alignment, rawTrend, "Neutral").replace("Strong ", "");
    const executionTimeframe = analysis.timeframe || getFormParams().timeframe || "Execution";
    const why = (mentor.story_steps || mentor.why || [])
        .map((item) => item.text)
        .filter(Boolean)
        .slice(0, 5);

    return {
        trend,
        higher_timeframe_bias: ["Bullish", "Bearish"].includes(higherBias) ? higherBias : "Neutral",
        execution_timeframe: executionTimeframe,
        execution_timeframe_trend: trend,
        execution_description: trend,
        timeframe_alignment: higherBias === trend ? "Aligned" : "Unconfirmed",
        alignment_summary: analysis.top_down_context?.summary || "Higher-timeframe context is not loaded.",
        price_location: "No clear level",
        market_intent: trend === "Bullish" || trend === "Bearish" ? "Continuing trend" : "Ranging / undecided",
        trade_status: ["Entry Ready", "Trade Active"].includes(tradeStatus) ? tradeStatus : tradeStatus === "Building Setup" ? "Wait" : "No Trade",
        why: why.length ? why : ["The market has not provided enough clear information yet."],
        top_down_summary: analysis.top_down_context?.summary || "Higher-timeframe context is not loaded.",
        market_story: story,
        next_action: nextAction,
        market_clarity: trend === "Bullish" || trend === "Bearish" ? "Medium" : "Low",
        trade_readiness: ["Entry Ready", "Trade Active"].includes(tradeStatus) ? "Ready" : tradeStatus === "Building Setup" ? "Building" : "Not Ready",
        market_timeline: [
            `Market structure reads ${trend.toLowerCase()}.`,
            ["Entry Ready", "Trade Active"].includes(tradeStatus) ? "Trade confirmation is complete." : "Confirmation is pending before considering a trade.",
        ],
    };
}

function readinessClass(value) {
    if (value === "Ready") {
        return "ready";
    }
    if (value === "Building") {
        return "building";
    }
    return "not-ready";
}

function renderMarketStoryTimeline(events) {
    marketStoryTimeline.innerHTML = "";
    const rows = events.length ? events.slice(0, 4) : ["Market story is not available yet."];

    for (const event of rows) {
        const item = document.createElement("li");
        const text = typeof event === "string"
            ? event
            : `${event.event_type || event.title || "Market update"}: ${event.explanation || event.detail || "Context updated."}`;
        item.textContent = formatMarketText(text);
        marketStoryTimeline.appendChild(item);
    }
}

function strategyLabel(value) {
    const labels = {
        auto: "Auto",
        universal_structure: "Structure Context",
        ict_2022: "ICT Precision",
        supply_demand: "Supply & Demand",
        breakout_retest: "Breakout & Retest",
    };
    return labels[value] || "Auto";
}

function traderTradeStatus(result, mentor, analysis) {
    const state = String(result.state || analysis.ict_state?.key || analysis.setup_status || "").toUpperCase();
    const mentorStatus = mentor.trade_status || "";
    const tradeDecision = result.trade_decision || analysis.trade_decision || mentor.trade_decision || "PENDING";

    if (state.includes("INVALID")) {
        return "Invalidated";
    }
    if (state.includes("TRADE_ACTIVE")) {
        return "Trade Active";
    }
    if (tradeDecision === "REJECT") {
        return "No Trade";
    }
    if (result.levels_mode === "final" && tradeDecision === "ACCEPT") {
        return "Entry Ready";
    }
    if (state.includes("CONFIRMATION") || state.includes("IFVG")) {
        return "Waiting for Confirmation";
    }
    if (state.includes("PULLBACK") || state.includes("IMPORTANT_ZONE") || state.includes("WAITING_FOR_ZONE") || state.includes("WAITING_FOR_ENTRY") || state.includes("MSS") || state.includes("LIQUIDITY") || mentorStatus === "Building Setup") {
        return "Building Setup";
    }
    return "No Trade Yet";
}

function cleanFallback(...values) {
    for (const value of values) {
        if (value !== null && value !== undefined && String(value).trim() !== "") {
            return String(value).trim();
        }
    }
    return "Not enough data yet.";
}

function firstSentence(text) {
    const value = cleanFallback(text);
    const match = value.match(/^(.+?[.!?])(?:\s|$)/);
    return match ? match[1] : value;
}

function importantZoneText(overlays) {
    const zone = overlays.entry_zone
        || overlays.pullback_zone
        || overlays.ifvg_zone
        || overlays.active_fvg
        || overlays.order_block;

    if (!zone) {
        return "Not enough data yet.";
    }

    const label = zone.tooltip || zone.label || zone.tag || "Zone";
    return `${shortZoneLabel(label)} · ${formatZone(zone)}`;
}

function shortZoneLabel(label) {
    const text = String(label || "Zone").toLowerCase();
    if (text.includes("ifvg")) {
        return "IFVG zone";
    }
    if (text.includes("order")) {
        return "Order block";
    }
    if (text.includes("demand") || text.includes("support")) {
        return "Demand zone";
    }
    if (text.includes("supply") || text.includes("resistance")) {
        return "Supply zone";
    }
    if (text.includes("fvg")) {
        return "FVG zone";
    }
    if (text.includes("pullback")) {
        return "Pullback zone";
    }
    return "Zone";
}

function confirmationText(overlays, analysis) {
    const confirmationPrice = overlays.confirmation_level?.price
        ?? overlays.mss_level?.level
        ?? analysis.active_zone?.level;

    if (confirmationPrice === null || confirmationPrice === undefined) {
        return "No confirmation level yet.";
    }

    return formatPrice(confirmationPrice, analysis);
}

function invalidationText(analysis, overlays) {
    const levels = analysis.levels || {};
    const value = overlays.invalidation_level
        ?? overlays.stop_loss
        ?? levels.stop_loss
        ?? analysis.invalidation_level;

    if (value === null || value === undefined || value === "") {
        return analysis.invalidation_reason || "No invalidation level yet.";
    }

    if (typeof value === "object") {
        return formatPrice(value.level || value.price, analysis);
    }

    return formatPrice(value, analysis);
}

function nextActionText(result, analysis, mentor) {
    const state = String(result.state || analysis.setup_status || "").toUpperCase();
    const mode = result.levels_mode || analysis.levels_mode;
    const tradeDecision = result.trade_decision || analysis.trade_decision || mentor.trade_decision || "PENDING";

    if (state.includes("INVALID")) {
        return "Avoid trade.";
    }
    if (state.includes("TRADE_ACTIVE")) {
        return "Manage active trade.";
    }
    if (tradeDecision === "REJECT") {
        return "No trade. Wait for a setup with sufficient reward.";
    }
    if (mode === "final" && tradeDecision === "ACCEPT") {
        return "Entry ready.";
    }
    if (state.includes("CONFIRMATION") || state.includes("IFVG")) {
        return "Monitor confirmation.";
    }
    return mentor.if_this_happens || "Wait.";
}

function statusClass(bias, setupStatus) {
    if (["VALID SETUP", "ENTRY READY"].includes(setupStatus) && bias === "LONG") {
        return "long";
    }
    if (["VALID SETUP", "ENTRY READY"].includes(setupStatus) && bias === "SHORT") {
        return "short";
    }
    if (setupStatus === "INVALIDATED") {
        return "invalidated";
    }
    if (bias === "LONG") {
        return "long-bias";
    }
    if (bias === "SHORT") {
        return "short-bias";
    }
    return "no-setup";
}

function headlineBias(analysis) {
    if (["VALID SETUP", "ENTRY READY"].includes(analysis.setup_status) && analysis.bias === "LONG") {
        return "VALID LONG SETUP";
    }
    if (["VALID SETUP", "ENTRY READY"].includes(analysis.setup_status) && analysis.bias === "SHORT") {
        return "VALID SHORT SETUP";
    }
    if (analysis.bias === "LONG") {
        return "LONG BIAS";
    }
    if (analysis.bias === "SHORT") {
        return "SHORT BIAS";
    }
    return "NO SETUP";
}

function buildMentorFallback(analysis) {
    const journey = fallbackProgression(analysis.checklist || {}, analysis.levels_mode || "hidden", analysis.setup_status);
    return {
        market_bias: readableBias(analysis.bias),
        market_phase: analysis.macro_dashboard?.market_phase?.current_phase || analysis.session?.phase || "Waiting",
        trade_status: fallbackTradeStatus(analysis.setup_status),
        trade_confidence: analysis.trade_score ?? analysis.score ?? 0,
        current_stage: journey.find((step) => step.is_current) || journey[0],
        setup_journey: journey,
        story_steps: [
            {
                status: isDetected(analysis.checklist?.htf_fvg) ? "completed" : "current",
                text: isDetected(analysis.checklist?.htf_fvg)
                    ? "Market context is present."
                    : "Market context has not formed yet.",
            },
            {
                status: isDetected(analysis.checklist?.liquidity_sweep) ? "completed" : "inactive",
                text: isDetected(analysis.checklist?.liquidity_sweep)
                    ? "Liquidity has been swept."
                    : "Price has not swept liquidity yet.",
            },
            {
                status: isDetected(analysis.checklist?.mss) ? "completed" : "inactive",
                text: isDetected(analysis.checklist?.mss)
                    ? "Market structure has shifted."
                    : "Market Structure Shift has not confirmed yet.",
            },
        ],
        why: [],
        next_trigger: analysis.missing_confirmation || analysis.suggested_action || "Wait for the next confirmation.",
        if_this_happens: analysis.suggested_action || "If the next event confirms, TradeScor will advance the setup journey.",
        what_next: analysis.missing_confirmation || analysis.suggested_action || "Wait for the next confirmation.",
        progression: journey,
        trade_opportunity: {
            status: analysis.levels_mode === "final" ? "Entry Ready" : "No Trade",
            message: analysis.suggested_action || "No valid trade yet.",
            levels_mode: analysis.levels_mode || "hidden",
        },
        narrative: analysis.market_narrative || analysis.summary || "Load a chart to read the market story.",
    };
}

function readableBias(bias) {
    if (bias === "LONG") {
        return "Bullish";
    }
    if (bias === "SHORT") {
        return "Bearish";
    }
    return "Neutral";
}

function fallbackTradeStatus(setupStatus) {
    if (["VALID SETUP", "ENTRY READY"].includes(setupStatus)) {
        return "Entry Ready";
    }
    if (setupStatus === "INVALIDATED") {
        return "Reset";
    }
    if (["WAITING FOR MSS", "WAITING FOR IFVG", "LIQUIDITY SWEPT"].includes(setupStatus)) {
        return setupStatus === "WAITING FOR IFVG" ? "Waiting for Confirmation" : "Building Setup";
    }
    return "Watching";
}

function fallbackProgression(checklist, levelsMode, setupStatus) {
    const invalidated = setupStatus === "INVALIDATED";
    const raw = [
        { key: "watching", label: "Watching", done: isDetected(checklist.liquidity_sweep) },
        { key: "liquidity_sweep", label: "Liquidity Sweep", done: isDetected(checklist.liquidity_sweep) },
        { key: "waiting_mss", label: "Waiting MSS", done: isDetected(checklist.mss) },
        { key: "waiting_ifvg", label: "Waiting IFVG", done: isDetected(checklist.ifvg) },
        { key: "entry_ready", label: "Entry Ready", done: levelsMode === "final" },
    ];

    let currentAssigned = false;

    return raw.map((step) => {
        if (step.done && !invalidated) {
            return { key: step.key, label: step.label, status: "completed", is_current: false };
        }
        if (!currentAssigned) {
            currentAssigned = true;
            return { key: step.key, label: step.label, status: invalidated ? "invalidated" : "current", is_current: true };
        }
        return { key: step.key, label: step.label, status: "inactive", is_current: false };
    });
}

function mentorStatusClass(tradeStatus, bias, setupStatus) {
    if (isReadyAction(tradeStatus)) {
        return tradeStatus === "READY TO SELL" ? "short" : "long";
    }
    if (tradeStatus === "NO CLEAN ENTRY" || setupStatus === "INVALIDATED") {
        return "invalidated";
    }
    if (isFormingAction(tradeStatus)) {
        return tradeStatus === "SELL SETUP FORMING" ? "short-bias" : "long-bias";
    }
    return "no-setup";
}

function renderWhy(items) {
    whyList.innerHTML = "";

    if (!items.length) {
        const item = document.createElement("li");
        item.className = "waiting";
        item.innerHTML = "<span>○</span><p>Load a chart to see why the scanner is waiting.</p>";
        whyList.appendChild(item);
        return;
    }

    for (const reason of items.slice(0, 5)) {
        const item = document.createElement("li");
        const status = String(reason.status || "waiting").toLowerCase();
        const icon = status === "completed" || status === "confirmed"
            ? "✓"
            : status === "current"
                ? "▶"
                : status === "info"
                    ? "•"
                : status === "invalidated"
                    ? "✗"
                    : "○";
        const marker = document.createElement("span");
        const text = document.createElement("p");

        item.className = status;
        marker.textContent = icon;
        text.textContent = reason.text || "--";
        item.append(marker, text);
        whyList.appendChild(item);
    }
}

function renderProgress(steps) {
    const fallbackSteps = steps.length ? steps : [
        { label: "Watching Market", status: "current" },
    ];

    setupChecklist.innerHTML = "";

    for (const step of fallbackSteps) {
        const item = document.createElement("li");
        const status = String(step.status || "inactive").toLowerCase();
        const icon = status === "completed" || status === "confirmed"
            ? "✓"
            : status === "current"
                ? "▶"
                : status === "waiting"
                    ? "⏳"
                    : status === "invalidated"
                        ? "✗"
                        : "○";
        const marker = document.createElement("span");
        const label = document.createElement("strong");

        item.className = status;
        marker.textContent = icon;
        label.textContent = userFacingText(step.label || "--");
        item.append(marker, label);
        setupChecklist.appendChild(item);
    }
}

function renderChecklist(checklist) {
    if (!technicalChecklist) {
        return;
    }

    for (const item of technicalChecklist.querySelectorAll("[data-check]")) {
        const key = item.dataset.check;
        const detected = isDetected(checklist[key]);
        item.classList.toggle("detected", detected);
        item.classList.toggle("waiting", !detected);
        item.querySelector("strong").textContent = detected ? "Detected" : "Waiting";
    }
}

function renderLevels(levels, setupStatus, levelsMode, invalidationReason, opportunity, displayStatus) {
    if (levelsMode !== "final") {
        levelEntry.textContent = "--";
        levelStop.textContent = "--";
        levelTp1.textContent = "--";
        levelTp2.textContent = "--";
        levelRr1.textContent = "--";
        levelRr2.textContent = "--";
        levelNote.textContent = invalidationReason || "Trade levels are unavailable. Confirmation is still pending.";
        levelList.classList.add("levels-locked");
        levelList.classList.remove("levels-projected");
        levelList.classList.remove("entry-only");
        detailState.textContent = displayStatus || userFacingStatus({ state: setupStatus });
        return;
    }

    levelEntry.textContent = formatZone(levels.entry_zone);
    levelStop.textContent = formatPrice(levels.stop_loss);
    levelTp1.textContent = formatPrice(levels.tp1);
    levelTp2.textContent = formatPrice(levels.tp2);
    levelRr1.textContent = formatRatio(levels.rr1);
    levelRr2.textContent = formatRatio(levels.rr2);
    levelNote.textContent = opportunity?.message || levels.display_note || "Confirmed levels are available.";
    levelList.classList.remove("levels-locked");
    levelList.classList.remove("levels-projected", "entry-only");
    detailState.textContent = displayStatus || "NO CLEAN ENTRY";
}

function renderObjectivePlan(plan) {
    const decision = String(plan.decision || "PENDING").toUpperCase();
    const primary = plan.primary_objective || plan.best_rejected_objective || null;
    const secondary = plan.secondary_objective || null;

    tradeQuality.classList.toggle("accepted", decision === "ACCEPT");
    tradeQuality.classList.toggle("rejected", decision === "REJECT");

    if (!primary) {
        objectivePrimary.textContent = "Not selected";
        objectivePrimaryReason.textContent = plan.reason || "A meaningful target is required before a trade can be approved.";
    } else {
        const status = decision === "REJECT" ? "Rejected" : "Selected";
        objectivePrimary.textContent = `${primary.name || "Objective"} · ${formatPrice(primary.price)} · ${formatRatio(primary.rr)}R`;
        objectivePrimaryReason.textContent = `${status}. ${primary.reason || plan.reason || "Directional liquidity objective."}`;
    }

    objectiveSecondaryCard.hidden = !secondary;
    if (secondary) {
        objectiveSecondary.textContent = `${secondary.name || "Objective"} · ${formatPrice(secondary.price)} · ${formatRatio(secondary.rr)}R`;
        objectiveSecondaryReason.textContent = secondary.reason || "Secondary objective beyond the primary target.";
    } else {
        objectiveSecondary.textContent = "Not selected";
        objectiveSecondaryReason.textContent = "No secondary objective selected.";
    }
}

function renderMacroDashboard(macro) {
    const session = macro.session || buildClientSessionContext();
    const topDown = macro.top_down_context || macro.top_down_bias || macro.top_down_analysis || {};
    const dxy = macro.dxy_correlation || {};
    const news = macro.economic_news || {};
    const phase = macro.market_phase || {};

    macroSummary.textContent = macro.context_summary || topDown.summary || "Macro context loaded.";
    macroAlignment.textContent = macro.overall_market_alignment || topDown.overall_alignment || "Neutral";
    macroSessionName.textContent = session.name || session.session || "--";
    macroSessionDetail.textContent = `${session.status || "--"} · ${session.phase || "--"} · Entry ${session.entry_allowed ? "Allowed" : "Blocked"}`;
    renderMacroTopDown(topDownRows(topDown));

    macroDxyTrend.textContent = dxy.dxy_trend || "Disabled";
    macroDxyStatus.textContent = dxy.message || dxy.correlation_status || "DXY module is disabled for this symbol.";

    macroNewsStatus.textContent = news.status || "No configured events";
    macroNewsDetail.textContent = news.warning || "No high-impact events are configured.";
    macroNewsWarning.hidden = !news.restriction_active;
    macroNewsWarning.textContent = news.warning || "High-impact news restriction active.";
    if (dashboardNewsStatus) {
        dashboardNewsStatus.textContent = news.status || "No configured events";
        dashboardNewsStatus.className = news.restriction_active ? "warn-text" : "good-text";
        dashboardNewsDetail.textContent = news.warning || "No high-impact news configured.";
    }

    macroPhaseName.textContent = phase.current_phase || "Waiting";
    macroPhaseDetail.textContent = phase.expected_behavior
        ? `${phase.expected_behavior} ${phase.recommended_focus || ""}`
        : "Market phase will appear after analysis.";
}

function renderMarketFilters(filters, session = null) {
    const news = filters.news_risk || {};
    const dxy = filters.dxy_confirmation || {};
    const risk = String(news.risk_level || "unavailable").toLowerCase();
    const riskLabel = news.available === false ? "Unavailable" : titleCase(risk.replaceAll("_", " "));
    const source = news.source || "--";
    const message = compactNewsMessage(news);
    if (decisionNewsRisk) {
        decisionNewsRisk.textContent = riskLabel;
        decisionNewsRisk.className = risk === "high" ? "warn-text" : risk === "unavailable" ? "muted-text" : "good-text";
    }
    if (decisionNewsSource) {
        decisionNewsSource.textContent = source;
        decisionNewsSource.className = source === "Local calendar" ? "info-text" : "muted-text";
    }
    if (decisionNewsMessage) {
        decisionNewsMessage.textContent = message;
    }
    if (decisionDxyStatus) {
        const dxyStatus = dxy.status || (dxy.enabled === false || /turned off/i.test(String(dxy.message || "")) ? "Off" : dxy.available ? "Available" : "Unavailable");
        decisionDxyStatus.textContent = dxyStatus;
        decisionDxyStatus.className = dxy.available ? "good-text" : "muted-text";
    }
    if (decisionDxyMessage) {
        decisionDxyMessage.textContent = dxy.message || "DXY data unavailable — not included in analysis.";
    }
    if (decisionSessionStatus) {
        const normalizedSession = session ? normalizeSession(session) : null;
        decisionSessionStatus.textContent = normalizedSession
            ? `${normalizedSession.name} · ${normalizedSession.status}`
            : "--";
    }
    if (dashboardNewsStatus) {
        dashboardNewsStatus.textContent = riskLabel;
        dashboardNewsStatus.className = news.blocks_entry ? "warn-text" : risk === "unavailable" ? "muted-text" : "good-text";
        dashboardNewsDetail.textContent = message;
    }
    if (settingsMarketauxStatus && /api token|api key missing|provider is disabled|turned off/i.test(message)) {
        settingsMarketauxStatus.textContent = message.includes("turned off")
            ? "News risk filter is turned off."
            : message;
    }
    if (settingsMarketauxStatus && /Marketaux .*unavailable|Marketaux .*rejected|does not have access/i.test(message)) {
        settingsMarketauxStatus.textContent = "Check the Marketaux API token and plan in the backend .env file.";
    }
}

function compactNewsMessage(news) {
    const message = String(news.message || news.warning || "Marketaux news unavailable.");
    if (/Marketaux API token was rejected|does not have access/i.test(message)) {
        return "Marketaux API token rejected or not allowed for this endpoint.";
    }
    return message.replace(/^News filter unavailable\s+—\s+/i, "");
}

function renderTopDownAnswer(topDown) {
    if (!topDown || Object.keys(topDown).length === 0) {
        const contextEnabled = getFormParams().multi_timeframe === "1";
        answerTopdown.textContent = contextEnabled ? "Not loaded" : "Selected timeframe only";
        answerTopdownSummary.textContent = contextEnabled
            ? "Enable MTF Context and click Load Chart."
            : "Multi-timeframe context is off for this load.";
        return;
    }

    answerTopdown.textContent = topDown.overall_alignment || "Neutral";
    answerTopdownSummary.textContent = topDown.summary || "Top-down context loaded.";
}

function renderMacroTopDown(rows) {
    macroTopdownList.innerHTML = "";

    if (!rows.length) {
        macroTopdownList.textContent = "No top-down bias data available.";
        return;
    }

    for (const row of rows) {
        const item = document.createElement("article");
        item.className = `macro-timeframe-item ${biasClass(row.bias)}`;
        item.innerHTML = `<strong>${row.label}</strong><span>${row.bias}</span><small>${row.state || "--"}</small>`;
        macroTopdownList.appendChild(item);
    }
}

function renderTopDown(topDown) {
    const rows = topDownRows(topDown);
    topdownAlignment.textContent = topDown.overall_alignment || "Neutral";
    topdownList.innerHTML = "";

    if (rows.length === 0) {
        topdownList.textContent = "No top-down context available.";
        return;
    }

    for (const row of rows) {
        const item = document.createElement("article");
        item.className = `mini-item ${biasClass(row.bias)}`;
        item.innerHTML = `<strong>${row.label}</strong><span>${row.bias}</span><small>${row.state || "--"}</small>`;
        topdownList.appendChild(item);
    }
}

function topDownRows(topDown) {
    if (!topDown) {
        return [];
    }

    if (Array.isArray(topDown.rows)) {
        return topDown.rows;
    }

    if (!topDown.timeframes || typeof topDown.timeframes !== "object") {
        return [];
    }

    return Object.entries(topDown.timeframes)
        .sort(([first], [second]) => sortTimeframes(first, second))
        .map(([timeframe, row]) => ({
            label: timeframe,
            bias: row.bias || "Neutral",
            state: row.structure || row.trend || row.status || "--",
            summary: row.summary || row.reason || row.description || row.status || row.structure || "Context loaded",
        }));
}

function renderSessionIntelligence(session) {
    const normalized = normalizeSession(session);
    const allowed = Boolean(normalized.entry_allowed);
    const marketOpen = Boolean(normalized.market_open);
    const killZoneActive = Boolean(normalized.kill_zone_active);

    headerSessionName.textContent = normalized.name;
    headerSessionStatus.textContent = marketOpen ? "OPEN" : "CLOSED";
    headerSessionStatus.className = marketOpen ? "good-text" : "warn-text";
    headerProgressLabel.textContent = normalized.name;
    headerProgressPercent.textContent = `${normalized.progress}%`;
    headerProgressFill.style.width = `${normalized.progress}%`;
    headerSessionStart.textContent = normalized.session_start;
    headerSessionNow.textContent = normalized.current_time_label;
    headerSessionEnd.textContent = normalized.session_end;
    headerSessionRemaining.textContent = normalized.time_remaining_label || normalized.time_remaining;
    headerNextSession.textContent = normalized.next_session_label || normalized.next_session;
    headerEntryAllowed.textContent = allowed ? "YES" : "NO";
    headerEntryAllowed.className = allowed ? "good-text" : "warn-text";
    clock.textContent = normalized.current_time_label;

    renderHeaderSessionTimeline(normalized.timeline || []);

    sessionEntry.textContent = allowed ? "Entry allowed" : "No entries";
    sessionEntry.className = allowed ? "good-text" : "warn-text";
    sessionCurrent.textContent = normalized.name;
    sessionStatus.textContent = normalized.status;
    sessionPhase.textContent = normalized.phase;
    sessionNext.textContent = normalized.next_session_label || normalized.next_session;
    sessionRemaining.textContent = normalized.time_remaining_label || normalized.time_remaining;
    sessionAllowed.textContent = allowed ? "YES" : "NO";
    sessionAllowed.className = allowed ? "good-text" : "warn-text";
    sessionBehavior.textContent = normalized.expected_behavior;

    if (homeNyTime) {
        homeNyTime.textContent = normalized.current_time_label;
        homeMarketOpen.textContent = marketOpen ? "OPEN" : "CLOSED";
        homeMarketOpen.className = marketOpen ? "good-text" : "warn-text";
        homeSessionName.textContent = normalized.name;
        homeKillZone.textContent = killZoneActive ? "ACTIVE" : "INACTIVE";
        homeKillZone.className = killZoneActive ? "good-text" : "muted-text";
        homeNextSession.textContent = normalized.next_session_label || normalized.next_session;
    }
    if (dashboardNyTime) {
        dashboardNyTime.textContent = normalized.current_time_label;
        dashboardMarketOpen.textContent = marketOpen ? "OPEN" : "CLOSED";
        dashboardMarketOpen.className = marketOpen ? "good-text" : "warn-text";
        dashboardSessionName.textContent = normalized.name;
        dashboardKillZone.textContent = killZoneActive ? "ACTIVE" : "INACTIVE";
        dashboardKillZone.className = killZoneActive ? "good-text" : "muted-text";
        dashboardNextSession.textContent = normalized.next_session_label || normalized.next_session;
    }
    if (settingsNyTime) {
        settingsNyTime.textContent = normalized.current_time_label;
    }
}

function renderHeaderSessionTimeline(timeline) {
    headerSessionTimeline.innerHTML = "";

    for (const item of timeline) {
        const row = document.createElement("span");
        row.className = item.state || "upcoming";
        row.textContent = `${timelineIcon(item.state)} ${item.name}`;
        headerSessionTimeline.appendChild(row);
    }
}

function timelineIcon(state) {
    if (state === "completed") {
        return "✓";
    }
    if (state === "current") {
        return "▶";
    }
    return "○";
}

function normalizeSession(session) {
    const fallback = buildClientSessionContext();
    const name = session.name || session.session || session.current_session || fallback.name;

    return {
        ...fallback,
        ...session,
        name,
        status: session.status || (session.active ? "ACTIVE" : fallback.status),
        current_time: session.current_time || fallback.current_time,
        current_time_label: session.current_time_label || fallback.current_time_label,
        next_session: session.next_session || session.next_kill_zone || fallback.next_session,
        next_session_label: session.next_session_label || fallback.next_session_label,
        next_transition: session.next_transition || fallback.next_transition,
        next_transition_label: session.next_transition_label || fallback.next_transition_label,
        time_remaining: session.time_remaining || fallback.time_remaining,
        time_remaining_label: session.time_remaining_label || session.time_remaining || fallback.time_remaining_label,
        time_until_next_session: session.time_until_next_session || fallback.time_until_next_session,
        time_until_next_session_label: session.time_until_next_session_label || fallback.time_until_next_session_label,
        market_open: typeof session.market_open === "boolean" ? session.market_open : fallback.market_open,
        market_status: session.market_status || fallback.market_status,
        kill_zone_active: typeof session.kill_zone_active === "boolean" ? session.kill_zone_active : fallback.kill_zone_active,
        kill_zone_status: session.kill_zone_status || fallback.kill_zone_status,
        session_start: session.session_start || fallback.session_start,
        session_end: session.session_end || fallback.session_end,
        phase: session.phase || fallback.phase,
        expected_behavior: session.expected_behavior || fallback.expected_behavior,
        progress: Number.isFinite(Number(session.progress)) ? Number(session.progress) : fallback.progress,
        timeline: session.timeline || fallback.timeline,
    };
}

function buildClientSessionContext() {
    const now = getNewYorkClock();
    const active = SESSION_DEFINITIONS.find((session) => now.minutes >= session.start && now.minutes < session.end);
    const session = active || {
        name: "Outside Trading Hours",
        entryAllowed: false,
        phase: "Context Only",
        expectedBehavior: "Continue updating market context. New valid entries are blocked by the session filter.",
    };
    const nextReferenceMinute = active ? active.end % (24 * 60) : now.minutes;
    const nextSession = nextSessionAfter(nextReferenceMinute);
    const remainingSeconds = active
        ? Math.max((active.end * 60) - now.secondsOfDay, 0)
        : secondsUntilMinute(now.secondsOfDay, nextSession.start);
    const progress = active
        ? Math.min(Math.round(((now.minutes - active.start) / (active.end - active.start)) * 100), 100)
        : 0;
    const killZoneActive = Boolean(active && ["London Kill Zone", "New York Kill Zone"].includes(active.name));
    const marketOpen = isForexMarketOpenClient(now);
    const nextTransitionName = active ? "Outside Trading Hours" : nextSession.name;
    const nextTransitionMinute = active ? active.end % (24 * 60) : nextSession.start;
    const transitionSeconds = secondsUntilMinute(now.secondsOfDay, nextTransitionMinute);

    return {
        name: session.name,
        session: session.name,
        status: active ? "ACTIVE" : "INACTIVE",
        active: Boolean(active),
        entry_allowed: Boolean(session.entryAllowed),
        kill_zone_active: killZoneActive,
        kill_zone_status: killZoneActive ? "ACTIVE" : "INACTIVE",
        market_open: marketOpen,
        market_status: marketOpen ? "OPEN" : "CLOSED",
        time_remaining: formatHms(remainingSeconds),
        time_remaining_label: formatRemainingLabel(remainingSeconds),
        next_session: nextSession.name,
        phase: session.phase,
        expected_behavior: session.expectedBehavior,
        current_time: now.timeText,
        current_time_label: now.timeLabel,
        timezone: "America/New_York",
        timezone_abbreviation: now.timeZoneName,
        progress,
        session_start: active ? minuteToTime(active.start) : "--",
        session_end: active ? minuteToTime(active.end) : "--",
        next_session_label: `${nextSession.name} at ${formatMinuteAmerican(nextSession.start, now.timeZoneName)}`,
        next_transition: nextTransitionName,
        next_transition_label: `${nextTransitionName} at ${formatMinuteAmerican(nextTransitionMinute, now.timeZoneName)}`,
        time_until_next_session: formatHms(transitionSeconds),
        time_until_next_session_label: formatRemainingLabel(transitionSeconds),
        timeline: SESSION_DEFINITIONS.map((item) => ({
            name: item.name,
            start: minuteToTime(item.start).slice(0, 5),
            end: minuteToTime(item.end).slice(0, 5),
            state: sessionTimelineState(item, now.minutes, active),
        })),
    };
}

function getNewYorkClock() {
    const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        weekday: "short",
        hourCycle: "h23",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    }).formatToParts(new Date());
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    const hour = Number(values.hour);
    const minute = Number(values.minute);
    const second = Number(values.second);
    const label = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
        timeZoneName: "short",
    }).format(new Date());
    const timeZoneName = label.split(" ").at(-1) || "ET";

    return {
        hour,
        minute,
        second,
        minutes: hour * 60 + minute,
        secondsOfDay: (hour * 3600) + (minute * 60) + second,
        timeText: `${pad2(hour)}:${pad2(minute)}:${pad2(second)}`,
        timeLabel: label,
        timeZoneName,
        weekday: values.weekday,
    };
}

function isForexMarketOpenClient(now) {
    if (now.weekday === "Sat") return false;
    if (now.weekday === "Sun") return now.minutes >= 17 * 60;
    if (now.weekday === "Fri") return now.minutes < 17 * 60;
    return true;
}

function nextSessionAfter(minutes) {
    return [...SESSION_DEFINITIONS]
        .map((session) => ({
            session,
            wait: ((session.start - minutes) + (24 * 60)) % (24 * 60) || (24 * 60),
        }))
        .sort((left, right) => left.wait - right.wait)[0].session;
}

function formatMinuteAmerican(value, timeZoneName) {
    const normalized = value % (24 * 60);
    const hour24 = Math.floor(normalized / 60);
    const minute = normalized % 60;
    const suffix = hour24 >= 12 ? "PM" : "AM";
    const hour12 = hour24 % 12 || 12;
    return `${hour12}:${pad2(minute)} ${suffix} ${timeZoneName}`;
}

function secondsUntilMinute(secondsOfDay, targetMinute) {
    const targetSeconds = targetMinute * 60;
    if (targetSeconds > secondsOfDay) {
        return targetSeconds - secondsOfDay;
    }

    return (24 * 3600) - secondsOfDay + targetSeconds;
}

function sessionTimelineState(session, minutes, active) {
    if (active && active.name === session.name) {
        return "current";
    }
    if (session.end <= minutes) {
        return "completed";
    }
    return "upcoming";
}

function minuteToTime(value) {
    const safeValue = value >= 24 * 60 ? 0 : value;
    const hour = Math.floor(safeValue / 60);
    const minute = safeValue % 60;
    return `${pad2(hour)}:${pad2(minute)}:00`;
}

function formatHms(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}`;
}

function formatRemainingLabel(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function pad2(value) {
    return String(value).padStart(2, "0");
}

function renderMarketContext(analysis) {
    const context = analysis.market_context || {};
    const activeZone = analysis.active_zone || {};
    const rows = [
        ["Bias Source", context.bias_source || "--"],
        ["Active FVG", context.active_fvg_type ? titleCase(context.active_fvg_type) : "--"],
        ["Dealing Range High", formatPrice(context.dealing_range_high, analysis)],
        ["Dealing Range Low", formatPrice(context.dealing_range_low, analysis)],
        ["Premium / Discount", context.premium_discount ? titleCase(context.premium_discount) : "--"],
        ["Current Session", context.current_session || "--"],
        ["Session Phase", context.session_phase || "--"],
        ["Entry Allowed", context.entry_allowed ? "YES" : "NO"],
        ["Active Zone", activeZone.name || "--"],
    ];

    contextCount.textContent = "Current chart";
    renderInfoRows(marketContextList, rows);
    renderLiquidityMap(analysis.liquidity_map || {});
}

function renderRecentStructure(analysis) {
    const structure = analysis.recent_structure || {};
    const zones = analysis.zones || {};
    const rows = [
        ["Last Swing High", formatPoint(structure.last_swing_high)],
        ["Last Swing Low", formatPoint(structure.last_swing_low)],
        ["Liquidity Sweep", formatSweep(structure.liquidity_sweep)],
        ["MSS", formatMss(structure.mss)],
        ["IFVG", formatZone(zones.ifvg)],
        ["Order Block", formatOrderBlock(structure.order_block)],
    ];

    structureCount.textContent = analysisDecisionStatus(analysis);
    renderInfoRows(structureList, rows);
}

function renderLiquidityMap(map) {
    const rows = [];

    if (map.current_price !== null && map.current_price !== undefined) {
        rows.push(["Current Price", formatPrice(map.current_price)]);
    }

    for (const level of map.buy_side || []) {
        rows.push([`Buy Side: ${level.label}`, formatPrice(level.price)]);
    }

    for (const level of map.sell_side || []) {
        rows.push([`Sell Side: ${level.label}`, formatPrice(level.price)]);
    }

    if (map.current_target && map.current_target.price !== undefined) {
        rows.push(["Current Target", `${map.current_target.label} ${formatPrice(map.current_target.price)}`]);
    }

    renderInfoRows(liquidityMapList, rows.length ? rows : [["Liquidity Map", "No nearby liquidity pools found."]]);
}

function renderSetupExplanation(analysis) {
    const displayStatus = analysisDecisionStatus(analysis);
    const rows = [
        ["Status", displayStatus],
        ["Readiness", `${analysis.readiness_level?.percent ?? analysis.readiness ?? 0}%`],
        ["Missing", formatMarketText(analysis.missing_confirmation || "--", analysis)],
        ["Action", scannerNextAction.textContent || "Analyze the market for the next action."],
        ["Summary", formatMarketText(analysis.summary || "--", analysis)],
    ];

    explanationStatus.textContent = analysis.bias || "NEUTRAL";
    renderInfoRows(setupExplanation, rows);
}

function resetAnalysisTimeline() {
    analysisTimelineEvents = [];
    analysisTimelineKeys = new Set();
    renderTimeline([]);
}

function recordTimelineEvents(events) {
    for (const event of events) {
        const normalized = normalizeTimelineEvent(event);
        const key = timelineEventKey(normalized);

        if (analysisTimelineKeys.has(key)) {
            continue;
        }

        analysisTimelineKeys.add(key);
        analysisTimelineEvents.push(normalized);
    }

    analysisTimelineEvents.sort((first, second) => timelineSortValue(second) - timelineSortValue(first));
    renderTimeline(analysisTimelineEvents);
}

function normalizeTimelineEvent(event) {
    return {
        time: event.time || "Current",
        event_type: event.event_type || event.title || "Event",
        direction: event.direction || "--",
        explanation: event.explanation || event.detail || "--",
        sort_time: event.sort_time || event.time || "Current",
    };
}

function timelineEventKey(event) {
    const type = String(event.event_type || "");

    if (
        type.startsWith("Setup ")
        || type.startsWith("Entry ")
        || type.startsWith("TP")
    ) {
        return `${type}|${event.direction}|${event.explanation}`;
    }

    return `${event.time}|${type}|${event.direction}|${event.explanation}`;
}

function timelineSortValue(event) {
    const parsed = Date.parse(event.sort_time || event.time);
    return Number.isFinite(parsed) ? parsed : 0;
}

function renderTimeline(events) {
    timelineList.innerHTML = "";

    if (!events.length) {
        timelineList.textContent = "No timeline events detected yet.";
        return;
    }

    const visibleEvents = events.slice(0, 5);

    for (const event of visibleEvents) {
        timelineList.appendChild(timelineItem(event));
    }

    if (events.length > visibleEvents.length) {
        const details = document.createElement("details");
        details.className = "timeline-more";
        const summary = document.createElement("summary");
        summary.textContent = "Show older events";
        details.appendChild(summary);

        for (const event of events.slice(visibleEvents.length)) {
            details.appendChild(timelineItem(event));
        }

        timelineList.appendChild(details);
    }
}

function timelineItem(event) {
    const item = document.createElement("article");
    const time = document.createElement("span");
    const title = document.createElement("strong");
    const direction = document.createElement("small");
    const explanation = document.createElement("p");

    item.className = "timeline-item";
    time.textContent = shortTime(event.time);
    title.textContent = event.event_type || event.title || "Event";
    direction.textContent = event.direction && event.direction !== "--" ? event.direction : "NEUTRAL";
    explanation.textContent = formatMarketText(event.explanation || event.detail || "--");
    item.append(time, title, direction, explanation);

    return item;
}

function renderRawAnalysis(analysis) {
    const debugPayload = {
        ...analysis,
        candles: `${analysis.candles?.length || 0} candles omitted from debug view`,
    };

    rawAnalysis.textContent = JSON.stringify(debugPayload, null, 2);
}

function renderAnswerQa(analysis) {
    const answers = analysis.trader_answers || {};
    const qa = analysis.answer_qa || {};
    const validation = analysis.answer_validation || qa.validation || { valid: true, warnings: [] };
    const conditions = qa.answer_conditions || {};
    const missingWarnings = qa.missing_data_warnings || [];
    const validationWarnings = validation.warnings || [];
    const temporalValidation = analysis.temporal_validation || qa.temporal_validation || { valid: true, warnings: [] };
    const temporalWarnings = temporalValidation.warnings || [];

    const totalWarnings = validationWarnings.length + temporalWarnings.length;
    answerQaValidation.textContent = validation.valid && temporalValidation.valid ? "Valid" : `${totalWarnings} warning${totalWarnings === 1 ? "" : "s"}`;
    answerQaValidation.className = validation.valid && temporalValidation.valid ? "valid" : "warning";
    answerQaCurrent.textContent = JSON.stringify(answers, null, 2);
    answerQaSource.textContent = JSON.stringify(qa.source_strategy || analysis.strategy_result || {}, null, 2);
    answerQaClarity.textContent = qa.clarity_explanation || "No clarity explanation is available.";

    const conditionRows = Object.entries(conditions).map(([answer, evidence]) => [
        titleCase(answer.replaceAll("_", " ")),
        Array.isArray(evidence) ? evidence.join(" ") : String(evidence || "--"),
    ]);
    renderInfoRows(answerQaConditions, conditionRows.length ? conditionRows : [["Conditions", "No answer conditions loaded."]]);
    renderQaWarnings(validationWarnings, missingWarnings, temporalWarnings);
    renderReplayAnswerQa();
}

function renderQaWarnings(validationWarnings, missingWarnings, temporalWarnings = []) {
    answerQaWarnings.innerHTML = "";
    const rows = [
        ...validationWarnings.map((warning) => `Validation: ${warning}`),
        ...missingWarnings.map((warning) => `Data: ${warning}`),
        ...temporalWarnings.map((warning) => `Temporal: ${warning}`),
    ];

    if (!rows.length) {
        answerQaWarnings.textContent = "No validation or missing-data warnings.";
        return;
    }

    for (const warning of rows) {
        const item = document.createElement("div");
        item.className = "qa-message";
        item.textContent = warning;
        answerQaWarnings.appendChild(item);
    }
}

function resetAnswerQaReplay() {
    answerQaSnapshots = new Map();
    answerQaChanges = [];
    renderReplayAnswerQa();
}

function recordReplayAnswerSnapshot(analysis, candle, index) {
    if (!analysis.trader_answers || !candle) {
        return;
    }

    for (const snapshotIndex of answerQaSnapshots.keys()) {
        if (snapshotIndex > index) {
            answerQaSnapshots.delete(snapshotIndex);
        }
    }

    answerQaSnapshots.set(index, {
        index,
        time: formatReplayCandleTime(candle.time),
        answers: JSON.parse(JSON.stringify(analysis.trader_answers)),
        qa: JSON.parse(JSON.stringify(analysis.answer_qa || {})),
    });
    rebuildReplayAnswerChanges();
    renderReplayAnswerQa();
}

function rebuildReplayAnswerChanges() {
    const snapshots = Array.from(answerQaSnapshots.values()).sort((first, second) => first.index - second.index);
    const fields = ["trend", "price_location", "trade_status", "next_action"];
    answerQaChanges = [];

    for (let index = 1; index < snapshots.length; index += 1) {
        const previous = snapshots[index - 1];
        const current = snapshots[index];

        for (const field of fields) {
            const before = String(previous.answers[field] || "--");
            const after = String(current.answers[field] || "--");
            if (before === after) {
                continue;
            }

            answerQaChanges.push({
                index: current.index,
                time: current.time,
                field,
                before,
                after,
                reason: explainAnswerChange(field, before, after, current),
            });
        }
    }
}

function explainAnswerChange(field, before, after, snapshot) {
    const conditions = snapshot.qa?.answer_conditions?.[field] || [];
    const evidence = Array.isArray(conditions) && conditions.length ? conditions[0] : "the latest candle changed the underlying conditions";

    if (field === "trade_status" && after === "Entry Ready") {
        return `Trade status changed from ${before} to Entry Ready because price completed the required confirmation and final levels became valid.`;
    }
    if (field === "trade_status" && after === "No Trade") {
        return `Trade status changed from ${before} to No Trade because the setup was invalidated or failed its trade-quality rules.`;
    }
    if (field === "trade_status") {
        return `Trade status changed from ${before} to ${after} because ${lowercaseFirst(evidence)}`;
    }
    if (field === "trend") {
        return `Trend changed from ${before} to ${after} because ${lowercaseFirst(evidence)}`;
    }
    if (field === "price_location") {
        return `Price location changed from ${before} to ${after} because ${lowercaseFirst(evidence)}`;
    }
    if (field === "next_action") {
        return "The next action changed because the current setup stage or required confirmation changed.";
    }
    return `${titleCase(field.replaceAll("_", " "))} changed because the latest candle changed its source conditions.`;
}

function renderReplayAnswerQa() {
    answerQaSnapshotCount.textContent = `${answerQaSnapshots.size} replay snapshot${answerQaSnapshots.size === 1 ? "" : "s"}`;
    answerQaReplayLog.innerHTML = "";

    if (!answerQaChanges.length) {
        answerQaReplayLog.textContent = answerQaSnapshots.size
            ? "No answer changes detected between analyzed replay candles yet."
            : "No replay answer changes recorded.";
        answerQaChangeReason.textContent = answerQaSnapshots.size
            ? "The five market answers have remained stable so far."
            : "Step through Replay Mode to explain answer changes.";
        return;
    }

    const newest = [...answerQaChanges].sort((first, second) => second.index - first.index).slice(0, 20);
    answerQaChangeReason.textContent = newest[0].reason;

    for (const change of newest) {
        const item = document.createElement("article");
        const title = document.createElement("strong");
        const detail = document.createElement("small");
        item.className = "qa-change";
        title.textContent = `${change.time} · ${titleCase(change.field.replaceAll("_", " "))}: ${change.before} -> ${change.after}`;
        detail.textContent = change.reason;
        item.append(title, detail);
        answerQaReplayLog.appendChild(item);
    }
}

function formatReplayCandleTime(value) {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
        return new Date(numeric * 1000).toLocaleString([], {
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }
    return shortTime(value);
}

function lowercaseFirst(value) {
    const text = String(value || "");
    return text ? `${text.charAt(0).toLowerCase()}${text.slice(1)}` : "the source conditions changed.";
}

function renderInfoRows(container, rows) {
    container.innerHTML = "";

    for (const [label, value] of rows) {
        const item = document.createElement("article");
        const key = document.createElement("strong");
        const detail = document.createElement("span");

        item.className = "info-item";
        key.textContent = label;
        detail.textContent = value || "--";
        item.append(key, detail);
        container.appendChild(item);
    }
}

function formatZone(zone) {
    if (!zone) {
        return "--";
    }

    const top = zone.top ?? zone.top_price;
    const bottom = zone.bottom ?? zone.bottom_price;

    if (top === undefined || bottom === undefined) {
        return "--";
    }

    return `${formatPrice(bottom)} - ${formatPrice(top)}`;
}

function formatPoint(point) {
    if (!point || point.price === undefined) {
        return "--";
    }

    return `${formatPrice(point.price)} at ${shortTime(point.time)}`;
}

function formatSweep(sweep) {
    if (!sweep || sweep.swept_level === undefined) {
        return "--";
    }

    return `${titleCase(sweep.side || "sweep")} at ${formatPrice(sweep.swept_level)} (${shortTime(sweep.time)})`;
}

function formatMss(mss) {
    if (!mss || mss.level === undefined) {
        return "--";
    }

    return `${titleCase(mss.direction || "MSS")} close break at ${formatPrice(mss.level)} (${shortTime(mss.time)})`;
}

function formatOrderBlock(orderBlock) {
    if (!orderBlock || orderBlock.top_price === undefined || orderBlock.bottom_price === undefined) {
        return "--";
    }

    return `${orderBlock.label || "Order Block"} ${formatPrice(orderBlock.bottom_price)} - ${formatPrice(orderBlock.top_price)}`;
}

function shortTime(value) {
    if (!value) {
        return "--";
    }

    return String(value).replace("T", " ").slice(0, 16);
}

function titleCase(value) {
    return String(value)
        .replace("-", " ")
        .split(" ")
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function isDetected(value) {
    if (typeof value === "boolean") {
        return value;
    }

    return String(value || "").toLowerCase() === "detected";
}

function zoneClass(zone, fallback) {
    if (!zone) {
        return fallback;
    }

    const type = String(zone.type || zone.direction || "").toLowerCase();

    if (type.includes("bullish")) {
        return "bullish";
    }
    if (type.includes("bearish")) {
        return "bearish";
    }
    if (type.includes("support") || type.includes("demand")) {
        return "bullish";
    }
    if (type.includes("resistance") || type.includes("supply")) {
        return "bearish";
    }
    if (type.includes("pullback")) {
        return "pullback";
    }
    return fallback;
}

function zoneColor(zone, fallback) {
    if (!zone || !zone.type) {
        return fallback;
    }

    if (String(zone.type).includes("bullish") || zone.direction === "bullish") {
        return "#22c55e";
    }
    if (String(zone.type).includes("bearish") || zone.direction === "bearish") {
        return "#ef4444";
    }
    return fallback;
}

function biasClass(bias) {
    const text = String(bias || "").toLowerCase();

    if (text.includes("bullish")) {
        return "bullish";
    }
    if (text.includes("bearish")) {
        return "bearish";
    }
    if (text.includes("pullback") || text.includes("waiting")) {
        return "waiting";
    }
    return "neutral";
}

function formatPrice(value, analysis = latestAnalysis) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return "--";
    }
    return numeric.toFixed(pricePrecision(analysis, numeric));
}

function formatSignedPrice(value, analysis = latestAnalysis) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return "--";
    }
    return `${numeric >= 0 ? "+" : ""}${numeric.toFixed(pricePrecision(analysis))}`;
}

function formatRatio(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric.toFixed(2) : "--";
}

function formatMarketText(value, analysis = latestAnalysis) {
    const text = userFacingText(value);
    return text.replace(/-?\d+\.\d+/g, (match, offset, source) => {
        const suffix = source.slice(offset + match.length).trimStart().charAt(0).toUpperCase();
        if (suffix === "R" || suffix === "%") {
            return match;
        }
        return formatPrice(Number(match), analysis);
    });
}

function pricePrecision(analysis = latestAnalysis, value = null) {
    const params = getFormParams();
    const symbol = String(analysis?.display_symbol || analysis?.symbol || params.symbol || "").toUpperCase();
    const assetType = String(analysis?.asset_type || "").toLowerCase();
    const numeric = Math.abs(Number(value));
    const configured = Number(analysis?.price_precision);

    if (Number.isInteger(configured) && configured >= 0 && configured <= 8) {
        return configured;
    }

    if (symbol.endsWith("/JPY") || symbol === "USDJPY" || symbol === "GBPJPY") {
        return 3;
    }
    if (assetType === "index" || ["NASDAQ 100", "DOW JONES 30", "S&P 500", "RUSSELL 2000"].includes(symbol)) {
        return 2;
    }
    if (assetType === "crypto" || symbol.includes("BTC") || symbol.includes("ETH")) {
        return Number.isFinite(numeric) && numeric > 0 && numeric < 1 ? 6 : 2;
    }
    if (/^[A-Z]{3}\/[A-Z]{3}$/.test(symbol)) {
        return 5;
    }
    return Number.isFinite(numeric) && numeric >= 100 ? 2 : 5;
}

function applyChartPriceFormat(analysis) {
    if (!candleSeries) {
        return;
    }
    const precision = pricePrecision(analysis);
    candleSeries.applyOptions({
        priceFormat: {
            type: "price",
            precision,
            minMove: 10 ** -precision,
        },
    });
}

function configureAutoRefresh() {
    clearInterval(refreshTimer);

    if (isReplayMode) {
        refreshText.textContent = "Auto-refresh paused in replay";
        return;
    }

    if (!autoRefreshToggle.checked || !lastLoadedParams) {
        refreshText.textContent = "Auto-refresh off";
        return;
    }

    const seconds = Math.max(Number(refreshIntervalSelect.value), 60);
    refreshText.textContent = `Auto-refresh ${seconds}s`;

    refreshTimer = setInterval(() => {
        if (lastLoadedParams) {
            refreshText.textContent = "Refreshing...";
            loadChart(lastLoadedParams, { fromTimer: true }).finally(() => {
                refreshText.textContent = `Auto-refresh ${seconds}s`;
            });
        }
    }, seconds * 1000);
}

function resetReplay(candles) {
    stopReplay();
    resetAnswerQaReplay();
    replayCandles = candles;
    replayStartIndex = Math.min(Math.max(20, MIN_REPLAY_CANDLES), candles.length);
    replayIndex = replayStartIndex;
    replayAnalyzing = false;
    setAnalysisMode("live");
    updateReplayControls();
    replayStatus.textContent = `${candles.length} candles ready for replay.`;
}

function disableReplay() {
    stopReplay();
    resetAnswerQaReplay();
    replayCandles = [];
    replayIndex = 0;
    replayStartIndex = 0;
    replayAnalyzing = false;
    updateReplayControls();
    replayStatus.textContent = "Load a chart to replay candles.";
}

function playReplay() {
    if (!replayCandles.length) {
        return;
    }

    stopReplay();
    enterReplayMode();

    if (replayIndex >= replayCandles.length) {
        replayIndex = replayStartIndex;
        resetAnalysisTimeline();
        resetAnswerQaReplay();
    }

    const speed = Math.max(Number(replaySpeed.value), 1);
    replayTimer = setInterval(() => {
        stepReplay();
    }, Math.max(120, 900 / speed));
    stepReplay();
}

function stopReplay() {
    clearInterval(replayTimer);
    replayTimer = null;
    updateReplayControls();
}

async function stepReplay() {
    if (!replayCandles.length || !candleSeries) {
        return;
    }

    enterReplayMode();

    if (replayIndex >= replayCandles.length) {
        finishReplay();
        return;
    }

    replayIndex = Math.min(replayIndex + 1, replayCandles.length);
    await analyzeReplayAtIndex();

    if (replayIndex >= replayCandles.length) {
        finishReplay();
    }
}

async function stepBackReplay() {
    if (!replayCandles.length || !candleSeries) {
        return;
    }

    enterReplayMode();
    stopReplay();
    replayIndex = Math.max(replayStartIndex, replayIndex - 1);
    await analyzeReplayAtIndex();
}

async function resetReplayView() {
    if (!replayCandles.length || !candleSeries) {
        return;
    }

    enterReplayMode(true);
    stopReplay();
    replayIndex = replayStartIndex;
    await analyzeReplayAtIndex(true);
}

async function analyzeReplayAtIndex(fitContent = false) {
    if (replayAnalyzing) {
        return;
    }

    replayAnalyzing = true;
    updateReplayControls();

    const candleSlice = replayCandles.slice(0, replayIndex);
    candleSeries.setData(candleSlice);
    clearPriceLines();
    clearZoneRectangles();

    if (fitContent) {
        chart.timeScale().fitContent();
    }

    replayStatus.textContent = `Analyzing candle ${replayIndex} of ${replayCandles.length}.`;

    try {
        const payload = await postJson("/api/analyze-replay", {
            symbol: lastLoadedParams?.symbol || getFormParams().symbol,
            timeframe: lastLoadedParams?.timeframe || getFormParams().timeframe,
            strategy: lastLoadedParams?.strategy || getFormParams().strategy,
            multi_timeframe: Object.keys(loadedContextCandles).length > 1,
            context_depth: lastLoadedParams?.context_depth || getFormParams().context_depth,
            candles: candleSlice,
            context_candles: loadedContextCandles,
        });
        const analysis = normalizeStrategyAnalysis(payload.analysis || payload);
        const candles = prepareCandlesForChart(payload.candles || candleSlice);

        analysis.candles = candles;
        latestAnalysis = analysis;
        drawAnalysisOverlays(analysis);
        renderAnalysis(analysis);
        recordReplayAnswerSnapshot(analysis, candleSlice[candleSlice.length - 1], replayIndex);
        chartTitle.textContent = `${analysis.display_symbol || analysis.symbol || lastLoadedParams?.symbol || "Chart"} · ${analysis.timeframe || lastLoadedParams?.timeframe || "M5"} · Replay ${replayIndex}/${replayCandles.length}`;
        setStatus(`${analysis.setup_status}`, "Replay");
        replayStatus.textContent = `Replay candle ${replayIndex} of ${replayCandles.length}.`;
    } catch (error) {
        stopReplay();
        showError(error.message);
    } finally {
        replayAnalyzing = false;
        updateReplayControls();
    }
}

function enterReplayMode(clearTimeline = false) {
    if (!isReplayMode || clearTimeline) {
        resetAnalysisTimeline();
    }
    if (clearTimeline) {
        resetAnswerQaReplay();
    }

    isReplayMode = true;
    setAnalysisMode("replay");
    clearInterval(refreshTimer);
    refreshText.textContent = "Auto-refresh paused in replay";
}

function finishReplay() {
    stopReplay();
    isReplayMode = false;
    setAnalysisMode("live");
    configureAutoRefresh();
    replayStatus.textContent = "Replay complete.";
}

function setAnalysisMode(mode) {
    isReplayMode = mode === "replay";

    if (!analysisModeBadge) {
        return;
    }

    analysisModeBadge.textContent = isReplayMode ? "REPLAY MODE" : "LIVE ANALYSIS";
    analysisModeBadge.classList.toggle("replay", isReplayMode);
    analysisModeBadge.classList.toggle("live", !isReplayMode);
}

function updateReplayControls() {
    const hasCandles = replayCandles.length > 0;
    const isAtStart = replayIndex <= replayStartIndex;
    const isAtEnd = replayIndex >= replayCandles.length;

    replayPlay.disabled = !hasCandles || isAtEnd || replayAnalyzing;
    replayPause.disabled = !hasCandles || !replayTimer;
    replayBack.disabled = !hasCandles || isAtStart || replayAnalyzing;
    replayStep.disabled = !hasCandles || isAtEnd || replayAnalyzing;
    replayReset.disabled = !hasCandles || replayAnalyzing;
    replaySpeed.disabled = !hasCandles;
}

function updateAutoRefreshControls() {
    refreshIntervalSelect.disabled = !autoRefreshToggle.checked;
    autoRefreshState.textContent = autoRefreshToggle.checked ? "On" : "Off";
    configureAutoRefresh();
}

function updateClock() {
    const replaySession = isReplayMode ? latestAnalysis?.session || latestAnalysis?.kill_zone : null;
    renderSessionIntelligence(replaySession || buildClientSessionContext());
}

window.addEventListener("resize", () => {
    resizeChartToContainer();
    redrawChartOverlays();
});

loadButton.addEventListener("click", () => loadChart(getFormParams()));
document.getElementById("symbol").addEventListener("change", () => {
    updateTopSelection();
    markScannerSelectionChanged();
    syncHomeControlsFromMain();
});
document.getElementById("timeframe").addEventListener("change", () => {
    updateTopSelection();
    markScannerSelectionChanged();
    syncHomeControlsFromMain();
});
document.getElementById("strategy").addEventListener("change", () => {
    updateTopSelection();
    markScannerSelectionChanged();
    const strategyWantsContext = getFormParams().strategy === "ict_2022";
    contextZonesToggle.checked = strategyWantsContext || readSavedSettings().contextZones !== false;
    syncHomeControlsFromMain();
    if (latestAnalysis) drawAnalysisOverlays(latestAnalysis);
});
tradePlanToggle.addEventListener("change", () => latestAnalysis && drawAnalysisOverlays(latestAnalysis));
contextZonesToggle.addEventListener("change", redrawChartOverlays);
advancedLabelsToggle.addEventListener("change", redrawChartOverlays);
dataModeSelect.addEventListener("change", updateTopSelection);
autoRefreshToggle.addEventListener("change", updateAutoRefreshControls);
refreshIntervalSelect.addEventListener("change", configureAutoRefresh);
replayPlay.addEventListener("click", playReplay);
replayPause.addEventListener("click", stopReplay);
replayBack.addEventListener("click", stepBackReplay);
replayStep.addEventListener("click", stepReplay);
replayReset.addEventListener("click", resetReplayView);
settingsToggle.addEventListener("click", () => {
    setAppView("settings");
});

homeAnalyze.addEventListener("click", async () => {
    syncMainControlsFromHome();
    homeAnalyze.disabled = true;
    homeAnalyze.textContent = "Analyzing...";
    await loadChart(getFormParams());
    homeAnalyze.disabled = false;
    homeAnalyze.textContent = "Analyze Market";
});

for (const button of appViewButtons) {
    button.addEventListener("click", () => setAppView(button.dataset.appView));
}

for (const button of openViewButtons) {
    button.addEventListener("click", () => setAppView(button.dataset.openView));
}

for (const control of [
    settingsDefaultSymbol,
    settingsDefaultTimeframe,
    settingsStrategyMode,
    settingsDefaultStrategy,
    settingsTradePlan,
    settingsContextZones,
    settingsAdvancedLabels,
    settingsShowSession,
    settingsAutoRefresh,
    settingsRefreshInterval,
    settingsDataMode,
    settingsMarketauxEnabled,
    settingsNewsRisk,
    settingsDxyConfirmation,
]) {
    control.addEventListener("change", saveSettingsFromPanel);
}

applySavedSettings();
setAppView("scanner");
loadRecentMarkets();
updateTopSelection();
updateAutoRefreshControls();
updateClock();
updateReplayControls();
renderTimeline([]);
setInterval(updateClock, 1000);

// ============================================================
// STRATEGY LAB  (rewritten: fixed performance, rendering, symbol sync)
// ============================================================

const labRunBtn = document.getElementById("lab-run-btn");
const labStatus = document.getElementById("lab-status");
const labWarnings = document.getElementById("lab-warnings");
const labResults = document.getElementById("lab-results");
const labBestName = document.getElementById("lab-best-name");
const labSummaryText = document.getElementById("lab-summary-text");
const labTableBody = document.getElementById("lab-table-body");
const labTradeLogBody = document.getElementById("lab-trade-log-body");
const labLogFilter = document.getElementById("lab-log-filter");
const labBestBadge = document.getElementById("lab-best-badge");
const labEquityChart = document.getElementById("lab-equity-chart");
const labEquityLegend = document.getElementById("lab-equity-legend");
const labPanel = document.getElementById("strategy-lab-panel");
const labTrustSummary = document.getElementById("lab-trust-summary");
const labModeSelect = document.getElementById("lab-mode");
const labModeHint = document.getElementById("lab-mode-hint");
const labRunStatusEl = document.getElementById("lab-run-status");
const labResultState = document.getElementById("lab-result-state");
const labResultIdentity = document.getElementById("lab-result-identity");

// Mismatch warning element injected into header after load-chart button
let _selectionMismatchEl = null;

const LAB_STRATEGY_COLORS = {
    universal_structure: "#2B84FF",
    supply_demand:       "#22c55e",
    breakout_retest:     "#60a5fa",
    ict_2022:            "#f472b6",
};

let _labAllTrades = {};
let _labEquityData = {};
let _pendingBacktestConfig = null;
let _renderedBacktestIdentity = null;
let _labRunPhase = "idle";

// ----------------------------------------------------------------
// Symbol/timeframe auto-sync: when panel opens, mirror main selects
// ----------------------------------------------------------------
if (labPanel) {
    labPanel.addEventListener("toggle", () => {
        if (labPanel.open) {
            _syncLabSelects();
        }
    });
}

function _syncLabSelects() {
    const sym = document.getElementById("symbol");
    const tf  = document.getElementById("timeframe");
    const labSym = document.getElementById("lab-symbol");
    const labTf  = document.getElementById("lab-timeframe");
    if (sym && labSym && sym.value) {
        // Find the closest matching option
        const match = [...labSym.options].find(o => o.value === sym.value);
        if (match) labSym.value = sym.value;
    }
    if (tf && labTf && tf.value) {
        const match = [...labTf.options].find(o => o.value === tf.value);
        if (match) labTf.value = tf.value;
    }
    _updateLabResultStaleWarning();
}

// ----------------------------------------------------------------
// Selection mismatch warning (main chart)
// ----------------------------------------------------------------
function _updateMismatchWarning() {
    const sym = document.getElementById("symbol");
    const tf  = document.getElementById("timeframe");
    if (!sym || !tf || !loadButton) return;

    const strategy = document.getElementById("strategy");
    const selected = `${sym.value}·${tf.value}·${strategy?.value || ""}`;
    const loaded = lastLoadedParams ? `${lastLoadedParams.symbol}·${lastLoadedParams.timeframe}·${lastLoadedParams.strategy || ""}` : null;

    if (!_selectionMismatchEl) {
        _selectionMismatchEl = document.createElement("small");
        _selectionMismatchEl.className = "selection-mismatch-hint";
        loadButton.insertAdjacentElement("afterend", _selectionMismatchEl);
    }

    if (loaded && selected !== loaded) {
        _selectionMismatchEl.textContent = "Needs update";
        _selectionMismatchEl.hidden = false;
    } else {
        _selectionMismatchEl.hidden = true;
    }
}

// Wire mismatch warning to main selects
document.getElementById("symbol").addEventListener("change", _updateMismatchWarning);
document.getElementById("timeframe").addEventListener("change", _updateMismatchWarning);
document.getElementById("strategy").addEventListener("change", _updateMismatchWarning);

// Also hide warning after successful chart load
const _origLoadChart = loadChart;
// (loadChart already calls _updateMismatchWarning implicitly via lastLoadedParams update)

// Update mode hint when selector changes
if (labModeSelect) {
    labModeSelect.addEventListener("change", () => {
        if (!labModeHint) return;
        if (labModeSelect.value === "accurate") {
            labModeHint.textContent = "Accurate Mode checks every candle and is capped at 300 bars to prevent timeout.";
        } else {
            labModeHint.textContent = "Fast checks every 15 candles. Accurate checks every candle.";
        }
        _updateLabResultStaleWarning();
    });
}

// ----------------------------------------------------------------
// Run Backtest
// ----------------------------------------------------------------
if (labRunBtn) labRunBtn.addEventListener("click", runStrategyLab);
if (labLogFilter) labLogFilter.addEventListener("change", () => renderTradeLog(_labAllTrades, labLogFilter.value));

function _readLabConfig() {
    const mode = (labModeSelect && labModeSelect.value) || "fast";
    const maxBars = mode === "accurate" ? 300 : 500;
    const barsInput = document.getElementById("lab-bars");
    const requestedBars = Math.max(50, parseInt(barsInput.value, 10) || 300);
    const bars = Math.min(maxBars, requestedBars);

    return {
        symbol: document.getElementById("lab-symbol").value || "EUR/USD",
        timeframe: document.getElementById("lab-timeframe").value || "M15",
        requestedBars,
        bars,
        maxBars,
        balance: parseFloat(document.getElementById("lab-balance").value) || 10000,
        risk: parseFloat(document.getElementById("lab-risk").value) || 1.0,
        mode,
        strategies: [...document.querySelectorAll('input[name="lab-strategy"]:checked')].map(c => c.value),
    };
}

function _setLabResultState(message, state) {
    if (!labResultState) return;
    labResultState.textContent = message;
    labResultState.className = `lab-result-state state-${state}`;
    labResultState.hidden = !message;
}

function clearStrategyLabResults() {
    _labAllTrades = {};
    _labEquityData = {};
    _renderedBacktestIdentity = null;

    labResults.hidden = true;
    labResults.classList.remove("results-stale");
    labBestName.textContent = "—";
    labSummaryText.textContent = "No new results were produced.";
    if (dashboardLabStatus) {
        dashboardLabStatus.textContent = "Research";
        dashboardLabSummary.textContent = "Run Strategy Lab when you want historical context. It never runs automatically.";
    }
    labTableBody.innerHTML = '<tr><td colspan="9" class="lab-table-empty">No results yet.</td></tr>';
    labTradeLogBody.innerHTML = '<tr><td colspan="9" class="lab-table-empty">No trades yet.</td></tr>';
    labRunStatusEl.innerHTML = "";
    labEquityChart.innerHTML = "";
    labEquityLegend.innerHTML = "";
    labTrustSummary.innerHTML = "";
    labTrustSummary.hidden = true;
    labResultIdentity.innerHTML = "";
    labResultIdentity.hidden = true;
    populateLogFilter([]);

    const equityWarning = document.getElementById("lab-equity-warning");
    const tradeCount = document.getElementById("lab-trade-log-count");
    if (equityWarning) equityWarning.hidden = true;
    if (tradeCount) tradeCount.hidden = true;
    if (labBestBadge) labBestBadge.hidden = true;
}

function _sameStrategies(left, right) {
    const a = [...(left || [])].sort();
    const b = [...(right || [])].sort();
    return a.length === b.length && a.every((value, index) => value === b[index]);
}

function _identityMatchesConfig(identity, config) {
    if (!identity || !config) return false;
    return identity.tested_symbol === config.symbol
        && identity.tested_timeframe === config.timeframe
        && Number(identity.tested_bars) === Number(config.bars)
        && Number(identity.requested_bars) === Number(config.requestedBars)
        && identity.tested_mode === config.mode
        && _sameStrategies(identity.tested_strategies, config.strategies);
}

function _renderLabResultIdentity(identity) {
    if (!labResultIdentity || !identity) return;
    const generated = identity.generated_at
        ? new Date(identity.generated_at).toLocaleString()
        : "Unknown";
    const requestedBars = Number(identity.requested_bars) || Number(identity.tested_bars) || 0;
    const testedBars = Number(identity.tested_bars) || 0;
    const barsLabel = requestedBars === testedBars
        ? String(testedBars)
        : `${testedBars} (requested ${requestedBars}; capped)`;
    labResultIdentity.innerHTML = `
        <span>tested_symbol: <strong>${escLab(identity.tested_symbol)}</strong></span>
        <span>tested_timeframe: <strong>${escLab(identity.tested_timeframe)}</strong></span>
        <span>tested_bars: <strong>${barsLabel}</strong></span>
        <span>tested_mode: <strong>${escLab(identity.tested_mode)}</strong></span>
        <span>tested_strategies: <strong>${(identity.tested_strategies || []).map(escLab).join(", ")}</strong></span>
        <span>generated_at: <strong>${escLab(generated)}</strong></span>`;
    labResultIdentity.hidden = false;
}

function _markLabRunFailed(detail) {
    clearStrategyLabResults();
    _pendingBacktestConfig = null;
    _labRunPhase = "failed";
    labStatus.textContent = "Backtest failed or timed out. No new results were produced.";
    _setLabResultState(
        "Backtest failed or timed out. No new results were produced. Previous results are hidden because they do not match the current request.",
        "failed",
    );
    renderLabWarnings(detail ? [detail] : []);
}

function _updateLabResultStaleWarning() {
    if (_labRunPhase !== "complete" || !_renderedBacktestIdentity) return;
    const current = _readLabConfig();
    const stale = !_identityMatchesConfig(_renderedBacktestIdentity, current);
    labResults.classList.toggle("results-stale", stale);
    if (stale) {
        _setLabResultState("Showing previous result. Run Backtest again to update.", "stale");
    } else {
        _setLabResultState("", "stale");
    }
}

[
    document.getElementById("lab-symbol"),
    document.getElementById("lab-timeframe"),
    document.getElementById("lab-bars"),
    ...document.querySelectorAll('input[name="lab-strategy"]'),
].filter(Boolean).forEach(el => el.addEventListener("change", _updateLabResultStaleWarning));
document.getElementById("lab-bars").addEventListener("input", _updateLabResultStaleWarning);

async function runStrategyLab() {
    const config = _readLabConfig();
    const { symbol, timeframe, bars, balance, risk, mode, strategies } = config;

    if (strategies.length === 0) {
        labStatus.textContent = "Select at least one strategy before running.";
        return;
    }

    const modeLabel = mode === "accurate" ? "Accurate Mode" : "Fast Mode";
    const wasCapped = config.requestedBars > bars;
    const capHint = wasCapped ? ` Requested ${config.requestedBars} bars; capped at ${bars}.` : "";
    const ictLoadHint = mode === "accurate" && strategies.includes("ict_2022") && config.requestedBars > 300
        ? " Accurate Mode with ICT and more than 300 requested bars may time out; this run is capped at 300."
        : "";
    const timeHint  = mode === "accurate"
        ? "Accurate Mode evaluates every candle and may take up to 110 s."
        : "This should complete in about 15–30 s.";

    const payload = {
        symbol,
        timeframe,
        bars: config.requestedBars,
        strategies,
        risk_per_trade: risk,
        starting_balance: balance,
        mode,
    };
    console.log("[StrategyLab] payload →", payload);

    const pendingBars = config.requestedBars === bars
        ? String(bars)
        : `${bars} tested (${config.requestedBars} requested; capped)`;
    const pendingConfig = (
        `Pending config — symbol: ${symbol}; timeframe: ${timeframe}; bars: ${pendingBars}; `
        + `mode: ${mode}; selected strategies: ${strategies.join(", ")}.`
    );

    clearStrategyLabResults();
    _pendingBacktestConfig = config;
    _labRunPhase = "running";
    labRunBtn.disabled = true;
    labStatus.textContent = `Running ${modeLabel} on ${symbol} ${timeframe} (${bars} tested bars, ${strategies.length} strategies)… ${timeHint}${capHint}${ictLoadHint}`;
    _setLabResultState(`Running new backtest. ${pendingConfig}${ictLoadHint}`, "running");
    labWarnings.hidden = true;

    // AbortController gives us a hard 120 s browser timeout
    const controller = new AbortController();
    const abortTimer = setTimeout(() => controller.abort(), 120_000);

    try {
        const resp = await fetch("/api/backtest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: controller.signal,
        });

        clearTimeout(abortTimer);

        let data;
        try {
            data = await resp.json();
        } catch (_) {
            _markLabRunFailed("Server returned a non-JSON response. Check the terminal for errors.");
            return;
        }

        console.log("[StrategyLab] response →", data);

        // Error states
        if (!resp.ok || data.ok === false || data.error) {
            const msg = data.error || `Server error ${resp.status}`;
            _markLabRunFailed(`Error: ${msg}`);
            return;
        }

        if (!_identityMatchesConfig(data.result_identity, _pendingBacktestConfig)) {
            _markLabRunFailed("The server returned a result for different settings, so it was not displayed.");
            return;
        }

        // Store for filter interactions
        _labAllTrades  = data.trade_logs || {};
        _labEquityData = data.equity_curves || {};

        // Render all panels
        renderLabWarnings(data.warnings || []);
        renderComparisonTable(data.strategy_results || [], data.run_status || []);
        renderBestSummary(data.comparison || {}, data.metadata);

        // Make results visible BEFORE drawing canvas (need layout)
        labResults.hidden = false;

        // Draw equity chart after layout is available
        requestAnimationFrame(() => renderEquityCurves(_labEquityData));

        renderTradeLog(_labAllTrades, "all");
        populateLogFilter(Object.keys(_labAllTrades));
        renderTrustSummary(data.metadata, data.comparison, data.run_status);
        renderRunStatus(data.run_status || []);
        _renderedBacktestIdentity = data.result_identity;
        _renderLabResultIdentity(_renderedBacktestIdentity);
        _pendingBacktestConfig = null;
        _labRunPhase = "complete";
        _setLabResultState("", "running");

        // Badge using result_status
        const resultStatus = (data.comparison || {}).result_status || "no_data";
        const best = (data.comparison || {}).best_strategy;
        const bestTrades = (best || {}).total_trades || 0;
        if (bestTrades > 0) {
            if (resultStatus === "confirmed") {
                labBestBadge.textContent = `Best performer: ${best.strategy}`;
            } else {
                labBestBadge.textContent = `Early leader — weak sample: ${best.strategy}`;
            }
            labBestBadge.hidden = false;
        } else {
            labBestBadge.hidden = true;
        }

        // Status summary
        const totalClosed = (data.strategy_results || []).reduce((s, m) => s + (m.total_trades || 0), 0);
        if (totalClosed === 0) {
            labStatus.textContent = `Backtest complete — no valid trades were found. Try more bars or a different timeframe.`;
        } else {
            labStatus.textContent = `Backtest complete. ${totalClosed} closed trades across ${strategies.length} strategies.`;
        }

    } catch (err) {
        if (err.name === "AbortError") {
            _markLabRunFailed("Backtest timed out after 120 seconds. Try fewer bars or fewer strategies.");
        } else {
            _markLabRunFailed(`Network error: ${err.message}`);
        }
        console.error("[StrategyLab] fetch error", err);
    } finally {
        clearTimeout(abortTimer);
        labRunBtn.disabled = false;
    }
}

// ----------------------------------------------------------------
// Render: warnings
// ----------------------------------------------------------------
function renderLabWarnings(warnings) {
    if (!warnings || !warnings.length) { labWarnings.hidden = true; return; }
    labWarnings.innerHTML = "<ul>" + warnings.map(w => `<li>${escLab(w)}</li>`).join("") + "</ul>";
    labWarnings.hidden = false;
}

// ----------------------------------------------------------------
// Render: comparison table (includes Not Tested rows from run_status)
// ----------------------------------------------------------------

function _sampleLabel(trades) {
    if (trades === 0) return "No Sample";
    if (trades < 10) return "Insufficient Data";
    if (trades < 20) return "Weak Sample";
    if (trades < 50) return "Usable Sample";
    return "Stronger Sample";
}

function _fmtPF(m) {
    const pf  = m.profit_factor || 0;
    const inf = m.profit_factor_infinite;
    const n   = m.total_trades || 0;
    if (inf && n < 20) return `<span title="${escLab(m.profit_factor_display_hint || 'No losses yet — sample too small.')}">N/A</span>`;
    if (inf)           return `<span title="${escLab(m.profit_factor_display_hint || 'No losing trades in sample.')}">Very high</span>`;
    if (pf >= 999)     return n < 20 ? "N/A" : "Very high";
    return pf.toFixed(2);
}

function renderComparisonTable(results, runStatus) {
    const statusMap = {};
    (runStatus || []).forEach(s => { statusMap[s.key] = s; });

    const rows = [];

    // Selected+ran strategies (with metrics)
    (results || []).forEach((m, i) => {
        const noTrades = (m.total_trades || 0) === 0;
        const sq = escLab(m.sample_quality || _sampleLabel(m.total_trades || 0));

        const pfHtml = noTrades ? "—" : _fmtPF(m);
        const pfRaw  = m.profit_factor || 0;
        const pfClass = (!noTrades && !m.profit_factor_infinite && pfRaw >= 1.3) ? "lab-cell-win"
            : (!noTrades && pfRaw > 0 && pfRaw < 1) ? "lab-cell-loss" : "";

        const expRaw   = m.expectancy || 0;
        const expClass = expRaw > 0 ? "lab-cell-win" : expRaw < 0 ? "lab-cell-loss" : "";
        const expText  = noTrades ? "—" : (expRaw >= 0 ? "+" : "") + expRaw.toFixed(3) + "R";
        const ddRaw    = m.max_drawdown || 0;

        // Rating column: sample quality label + ran/not
        const ratingText = noTrades ? `Ran — 0 trades` : sq;
        const ratingCls  = noTrades ? "lab-cell-neutral"
            : (m.total_trades || 0) < 10 ? "lab-cell-loss"
            : (m.total_trades || 0) < 20 ? "lab-cell-neutral"
            : m.rating === "Strong" ? "lab-cell-win"
            : m.rating === "Avoid"  ? "lab-cell-loss"
            : "";

        // Reason column from run_status
        const statusEntry = statusMap[m.strategy_key] || {};
        const reason = escLab((statusEntry.main_reason || m.main_reason || "").substring(0, 80));

        const isBestRow = i === 0 && !noTrades && (m.total_trades || 0) >= 20;

        rows.push(`<tr class="${isBestRow ? "lab-best-row" : ""}">
            <td>${escLab(m.strategy)}</td>
            <td>${m.total_trades || 0}</td>
            <td>${noTrades ? "—" : (m.win_rate || 0).toFixed(1) + "%"}</td>
            <td class="${pfClass}">${pfHtml}</td>
            <td class="${noTrades ? "" : expClass}">${expText}</td>
            <td>${noTrades ? "—" : ddRaw.toFixed(2) + "R"}</td>
            <td>${noTrades ? "—" : (m.average_rr || 0).toFixed(3) + "R"}</td>
            <td class="${ratingCls}">${ratingText}</td>
            <td class="lab-cell-neutral lab-reason-cell" title="${reason}">${reason || "—"}</td>
        </tr>`);
    });

    // Not-tested strategies (from run_status)
    (runStatus || []).forEach(s => {
        if (s.selected) return;
        const reason = escLab((s.main_reason || "").substring(0, 80));
        rows.push(`<tr class="lab-not-tested-row">
            <td>${escLab(s.strategy)}</td>
            <td>—</td>
            <td colspan="6" class="lab-cell-neutral" style="font-style:italic;">Not Tested — checkbox was off</td>
            <td class="lab-cell-neutral lab-reason-cell">${reason}</td>
        </tr>`);
    });

    if (!rows.length) {
        labTableBody.innerHTML = '<tr><td colspan="9" class="lab-table-empty">No strategy results returned.</td></tr>';
        return;
    }

    labTableBody.innerHTML = rows.join("");
}

// ----------------------------------------------------------------
// Render: best strategy summary card
// ----------------------------------------------------------------
function renderBestSummary(comparison, meta) {
    if (!comparison) return;
    const best    = comparison.best_strategy;
    const baseSummary = comparison.summary || "Run a backtest to compare strategies.";
    const resultStatus = comparison.result_status || "no_data";

    const approximate = meta && meta.approximate;
    const bestTrades = (best || {}).total_trades || 0;
    const bestExp    = (best || {}).expectancy   || 0;
    const bestPf     = (best || {}).profit_factor || 0;

    let qualifyText = "";
    if (approximate && bestTrades > 0) {
        qualifyText = " Use Accurate Mode to confirm before trusting this result.";
    } else if (!approximate && meta && bestTrades > 0 && bestExp > 0 && bestPf > 1.3 && bestTrades >= 20) {
        qualifyText = " Accurate Mode — result confirmed with sufficient sample size.";
    }

    labSummaryText.textContent = baseSummary + qualifyText;
    if (dashboardLabSummary) {
        dashboardLabSummary.textContent = baseSummary + qualifyText;
    }

    if (bestTrades === 0 || resultStatus === "no_data" || resultStatus === "insufficient") {
        labBestName.textContent = "No winner — insufficient data";
        if (dashboardLabStatus) dashboardLabStatus.textContent = "No winner";
    } else if (resultStatus === "early_leader" || bestTrades < 20) {
        labBestName.textContent = `Early leader — weak sample: ${(best || {}).strategy || "—"}`;
        if (dashboardLabStatus) dashboardLabStatus.textContent = "Early leader";
    } else {
        labBestName.textContent = `Best performer — usable sample: ${(best || {}).strategy || "—"}`;
        if (dashboardLabStatus) dashboardLabStatus.textContent = "Usable sample";
    }
}

// ----------------------------------------------------------------
// Render: trust summary card
// ----------------------------------------------------------------
function renderTrustSummary(meta, comparison, runStatus) {
    if (!labTrustSummary || !meta) return;

    const approximate = meta.approximate;
    const modeLabel   = approximate
        ? "Fast Mode — approximate results"
        : "Accurate Mode — more thorough evaluation";
    const badge       = approximate ? "Approximate" : "Candle-by-candle";
    const badgeClass  = approximate ? "lab-badge-approx" : "lab-badge-accurate";

    const total    = meta.total_candles     || 0;
    const evaled   = meta.evaluated_candles || 0;
    const coverage = total > 0 ? Math.round((evaled / total) * 100) : 0;
    const stepText = meta.strategy_step === 1 ? "Every candle" : `Every ${meta.strategy_step} candles`;

    // Aggregate sample info
    const totalClosed = (runStatus || []).reduce((s, r) => s + (r.trades_found || 0), 0);
    const resultStatus = (comparison || {}).result_status || "no_data";
    const resultStatusLabel = {
        "no_data": "Not enough data to rank strategies",
        "insufficient": "Insufficient sample — no winner",
        "early_leader": "Early indication only — small sample",
        "confirmed": "Adequate sample — result is directionally reliable",
    }[resultStatus] || "Unknown";
    const sqLabel = _sampleLabel(totalClosed);

    labTrustSummary.innerHTML = `
        <div class="lab-trust-header">
            <span class="lab-trust-label">Backtest Trust</span>
            <span class="lab-trust-badge ${badgeClass}">${escLab(badge)}</span>
        </div>
        <dl class="lab-trust-grid">
            <div><dt>Mode</dt><dd>${escLab(modeLabel)}</dd></div>
            <div><dt>Signal Scan</dt><dd>${escLab(stepText)}</dd></div>
            <div><dt>Analysis Window</dt><dd>${meta.analysis_window || "—"} candles</dd></div>
            <div><dt>Signal Evaluations</dt><dd>${evaled} / ${total} candles (${coverage}% coverage)</dd></div>
            <div><dt>Closed Trades</dt><dd>${totalClosed}</dd></div>
            <div><dt>Sample Quality</dt><dd>${escLab(sqLabel)}</dd></div>
            <div><dt>Result Status</dt><dd>${escLab(resultStatusLabel)}</dd></div>
        </dl>
    `;
    labTrustSummary.hidden = false;
}


function renderEquityCurves(curves) {
    if (!labEquityChart) return;
    labEquityChart.innerHTML = "";
    if (labEquityLegend) labEquityLegend.innerHTML = "";

    // Count total closed trades and show small-sample warning
    const totalClosed = Object.values(curves || {}).reduce(
        (sum, pts) => sum + (pts || []).filter(p => p.trade > 0).length, 0
    );
    const warnEl = document.getElementById("lab-equity-warning");
    if (warnEl) {
        if (totalClosed === 0) {
            warnEl.textContent = "No closed trades — equity curve is not available.";
            warnEl.hidden = false;
        } else if (totalClosed < 20) {
            warnEl.textContent = `Equity curve is based on only ${totalClosed} closed trade${totalClosed !== 1 ? "s" : ""}. This is not enough data to judge performance.`;
            warnEl.hidden = false;
        } else {
            warnEl.hidden = true;
        }
    }

    const keys = Object.keys(curves || {});

    // Check if there's any data to draw
    const hasData = keys.some(k => (curves[k] || []).filter(p => p.trade > 0).length > 0);
    if (!hasData) {
        labEquityChart.innerHTML = '<p style="text-align:center;color:var(--muted);padding:80px 0;margin:0;">No equity curve available — no closed trades in this backtest.</p>';
        return;
    }

    const W = labEquityChart.offsetWidth || labEquityChart.clientWidth || 800;
    const H = 220;
    const PAD = { top: 16, right: 20, bottom: 28, left: 68 };

    const canvas = document.createElement("canvas");
    canvas.className = "lab-equity-canvas";
    canvas.width  = W;
    canvas.height = H;
    labEquityChart.appendChild(canvas);

    const ctx = canvas.getContext("2d");

    // Y range across all series
    const allBalances = keys.flatMap(k => (curves[k] || []).map(p => p.balance));
    const minB   = Math.min(...allBalances);
    const maxB   = Math.max(...allBalances);
    const bRange = maxB - minB || 1;

    // Grid lines
    ctx.strokeStyle = "rgba(212,175,55,0.10)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = PAD.top + (H - PAD.top - PAD.bottom) * (i / 4);
        ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y); ctx.stroke();
        const label = (maxB - bRange * (i / 4)).toLocaleString("en-US", { maximumFractionDigits: 0 });
        ctx.fillStyle = "rgba(167,158,135,0.75)";
        ctx.font = "10px Inter,Arial,sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(label, PAD.left - 4, y + 4);
    }

    // Plot each strategy
    keys.forEach((key) => {
        const points = (curves[key] || []);
        if (points.length < 2) return;

        const color    = LAB_STRATEGY_COLORS[key] || "#aaa";
        const maxTrade = Math.max(...points.map(p => p.trade));
        if (maxTrade === 0) return;

        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.lineJoin = "round";

        points.forEach((p, idx) => {
            const x = PAD.left + (W - PAD.left - PAD.right) * (p.trade / maxTrade);
            const y = PAD.top  + (H - PAD.top - PAD.bottom) * (1 - (p.balance - minB) / bRange);
            if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Legend entry
        if (labEquityLegend) {
            const item = document.createElement("span");
            item.className = "lab-equity-legend-item";
            item.innerHTML = `<span class="lab-equity-legend-dot" style="background:${color}"></span>${escLab(key.replace(/_/g, " "))}`;
            labEquityLegend.appendChild(item);
        }
    });

    // X-axis label
    ctx.fillStyle = "rgba(167,158,135,0.55)";
    ctx.font = "10px Inter,Arial,sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Trades →", W / 2, H - 5);
}

// ----------------------------------------------------------------
// Render: trade log
// ----------------------------------------------------------------
function renderTradeLog(tradeLogs, filter) {
    if (!labTradeLogBody) return;

    const rows = [];
    Object.entries(tradeLogs || {}).forEach(([key, trades]) => {
        if (filter !== "all" && key !== filter) return;
        (trades || []).forEach(t => rows.push(t));
    });

    rows.sort((a, b) => (a.entry_time || 0) - (b.entry_time || 0));

    // Show trade count warning above log
    const tradeLogHeader = document.getElementById("lab-trade-log-count");
    if (tradeLogHeader) {
        const closed = rows.filter(t => t.result !== "OPEN_AT_END").length;
        if (closed === 0) {
            tradeLogHeader.textContent = "No closed trades in this selection.";
        } else if (closed < 20) {
            tradeLogHeader.textContent = `Showing ${closed} closed trade${closed !== 1 ? "s" : ""}. More trades are needed before comparing strategies reliably.`;
        } else {
            tradeLogHeader.textContent = `${closed} closed trades.`;
        }
        tradeLogHeader.hidden = false;
    }

    if (!rows.length) {
        labTradeLogBody.innerHTML = '<tr><td colspan="9" class="lab-table-empty">No trades for this selection.</td></tr>';
        return;
    }

    labTradeLogBody.innerHTML = rows.map(t => {
        const resClass = t.result === "TP1" ? "lab-cell-win"
            : t.result === "TP2" ? "lab-cell-tp2"
            : t.result === "SL"  ? "lab-cell-loss"
            : "lab-cell-neutral";
        const rrClass  = (t.rr_result || 0) > 0 ? "lab-cell-win"
            : (t.rr_result || 0) < -0.9 ? "lab-cell-loss"
            : "lab-cell-neutral";
        const dirClass = t.direction === "Bullish" ? "lab-cell-win" : "lab-cell-loss";

        const entryMs  = (t.entry_time || 0) * 1000;
        const timeStr  = entryMs > 0
            ? new Date(entryMs).toLocaleString("en-GB", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" })
            : "—";

        return `<tr>
            <td title="${escLab(t.strategy)}">${escLab((t.strategy || "").split(" ").slice(0,2).join(" "))}</td>
            <td class="${dirClass}">${t.direction === "Bullish" ? "▲ Long" : "▼ Short"}</td>
            <td>${timeStr}</td>
            <td>${fmtPrice(t.entry)}</td>
            <td>${fmtPrice(t.stop_loss)}</td>
            <td>${fmtPrice(t.tp1)}</td>
            <td>${fmtPrice(t.exit_price)}</td>
            <td class="${resClass}">${escLab(t.result || "—")}</td>
            <td class="${rrClass}">${(t.rr_result || 0) >= 0 ? "+" : ""}${(t.rr_result || 0).toFixed(2)}R</td>
        </tr>`;
    }).join("");
}

// ----------------------------------------------------------------
// Render: Strategy Run Status cards
// ----------------------------------------------------------------
function renderRunStatus(runStatus) {
    if (!labRunStatusEl) return;
    if (!runStatus || !runStatus.length) {
        labRunStatusEl.innerHTML = "";
        return;
    }

    labRunStatusEl.innerHTML = runStatus.map(s => {
        const ran = s.ran;
        const trades = s.trades_found || 0;
        const cardClass = ran ? (trades > 0 ? "card-ran" : "card-ran") : "card-not-tested";

        let pillHtml;
        if (!ran) {
            pillHtml = `<span class="lab-status-pill pill-not-tested">Not Tested</span>`;
        } else if (trades === 0) {
            pillHtml = `<span class="lab-status-pill pill-no-trades">Ran · 0 trades</span>`;
        } else {
            pillHtml = `<span class="lab-status-pill pill-ran">Ran · ${trades} trade${trades !== 1 ? "s" : ""}</span>`;
        }

        let statsHtml = "";
        if (ran) {
            const diag = s.diagnostics || {};
            statsHtml = `<dl class="lab-status-card-stats">
                <div><dt>Candles</dt><dd>${s.candles_checked || 0}</dd></div>
                <div><dt>Evaluations</dt><dd>${s.evaluation_count || 0}</dd></div>
                <div><dt>Trades opened</dt><dd>${s.trades_opened || 0}</dd></div>
                <div><dt>Trades closed</dt><dd>${s.trades_closed || 0}</dd></div>
                <div><dt>Setups found</dt><dd>${diag.potential_setups || 0}</dd></div>
                <div><dt>Missed entries</dt><dd>${diag.missed_entries || 0}</dd></div>
            </dl>`;
        }

        const reasonHtml = `<p class="lab-status-card-reason">${escLab(s.main_reason || "")}</p>`;

        let ictNoteHtml = "";
        if (s.ict_note) {
            ictNoteHtml = `<p class="lab-status-ict-note">${escLab(s.ict_note)}</p>`;
        }

        return `<div class="lab-status-card ${cardClass}">
            <div class="lab-status-card-header">
                <span class="lab-status-card-name">${escLab(s.strategy)}</span>
                ${pillHtml}
            </div>
            ${statsHtml}
            ${reasonHtml}
            ${ictNoteHtml}
        </div>`;
    }).join("");
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------
function populateLogFilter(keys) {
    if (!labLogFilter) return;
    labLogFilter.innerHTML = '<option value="all">All strategies</option>';
    (keys || []).forEach(k => {
        const opt = document.createElement("option");
        opt.value = k;
        opt.textContent = k.replace(/_/g, " ");
        labLogFilter.appendChild(opt);
    });
}

function fmtPrice(v) {
    if (v === null || v === undefined) return "—";
    const n = parseFloat(v);
    return isNaN(n) ? "—" : n.toFixed(5);
}

function escLab(s) {
    return String(s || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}
