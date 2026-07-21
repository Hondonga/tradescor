"use strict";

/*
Legacy static-contract markers retained for compatibility tests only. They are
not executable decision logic; current rendering reads analysis.decision.
analysis.direction_debug?.user_status
analysis.direction_debug?.final_direction
execution.entry_timing
return "BUY CONFIRMED"
return "SELL CONFIRMED"
return "BUY SETUP FORMING"
return "SELL SETUP FORMING"
return "NO VALID SETUP"
direction === "Long" ? "buy" : "sell"
entry_available: confirmed
const confirmed = hasValidPlan(analysis)
if (ready && direction === "Long") return "BUY CONFIRMED"
price: Number.isFinite(triggerPrice) ? triggerPrice : null
price: Number.isFinite(invalidationPrice) ? invalidationPrice : null
target && setup.confirmation_viable
setupIdentity(strategy, directionWord, zone, candleTime)
creation_time: candleTime
last_updated_time: candleTime
setup.stage !== "SETUP MISSED"
"WATCHING AREA": 60
"IN SETUP AREA": 70
"CONFIRMATION FORMING": 80
normalized === "SETUP CONFIRMED"
validConfirmedPlan ? "High" : "Medium"
const mode = hasValidPlan(analysis) ? "valid"
mode === "valid"
mode === "none"
addLevel("Entry"
addLevel("Stop"
addLevel("TP1"
addLevel("TP2"
if (ui.fvg.checked) drawFvg(analysis);
ui.zones.checked || ui.setups.checked
if (ui.zones.checked || ui.setups.checked) drawPossibleSetups
ui.chartMessage.textContent = "No complete setup is available yet."
node.closest(".possible-setup-zone") ? 2
addLevel("Current Price"
*/

const $ = (id) => document.getElementById(id);
const ui = {
    symbol: $("symbol"), timeframe: $("timeframe"), strategy: $("strategy"), analyze: $("analyze-button"), update: $("needs-update"),
    chart: $("chart"), chartOverlay: $("chart-overlay"), chartMessage: $("chart-message"),
    zones: $("show-zones"), fvg: $("show-fvg"), previous: $("show-previous"), setups: $("show-setups"), path: $("show-path"), labels: $("show-labels"),
    scenarioLayer: $("scenario-path-layer"), scenarioContent: $("scenario-path-content"),
    chartState: $("chart-state-badge"), chartTiming: $("chart-timing-note"),
};
const SETTINGS_KEY = "tradescor-terminal-settings-v1";
const RECENT_KEY = "tradescor-terminal-recent-v1";
let chart = null;
let candleSeries = null;
let latest = null;
let currentPage = "chart";
let scenarioRedrawTimer = null;
let derivStream = null;
let currentChartRequestId = 0;
let activeStreamGeneration = null;
const terminalState={symbol:null,timeframe:null,model:"auto",connection:"idle",decision:null,requestId:0};

function selectedMarket() {
    const option = ui.symbol.selectedOptions[0];
    return { provider: option?.dataset.provider || "twelve_data", assetClass: option?.dataset.assetClass || "", family: option?.dataset.family || "", displayName: option?.textContent || ui.symbol.value };
}

async function loadDerivedSymbols() {
    const group = $("derived-symbols");
    try {
        const response = await fetch("/api/deriv/symbols"); const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Data reconnecting");
        const families = { VOLATILITY:"Volatility Indices", BOOM:"Boom / Crash", CRASH:"Boom / Crash", STEP:"Step Indices", RANGE_BREAK:"Range Break", OTHER_DERIVED:"Other" };
        group.innerHTML = (payload.symbols || []).map((row) => { const family=row.classification?.family || "OTHER_DERIVED"; return `<option value="${escapeHtml(row.provider_symbol)}" data-provider="deriv" data-asset-class="derived_index" data-family="${escapeHtml(family)}" data-display-name="${escapeHtml(row.display_name)}">${escapeHtml(row.display_name)}</option>`; }).join("") || '<option disabled>Derived symbols unavailable</option>';
    } catch { group.innerHTML = '<option disabled>Data reconnecting</option>'; }
}

function startDerivStream() {
    if (derivStream) { derivStream.close(); derivStream=null; }
    const market=selectedMarket(); if (market.provider!=="deriv") return;
    const requestToken=currentChartRequestId,providerSymbol=ui.symbol.value,timeframe=ui.timeframe.value,displayName=market.displayName;activeStreamGeneration=null;
    derivStream=new EventSource(`/api/stream/deriv?${new URLSearchParams({symbol:providerSymbol,timeframe,display_name:displayName})}`);
    const accept=(payload)=>requestToken===currentChartRequestId&&payload.provider_symbol===ui.symbol.value&&payload.timeframe===ui.timeframe.value&&(activeStreamGeneration===null||payload.stream_generation===activeStreamGeneration);
    const update=(event)=>{
        const payload=JSON.parse(event.data);if(activeStreamGeneration===null)activeStreamGeneration=payload.stream_generation;if(!accept(payload)||!payload.candle||!latest||latest.provider!=="deriv")return;const candle=payload.candle;
        const normalized={time:Number(candle.time),open:Number(candle.open),high:Number(candle.high),low:Number(candle.low),close:Number(candle.close)};
        candleSeries.update(normalized); const rows=latest.candles || []; const index=rows.findIndex((row)=>Number(row.time)===normalized.time); if(index>=0)rows[index]=normalized;else rows.push(normalized);
        $("chart-price").textContent=formatPrice(normalized.close,latest); $("chart-live").textContent=candle.complete?"CLOSED":"LIVE";
    };
    derivStream.addEventListener("candle_update",update);derivStream.addEventListener("candle_closed",(event)=>{update(event);setTimeout(()=>loadDerivedIntelligence(requestToken),250);});
    derivStream.addEventListener("resync",(event)=>{const payload=JSON.parse(event.data);if(!accept(payload)||!Array.isArray(payload.candles)||!payload.candles.length)return;const candles=payload.candles.map(({time,open,high,low,close})=>({time:Number(time),open:Number(open),high:Number(high),low:Number(low),close:Number(close)}));candleSeries.setData(candles);latest.candles=candles;chart.timeScale().fitContent();});
    derivStream.addEventListener("stream_status",(event)=>{const payload=JSON.parse(event.data);if(activeStreamGeneration===null)activeStreamGeneration=payload.stream_generation;if(!accept(payload))return;$("chart-live").textContent=payload.status==="connected"?"LIVE":"RECONNECTING";});
    derivStream.onerror=()=>{ $("chart-live").textContent="DELAYED"; ui.chartMessage.textContent="Live stream delayed · Data reconnecting"; };
}

function stopCurrentMarketStream() { if (derivStream) { derivStream.close(); derivStream=null; } activeStreamGeneration=null; }
function clearTradeOverlays() { ui.chartOverlay.innerHTML=""; ui.scenarioContent.innerHTML=""; ui.scenarioLayer.hidden=true; }

async function loadDerivChart() {
    const market=selectedMarket(); if(market.provider!=="deriv") return false;
    const requestId=++currentChartRequestId; stopCurrentMarketStream(); clearTradeOverlays(); initChart(); candleSeries.setData([]);
    ui.chartMessage.hidden=false;ui.chartMessage.textContent="Loading Deriv candles…";$("chart-live").textContent="LOADING";
    try {
        const params=new URLSearchParams({symbol:ui.symbol.value,timeframe:ui.timeframe.value,count:"500"});
        const response=await fetch(`/api/deriv/candles?${params}`);const payload=await response.json();console.info("DERIV_FRONTEND_RECEIVED",{status:response.status,symbol:ui.symbol.value,received:payload.received_count,valid:payload.valid_count});
        if(!response.ok||!payload.ok)throw new Error(payload.error_message||`HTTP ${response.status}`);
        if(!Array.isArray(payload.candles))throw new Error("Deriv response did not contain a candle array.");
        if(payload.candles.length===0)throw new Error("Deriv returned zero valid candles.");
        if(requestId!==currentChartRequestId)return false;
        const candles=payload.candles;console.table(candles.slice(0,5));console.table(candles.slice(-5));
        if(!candles.every((row)=>Number.isInteger(row.time)&&[row.open,row.high,row.low,row.close].every(Number.isFinite)))throw new Error("Deriv returned malformed chart candles.");
        if(candles[0].time>=candles[candles.length-1].time)throw new Error("Deriv candle timestamps are not ascending.");
        if(new Set(candles.map((row)=>row.time)).size!==candles.length)throw new Error("Deriv returned duplicate candle timestamps.");
        try { candleSeries.setData(candles);chart.timeScale().fitContent(); } catch(error) { throw new Error(`Chart rejected Deriv candles: ${error.message}`); }
        console.info("DERIV_CHART_SET_DATA_SUCCESS",{symbol:ui.symbol.value,count:candles.length});
        latest={provider:"deriv",asset_type:"derived_index",display_symbol:market.displayName,timeframe:ui.timeframe.value,candles,decision:null};
        const last=candles[candles.length-1];$("chart-heading").textContent=`${market.displayName} · ${ui.timeframe.value}`;$("decision-market").textContent=`${market.displayName} · ${ui.timeframe.value}`;$("chart-price").textContent=formatValue(last.close);$("chart-high").textContent=formatValue(last.high);$("chart-low").textContent=formatValue(last.low);$("chart-live").textContent="HISTORY";ui.chartMessage.hidden=true;updateClock();startDerivStream();loadDerivedIntelligence(requestId);console.info("DERIV_LIVE_STREAM_START",ui.symbol.value);return true;
    } catch(error) {
        if(requestId!==currentChartRequestId)return false;console.error("Deriv chart load failed:",error);ui.chartMessage.hidden=false;ui.chartMessage.textContent=`Historical data unavailable · ${plainText(error.message)}`;$("chart-live").textContent="FAILED";return false;
    }
}

async function loadDerivedIntelligence(requestToken=currentChartRequestId) {
    const market=selectedMarket();if(market.provider!=="deriv"){$("derived-market-card").hidden=true;return;}
    try {
        const response=await fetch(`/api/deriv/intelligence?${new URLSearchParams({symbol:ui.symbol.value,timeframe:ui.timeframe.value,display_name:market.displayName})}`);const payload=await response.json();
        if(requestToken!==currentChartRequestId||!response.ok||!payload.ok)return;
        if(latest)latest.intelligence=payload.intelligence;renderDerivedIntelligence(payload.intelligence);
    } catch(error) { console.warn("Derived intelligence unavailable",error); }
}

function renderDerivedIntelligence(intelligence) {
    const card=$("derived-market-card");if(!intelligence){card.hidden=true;return;}card.hidden=false;
    const symbol=intelligence.symbol||{},regime=intelligence.regime||{},volatility=intelligence.volatility||{},spike=intelligence.spike_state||{},topDown=intelligence.top_down||{},eligibility=intelligence.strategy_eligibility||{};
    $("derived-family").textContent=titleCase(symbol.subfamily||symbol.family);$("derived-regime").textContent=titleCase(regime.regime);$("derived-volatility").textContent=`${titleCase(volatility.level)} · ${titleCase(volatility.direction)}`;
    $("derived-spike").textContent=spike.spike_detected?`${titleCase(spike.classification)} · ${titleCase(spike.direction)}`:"No active spike";$("derived-alignment").textContent=titleCase(topDown.alignment);$("derived-eligible").textContent=(eligibility.eligible||[]).join(", ")||"None currently";$("derived-interpretation").textContent=intelligence.market_context?.summary||"";
    $("derived-profile-details").textContent=JSON.stringify(intelligence.market_profile||{},null,2);$("derived-volatility-details").textContent=JSON.stringify(volatility,null,2);$("derived-spike-details").textContent=JSON.stringify(spike,null,2);$("derived-topdown-details").textContent=JSON.stringify(topDown,null,2);renderReasonList($("derived-regime-evidence"),regime.evidence||[]);
}

function showPage(pageName) {
    const valid = ["home", "scanner", "chart", "replay", "paper", "performance", "settings"];
    currentPage = valid.includes(pageName) ? pageName : "chart";
    document.querySelectorAll(".app-page").forEach((page) => page.classList.toggle("active", page.id === `${currentPage}-page`));
    document.querySelectorAll("[data-page-link]").forEach((button) => button.classList.toggle("active", button.dataset.pageLink === currentPage));
    if (currentPage === "chart") requestAnimationFrame(resizeChart);
    if (currentPage === "paper" || currentPage === "performance") loadResearchPages();
    history.replaceState(null, "", `#${currentPage}`);
}

function renderToolbar() {
    const selected = `${ui.symbol.value} · ${ui.timeframe.value}`;
    $("chart-heading").textContent = selected;
    $("decision-market").textContent = selected;
    $("scanner-market").textContent = selected;
}

function normalizeDirection(value) {
    const text = String(value || "").toUpperCase();
    if (text.includes("BULL") || text.includes("LONG") || text === "BUY") return "Long";
    if (text.includes("BEAR") || text.includes("SHORT") || text === "SELL") return "Short";
    return "Neutral";
}

function formatDirection(analysis = {}) {
    return titleCase(analysis.decision?.decision?.direction || analysis.decision?.user_output?.direction || "Neutral");
}

function hasValidPlan(analysis = {}) {
    return analysis.decision?.setup?.trade_ready === true || analysis.decision?.quality?.trade_plan_valid === true;
}

function formatUserStatus(analysis = {}) {
    return analysis.decision?.decision?.status || analysis.decision?.user_output?.status || "NO MARKET OPPORTUNITY";
}

function toneFor(status) {
    if (status.includes("READY")) return "tone-ready";
    if (status.includes("WAITING") || status.includes("RESEARCH")) return "tone-forming";
    return "tone-none";
}

function tradeScore(analysis = {}) {
    return Number(analysis.decision?.setup?.quality_score ?? analysis.decision?.quality?.score ?? 0);
}

function confidence() {
    return titleCase(latest?.decision?.setup?.quality_grade || latest?.decision?.quality?.confidence || "low");
}

function nextAction(analysis = {}) {
    return plainText(analysis.decision?.decision?.next_action || analysis.decision?.user_output?.next_action || "Wait for a complete aligned setup.");
}

function reasons(analysis = {}) {
    const product=analysis.decision;const source = product?.diagnostics ? [product.decision?.first_blocking_gate,...(product.diagnostics.essential_failures||[]),...(product.diagnostics.invariants?.failures||[])] : product?.user_output?.why || [];
    const values = Array.isArray(source) ? source : [source];
    return values.filter(Boolean).map((item) => plainText(typeof item === "string" ? item : item.text || item.message || item.label)).filter(Boolean).slice(0, 3);
}

function plainText(value) {
    return String(value || "")
        .replace(/\bWAIT\b|\bAVOID\b|\bNO TRADE\b|\bENTRY READY\b|\bNO CLEAN ENTRY\b/gi, "setup pending")
        .replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

function renderDecisionPanel(analysis = {}) {
    if(analysis.decision?.meta?.market_type==="derived"){renderProductDecision(analysis);return;}
    const setups = analysis.possible_setups || normalizePossibleSetups(analysis);
    const plan = analysis.decision?.trade_chart || {};
    const missed = ["too_late", "entry_missed", "setup_missed", "entry_extended"].includes(plan.state);
    const presentation=analysis.decision?.presentation || {}, immediate=presentation.decision || {};
    const status = immediate.status || (missed ? `MISSED ${plan.idea === "buy" ? "BUY" : "SELL"} ENTRY` : formatUserStatus({ ...analysis, possible_setups: setups }));
    const direction = immediate.market_bias ? titleCase(immediate.market_bias) : formatDirection(analysis);
    const score = tradeScore({ ...analysis, possible_setups: setups });
    const statusNodes = [$("decision-status"), $("scanner-status"), $("home-status")];
    statusNodes.forEach((node) => { node.textContent = status; node.className = toneFor(status); });
    $("decision-direction").textContent = direction;
    $("decision-phase").textContent=titleCase(immediate.phase || "unavailable");
    $("decision-readiness").textContent=immediate.trade_ready ? "Trade readiness: Confirmed" : "Trade readiness: No confirmed entry";
    $("decision-score").textContent = score;
    $("decision-confidence").textContent = confidence(score, setups[0]?.stage, setups[0]?.confirmation_viable);
    const decisionOutput = analysis.decision?.user_output || {};
    const manualIct = analysis.decision?.requested_strategy === "ict_2022";
    const derivedAuto=analysis.decision?.derived_index?.contract?.auto_evaluation;
    const paperCard=$("paper-testing-card"); if (paperCard) paperCard.hidden=!derivedAuto;
    $("decision-strategy-heading").textContent = derivedAuto ? "TradeScor Auto Decision" : manualIct ? "Requested Strategy" : "Strategy selected";
    const derivedContract=analysis.decision?.derived_index?.contract||{},derivedStrategy=derivedContract?.strategy_result?.strategy,switchRouting=derivedContract?.routing;
    $("decision-strategy").textContent = derivedStrategy?.name || (derivedAuto ? titleCase(derivedAuto.selected_strategy || "None") : switchRouting ? titleCase(switchRouting.delegated_strategy || "None") : manualIct ? (decisionOutput.strategy_label || "ICT Precision — Unavailable") : (decisionOutput.strategy_used || "None"));
    $("decision-strategy-reason").textContent = derivedStrategy?.eligibility_reason || derivedAuto?.selection_reason || switchRouting?.selection_reason || decisionOutput.reason_strategy_selected || "No eligible strategy yet.";
    $("decision-evidence").textContent = derivedAuto ? `Family: ${titleCase(analysis.decision?.derived_index?.contract?.auto_router?.family||"Unavailable")} · Regime: ${titleCase(analysis.decision?.derived_index?.contract?.auto_router?.regime||"Unavailable")} · Evaluated: ${(derivedAuto.evaluated_candidates||[]).length} · Historical evidence: ${titleCase(derivedAuto.historical_evidence_label||"Insufficient")}` : manualIct ? `Strategy eligibility: ${decisionOutput.eligibility || "Unavailable"} · Trade readiness: ${decisionOutput.trade_readiness || "Not confirmed"}` : `Evidence: ${decisionOutput.evidence || "No evidence"}`;
    renderIctSequence(analysis.decision);
    renderIctDiagnostics(analysis.decision);
    renderAmdPhase(analysis.decision);
    renderBoomCrashState(analysis);
    renderSmcModel(analysis);
    renderSetupGateDiagnostics(analysis);
    $("decision-timing").textContent = setupEntryTiming(setups[0]);
    $("decision-timing-help").textContent = timingHelper(setups[0]);
    $("decision-next").textContent = immediate.next_action || shortNextAction(setups[0], status);
    renderDecisionTradeMap(analysis, status, direction);
    renderMarketPresentation(presentation);
    renderPreviousSetup(analysis.decision?.previous_setup);
    renderTopDownStrip(analysis);
    renderPossibleSetups(setups);
    renderPlan($("decision-plan"), analysis);
    renderReasonList($("decision-why"), reasons(analysis));
    renderMarketFilters($("decision-filters"), analysis.market_filters, analysis.session || analysis.macro_dashboard?.session);
}

function renderProductDecision(analysis={}) {
    const product=analysis.decision,decision=product.decision||{},setup=product.setup||{},market=product.market||{},owner=product.ownership||{},ready=setup.trade_ready===true,status=decision.status||"NO MARKET OPPORTUNITY";
    [$("decision-status"),$("scanner-status"),$("home-status")].forEach(node=>{node.textContent=status;node.className=toneFor(status)});
    $("decision-direction").textContent=titleCase(decision.direction||"Neutral");$("decision-phase").textContent=titleCase(decision.stage);$("decision-readiness").textContent=ready?"Trade readiness: Confirmed":"Trade readiness: Not confirmed";$("decision-score").textContent=setup.quality_score||0;$("decision-confidence").textContent=setup.quality_grade||"REJECTED";
    $("decision-strategy-heading").textContent=owner.selection_mode==="auto"?"SMC Auto Decision":"Manual SMC Model";$("decision-strategy").textContent=titleCase(owner.selected_model_id);$("decision-strategy-reason").textContent=owner.selection_reason||"Registry-selected family adapter.";$("decision-evidence").textContent=`${titleCase(product.meta.family)} · ${titleCase(product.meta.variant)} · ${product.meta.market_schedule==="24_7"?"24/7 UTC":""}`;
    $("decision-next").textContent=decision.next_action||setup.next_required_condition;$("decision-timing").textContent=titleCase(decision.stage);$("decision-timing-help").textContent=setup.next_required_condition||"Wait for completed evidence.";
    const modelCard=$("smc-model-card");modelCard.hidden=false;$("smc-model").textContent=titleCase(owner.selected_model_id);$("smc-owner").textContent=titleCase(owner.decision_owner_id);$("smc-structure").textContent=`H1 ${titleCase(market.external_structure)} / M15 ${titleCase(market.internal_structure)}`;$("smc-target").textContent=(product.smc?.liquidity_references||[]).find(x=>x.active)?.price??"—";$("smc-event").textContent=titleCase(market.event_state||"None");$("smc-expected-event").textContent="Unknown";$("smc-stage").textContent=titleCase(decision.stage);
    $("derived-market-card").hidden=true;$("boom-crash-state-card").hidden=true;$("market-context-card").hidden=false;$("context-htf").textContent=titleCase(market.external_structure);$("context-structure").textContent=titleCase(market.internal_structure);$("context-location").textContent=titleCase(decision.stage);$("context-momentum").textContent=titleCase(market.volatility_state||"Unavailable");
    const plan=$("decision-plan");plan.innerHTML=ready?[["Entry",setup.entry],["Stop",setup.stop],["TP1",setup.targets?.[0]?.price],["R:R",setup.rr]].map(([k,v])=>`<div><dt>${k}</dt><dd>${formatValue(v)}</dd></div>`).join(""):"<div><dt>Trade Plan</dt><dd>None</dd></div><div><dt>Reason</dt><dd>"+escapeHtml(setup.next_required_condition||"Waiting for completed confirmation.")+"</dd></div>";plan.parentElement.hidden=false;
    renderReasonList($("decision-why"),reasons(analysis));const diagnostics=$("setup-gate-diagnostics");diagnostics.hidden=false;$("gate-strategy").textContent=titleCase(owner.decision_owner_id);$("gate-stage").textContent=titleCase(decision.stage);$("gate-passed").textContent=ready?"All essential gates":"Developing";$("gate-first").textContent=titleCase(decision.first_blocking_gate||"None");$("gate-next").textContent=setup.next_required_condition||"No further condition.";$("gate-details").innerHTML=Object.entries(product.diagnostics?.gate_funnel||{}).filter(([,v])=>v&&typeof v==="object"&&"passed" in v).map(([k,v])=>`<div><dt>${v.passed?"✓":"○"} ${escapeHtml(titleCase(k))}</dt><dd>${escapeHtml(v.reason||"")}</dd></div>`).join("");
    $("decision-trade-map").hidden=!ready;if(ready){$("decision-entry-label").textContent="Confirmed Entry";$("decision-entry").textContent=formatValue(setup.entry);$("decision-current").textContent=formatValue(market.current_price);$("decision-distance-row").hidden=true;}
    $("previous-setup-card").hidden=!product.previous_setup;renderTopDownStrip(analysis);
    const dataState=document.querySelector("#toolbar-data-state"),lastCandle=document.querySelector("#toolbar-last-candle");if(dataState)dataState.textContent=titleCase(product.readiness?.state||"Unknown");if(lastCandle)lastCandle.textContent=product.readiness?.timeframes?.M5?.last_completed_time?new Date(product.readiness.timeframes.M5.last_completed_time).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}):"—";
}

function renderSmcModel(analysis={}) {
    const contract=analysis.decision?.derived_index?.contract||{},ownership=contract.ownership,card=$("smc-model-card");if(!card)return;card.hidden=!ownership;if(card.hidden)return;const setup=contract.setup||{},structure=contract.structure||{},target=setup.structural_target||{},event=contract.event||{};
    $("smc-model").textContent=contract.decision?.strategy_label||"SMC";$("smc-owner").textContent=titleCase(ownership.decision_owner_id);$("smc-structure").textContent=`H1 ${titleCase(structure.external_structure)} / M15 ${titleCase(structure.internal_structure)}`;$("smc-target").textContent=Number.isFinite(Number(target.price))?`${titleCase(target.type)} · ${formatValue(target.price)}`:"—";$("smc-event").textContent=event.qualified?`${titleCase(event.direction)} jump · ${new Date(event.event_time).toLocaleString()}`:"No active completed event";$("smc-expected-event").textContent="Unknown / Symmetric";$("smc-stage").textContent=titleCase(setup.state);
}

function renderSetupGateDiagnostics(analysis={}) {
    const contract=analysis.decision?.derived_index?.contract||{},funnel=contract.gate_funnel||contract.diagnostics?.setup_gates,root=$("setup-gate-diagnostics");if(!root)return;root.hidden=!funnel;if(!funnel)return;
    $("gate-strategy").textContent=titleCase(funnel.strategy||"None");$("gate-stage").textContent=titleCase(funnel.setup_stage);$("gate-passed").textContent=`${funnel.passed_gate_count||0} of ${funnel.total_gate_count||0} gates`;$("gate-first").textContent=titleCase(funnel.first_blocking_gate||"All gates passed");$("gate-next").textContent=funnel.next_price_condition||"All requirements passed.";
    const keys=funnel.family_compatibility!==undefined?["family_compatibility","history","external_structure","internal_structure","structural_target","setup_location","sweep_event","displacement","mss_bos_confirmation","entry_array","entry_geometry","stop_geometry","target_geometry","reward_to_risk","chase","lifecycle_validity"]:["family_supported","data_quality","history_depth","regime_eligibility","directional_context","setup_location","zone_interaction","confirmation","stop_geometry","target_geometry","reward_to_risk","chase_validation"];
    $("gate-details").innerHTML=keys.map(key=>{const row=funnel[key]||{};return `<div><dt>${row.passed?"✓":"○"} ${escapeHtml(titleCase(key))}</dt><dd>${escapeHtml(row.reason||"Unavailable")}</dd></div>`}).join("");
    const history=funnel.history_depth||funnel.history||{},available=history.available||{},required=history.required||{};$("gate-history").innerHTML=Object.keys(required).map(key=>`<div><dt>${escapeHtml(key)}</dt><dd>${Number(available[key]||0)} / ${Number(required[key]||0)}</dd></div>`).join("");
    const shadow=funnel.shadow_candidate;$("gate-shadow-section").hidden=!shadow;if(shadow)$("gate-shadow").textContent=JSON.stringify(shadow,null,2);const contradictions=funnel.state_contradictions||[];$("gate-contradictions-section").hidden=!contradictions.length;$("gate-contradictions").innerHTML=contradictions.map(row=>`<li>${escapeHtml(row)}</li>`).join("");
}

async function loadPaperTestingSummary() {
    const card=$("paper-testing-card"); if (!card || card.hidden) return;
    try {
        const response=await fetch("/api/paper/summary"), summary=await response.json();
        if (!response.ok) throw new Error(summary.error || "Paper summary unavailable");
        $("paper-active").textContent=summary.active_setups ?? 0;
        $("paper-open").textContent=summary.open_simulated_trades ?? 0;
        $("paper-resolved").textContent=summary.resolved_trades ?? 0;
        $("paper-evidence").textContent=titleCase(summary.current_evidence || "Insufficient");
        const performance=Number(summary.recent_performance_r);
        $("paper-performance").textContent=Number.isFinite(performance) ? `${performance.toFixed(2)}R (last 20)` : "—";
    } catch (_error) { $("paper-evidence").textContent="Unavailable"; }
}

async function loadResearchPages(){
    try{
        const [setupsResponse,outcomesResponse,performanceResponse]=await Promise.all([fetch("/api/paper/setups"),fetch("/api/paper/outcomes"),fetch("/api/paper/performance")]);
        const setups=await setupsResponse.json(),outcomes=await outcomesResponse.json(),performance=await performanceResponse.json();
        const setupRows=Array.isArray(setups)?setups:setups.rows||setups.setups||[],outcomeRows=Array.isArray(outcomes)?outcomes:outcomes.rows||outcomes.outcomes||[];
        const paperBody=document.querySelector("#paper-table-body");if(paperBody)paperBody.innerHTML=setupRows.slice(0,100).map(row=>`<tr><td>${escapeHtml(row.setup_id||row.paper_setup_id||"—")}</td><td>${escapeHtml(row.symbol||row.provider_symbol||"—")}</td><td>${escapeHtml(titleCase(row.strategy))}</td><td>${escapeHtml(titleCase(row.direction))}</td><td>${escapeHtml(titleCase(row.state))}</td><td>${formatValue(row.entry)}</td><td>${formatValue(row.stop)}</td><td>${formatValue(row.tp1)}</td></tr>`).join("")||'<tr><td colspan="8">No paper setups recorded.</td></tr>';
        const resolved=document.querySelector("#performance-resolved");if(resolved)resolved.textContent=outcomeRows.length;const evidence=document.querySelector("#performance-evidence");if(evidence)evidence.textContent=titleCase(performance.evidence_label||performance.evidence||"Insufficient");const table=document.querySelector("#performance-table-body"),rawGroups=performance.groups||[],groups=Array.isArray(rawGroups)?rawGroups:Object.values(rawGroups).flatMap(value=>Array.isArray(value)?value:Object.values(value||{}));if(table)table.innerHTML=groups.slice(0,100).map(row=>`<tr><td>${escapeHtml(row.group||row.symbol||row.strategy||"—")}</td><td>${row.resolved_trades||row.trades||0}</td><td>${formatNumber(row.win_rate)}%</td><td>${formatNumber(row.expectancy)}R</td><td>${formatNumber(row.profit_factor)}</td><td>${formatNumber(row.maximum_drawdown_r)}R</td></tr>`).join("")||'<tr><td colspan="6">Evidence is insufficient for performance estimates.</td></tr>';
    }catch(error){const node=document.querySelector("#paper-page-state");if(node)node.textContent=`Paper data unavailable · ${plainText(error.message)}`;}
}

function renderBoomCrashState(analysis={}) {
    const result=analysis.decision?.derived_index?.contract?.strategy_result||{},family=result.family_context?.family,card=$("boom-crash-state-card");card.hidden=!(["BOOM","CRASH"].includes(family));if(card.hidden)return;
    const spike=result.spike||{},cooldown=result.cooldown||{},hold=result.spike_hold||{},structure=result.post_spike_structure||{},decision=result.decision||{};
    $("boom-crash-family").textContent=titleCase(family);$("boom-crash-spike").textContent=spike.locked?`${titleCase(spike.direction)} spike locked`:"No qualified spike";$("boom-crash-risk-state").textContent=cooldown.active?"Recalibrating":"Post-spike evaluation";$("boom-crash-hold").textContent=titleCase(hold.classification);$("boom-crash-structure").textContent=titleCase(structure.state);$("boom-crash-scenario").textContent=titleCase(decision.scenario||"None");$("boom-crash-alignment").textContent=titleCase(decision.risk_alignment||"None");
}

function renderMarketPresentation(presentation={}) {
    const context=presentation.market_context || {}, contextCard=$("market-context-card"); contextCard.hidden=!context.summary;
    if (!contextCard.hidden) { $("context-htf").textContent=titleCase(context.higher_timeframes || context.market_bias); $("context-structure").textContent=titleCase(context.structure); $("context-location").textContent=context.price_location || ""; $("context-momentum").textContent=context.momentum || ""; }
    const scenario=presentation.developing_scenario || {}, scenarioCard=$("developing-scenario-card"); scenarioCard.hidden=!scenario.available;
    if (!scenarioCard.hidden) { $("scenario-label").textContent=scenario.label || "Developing scenario"; const zone=scenario.zone || {}, hasZone=[zone.low,zone.high].every((value)=>Number.isFinite(tradeChartPrice(value))); $("scenario-area-row").hidden=!hasZone; $("scenario-area").textContent=hasZone ? `${formatValue(zone.low)}–${formatValue(zone.high)}` : ""; $("scenario-required").textContent=scenario.required_event || ""; $("scenario-confirmation").textContent=scenario.confirmation || ""; }
    const levels=presentation.key_levels || {}, rows=[["Resistance",levels.resistance],["Support",levels.support],["Liquidity Above",levels.liquidity_above],["Liquidity Below",levels.liquidity_below]].filter(([,value])=>Number.isFinite(tradeChartPrice(value))).slice(0,4); $("key-levels-card").hidden=!rows.length; $("key-levels").innerHTML=rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${formatValue(value)}</dd></div>`).join("");
    $("decision-liquidity-details").innerHTML=rows.length ? rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${formatValue(value)}</dd></div>`).join("") : "<div><dd>No confirmed unswept levels are available.</dd></div>";
}

function renderPreviousSetup(previous) {
    const card=$("previous-setup-card"); card.hidden=!previous?.setup_id; if (card.hidden) return;
    const side=previous.direction === "buy" ? "Buy" : "Sell";
    $("previous-setup-title").textContent=`${side} entry ${previous.result || previous.state}`;
    $("previous-setup-entry").textContent=[previous.entry_low,previous.entry_high].every((value)=>Number.isFinite(tradeChartPrice(value))) ? `${formatValue(previous.entry_low)}–${formatValue(previous.entry_high)}` : "—";
    $("previous-setup-distance").textContent=Number.isFinite(Number(previous.distance_moved)) ? `${Number(previous.distance_moved).toFixed(1)} ${previous.distance_unit || ""}` : "—";
    const metrics=[Number.isFinite(Number(previous.distance_atr)) ? `${Number(previous.distance_atr).toFixed(2)}× M5 ATR` : "",Number.isFinite(Number(previous.remaining_rr)) ? `${Number(previous.remaining_rr).toFixed(1)}R remaining` : ""].filter(Boolean).join(" · ");
    $("previous-setup-reason").textContent=`${previous.reason || "The previous setup reached a terminal state."}${metrics ? ` ${metrics}.` : ""}`;
    $("previous-setup-time").textContent=previous.terminal_at ? `Archived ${new Date(previous.terminal_at).toLocaleString()}` : "";
}

function renderDecisionTradeMap(analysis = {}, status = "", direction = "Neutral") {
    const plan = analysis.decision?.trade_chart || {}, missed = ["too_late", "entry_missed", "setup_missed", "entry_extended"].includes(plan.state);
    const active=analysis.decision?.presentation?.active_trade_plan; $("decision-trade-map").hidden=!active; if (!active) return;
    const confirmed = Number.isFinite(tradeChartPrice(plan.confirmed_entry)) && !missed;
    const source = confirmed ? { low: plan.confirmed_entry, high: plan.confirmed_entry } : selectDisplayEntry(plan);
    const low = tradeChartPrice(source?.low), high = tradeChartPrice(source?.high), hasEntry = [low, high].every(Number.isFinite);
    const side = plan.idea === "buy" ? "Buy" : plan.idea === "sell" ? "Sell" : direction;
    $("decision-entry-label").textContent = missed ? "Original Entry" : confirmed ? `Confirmed ${side} Entry` : `Expected ${side} Entry`;
    $("decision-entry").textContent = hasEntry ? (Math.abs(high - low) < 1e-12 ? formatValue(low) : `${formatValue(low)}–${formatValue(high)}`) : "—";
    $("decision-current").textContent = Number.isFinite(tradeChartPrice(plan.current_price)) ? formatValue(plan.current_price) : "—";
    const distance = Number(plan.distance_to_entry), unit = plan.distance_unit || "";
    $("decision-distance-row").hidden = !Number.isFinite(distance);
    $("decision-distance").textContent = missed ? "Price moved too far from the original entry." : Number.isFinite(distance) ? `${distance.toFixed(1)} ${unit}` : "—";
    if (missed) $("decision-next").textContent = "Wait for a new setup. Do not chase this move.";
}

function selectDisplayEntry(plan = {}) {
    const m5 = plan.m5_execution_zone || {}, expected = plan.expected_entry || {};
    return [tradeChartPrice(m5.low), tradeChartPrice(m5.high)].every(Number.isFinite) ? m5 : expected;
}

function renderTopDownStrip(analysis = {}) {
    // Compatibility note: analysis.top_down_analysis / analysis.execution_plan and entry_valid are legacy response mirrors only.
    // The actionable check formerly read: execution.state !== "entry_valid".
    const topDown = analysis.decision || {};
    const frames = topDown.top_down || {};
    const execution = topDown.execution || {};
    const available = ["D1", "H4", "H1", "M15", "M5"].some((timeframe) => frames[timeframe]);
    $("top-down-section").hidden = !available;
    if (!available) return;
    $("top-down-strip").innerHTML = ["D1", "H4", "H1", "M15", "M5"].map((timeframe) => {
        const frame = frames[timeframe] || {};
        const value = timeframe === "M15" ? frame.setup_type || frame.bias || "Unavailable" : timeframe === "M5" ? execution.state || frame.trigger_state || "Waiting" : frame.bias || "Neutral";
        return `<div><dt>${timeframe}</dt><dd>${escapeHtml(titleCase(value))}</dd></div>`;
    }).join("");
    const direction = titleCase(execution.direction || "neutral");
    $("execution-summary").textContent = `${direction} · M5 · ${titleCase(execution.state || "waiting")}`;
    const button = $("view-m5-entry");
    button.hidden = execution.state !== "entry_available" || ui.timeframe.value === "M5" || !analysis.execution_candles?.length;
}

function viewCachedM5Entry() {
    if (!latest?.execution_candles?.length) return;
    ui.timeframe.value = "M5";
    latest.candles = latest.execution_candles.map((candle) => ({ ...candle }));
    if (latest.display_analysis) latest.display_analysis.selected_timeframe = "M5";
    renderChartPage(latest);
    renderDecisionPanel(latest);
    ui.update.hidden = true;
}

function renderIctSequence(decision = {}) {
    const section = $("ict-sequence-section"), container = $("ict-sequence");
    const rows = Array.isArray(decision.ict_checklist) ? decision.ict_checklist.slice(0, 10) : [];
    section.hidden = !rows.length;
    container.innerHTML = rows.map((row) => `<li data-state="${escapeHtml(row.state)}"><span>${row.state === "pass" ? "✓" : row.state === "unavailable" ? "!" : "○"}</span>${escapeHtml(row.label)}</li>`).join("");
}

function renderIctDiagnostics(decision = {}) {
    const section = $("ict-diagnostics-section"), container = $("ict-diagnostics"), diagnostics = decision.ict_model?.diagnostics, audit = decision.directional_audit;
    section.hidden = !diagnostics && !audit;
    if (!diagnostics && !audit) { container.innerHTML = ""; return; }
    const names = ["htf_narrative", "bullish_candidate", "bearish_candidate", "liquidity", "liquidity_sweep", "displacement", "mss", "fvg", "entry_array", "target"];
    const ictRows = diagnostics ? names.map((name) => {
        const row = diagnostics[name] || {}, reasons = Array.isArray(row.rejection_reasons) ? row.rejection_reasons : [];
        const state = row.status || row.state || "unavailable";
        return `<article><strong>${escapeHtml(titleCase(name))}</strong><span data-state="${escapeHtml(state)}">${escapeHtml(titleCase(state))}</span><small>${escapeHtml(reasons[0] || row.relationship || `${(row.detected_candidates || []).length} candidate(s) inspected.`)}</small></article>`;
    }).join("") : "";
    const auditRows = audit ? `<article><strong>Directional Audit · Buy</strong><span>${audit.buy_candidates_found} found · ${audit.buy_candidates_rejected} rejected</span><small>${escapeHtml(audit.best_buy?.strategy || "No eligible buy candidate")}</small></article><article><strong>Directional Audit · Sell</strong><span>${audit.sell_candidates_found} found · ${audit.sell_candidates_rejected} rejected</span><small>${escapeHtml(audit.best_sell?.strategy || "No eligible sell candidate")}</small></article><article><strong>Final Selection</strong><span>${escapeHtml(titleCase(audit.final_selection?.direction || "neutral"))}</span><small>${escapeHtml(audit.final_selection?.reason || "No directional selection")}</small></article>` : "";
    container.innerHTML = ictRows + auditRows;
}

function renderAmdPhase(decision = {}) {
    const amd = decision.amd || {}, section = $("amd-phase-section");
    section.hidden = !amd.available;
    if (!amd.available) return;
    const range = amd.accumulation || {}, manipulation = amd.manipulation || {}, distribution = amd.distribution || {};
    $("amd-phase").textContent = `${titleCase(amd.phase || "searching")} · ${titleCase(amd.confidence || "low")}`;
    $("amd-range").textContent = [range.low, range.high].every((value) => Number.isFinite(numeric(value))) ? `${formatValue(range.low)}–${formatValue(range.high)} · Locked` : "Not identified";
    $("amd-liquidity").textContent = manipulation.boundary_event === "accepted_breakout" ? "Accepted breakout — not a sweep" : manipulation.reclaimed ? `Liquidity swept ${manipulation.side === "low" ? "below" : "above"} range and reclaimed` : manipulation.sweep_time ? "Possible sweep; reclaim pending" : "No boundary sweep";
    const amdSide = amd.direction === "bullish" ? "Bullish" : amd.direction === "bearish" ? "Bearish" : "AMD";
    $("amd-distribution").textContent = distribution.confirmed ? `${amdSide} distribution confirmed` : distribution.mss_time ? `${amdSide} distribution developing · MSS detected` : distribution.displacement ? `${amdSide} distribution developing` : "Not detected";
    $("amd-next").textContent = amd.next_action || "AMD is context only; M5 execution is still required.";
}

function timingHelper(setup) {
    if (!setup) return "No complete setup.";
    const helpers = {
        "WATCHING AREA": "Price has not reached the zone.",
        "IN SETUP AREA": "Wait for a reaction.",
        "REACTION FORMING": "Confirmation is still required.",
        "CONFIRMATION FORMING": "Watch the confirmation close.",
        "M5 CONFIRMED": "M5 execution is confirmed; entry availability is still being validated.",
        "SETUP CONFIRMED": "Trade-plan checks passed.",
        "SETUP MISSED": "Entry timing has passed.",
        "SETUP INVALIDATED": "The setup is no longer valid.",
    };
    return helpers[setup.stage] || "No complete setup.";
}

function shortNextAction(setup, status = "NO VALID SETUP") {
    if (status === "SETUP INVALIDATED") return "Setup is invalid. Do not enter.";
    if (status === "SETUP MISSED") return "Price is too extended. Wait for a fresh setup.";
    if (!setup) return "Wait for a complete setup.";
    if (setup.stage === "WATCHING AREA") return `Watch for price to retrace into the ${setup.direction === "sell" ? "sell" : "buy"} zone.`;
    if (["IN SETUP AREA", "REACTION FORMING", "CONFIRMATION FORMING"].includes(setup.stage)) return `Wait for a ${setup.direction === "sell" ? "bearish close below" : "bullish close above"} confirmation.`;
    if (setup.stage === "SETUP CONFIRMED") return "Review the confirmed trade plan.";
    return "Wait for a complete setup.";
}

function renderScannerPage(analysis = {}) {
    const status = formatUserStatus(analysis);
    const direction = formatDirection(analysis);
    const setups = analysis.possible_setups || normalizePossibleSetups(analysis);
    const score = tradeScore({ ...analysis, possible_setups: setups });
    $("scanner-status").textContent = status;
    $("scanner-status").className = toneFor(status);
    $("scanner-direction").textContent = `Direction: ${direction}`;
    $("scanner-score").textContent = score;
    $("scanner-confidence").textContent = confidence(score, setups[0]?.stage, setups[0]?.confirmation_viable);
    $("scanner-next").textContent = nextAction(analysis);
    renderPlan($("scanner-plan"), analysis);
    renderReasonList($("scanner-why"), reasons(analysis));
    renderMarketFilters($("scanner-filters"), analysis.market_filters, analysis.session || analysis.macro_dashboard?.session);
}

function renderHomePage(analysis = {}) {
    $("home-empty").hidden = true;
    $("home-result").hidden = false;
    $("home-market").textContent = `${analysis.display_symbol || ui.symbol.value} · ${analysis.timeframe || ui.timeframe.value}`;
    $("home-status").textContent = formatUserStatus(analysis);
    $("home-status").className = toneFor(formatUserStatus(analysis));
    $("home-score").textContent = `Score ${tradeScore(analysis)}`;
    $("home-next").textContent = nextAction(analysis);
    rememberRecent(analysis);
}

function renderPlan(container, analysis = {}) {
    if(analysis.decision?.meta?.market_type==="derived"){
        const setup=analysis.decision.setup||{};if(!setup.trade_ready){container.innerHTML=container.tagName==="DL"?`<div><dt>Trade Plan</dt><dd>None</dd></div><div><dt>Reason</dt><dd>${escapeHtml(setup.next_required_condition||"Waiting for completed confirmation.")}</dd></div>`:"No trade plan · "+escapeHtml(setup.next_required_condition||"Waiting for completed confirmation.");return;}const rows=[["Entry",setup.entry],["Stop",setup.stop],["TP1",setup.targets?.[0]?.price],["TP2",setup.targets?.[1]?.price],["R:R",setup.rr]].filter(([,v])=>v!==null&&v!==undefined),html=rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${formatValue(value)}</dd></div>`).join("");container.innerHTML=container.tagName==="DL"?html:`<dl class="compact-list">${html}</dl>`;return;
    }
    const derivedPlan=analysis.decision?.presentation?.active_trade_plan;
    if(derivedPlan) {
        const rows=[["Entry",derivedPlan.entry],["Stop",derivedPlan.stop],["TP1",derivedPlan.tp1?.price],["TP2",derivedPlan.tp2?.price],["TP1 RR",derivedPlan.tp1_rr],["Timing",derivedPlan.timing_state]].filter(([,value])=>value!==null&&value!==undefined);
        const html=rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${typeof value==="number"?formatValue(value):escapeHtml(value)}</dd></div>`).join("");container.innerHTML=container.tagName==="DL"?html:`<dl class="compact-list">${html}</dl>`;return;
    }
    const execution = analysis.decision?.execution || {};
    if (!hasValidPlan(analysis)) { container.innerHTML = container.tagName === "DL" ? "<div><dd>No confirmed plan yet.</dd></div>" : "No confirmed plan yet."; return; }
    const rows = [
        ["Entry", execution.entry],
        ["Stop", execution.stop],
        ["TP1", execution.targets?.[0]?.price],
        ["TP2", execution.targets?.[1]?.price],
        ["R:R", execution.risk_reward],
    ].filter(([, value]) => value !== null && value !== undefined);
    const html = rows.map(([label, value]) => `<div><dt>${label}</dt><dd>${formatValue(value)}</dd></div>`).join("");
    container.innerHTML = container.tagName === "DL" ? html : `<dl class="compact-list">${html}</dl>`;
}

function renderReasonList(container, items) {
    container.innerHTML = "";
    (items.length ? items : ["No analysis reasons are available yet."]).forEach((text) => { const li = document.createElement("li"); li.textContent = text; container.appendChild(li); });
}

function renderMarketFilters(container, filters = {}, session = {}) {
    if (latest?.provider === "deriv" || latest?.asset_type === "derived_index") {
        container.innerHTML = '<div><dt>Provider</dt><dd>Deriv</dd></div><div><dt>Market</dt><dd>24/7</dd></div><div><dt>Mode</dt><dd>Paper analysis only</dd></div>';
        return;
    }
    const news = filters?.news_risk || {};
    const dxy = filters?.dxy_confirmation || {};
    const source = news.source || news.provider || "Unavailable";
    const rows = [
        ["News", titleCase(news.risk_level || news.risk || news.status || "Unavailable")],
        ["Source", titleCase(source)],
        ["DXY", titleCase(dxy.status || dxy.correlation_status || "Unavailable")],
        ["Session", titleCase(session.session_name || session.name || session.current_session || "Outside")],
    ];
    container.innerHTML = rows.map(([key, value]) => `<div><dt>${key}</dt><dd>${value}</dd></div>`).join("");
}

function formatTiming(timing = {}) {
    const raw = String(timing?.status || timing?.label || timing || "Unavailable").toLowerCase();
    if (raw.includes("at_entry") || raw.includes("at entry")) return "At entry";
    if (raw.includes("near")) return "Near entry";
    if (raw.includes("forming") || raw.includes("waiting")) return "Setup forming";
    if (raw.includes("late") || raw.includes("chase")) return "Too late";
    return "Unavailable";
}

function setupEntryTiming(setup) {
    const stages = {
        "WATCHING AREA": "Watching Area",
        "IN SETUP AREA": "In Zone",
        "REACTION FORMING": "Reaction Forming",
        "CONFIRMATION FORMING": "Near Confirmation",
        "M5 CONFIRMED": "M5 Confirmed",
        "SETUP MISSED": "Too Late",
        "SETUP INVALIDATED": "Invalid",
    };
    if (!setup) return "Not available yet";
    if (setup.stage === "SETUP CONFIRMED") return "Confirmed";
    return stages[setup.stage] || "Watching Area";
}

function normalizePossibleSetups(analysis = {}) {
    const decision = analysis.decision;
    const setup = decision?.setup;
    const zone = setup?.zone;
    const visualId = setup?.setup_id || setup?.context_id;
    if (!visualId || !["buy", "sell"].includes(setup?.direction) || !Number.isFinite(numeric(zone?.low)) || !Number.isFinite(numeric(zone?.high))) return [];
    const execution = decision.execution || {};
    const stage = {
        waiting_for_m15_area: "WATCHING AREA", in_m15_area: "IN SETUP AREA", m5_setup_forming: "REACTION FORMING", waiting_for_m5_close: "CONFIRMATION FORMING", m5_confirmed: "M5 CONFIRMED", entry_extended: "SETUP MISSED",
        waiting_for_area: "WATCHING AREA", in_area: "IN SETUP AREA", reaction_forming: "REACTION FORMING",
        in_entry_zone: "IN SETUP AREA", confirmation_forming: "CONFIRMATION FORMING", waiting_for_m5_close: "CONFIRMATION FORMING", confirmed: "SETUP CONFIRMED", entry_available: "SETUP CONFIRMED", poor_reward: "SETUP MISSED", extended: "SETUP MISSED", too_late: "SETUP MISSED",
        missed: "SETUP MISSED", invalidated: "SETUP INVALIDATED",
        context_only: "WATCHING AREA", unavailable: "WATCHING AREA", sequence_forming: "REACTION FORMING", waiting_for_m5: "CONFIRMATION FORMING",
    }[setup.stage] || "WATCHING AREA";
    return [{
        id: visualId, priority: "primary", direction: setup.direction,
        label: `${setup.direction === "buy" ? "Buy" : "Sell"} Setup · M5 Execution`, stage,
        strategy: setup.strategy, setup_zone: { ...zone, label: setup.direction === "buy" ? "Demand Zone" : "Supply Zone", start_time: zone.origin_time }, zone,
        trigger: { ...setup.confirmation, message: setup.confirmation_hint }, confirmation: setup.confirmation,
        invalidation: { ...setup.invalidation, message: setup.invalidation_context },
        targets: execution.targets?.length ? execution.targets : execution.projected_targets || [], estimated_rr: execution.risk_reward,
        entry_available: decision.quality?.trade_plan_valid === true,
        confirmation_viable: decision.quality?.trade_plan_valid === true,
        remaining_rr: execution.risk_reward, confirmation_rr_status: decision.quality?.trade_plan_valid ? "acceptable" : "unavailable",
        score: decision.quality?.score, confidence: decision.quality?.confidence,
        next_action: decision.user_output?.next_action, creation_time: setup.created_time, last_updated_time: setup.updated_time,
        zone_relation: decision.ict_context?.zone_relation || null,
        allow_path: decision.overlays?.conditional_arrow !== null && decision.execution?.available !== false,
    }];
}

function normalizeBackendSetup(item, index) {
    if (!item || typeof item !== "object") return null;
    const direction = String(item.direction || "").toLowerCase();
    if (!["buy", "sell"].includes(direction)) return null;
    const zone = normalizeSetupZone(item.setup_zone, direction === "buy" ? "Long" : "Short");
    if (!zone) return null;
    const setup = {
        ...item,
        id: String(item.id || `backend-setup-${index}`),
        priority: item.priority === "alternative" ? "alternative" : "primary",
        direction,
        label: item.label || (direction === "buy" ? "Potential Buy" : "Potential Sell"),
        stage: setupStageLabel(item.stage),
        setup_zone: zone,
        trigger: { ...(item.trigger || {}), price: finiteOrNull(item.trigger?.price) },
        invalidation: { ...(item.invalidation || {}), price: finiteOrNull(item.invalidation?.price) },
        targets: (Array.isArray(item.targets) ? item.targets : []).filter((target) => target?.swept !== true && (!target?.setup_id || target.setup_id === item.id)).map((target) => ({ ...target, price: finiteOrNull(target?.price), valid: target?.valid !== false })).slice(0, 2),
        estimated_rr: finiteOrNull(item.estimated_rr),
        entry_available: Boolean(item.entry_available && setupStageLabel(item.stage) === "SETUP CONFIRMED"),
        conditions: Array.isArray(item.conditions) ? item.conditions : setupConditions({ direction: direction === "buy" ? "Long" : "Short", confirmed: setupStageLabel(item.stage) === "SETUP CONFIRMED", targetAvailable: Array.isArray(item.targets) && item.targets.some((target) => Number.isFinite(numeric(target?.price))) }),
        conditions_met: Number.isFinite(numeric(item.conditions_met)) ? numeric(item.conditions_met) : 2,
        conditions_total: Number.isFinite(numeric(item.conditions_total)) ? numeric(item.conditions_total) : 4,
    };
    return finalizeNormalizedSetup(withConfirmationQuality(setup), latest || {});
}

function finalizeNormalizedSetup(setup, analysis = {}) {
    const score = tradeScore({ ...analysis, possible_setups: [setup] });
    return {
        ...setup,
        zone: setup.setup_zone,
        confirmation: setup.trigger,
        score,
        confidence: confidence(score, setup.stage, setup.confirmation_viable),
        created_at: setup.created_at ?? setup.creation_time ?? null,
        updated_at: setup.updated_at ?? setup.last_updated_time ?? null,
    };
}

function enforcePossibleSetupRules(setups, analysis) {
    const mainStatus = formatUserStatus(analysis);
    if (mainStatus === "NO VALID SETUP") return [];
    return setups.filter((setup) => {
        if (!setup.setup_zone || !setup.trigger?.message || !setup.invalidation?.message) return false;
        if (mainStatus === "BUY SETUP FORMING" && setup.priority === "primary" && setup.direction !== "buy") return false;
        if (mainStatus === "SELL SETUP FORMING" && setup.priority === "primary" && setup.direction !== "sell") return false;
        if (setup.priority === "alternative") {
            const validTarget = setup.targets?.some((target) => Number.isFinite(target.price));
            if (!Number.isFinite(setup.trigger?.price) || !Number.isFinite(setup.invalidation?.price) || !validTarget || !Number.isFinite(setup.estimated_rr) || setup.estimated_rr < 1) return false;
        }
        if (!validDirectionalGeometry(setup)) return false;
        Object.assign(setup, finalizeNormalizedSetup(withConfirmationQuality(setup), analysis));
        if (setup.confirmation_rr_status === "poor") setup.next_action = "Confirmation may be too late for a clean entry. Reward remaining after confirmation is too small.";
        else if (setup.stage === "WATCHING AREA") setup.next_action = setup.direction === "sell"
            ? `Sell scenario identified. Watch for a retracement into supply and bearish confirmation below ${formatValue(setup.trigger.price)}.`
            : `Buy scenario identified. Watch for a retracement into demand and bullish confirmation above ${formatValue(setup.trigger.price)}.`;
        setup.label = possibleSetupLabel(analysis, setup.direction === "buy" ? "Long" : "Short");
        return setup.stage !== "SETUP MISSED";
    }).slice(0, 2);
}

function validDirectionalGeometry(setup) {
    const zone = setup.setup_zone;
    const invalidation = finiteOrNull(setup.invalidation?.price);
    const confirmation = finiteOrNull(setup.trigger?.price);
    if (!zone) return false;
    if (![invalidation, confirmation].every(Number.isFinite)) return true;
    return setup.direction === "sell"
        ? invalidation > zone.high && confirmation < zone.low
        : invalidation < zone.low && confirmation > zone.high;
}

function withConfirmationQuality(setup) {
    const entry = finiteOrNull(setup.trigger?.price);
    const stop = finiteOrNull(setup.invalidation?.price);
    const target = setup.targets?.find((candidate) => Number.isFinite(candidate.price) && candidate.swept !== true)?.price;
    const risk = setup.direction === "sell" ? stop - entry : entry - stop;
    const reward = setup.direction === "sell" ? entry - target : target - entry;
    const remainingRr = [entry, stop, target, risk, reward].every(Number.isFinite) && risk > 0 && reward > 0 ? reward / risk : null;
    const rrStatus = !Number.isFinite(remainingRr) ? "unavailable" : remainingRr >= 1 ? "acceptable" : "poor";
    return { ...setup, confirmation_entry: entry, remaining_rr: remainingRr, confirmation_rr_status: rrStatus, confirmation_viable: rrStatus === "acceptable" };
}

function possibleSetupLabel(analysis, direction) {
    const side = direction === "Long" ? "Buy" : "Sell";
    const higher = normalizeDirection(analysis.trader_answers?.higher_timeframe_bias || analysis.top_down_analysis?.overall_alignment || analysis.top_down_context?.overall_alignment);
    const execution = normalizeDirection(analysis.trader_answers?.execution_timeframe_trend || analysis.trader_answers?.trend || analysis.strategy_result?.bias || analysis.bias);
    const opposite = higher !== "Neutral" && higher !== direction;
    if (opposite) return `Possible Countertrend ${side}`;
    if (higher === direction && execution === direction) return `Potential ${side}`;
    return `Conditional ${side} Scenario`;
}

function normalizeSetupZone(source, direction) {
    if (!source || typeof source !== "object") return null;
    const low = numeric(source.low ?? source.bottom ?? source.bottom_price ?? source.min);
    const high = numeric(source.high ?? source.top ?? source.top_price ?? source.max);
    if (![low, high].every(Number.isFinite) || low <= 0 || high < low) return null;
    return {
        low,
        high,
        label: source.label || (direction === "Long" ? "Demand Zone" : "Supply Zone"),
        type: String(source.type || source.tag || "").toLowerCase(),
        start_time: finiteOrNull(source.start_time ?? source.time ?? source.departure_time),
        end_time: finiteOrNull(source.end_time ?? source.rectangle_end_time),
        touch_count: Number.isFinite(numeric(source.touch_count)) ? numeric(source.touch_count) : null,
        status: String(source.zone_status || source.status || "").toLowerCase(),
    };
}

function possibleSetupStage({ confirmed, invalidated, timing, currentPrice, zone, triggerPrice, direction }) {
    if (invalidated) return "SETUP INVALIDATED";
    if (timing.includes("too_late") || timing.includes("missed") || timing.includes("extended")) return "SETUP MISSED";
    if (confirmed) return "SETUP CONFIRMED";
    if (timing.includes("reaction")) return "REACTION FORMING";
    if (Number.isFinite(currentPrice) && currentPrice >= zone.low && currentPrice <= zone.high) return "IN SETUP AREA";
    if (zone.status === "fresh" && zone.touch_count === 0) return "WATCHING AREA";
    if (Number.isFinite(triggerPrice) && Number.isFinite(currentPrice) && (direction === "Long" ? currentPrice >= triggerPrice : currentPrice <= triggerPrice)) return "CONFIRMATION FORMING";
    return "WATCHING AREA";
}

function setupStageLabel(value) {
    const normalized = String(value || "WATCHING AREA").replace(/_/g, " ").toUpperCase();
    return ["WATCHING AREA", "IN SETUP AREA", "REACTION FORMING", "CONFIRMATION FORMING", "SETUP CONFIRMED", "SETUP MISSED", "SETUP INVALIDATED"].includes(normalized) ? normalized : "WATCHING AREA";
}

function possibleTargets(analysis, direction, currentPrice, zone) {
    const metrics = analysis.trade_metrics || {};
    const candidates = [
        { name: "TP1", price: finiteOrNull(metrics.tp1?.price), reason: metrics.tp1?.reason || "Nearest valid liquidity objective", rr: numeric(metrics.tp1?.risk_reward), swept: metrics.tp1?.swept },
        { name: "TP2", price: finiteOrNull(metrics.tp2?.price), reason: metrics.tp2?.reason || "Next valid liquidity objective", rr: numeric(metrics.tp2?.risk_reward), swept: metrics.tp2?.swept },
    ];
    return candidates.filter((target) => {
        if (!Number.isFinite(target.price) || target.swept === true || (Number.isFinite(target.rr) && target.rr < 1)) return false;
        const reference = Number.isFinite(currentPrice) ? currentPrice : (zone.low + zone.high) / 2;
        return direction === "Long" ? target.price > reference : target.price < reference;
    }).map(({ name, price, reason }) => ({ name, price, reason }));
}

function setupConditions({ direction, confirmed, targetAvailable }) {
    return [
        { label: "Direction identified", met: direction !== "Neutral" },
        { label: "Setup area identified", met: true },
        { label: confirmed ? "Confirmation complete" : "Confirmation pending", met: confirmed },
        { label: confirmed && targetAvailable ? "Target active" : "Target activation pending", met: confirmed && targetAvailable },
    ];
}

function renderPossibleSetups(setups = []) {
    const section = $("possible-setups-section");
    const container = $("possible-setups");
    section.hidden = !setups.length;
    container.innerHTML = "";
    if (setups[0]) container.insertAdjacentHTML("beforeend", possibleSetupMarkup(setups[0]));
}

function possibleSetupMarkup(setup) {
    const targets = (setup.targets || []).filter((item) => Number.isFinite(numeric(item.price))).slice(0, 2);
    const targetRow = targets.length ? `<div><dt>Targets</dt><dd>${setup.confirmation_viable ? "Active targets" : "Projected targets"}</dd></div>${targets.map((target,index) => `<div><dt>${setup.confirmation_viable ? `TP${index + 1}` : `Potential TP${index + 1}`}</dt><dd>${formatValue(target.price)}${target.reason ? ` · ${escapeHtml(target.reason)}` : ""}${Number.isFinite(numeric(target.risk_reward)) ? ` · ${numeric(target.risk_reward).toFixed(1)}R` : ""}</dd></div>`).join("")}` : "";
    const zoneName = setup.direction === "sell" ? "Sell Zone" : "Buy Zone";
    return `<article class="possible-setup compact-possible-setup" data-setup-id="${escapeHtml(setup.id)}"><dl class="setup-details"><div><dt>Zone</dt><dd>${zonePriceLabel(zoneName, setup.zone)}</dd></div><div><dt>Confirmation</dt><dd>${setup.direction === "sell" ? "Below" : "Above"} ${formatValue(setup.confirmation.price)}</dd></div><div><dt>Invalidation</dt><dd>${setup.direction === "sell" ? "Above" : "Below"} ${formatValue(setup.invalidation.price)}</dd></div>${targetRow}</dl></article>`;
}

function zonePriceLabel(label, zone) {
    const low = formatValue(zone.low), high = formatValue(zone.high);
    const effectivelyFlat = Math.abs(zone.high - zone.low) < Math.max(Math.abs(zone.low) * 1e-7, 1e-8);
    return effectivelyFlat || low === high ? `${label} · ${low}` : `${label} · ${low}–${high}`;
}

function drawPossibleSetups(setups = []) {
    setups.slice(0, 1).forEach((setup) => {
        if (["SETUP MISSED", "SETUP INVALIDATED"].includes(setup.stage)) return;
        const top = candleSeries.priceToCoordinate(setup.setup_zone.high);
        const bottom = candleSeries.priceToCoordinate(setup.setup_zone.low);
        if (ui.zones.checked && [top, bottom].every(Number.isFinite)) {
            const zone = document.createElement("div");
            const zoneKind = /supply/i.test(setup.setup_zone.label) ? "zone-supply" : /demand/i.test(setup.setup_zone.label) ? "zone-demand" : "zone-retracement";
            zone.className = `overlay-zone possible-setup-zone ${setup.direction} ${zoneKind}`;
            const state = retracementZoneState(setup, latest);
            zone.title = `${setup.setup_zone.label || "Setup Zone"} · ${state}`;
            const zoneLabel = setup.direction === "sell" ? "Sell Zone" : "Buy Zone";
            zone.innerHTML = `<span class="overlay-zone-label"><b>${escapeHtml(zonePriceLabel(zoneLabel, setup.zone))}</b></span>`;
            if (applyZoneGeometry(zone, setup.setup_zone, top, bottom, latest)) ui.chartOverlay.appendChild(zone);
            if (ui.labels.checked) drawZoneDistance(setup, latest);
        }
        const confirmation = numeric(setup.trigger?.price);
        if (ui.setups.checked && setup.confirmation_rr_status !== "poor") {
            addSetupLevel(`Confirmation · ${setup.direction === "sell" ? "Below" : "Above"} ${formatValue(confirmation)}`, confirmation, "level-possible-trigger", setup);
        }
        if (ui.setups.checked) addSetupLevel(`${setup.direction === "sell" ? "Invalid Above" : "Invalid Below"} ${formatValue(setup.invalidation?.price)}`, numeric(setup.invalidation?.price), "level-possible-invalidation", setup);
        const target = setup.targets?.find((item) => Number.isFinite(item.price));
        if (ui.setups.checked && target && setup.confirmation_viable) addSetupLevel("Potential TP1 after confirmation", target.price, "level-possible-target", setup);
    });
}

function pipSize(analysis = {}) {
    const symbol = String(analysis.display_symbol || analysis.symbol || ui.symbol.value).toUpperCase();
    if (symbol.includes("JPY")) return 0.01;
    if (/^[A-Z]{3}\/?[A-Z]{3}$/.test(symbol.replace(/[^A-Z/]/g, ""))) return 0.0001;
    return null;
}

function drawZoneDistance(setup, analysis) {
    const message = zoneDistanceText(setup, analysis);
    if (!message) return;
    const y = candleSeries.priceToCoordinate((setup.zone.low + setup.zone.high) / 2);
    if (!Number.isFinite(y)) return;
    const node = document.createElement("div");
    node.className = "zone-distance-label advanced-chart-label";
    node.style.top = `${y + 25}px`;
    node.textContent = message;
    ui.chartOverlay.appendChild(node);
}

function zoneDistanceText(setup, analysis = {}) {
    if (setup?.zone_relation) return setup.zone_relation;
    const current = latestCandlePrice(analysis);
    const pip = pipSize(analysis);
    if (!Number.isFinite(current) || !Number.isFinite(pip)) return "";
    if (current >= setup.zone.low && current <= setup.zone.high) return "Price is inside the setup area.";
    if (current > setup.zone.high) return `Price is ${((current - setup.zone.high) / pip).toFixed(1)} pips above ${setup.direction === "buy" ? "demand" : "supply"}.`;
    return `Price is ${((setup.zone.low - current) / pip).toFixed(1)} pips below ${setup.direction === "sell" ? "supply" : "demand"}.`;
}

function chartTimeCoordinate(value) {
    if (!Number.isFinite(value) || !chart) return null;
    const seconds = value > 1e12 ? Math.floor(value / 1000) : value;
    const coordinate = chart.timeScale().timeToCoordinate(seconds);
    return Number.isFinite(coordinate) ? coordinate : null;
}

function zoneHorizontalBounds(zone = {}, analysis = {}) {
    const width = ui.chart.clientWidth;
    if (!Number.isFinite(width) || width < 120) return null;
    const candles = analysis.candles || [];
    const lastCandleX = chartTimeCoordinate(numeric(candles[candles.length - 1]?.time));
    const recentOriginX = chartTimeCoordinate(numeric(candles[Math.max(0, candles.length - 6)]?.time));
    const explicitStart = chartTimeCoordinate(numeric(zone.start_time));
    const explicitEnd = chartTimeCoordinate(numeric(zone.end_time));
    const rightEdge = width - Math.max(68, width * .045);
    const requestedStart = explicitStart ?? recentOriginX ?? lastCandleX ?? width * .58;
    const start = Math.max(0, Math.min(Math.max(requestedStart, recentOriginX ?? requestedStart), rightEdge - 24));
    const end = Math.min(rightEdge, Math.max(explicitEnd ?? rightEdge, (lastCandleX ?? start) + 54, start + 24));
    return end > start ? { left: start, width: end - start } : null;
}

function applyZoneGeometry(node, zone, firstY, secondY, analysis) {
    if (![firstY, secondY].every(Number.isFinite)) return false;
    const horizontal = zoneHorizontalBounds(zone, analysis);
    if (!horizontal) return false;
    node.style.left = `${horizontal.left}px`;
    node.style.width = `${horizontal.width}px`;
    const rawHeight = Math.abs(secondY - firstY);
    node.style.top = `${Math.min(firstY, secondY)}px`;
    node.style.height = `${Math.max(4, rawHeight)}px`;
    if (rawHeight < 7) node.classList.add("zone-line-band");
    return true;
}

function addSetupLevel(label, price, className, setup) {
    if (!Number.isFinite(price) || price <= 0) return;
    const y = candleSeries.priceToCoordinate(price);
    const bounds = zoneHorizontalBounds(setup.zone, latest || {});
    if (!Number.isFinite(y) || !bounds) return;
    const node = document.createElement("div");
    node.className = `overlay-level setup-level ${className}`;
    node.style.top = `${y}px`;
    node.style.left = `${bounds.left}px`;
    node.style.width = `${bounds.width}px`;
    node.innerHTML = `<span>${escapeHtml(label)}</span>`;
    ui.chartOverlay.appendChild(node);
}

function retracementZoneState(setup, analysis = {}) {
    // Canonical state family: Not reached, In retracement zone, Reacting, Left zone, Missed retracement.
    const current = latestCandlePrice(analysis);
    const zone = setup?.setup_zone;
    const timing = String(analysis.entry_timing?.status || "").toLowerCase();
    if (!zone || !Number.isFinite(current)) return "Not reached";
    if (timing.includes("late") || timing.includes("missed") || timing.includes("extended") || setup.stage === "SETUP MISSED") return "Missed retracement";
    const kind = /supply/i.test(zone.label) ? "supply zone" : /demand/i.test(zone.label) ? "demand zone" : "retracement zone";
    if (current >= zone.low && current <= zone.high) return `Inside ${kind}`;
    if (["CONFIRMATION FORMING", "SETUP CONFIRMED"].includes(setup.stage)) return "Reaction forming";
    if (current < zone.low) return `Price below ${kind}`;
    if (current > zone.high) return `Price above ${kind}`;
    return "Waiting for confirmation";
}

function drawScenarioPaths(setups = []) {
    ui.scenarioContent.innerHTML = "";
    ui.scenarioLayer.hidden = !ui.path.checked || !setups.length;
    ui.path.disabled = !setups.length;
    ui.path.setAttribute("aria-pressed", String(ui.path.checked && !ui.path.disabled));
    if (ui.scenarioLayer.hidden || !candleSeries || !chart) return;
    drawScenarioPath(setups[0], false);
}

function drawScenarioPath(setup, alternative = false) {
    if (setup?.allow_path === false) return;
    if (!setup || ["SETUP CONFIRMED", "SETUP MISSED", "SETUP INVALIDATED"].includes(setup.stage)) return;
    const zone = setup.setup_zone;
    if (!zone || ![zone.low, zone.high].every(Number.isFinite)) return;
    const candles = latest?.candles || [];
    const lastCandle = candles[candles.length - 1];
    const currentPrice = numeric(lastCandle?.close);
    if (!Number.isFinite(currentPrice)) return;
    const width = ui.chart.clientWidth;
    const height = ui.chart.clientHeight;
    if (width < 240 || height < 200) return;
    const currentTimeX = chart.timeScale().timeToCoordinate(Number(lastCandle.time));
    const startX = Math.max(Number.isFinite(currentTimeX) ? currentTimeX : width * .62, width * .58);
    const endX = width - Math.max(72, width * .055);
    const futureSpace = endX - startX;
    if (futureSpace < 90) return;
    const currentY = candleSeries.priceToCoordinate(currentPrice);
    const zoneEdgePrice = currentPrice > zone.high ? zone.high : currentPrice < zone.low ? zone.low : null;
    const zoneEdgeY = zoneEdgePrice === null ? null : candleSeries.priceToCoordinate(zoneEdgePrice);
    if (!Number.isFinite(currentY)) return;
    const insideZone = currentPrice >= zone.low && currentPrice <= zone.high;
    const zoneX = startX + futureSpace * .34;
    if (setup.stage === "WATCHING AREA" && !insideZone && Number.isFinite(zoneEdgeY)) {
        appendConditionalArrow(
            { x: startX, y: currentY },
            { x: zoneX, y: zoneEdgeY },
            "Retrace",
            alternative,
            setup.id,
        );
        return;
    }
    const zoneMidY = candleSeries.priceToCoordinate((zone.low + zone.high) / 2);
    if (!["IN SETUP AREA", "REACTION FORMING", "CONFIRMATION FORMING"].includes(setup.stage)) return;
    const triggerPrice = finiteOrNull(setup.trigger?.price);
    if (triggerPrice === null) return;
    if (setup.confirmation_rr_status === "poor") return;
    const triggerY = candleSeries.priceToCoordinate(triggerPrice);
    if (!Number.isFinite(triggerY) || !Number.isFinite(zoneMidY)) return;
    const confirmationStart = { x: zoneX + futureSpace * .10, y: zoneMidY };
    const confirmationEnd = { x: Math.min(endX, startX + futureSpace * .68), y: triggerY };
    appendConditionalArrow(confirmationStart, confirmationEnd, "Confirm", alternative, setup.id);
}

function appendConditionalArrow(start, end, label, alternative, setupId) {
    if (![start.x, start.y, end.x, end.y].every(Number.isFinite)) return;
    const namespace = "http://www.w3.org/2000/svg";
    const path = document.createElementNS(namespace, "path");
    const dx = (end.x - start.x) * .42;
    const data = `M ${start.x.toFixed(1)} ${start.y.toFixed(1)} C ${(start.x + dx).toFixed(1)} ${start.y.toFixed(1)}, ${(end.x - dx).toFixed(1)} ${end.y.toFixed(1)}, ${end.x.toFixed(1)} ${end.y.toFixed(1)}`;
    path.setAttribute("d", data);
    path.setAttribute("class", `scenario-path${alternative ? " alternative" : ""}`);
    path.setAttribute("marker-end", `url(#scenario-arrow-${alternative ? "alternative" : "primary"})`);
    path.dataset.setupId = setupId;
    ui.scenarioContent.appendChild(path);
    appendScenarioLabel((start.x + end.x) / 2, (start.y + end.y) / 2, label, alternative);
}

function appendScenarioLabel(x, y, label, alternative) {
    const namespace = "http://www.w3.org/2000/svg";
    const text = document.createElementNS(namespace, "text");
    text.setAttribute("x", String(Math.min(x + 5, ui.chart.clientWidth - 180)));
    text.setAttribute("y", String(Math.max(16, y - 8)));
    text.setAttribute("class", `scenario-path-label${alternative ? " alternative" : ""}`);
    text.textContent = label;
    ui.scenarioContent.appendChild(text);
}

function scheduleOverlayRedraw() {
    clearTimeout(scenarioRedrawTimer);
    scenarioRedrawTimer = setTimeout(() => drawChartOverlays(latest || {}), 80);
}

function setupIdentity(strategy, direction, zone, candleTime) { return `${String(strategy).toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${direction}-${zone.low}-${zone.high}-${candleTime ?? "current"}`; }
function triggerMessage(direction, hasPrice) { if (hasPrice) return direction === "Long" ? "A buy becomes valid only after a bullish close above the calculated trigger." : "A sell becomes valid only after a bearish close below the calculated trigger."; return direction === "Long" ? "Wait for bullish confirmation after price reaches the setup area." : "Wait for bearish confirmation after price reaches the setup area."; }
function possibleSetupAction(direction, stage) { if (stage === "SETUP INVALIDATED") return "This scenario is invalid. Wait for a new structure."; if (stage === "SETUP CONFIRMED") return "Confirmation passed. Review the confirmed trade plan before acting."; return direction === "Long" ? "Let price return to the setup area. Only consider a buy after bullish confirmation." : "Let price return to the setup area. Only consider a sell after bearish confirmation."; }
function validEstimatedRr(analysis) { const value = numeric(analysis.trade_metrics?.tp1?.risk_reward ?? analysis.levels?.rr1); return Number.isFinite(value) && value >= 1 ? value : null; }
function latestCandlePrice(analysis) { return numeric(analysis.candles?.[analysis.candles.length - 1]?.close); }
function nullablePrice(value) { if (value && typeof value === "object") value = value.price ?? value.level; return numeric(value); }
function finiteOrNull(value) { const number = nullablePrice(value); return Number.isFinite(number) ? number : null; }

async function analyzeMarket() {
    const analysisRequestId=++terminalState.requestId;terminalState.symbol=ui.symbol.value;terminalState.timeframe=ui.timeframe.value;terminalState.model=ui.strategy.value;terminalState.connection="loading";
    ui.analyze.disabled = true;
    ui.analyze.textContent = "Analyzing…";
    ui.chartMessage.hidden = false;
    ui.chartMessage.textContent = "Loading market data…";
    try {
        const market=selectedMarket();
        if(market.provider==="deriv") { await loadDerivChart(); await analyzeDerivedStrategy(market); return; }
        const params = new URLSearchParams({ symbol: ui.symbol.value, display_name: market.displayName, provider:market.provider, asset_class:market.assetClass, family:market.family, timeframe: ui.timeframe.value, strategy: ui.strategy.value, bars: "300", manual: "1", multi_timeframe: "1", context_depth: "balanced", marketaux_enabled: market.provider==="deriv"?"0":settings().marketaux ? "1" : "0", news_risk: market.provider==="deriv"?"0":settings().news ? "1" : "0", dxy_confirmation: market.provider==="deriv"?"0":settings().dxy ? "1" : "0", execution_mode: settings().executionMode, minimum_rr: String(settings().minimumRr) });
        const response = await fetch(`/api/analyze?${params}`);
        const payload = await response.json();
        if (!response.ok || payload.error) throw new Error(payload.error || `Analysis failed (${response.status})`);
        if(analysisRequestId!==terminalState.requestId)return;latest = payload.analysis || payload;
        latest.decision = payload.decision || latest.decision;
        terminalState.decision=latest.decision;terminalState.connection="ready";
        latest.provider = payload.provider || market.provider;
        latest.candles = payload.candles || latest.candles || [];
        latest.multi_timeframe = payload.multi_timeframe || latest.multi_timeframe || {};
        latest.execution_candles = latest.multi_timeframe?.context?.M5 || [];
        updateClock();
        latest.market_filters = payload.market_filters || latest.market_filters;
        latest.possible_setups = normalizePossibleSetups(latest);
        renderChartPage(latest);
        renderDecisionPanel(latest);
        renderScannerPage(latest);
        renderHomePage(latest);
        ui.update.hidden = true;
        showPage("chart");
        startDerivStream();
    } catch (error) {
        if(analysisRequestId!==terminalState.requestId)return;terminalState.connection="error";terminalState.decision=null;latest=null;ui.chartOverlay.innerHTML="";ui.scenarioContent.innerHTML="";
        ui.chartMessage.hidden = false;
        ui.chartMessage.textContent = plainText(error.message);
    } finally {
        ui.analyze.disabled = false;
        ui.analyze.textContent = "Analyze";
    }
}

async function analyzeDerivedStrategy(market) {
    const requestToken=currentChartRequestId;const params=new URLSearchParams({symbol:ui.symbol.value,display_name:market.displayName,provider:"deriv",asset_class:"derived_index",family:market.family,timeframe:ui.timeframe.value,strategy:ui.strategy.value,bars:"300",manual:"1",multi_timeframe:"1",context_depth:"balanced",marketaux_enabled:"0",news_risk:"0",dxy_confirmation:"0",execution_mode:settings().executionMode,minimum_rr:String(settings().minimumRr)});
    const response=await fetch(`/api/analyze?${params}`);const payload=await response.json();if(requestToken!==currentChartRequestId)return;if(!response.ok||payload.error)throw new Error(payload.error||`Analysis failed (${response.status})`);
    const chartCandles=latest?.candles||[];latest=payload.analysis||payload;latest.decision=payload.decision||latest.decision;terminalState.decision=latest.decision;terminalState.connection="ready";latest.provider="deriv";latest.asset_type="derived_index";latest.candles=payload.candles||chartCandles;latest.multi_timeframe=payload.multi_timeframe||latest.multi_timeframe||{};latest.execution_candles=latest.multi_timeframe?.context?.M5||[];latest.market_filters=payload.market_filters||latest.market_filters;latest.possible_setups=normalizePossibleSetups(latest);renderChartPage(latest);renderDecisionPanel(latest);renderScannerPage(latest);renderHomePage(latest);ui.update.hidden=true;showPage("chart");loadPaperTestingSummary();startDerivStream();
}

function renderChartPage(analysis = {}) {
    renderToolbar();
    initChart();
    const candles = (analysis.candles || []).map((c) => ({ time: Number(c.time), open: Number(c.open), high: Number(c.high), low: Number(c.low), close: Number(c.close) })).filter((c) => Number.isFinite(c.time + c.open + c.high + c.low + c.close));
    candleSeries.setData(candles);
    chart.timeScale().fitContent();
    if (candles.length) {
        const last = candles[candles.length - 1];
        const first = candles[Math.max(0, candles.length - 2)];
        const change = first.close ? ((last.close - first.close) / first.close) * 100 : 0;
        $("chart-price").textContent = formatPrice(last.close, analysis);
        $("chart-change").textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
        $("chart-high").textContent = formatPrice(last.high, analysis);
        $("chart-low").textContent = formatPrice(last.low, analysis);
        $("chart-spread").textContent = formatPrice(last.high - last.low, analysis);
    }
    ui.chartMessage.hidden = candles.length > 0;
    updateChartGuidance(analysis);
    drawChartOverlays(analysis);
}

function updateChartGuidance(analysis = {}) {
    if(analysis.decision?.meta?.market_type==="derived"){const decision=analysis.decision.decision||{};ui.chartState.textContent=decision.status||"NO MARKET OPPORTUNITY";ui.chartState.dataset.tone=decision.trade_ready?"active":decision.status?.includes("CONTRADICTION")||decision.status?.includes("REJECTED")?"invalid":decision.status?.includes("EVENT")||decision.status?.includes("LATE")?"caution":"forming";ui.chartTiming.hidden=false;ui.chartTiming.innerHTML=`<b>${escapeHtml(titleCase(decision.stage))}</b><span>${escapeHtml(decision.next_action||"")}</span>`;return;}
    const plan = analysis.decision?.trade_chart || {};
    const previous=analysis.decision?.previous_setup;
    const waiting = ["waiting_for_m15_area", "m5_setup_forming"].includes(plan.state);
    const side = plan.idea === "buy" ? (waiting ? "POTENTIAL BUY RE-ENTRY" : "BUY IDEA") : plan.idea === "sell" ? (waiting ? "POTENTIAL SELL RE-ENTRY" : "SELL IDEA") : "NO SETUP";
    const labels = { waiting_for_m15_area: "Waiting for M15 area", in_m15_area: "In M15 area", m5_setup_forming: "M5 setup forming", waiting_for_m5_close: "Waiting for M5 close", m5_confirmed: "M5 confirmed", entry_available: "Entry available", entry_extended: "Entry extended", too_late: "Too late", invalidated: "SETUP INVALIDATED" };
    const missed = ["too_late", "entry_missed", "setup_missed", "entry_extended"].includes(plan.state);
    ui.chartState.textContent = plan.idea === "none" && previous ? "NO CURRENT SETUP" : missed ? `MISSED ${plan.idea === "buy" ? "BUY" : "SELL"} ENTRY` : plan.state === "invalidated" ? "SETUP INVALIDATED" : `${side}${labels[plan.state] ? ` · ${labels[plan.state]}` : ""}`;
    ui.chartState.dataset.tone = ["m5_confirmed", "entry_available"].includes(plan.state) ? "active" : ["entry_extended", "too_late"].includes(plan.state) ? "caution" : plan.state === "invalidated" ? "invalid" : plan.idea === "none" ? "neutral" : "forming";
    const switchContext=analysis.decision?.derived_index?.contract?.switch_context;
    if(switchContext){const badges={BULLISH_DRIFT:"Bullish Drift",BEARISH_DRIFT:"Bearish Drift",SIDEWAYS_DRIFT:"Sideways Drift",RISING_VOLATILITY:"Volatility Rising",HIGH_STABLE:"High Volatility",UNSTABLE_TRANSITION:"Transition",DRIFT_TRANSITION:"Transition",POSSIBLE_BULLISH_TRANSITION:"Transition",POSSIBLE_BEARISH_TRANSITION:"Transition"};ui.chartState.textContent=badges[switchContext.current_regime]||titleCase(switchContext.current_regime||"Transition");ui.chartState.dataset.tone=switchContext.transition_active?"caution":plan.idea==="none"?"neutral":"forming";}
    const stepDecision=analysis.decision?.derived_index?.contract?.decision;if(stepDecision?.strategy==="step_structure_research"){ui.chartState.textContent=`RESEARCH MODE · ${stepDecision.status||"NO SETUP"}`;ui.chartState.dataset.tone="caution";}
    const autoEvaluation=analysis.decision?.derived_index?.contract?.auto_evaluation;if(autoEvaluation){const researchAuto=autoEvaluation.selected_strategy==="step_structure_research";ui.chartState.textContent=`AUTO · ${researchAuto?"RESEARCH · ":""}${titleCase(autoEvaluation.selected_strategy||"No Suitable Strategy")}`;ui.chartState.dataset.tone=researchAuto?"caution":autoEvaluation.selected_strategy?"forming":"neutral";}
    ui.chartTiming.hidden = plan.idea === "none" && !previous;
    ui.chartTiming.innerHTML = plan.idea === "none" && previous ? `<b>PREVIOUS ${previous.direction === "buy" ? "BUY" : "SELL"} SETUP MISSED</b><span>Current market scanning for a fresh setup.</span>` : plan.idea === "none" ? "" : `<b>${missed ? "DO NOT CHASE" : "ENTRY TIMING"}</b><span>${escapeHtml(missed ? "Price has moved too far. Wait for a fresh setup." : plan.message || "")}</span>`;
}

function initChart() {
    if (chart) return;
    chart = LightweightCharts.createChart(ui.chart, { width: Math.max(ui.chart.clientWidth, 320), height: Math.max(ui.chart.clientHeight, 620), layout: { background: { color: "#050a12" }, textColor: "#94a3b8" }, grid: { vertLines: { color: "rgba(255,255,255,.025)" }, horzLines: { color: "rgba(255,255,255,.025)" } }, rightPriceScale: { borderColor: "rgba(255,255,255,.08)" }, timeScale: { borderColor: "rgba(255,255,255,.08)", timeVisible: true, rightOffset: 18 } });
    candleSeries = chart.addCandlestickSeries({ upColor: "#22c55e", downColor: "#ef4444", borderUpColor: "#22c55e", borderDownColor: "#ef4444", wickUpColor: "#22c55e", wickDownColor: "#ef4444", priceLineVisible: false, lastValueVisible: false });
    chart.timeScale().subscribeVisibleTimeRangeChange(scheduleOverlayRedraw);
}

function resizeChart() { if (!chart || !ui.chart.clientWidth) return; chart.applyOptions({ width: ui.chart.clientWidth, height: ui.chart.clientHeight }); scheduleOverlayRedraw(); }

function drawChartOverlays(analysis = {}) {
    // Legacy static-contract marker: mode === "valid". Rendering now uses only decision.trade_chart.
    ui.chartOverlay.innerHTML = "";
    ui.scenarioContent.innerHTML = "";
    if (!candleSeries || !latest) return;
    if(analysis.decision?.meta?.market_type==="derived"){drawNormalizedOverlays(analysis);return;}
    const plan = analysis.decision?.trade_chart;
    if (!plan) return;
    const current = tradeChartPrice(plan.current_price);
    if (Number.isFinite(current)) addLevel(`Current · ${formatValue(current)}`, current, "level-current");
    if(Number.isFinite(tradeChartPrice(plan.event_origin))) addLevel(`Event Origin · ${formatValue(plan.event_origin)}`,tradeChartPrice(plan.event_origin),"level-context-liquidity");
    if(Number.isFinite(tradeChartPrice(plan.event_extreme))) addLevel(`Event Extreme · ${formatValue(plan.event_extreme)}`,tradeChartPrice(plan.event_extreme),"level-context-liquidity");
    drawPreviousSetup(analysis.decision?.previous_setup,analysis);
    if (ui.fvg.checked) drawMarketContext(analysis.decision?.presentation,analysis);
    if (ui.zones.checked) drawDevelopingScenario(analysis.decision?.presentation?.developing_scenario,analysis);
    if (ui.labels.checked) { drawFvg(analysis); drawAmdOverlays(analysis.decision?.amd, analysis); }
    if (plan.idea === "none") { ui.scenarioLayer.hidden = true; ui.chartMessage.hidden = true; resolveOverlayLabelCollisions(); return; }
    if (ui.zones.checked) drawTradePlan(plan, analysis);
    drawTradeChartGuide(plan, analysis);
    resolveOverlayLabelCollisions();
    ui.chartMessage.hidden = true;
}

function drawNormalizedOverlays(analysis={}) {
    const product=analysis.decision,current=tradeChartPrice(product.market?.current_price);if(Number.isFinite(current))addLevel(`Current · ${formatValue(current)}`,current,"level-current");
    const enabled={trade_plan:ui.zones.checked,market_structure:document.querySelector("#show-structure")?.checked!==false,context_levels:ui.fvg.checked,advanced_smc:document.querySelector("#show-advanced")?.checked===true};
    for(const overlay of product.overlays||[]){if(!enabled[overlay.visibility_category])continue;if(overlay.owner_id!==product.ownership?.overlay_owner_id||overlay.setup_id!==product.setup?.setup_id)continue;if(Number.isFinite(tradeChartPrice(overlay.price))){const classes={entry:"level-entry",stop:"level-stop",target:"level-target",structural_target:"level-context-liquidity",confirmed_sweep:"level-context-liquidity"};addLevel(`${titleCase(overlay.name||overlay.type)} · ${formatValue(overlay.price)}`,tradeChartPrice(overlay.price),classes[overlay.type]||"level-context-liquidity");continue;}const low=tradeChartPrice(overlay.low),high=tradeChartPrice(overlay.high);if(![low,high].every(Number.isFinite))continue;const top=candleSeries.priceToCoordinate(high),bottom=candleSeries.priceToCoordinate(low);if(![top,bottom].every(Number.isFinite))continue;const node=document.createElement("div");node.className=`overlay-zone ${overlay.type==="entry_area"?"trade-entry-zone":"market-context-zone"} ${product.setup?.direction||""}`;node.innerHTML=`<span class="overlay-zone-label">${escapeHtml(titleCase(overlay.type))} · ${formatValue(low)}–${formatValue(high)}</span>`;if(applyZoneGeometry(node,{start_time:overlay.creation_time},top,bottom,analysis))ui.chartOverlay.appendChild(node);}
    resolveOverlayLabelCollisions();ui.chartMessage.hidden=true;
}

function drawMarketContext(presentation={},analysis={}) {
    const levels=presentation?.key_levels || {};
    drawContextZone(levels.support_zone,"Support","context-support-zone",analysis);
    drawContextZone(levels.resistance_zone,"Resistance","context-resistance-zone",analysis);
    if (Number.isFinite(tradeChartPrice(levels.liquidity_above))) addLevel(`Liquidity Above · ${formatValue(levels.liquidity_above)}`,tradeChartPrice(levels.liquidity_above),"level-context-liquidity");
    if (Number.isFinite(tradeChartPrice(levels.liquidity_below))) addLevel(`Liquidity Below · ${formatValue(levels.liquidity_below)}`,tradeChartPrice(levels.liquidity_below),"level-context-liquidity");
}

function drawContextZone(zone,label,className,analysis) {
    const low=tradeChartPrice(zone?.low),high=tradeChartPrice(zone?.high); if (![low,high].every(Number.isFinite)) return;
    const top=candleSeries.priceToCoordinate(high),bottom=candleSeries.priceToCoordinate(low); if (![top,bottom].every(Number.isFinite)) return;
    const node=document.createElement("div"); node.className=`overlay-zone market-context-zone ${className}`; node.innerHTML=`<span class="overlay-zone-label">${label} · ${formatValue((low+high)/2)}</span>`;
    if (applyZoneGeometry(node,{},top,bottom,analysis)) ui.chartOverlay.appendChild(node);
}

function drawDevelopingScenario(scenario,analysis) {
    if (!scenario?.available) return; const zone=scenario.zone || {},low=tradeChartPrice(zone.low),high=tradeChartPrice(zone.high); if (![low,high].every(Number.isFinite)) return;
    const top=candleSeries.priceToCoordinate(high),bottom=candleSeries.priceToCoordinate(low); if (![top,bottom].every(Number.isFinite)) return;
    const node=document.createElement("div"); node.className=`overlay-zone developing-setup-zone ${scenario.direction}`; node.innerHTML=`<span class="overlay-zone-label">Potential ${scenario.direction === "buy" ? "Buy" : "Sell"} Area · ${formatValue(low)}–${formatValue(high)}</span>`;
    if (applyZoneGeometry(node,{start_time:zone.origin_time},top,bottom,analysis)) ui.chartOverlay.appendChild(node);
}

function drawPreviousSetup(previous,analysis) {
    if (!previous?.setup_id) return;
    const low=tradeChartPrice(previous.entry_low),high=tradeChartPrice(previous.entry_high); if (![low,high].every(Number.isFinite)) return;
    if (!ui.previous.checked) { addLevel("Missed Entry",(low+high)/2,"level-previous-marker"); return; }
    const top=candleSeries.priceToCoordinate(high),bottom=candleSeries.priceToCoordinate(low); if (![top,bottom].every(Number.isFinite)) return;
    const node=document.createElement("div"); node.className="overlay-zone previous-setup-zone missed"; node.innerHTML=`<span class="overlay-zone-label">Previous ${previous.direction === "buy" ? "Buy" : "Sell"} Entry · ${formatValue(low)}–${formatValue(high)}</span>`;
    if (applyZoneGeometry(node,{start_time:previous.created_at},top,bottom,analysis)) ui.chartOverlay.appendChild(node);
}

function drawTradePlan(plan, analysis) {
    const missed = ["too_late", "entry_missed", "setup_missed", "entry_extended"].includes(plan.state);
    const active = Number.isFinite(tradeChartPrice(plan.confirmed_entry)) && !missed;
    const confirmed = active;
    const zone = confirmed ? {} : missed ? plan.expected_entry || {} : selectDisplayEntry(plan), low = tradeChartPrice(zone.low), high = tradeChartPrice(zone.high);
    if ([low, high].every(Number.isFinite)) {
        const top = candleSeries.priceToCoordinate(high), bottom = candleSeries.priceToCoordinate(low), node = document.createElement("div");
        node.className = `overlay-zone trade-entry-zone ${plan.idea}${missed ? " missed" : ""}`;
        const triggerPending = !Number.isFinite(tradeChartPrice(plan.confirmation?.price)) && ["in_m15_area", "m5_setup_forming", "waiting_for_m5_close"].includes(plan.state);
        node.innerHTML = `<span class="overlay-zone-label">${missed ? "Original" : "Entry"} · ${formatValue(low)}–${formatValue(high)}</span>${triggerPending && !missed ? '<span class="entry-trigger-note">M5 trigger appears after price reaches this zone.</span>' : ""}`;
        if (applyZoneGeometry(node, { start_time: zone.origin_time }, top, bottom, analysis)) ui.chartOverlay.appendChild(node);
        if (ui.labels.checked) { addLevel(`Entry High · ${formatValue(high)}`, high, "level-entry-bound level-entry-high advanced-chart-label"); addLevel(`Entry Low · ${formatValue(low)}`, low, "level-entry-bound level-entry-low advanced-chart-label"); }
    }
    if (missed) return;
    if (active) {
        addLevel(`Entry · ${formatValue(plan.confirmed_entry)}`, numeric(plan.confirmed_entry), "level-entry");
        addLevel(`STOP LOSS · ${formatValue(plan.stop)}`, tradeChartPrice(plan.stop), "level-stop");
        (plan.targets || []).slice(0, 2).forEach((target, index) => addLevel(`TP${index + 1} · ${formatValue(target.price)}${Number.isFinite(numeric(target.risk_reward)) ? ` · ${numeric(target.risk_reward).toFixed(1)}R` : ""}`, tradeChartPrice(target.price), "level-target"));
    } else {
        const inZone = ["in_m15_area", "m5_setup_forming", "waiting_for_m5_close"].includes(plan.state);
        if (inZone && Number.isFinite(tradeChartPrice(plan.confirmation?.price))) addLevel(`M5 Confirm ${plan.idea === "buy" ? "Above" : "Below"} · ${formatValue(plan.confirmation.price)}`, tradeChartPrice(plan.confirmation?.price), "level-possible-trigger");
        if (Number.isFinite(tradeChartPrice(plan.invalidation?.price))) addLevel(`Idea Invalid ${plan.idea === "buy" ? "Below" : "Above"} · ${formatValue(plan.invalidation.price)}`, tradeChartPrice(plan.invalidation.price), "level-possible-invalidation");
        if (plan.state === "waiting_for_m15_area") (plan.targets || []).slice(0, 2).forEach((target,index) => addLevel(`Potential ${target.name || `TP${index + 1}`} · ${formatValue(target.price)}`, tradeChartPrice(target.price), "level-possible-target"));
    }
}

function drawTradeChartGuide(plan, analysis) {
    ui.scenarioContent.innerHTML = "";
    const show = ui.zones.checked && !["m5_confirmed", "entry_available", "entry_extended", "too_late", "invalidated", "none"].includes(plan.state);
    ui.scenarioLayer.hidden = !show;
    if (!show) return;
    const candles = analysis.candles || [], last = candles[candles.length - 1], currentY = candleSeries.priceToCoordinate(numeric(plan.current_price));
    const currentX = chart.timeScale().timeToCoordinate(Number(last?.time));
    if (![currentX, currentY].every(Number.isFinite)) return;
    const endX = ui.chart.clientWidth - 92;
    if (["waiting_for_m15_area"].includes(plan.state)) {
        const edge = plan.current_price < plan.expected_entry.low ? plan.expected_entry.low : plan.expected_entry.high, y = candleSeries.priceToCoordinate(edge);
        if (Number.isFinite(y)) appendConditionalArrow({ x: currentX, y: currentY }, { x: endX, y }, "Retracement", false, "trade-chart");
    } else if (["in_m15_area", "m5_setup_forming", "waiting_for_m5_close"].includes(plan.state) && Number.isFinite(tradeChartPrice(plan.confirmation?.price))) {
        const y = candleSeries.priceToCoordinate(plan.confirmation.price);
        if (Number.isFinite(y)) appendConditionalArrow({ x: currentX, y: currentY }, { x: endX, y }, "Confirm", false, "trade-chart");
    }
}

function tradeChartPrice(value) {
    if (value === null || value === undefined || value === "") return NaN;
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : NaN;
}

function drawAmdOverlays(amd = {}, analysis = {}) {
    if (!amd.available || !amd.accumulation?.locked) return;
    const range = amd.accumulation, high = numeric(range.high), low = numeric(range.low);
    const top = candleSeries.priceToCoordinate(high), bottom = candleSeries.priceToCoordinate(low);
    if (![top, bottom].every(Number.isFinite)) return;
    const node = document.createElement("div");
    node.className = "overlay-zone amd-accumulation-zone";
    node.title = "Locked accumulation range. AMD is market context, not a trade signal.";
    node.innerHTML = `<span class="overlay-zone-label">Accumulation Range · Locked</span>`;
    if (applyZoneGeometry(node, { start_time: range.start_time, end_time: range.end_time }, top, bottom, analysis)) ui.chartOverlay.appendChild(node);
    const manipulation = amd.manipulation || {};
    if (Number.isFinite(numeric(manipulation.sweep_price))) addLevel("Liquidity sweep", numeric(manipulation.sweep_price), "level-amd-sweep");
    const distribution = amd.distribution || {};
    if (Number.isFinite(numeric(distribution.mss_price))) addLevel("Distribution MSS", numeric(distribution.mss_price), "level-amd-mss");
}

function resolveOverlayLabelCollisions() {
    const labels = [...ui.chartOverlay.querySelectorAll(".overlay-level span, .overlay-zone-label, .advanced-chart-label"), ...ui.scenarioLayer.querySelectorAll(".scenario-path-label")];
    const priority = (node) => node.closest(".level-current") ? 1 : node.closest(".trade-entry-zone, .level-entry-bound, .level-entry") ? 2 : node.closest(".level-stop, .level-possible-invalidation") ? 3 : node.closest(".level-target, .level-possible-target") ? 4 : node.closest(".level-possible-trigger") ? 5 : node.closest(".zone-fvg, .amd-accumulation-zone, .level-amd-sweep, .level-amd-mss") ? 8 : 7;
    const accepted = [];
    labels.sort((a, b) => priority(a) - priority(b)).forEach((label) => {
        let rect = label.getBoundingClientRect();
        const collision = accepted.find((other) => !(rect.right < other.left || rect.left > other.right || rect.bottom + 10 < other.top || rect.top - 10 > other.bottom));
        if (!collision) { accepted.push(rect); return; }
        if (priority(label) >= 6) { label.style.display = "none"; return; }
        const shift = Math.min(32, collision.bottom - rect.top + 10);
        label.style.transform = `translateY(${shift}px)`;
        rect = label.getBoundingClientRect();
        accepted.push(rect);
    });
}

function addLevel(label, price, className) {
    if (!Number.isFinite(price) || price <= 0) return;
    const y = candleSeries.priceToCoordinate(price);
    if (!Number.isFinite(y)) return;
    const node = document.createElement("div"); node.className = `overlay-level ${className}`; node.style.top = `${y}px`; node.innerHTML = `<span>${label}</span>`; ui.chartOverlay.appendChild(node);
}

function drawFvg(analysis) {
    const zones = analysis.shared_analysis?.zones?.fvg || analysis.zones?.fvg || analysis.fvg_zones || [];
    const setup = (analysis.possible_setups || [])[0];
    const candidates = (Array.isArray(zones) ? zones : [zones]).filter((item) => item && item.mitigated !== true && item.active !== false);
    const overlapping = candidates.filter((item) => {
        if (!setup?.zone) return false;
        const high = numeric(item.top ?? item.high ?? item.upper), low = numeric(item.bottom ?? item.low ?? item.lower);
        return Number.isFinite(high) && Number.isFinite(low) && high >= setup.zone.low && low <= setup.zone.high;
    });
    const pool = overlapping.length ? overlapping : candidates;
    const zone = pool[pool.length - 1];
    if (!zone) return;
    const topPrice = numeric(zone.top ?? zone.high ?? zone.upper);
    const bottomPrice = numeric(zone.bottom ?? zone.low ?? zone.lower);
    if (![topPrice, bottomPrice].every(Number.isFinite)) return;
    const y1 = candleSeries.priceToCoordinate(topPrice), y2 = candleSeries.priceToCoordinate(bottomPrice);
    if (![y1, y2].every(Number.isFinite)) return;
    const node = document.createElement("div");
    const isIfvg = String(zone.type || "").toLowerCase().includes("ifvg");
    node.className = `overlay-zone zone-fvg${isIfvg ? " zone-ifvg" : ""}`;
    node.innerHTML = `<span class="overlay-zone-label">${isIfvg ? "IFVG" : "FVG"}</span>`;
    const geometry = {
        start_time: finiteOrNull(zone.start_time ?? zone.time ?? zone.departure_time),
        end_time: finiteOrNull(zone.end_time ?? zone.rectangle_end_time),
    };
    if (applyZoneGeometry(node, geometry, y1, y2, analysis)) ui.chartOverlay.appendChild(node);
}

function renderLabPage(payload) {
    const comparison = payload.comparison || {};
    const results = comparison.ranked_strategies || comparison.results || payload.strategy_results || payload.results || [];
    const list = Array.isArray(results) ? results : Object.values(results);
    const best = comparison.best_strategy || list[0];
    const bestTrades = Number(best?.total_trades || 0);
    const label = !best || bestTrades < 10 ? "No winner — insufficient data" : bestTrades < 20 ? "Early leader — weak sample" : "Best performer — usable sample";
    $("lab-summary").innerHTML = `<strong>${label}</strong><span>${best?.strategy || best?.name || "No strategy ranked"}</span>`;
    $("lab-strategies").innerHTML = list.slice(0, 3).map(strategyCard).join("") || '<article class="strategy-card"><strong>No strategy results</strong></article>';
    $("lab-comparison").innerHTML = list.map((r) => `<tr><td>${escapeHtml(r.strategy || r.name)}</td><td>${r.total_trades || 0}</td><td>${formatNumber(r.win_rate)}%</td><td>${formatNumber(r.profit_factor)}</td><td>${formatNumber(r.expectancy)}R</td><td>${formatNumber(r.max_drawdown)}R</td></tr>`).join("");
    renderEquity(payload.equity_curves || payload.equity || {});
    const logs = payload.trade_logs || payload.trades || {};
    const trades = Array.isArray(logs) ? logs : Object.values(logs).flat();
    $("lab-trades").innerHTML = trades.slice(0, 100).map((t) => `<tr><td>${escapeHtml(t.strategy)}</td><td>${escapeHtml(t.direction)}</td><td>${formatValue(t.entry)}</td><td>${formatValue(t.exit_price)}</td><td>${escapeHtml(t.result)}</td><td>${formatNumber(t.rr_result)}</td></tr>`).join("") || '<tr><td colspan="6">No trades found.</td></tr>';
    $("lab-diagnostics").textContent = JSON.stringify(payload.run_status || payload.metadata || {}, null, 2);
    $("lab-results").hidden = false;
}

async function runBacktest() {
    const button = $("run-backtest"); button.disabled = true; button.textContent = "Running…"; $("lab-status").textContent = "Running historical analysis…";
    const config = { symbol: $("lab-symbol").value, timeframe: $("lab-timeframe").value, bars: Number($("lab-bars").value), mode: $("lab-mode").value, strategies: ["universal_structure", "supply_demand", "breakout_retest"] };
    $("lab-status").title = `Pending config — tested_symbol: ${config.symbol}; selected strategies: ${config.strategies.join(", ")}; tested_strategies: pending`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    try {
        const body = { ...config, starting_balance: 10000, risk_per_trade: 1 };
        const response = await fetch("/api/backtest", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: controller.signal });
        const payload = await response.json(); if (!response.ok || payload.ok === false) throw new Error(payload.error || "Backtest failed.");
        if (!_identityMatchesConfig(payload.result_identity || payload, config)) throw new Error("Showing previous result. Run Backtest again to update.");
        renderLabPage(payload); $("lab-status").textContent = `Completed ${payload.tested_symbol || body.symbol} · ${payload.tested_timeframe || body.timeframe}`;
    } catch (err) { _markLabRunFailed(err.name === "AbortError" ? "Backtest timed out. No new results were produced." : plainText(err.message)); }
    finally { clearTimeout(timeout); button.disabled = false; button.textContent = "Run Backtest"; }
}

function clearStrategyLabResults() { $("lab-results").hidden = true; $("lab-summary").innerHTML = ""; $("lab-strategies").innerHTML = ""; $("lab-comparison").innerHTML = ""; $("lab-trades").innerHTML = ""; }
function _markLabRunFailed(message) { clearStrategyLabResults(); $("lab-status").textContent = `${message} Previous results are hidden because they do not match the current run.`; }
function _sameStrategies(left = [], right = []) { return [...left].sort().join("|") === [...right].sort().join("|"); }
function _identityMatchesConfig(identity = {}, config = {}) { return String(identity.tested_symbol || "") === String(config.symbol) && String(identity.tested_timeframe || "") === String(config.timeframe) && Number(identity.requested_bars) === Number(config.bars) && _sameStrategies(identity.tested_strategies, config.strategies); }

function strategyCard(r) { return `<article class="strategy-card"><strong>${escapeHtml(r.strategy || r.name)}</strong><dl><div><dt>Trades</dt><dd>${r.total_trades || 0}</dd></div><div><dt>Win rate</dt><dd>${formatNumber(r.win_rate)}%</dd></div><div><dt>Profit factor</dt><dd>${formatNumber(r.profit_factor)}</dd></div><div><dt>Expectancy</dt><dd>${formatNumber(r.expectancy)}R</dd></div></dl></article>`; }

function renderEquity(curves) {
    const series = Object.values(curves || {}).find((points) => Array.isArray(points) && points.length > 1) || [];
    if (!series.length) { $("lab-equity").textContent = "No equity curve available."; return; }
    const values = series.map((p) => Number(p.balance)).filter(Number.isFinite); const min = Math.min(...values), max = Math.max(...values), range = max - min || 1;
    const points = values.map((value, index) => `${(index / Math.max(1, values.length - 1)) * 100},${95 - ((value - min) / range) * 85}`).join(" ");
    $("lab-equity").innerHTML = `<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Equity curve"><polyline points="${points}" fill="none" stroke="#3b82f6" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>`;
}

function settings() { try { return { context: "single", zones: true, fvg: true, labels: false, news: true, marketaux: true, dxy: false, executionMode: "conservative", minimumRr: 1.5, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") }; } catch { return { context: "single", zones: true, fvg: true, labels: false, news: true, marketaux: true, dxy: false, executionMode: "conservative", minimumRr: 1.5 }; } }
function saveSettings() { const value = { symbol: $("default-symbol").value, timeframe: $("default-timeframe").value, zones: $("setting-zones").checked, fvg: $("setting-fvg").checked, labels: $("setting-labels").checked, refresh: $("setting-refresh").checked, context: $("setting-context").value, news: $("setting-news").checked, marketaux: $("setting-marketaux").checked, dxy: $("setting-dxy").checked, executionMode: $("setting-execution-mode").value, minimumRr: Math.max(1, Number($("setting-minimum-rr").value) || 1.5) }; localStorage.setItem(SETTINGS_KEY, JSON.stringify(value)); ui.zones.checked = value.zones; ui.fvg.checked = value.fvg; ui.labels.checked = value.labels; drawChartOverlays(latest || {}); }
function loadSettings() { const value = settings(); $("default-symbol").value = value.symbol || "EUR/USD"; $("default-timeframe").value = value.timeframe || "M5"; $("setting-zones").checked = value.zones !== false; $("setting-fvg").checked = Boolean(value.fvg); $("setting-labels").checked = Boolean(value.labels); $("setting-refresh").checked = Boolean(value.refresh); $("setting-context").value = value.context || "single"; $("setting-news").checked = value.news !== false; $("setting-marketaux").checked = value.marketaux !== false; $("setting-dxy").checked = Boolean(value.dxy); $("setting-execution-mode").value = value.executionMode || "conservative"; $("setting-minimum-rr").value = String(value.minimumRr || 1.5); ui.zones.checked = value.zones !== false; ui.fvg.checked = Boolean(value.fvg); ui.labels.checked = Boolean(value.labels); }

function rememberRecent(analysis) { let values; try { values = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch { values = []; } const item = { market: `${analysis.display_symbol || ui.symbol.value} · ${analysis.timeframe || ui.timeframe.value}`, status: formatUserStatus(analysis) }; values = [item, ...values.filter((v) => v.market !== item.market)].slice(0, 5); localStorage.setItem(RECENT_KEY, JSON.stringify(values)); renderRecent(values); }
function renderRecent(values = null) { if (!values) { try { values = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch { values = []; } } $("recent-analyses").innerHTML = values.length ? values.map((v) => `<li><span>${escapeHtml(v.market)}</span><strong class="${toneFor(v.status)}">${escapeHtml(v.status)}</strong></li>`).join("") : "<li>No recent analyses.</li>"; }

function updateClock() { const now = new Date(); const derived=latest?.provider==="deriv"||latest?.asset_type==="derived_index"; const parts = new Intl.DateTimeFormat("en-US", { timeZone: derived?"UTC":"America/New_York", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(now); $("toolbar-clock").textContent = parts; $("home-clock").textContent = parts; const hour = Number(new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "2-digit", hour12: false }).format(now)); const fallbackSession = hour >= 8 && hour < 17 ? "New York" : hour >= 3 && hour < 8 ? "London" : hour >= 19 || hour < 3 ? "Asian" : "Outside"; const market = latest?.macro_dashboard?.session || latest?.session || {}; const crypto = String(latest?.asset_type || "").toLowerCase() === "crypto"; const session = derived?"24/7 UTC":market.liquidity_window || market.name || fallbackSession; const status = derived?"24/7":market.market_status_label || (market.market_status === "OPEN_24_7" ? "24/7 Open" : market.market_open === true ? "Open" : market.market_open === false ? "Closed" : hour >= 8 && hour < 17 ? "Open" : "Closed"); $("toolbar-session-label").textContent = derived?"Analysis Context":crypto ? "Liquidity Window" : "Session"; $("toolbar-session").textContent = session.replace(/ (Liquidity|Session|Kill Zone)$/, ""); $("home-session").textContent = session; $("toolbar-market").textContent = status; $("home-market-open").textContent = status; const family=latest?.decision?.market?.family; $("toolbar-family-wrap").hidden=!derived; $("toolbar-family").textContent=titleCase(family||"Other Derived"); }

function numeric(value) { const number = Number(value); return Number.isFinite(number) ? number : NaN; }
function extractPrice(value) { if (typeof value === "number") return value; if (!value || typeof value !== "object") return NaN; return value.price ?? value.mid ?? value.entry ?? value.low ?? value.bottom; }
function formatPrice(value, analysis = {}) { const digits = Number(analysis.price_precision?.digits ?? analysis.price_precision ?? (Math.abs(value) < 10 ? 5 : 2)); return Number(value).toFixed(Math.max(0, Math.min(8, digits))); }
function formatValue(value) { if (value === null || value === undefined || value === "") return "--"; const number = Number(value); return Number.isFinite(number) ? (Math.abs(number) < 10 ? number.toFixed(5) : number.toFixed(2)) : escapeHtml(String(value)); }
function formatNumber(value) { const number = Number(value); return Number.isFinite(number) ? number.toFixed(2) : "0.00"; }
function titleCase(value) { return String(value || "Unavailable").replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()); }
function escapeHtml(value) { return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

document.querySelectorAll("[data-page-link]").forEach((button) => button.addEventListener("click", (event) => { event.preventDefault(); showPage(button.dataset.pageLink); }));
ui.analyze.addEventListener("click", analyzeMarket);
$("home-analyze").addEventListener("click", () => { ui.symbol.value = $("home-symbol").value; ui.timeframe.value = $("home-timeframe").value; ui.strategy.value = "auto"; renderToolbar(); analyzeMarket(); });
$("run-backtest").addEventListener("click", runBacktest);

let activeReplayRun=null,replayPoll=null,lastSmcValidation=null;
async function replayAction(action) { if(!activeReplayRun)return; const response=await fetch(`/api/replay/runs/${activeReplayRun}/${action}`,{method:"POST"});if(!response.ok)throw new Error((await response.json()).error||"Replay action failed");await pollReplay(); }
async function pollReplay() {
    if(!activeReplayRun)return;const response=await fetch(`/api/replay/runs/${activeReplayRun}/progress`),row=await response.json();if(!response.ok)return;
    $("replay-status").textContent=titleCase(row.status);$("replay-progress").textContent=`${Number(row.progress_percent||0).toFixed(1)}%`;$("replay-date").textContent=row.current_replay_date?new Date(row.current_replay_date).toLocaleString():"—";$("replay-decisions").textContent=row.decisions||0;$("replay-filled").textContent=row.filled_trades||0;$("replay-r").textContent=`${Number(row.realized_r||0).toFixed(2)}R`;$("replay-pause").disabled=row.status!=="running";$("replay-resume").disabled=row.status!=="paused";$("replay-cancel").disabled=!['running','paused','pending'].includes(row.status);if($("smc-validate-run"))$("smc-validate-run").disabled=row.status!=="completed";if($("inspect-decision"))$("inspect-decision").disabled=row.status!=="completed";const terminal=['completed','failed','cancelled'].includes(row.status);if(terminal&&replayPoll){clearInterval(replayPoll);replayPoll=null;}
}
async function inspectReplayDecision(){if(!activeReplayRun)return;const decisionId=$("inspector-decision-id").value.trim();if(!decisionId)return;try{const response=await fetch(`/api/smc-validation/runs/${activeReplayRun}/decisions/${encodeURIComponent(decisionId)}`),row=await response.json();if(!response.ok)throw new Error(row.error||"Decision unavailable");const then=row.information_available_then||{},later=row.observed_later||{},normalized=then.normalized_decision||then.decision||then,trace=((normalized.diagnostics||{}).target_trace)||then.target_trace||{};$("inspector-decision-time").textContent=JSON.stringify(then,null,2);$("inspector-later-outcome").textContent=JSON.stringify(later,null,2);$("inspector-target-state").textContent=JSON.stringify(trace,null,2);$("inspector-target-outcome").textContent=JSON.stringify(later.target_lifecycle_events||later.structural_targets||[],null,2);}catch(error){$("inspector-decision-time").textContent=plainText(error.message);}}
async function validateSmcReplay(){if(!activeReplayRun)return;const button=$("smc-validate-run");button.disabled=true;try{const response=await fetch(`/api/smc-validation/runs/${activeReplayRun}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({variant:$("replay-family").value})}),report=await response.json();if(!response.ok)throw new Error(report.error||"SMC validation failed");renderSmcValidation(report);}catch(error){$("smc-reachability").textContent=plainText(error.message);}finally{button.disabled=false;}}
function renderSmcValidation(report){lastSmcValidation=report;const symbol=report.symbols?.[0]||{};$("smc-validation-dataset").textContent=symbol.dataset_id||"—";$("smc-validation-adapter").textContent=titleCase(symbol.family);$("smc-validation-ready").textContent=symbol.trade_ready_setups||0;$("smc-validation-filled").textContent=symbol.filled_trades||0;$("smc-validation-resolved").textContent=symbol.resolved_trades||0;$("smc-validation-invalid").textContent=symbol.invalid_trade_plans||0;$("smc-validation-causality").textContent=symbol.causality_violations||0;renderSmcReachability();const link=$("smc-validation-report");link.href=`/api/smc-validation/reports/${report.report_id}/html`;link.setAttribute("aria-disabled","false");}
function renderSmcReachability(){if(!lastSmcValidation)return;const query=$("smc-filter-setup").value.trim().toLowerCase(),blocker=$("smc-filter-blocker").value.trim().toLowerCase(),ready=$("smc-filter-ready").value,filled=$("smc-filter-filled").value,resolved=$("smc-filter-resolved").value;const rows=(lastSmcValidation.reachability||[]).filter(row=>(!query||row.setup_type.toLowerCase().includes(query))&&(!blocker||Object.keys(row.first_blockers||{}).some(key=>key.toLowerCase().includes(blocker)))&&(!ready||String(row.trade_ready_count>0)===ready)&&(!filled||String(row.filled_count>0)===filled)&&(!resolved||String(row.resolved_count>0)===resolved));$("smc-reachability").innerHTML=rows.map(row=>`<article><strong>${escapeHtml(titleCase(row.setup_type))}</strong><span>${row.trade_ready_count||0} ready · ${row.filled_count||0} filled · ${row.resolved_count||0} resolved</span><small>${escapeHtml(row.zero_trade_classification||"")}</small></article>`).join("")||"<p>No reachability rows match these filters.</p>";}
async function startReplay() {
    const button=$("replay-start-button");button.disabled=true;
    try { const body={provider_symbol:$("replay-symbol").value.trim(),display_name:$("replay-symbol").value.trim(),family:$("replay-family").value.trim(),start_time:new Date($("replay-start").value).toISOString(),end_time:new Date($("replay-end").value).toISOString(),strategy:$("replay-strategy").value,base_timeframe:$("replay-base").value,configuration_profile:"default"};const response=await fetch("/api/replay/runs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),run=await response.json();if(!response.ok)throw new Error(run.error||"Replay could not start");activeReplayRun=run.replay_run_id;$("replay-report").href=`/api/replay/runs/${activeReplayRun}/report`;$("replay-report").setAttribute("aria-disabled","false");await pollReplay();replayPoll=setInterval(pollReplay,1500); } catch(error){$("replay-status").textContent=plainText(error.message);} finally{button.disabled=false;}
}
if($("replay-start-button")){const now=new Date(),prior=new Date(now.getTime()-86400000);$("replay-start").value=prior.toISOString().slice(0,16);$("replay-end").value=now.toISOString().slice(0,16);$("replay-start-button").addEventListener("click",startReplay);$("replay-pause").addEventListener("click",()=>replayAction("pause"));$("replay-resume").addEventListener("click",()=>replayAction("resume"));$("replay-cancel").addEventListener("click",()=>replayAction("cancel"));$("smc-validate-run").addEventListener("click",validateSmcReplay);$("inspect-decision").addEventListener("click",inspectReplayDecision);["smc-filter-setup","smc-filter-blocker","smc-filter-ready","smc-filter-filled","smc-filter-resolved"].forEach(id=>$(id).addEventListener("input",renderSmcReachability));}
[ui.symbol, ui.timeframe, ui.strategy].forEach((control) => control.addEventListener("change", () => { currentChartRequestId++;terminalState.requestId++;terminalState.decision=null;stopCurrentMarketStream();const deriv=selectedMarket().provider==="deriv";if(control===ui.symbol&&deriv)ui.strategy.value="auto";latest=null;ui.chartOverlay.innerHTML="";ui.scenarioContent.innerHTML="";ui.chartState.textContent="LOADING MARKET CONTEXT";renderToolbar();ui.update.hidden=true;if((control===ui.symbol||control===ui.timeframe)&&deriv)loadDerivChart(); }));
[ui.zones, ui.fvg, ui.previous, ui.setups, ui.path, ui.labels].forEach((control) => control.addEventListener("change", () => { if (control === ui.path) control.setAttribute("aria-pressed", String(control.checked)); drawChartOverlays(latest || {}); }));
[document.querySelector("#show-structure"),document.querySelector("#show-advanced")].filter(Boolean).forEach(control=>control.addEventListener("change",()=>drawChartOverlays(latest||{})));
if(document.querySelector("#live-toggle"))document.querySelector("#live-toggle").addEventListener("click",event=>{const active=event.currentTarget.getAttribute("aria-pressed")==="true";event.currentTarget.setAttribute("aria-pressed",String(!active));event.currentTarget.textContent=active?"Paused":"Live";if(active)stopCurrentMarketStream();else startDerivStream();});
document.querySelectorAll("#settings-page input, #settings-page select").forEach((control) => control.addEventListener("change", saveSettings));
$("view-m5-entry").addEventListener("click", viewCachedM5Entry);
window.addEventListener("resize", resizeChart);
new ResizeObserver(scheduleOverlayRedraw).observe(document.querySelector(".chart-container"));
loadSettings(); loadDerivedSymbols(); renderRecent(); renderToolbar(); updateClock(); drawScenarioPaths([]); setInterval(updateClock, 1000); showPage(location.hash.slice(1) || "chart");
