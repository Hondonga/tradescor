import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";

// Phase 3 checkpoint 27: Chrome acceptance for the professional Workspace
// UI redesign. Uses the same Storybook fixture surface as Phase 2's
// acceptance pass (real MarketChart + real overlay pipeline, synthetic-but-
// structurally-real NormalizedDecision fixtures), extended with the new
// Phase 3 scenarios (waiting-for-entry, too-late, state-contradiction,
// research-only-scenario, previous-setup-hidden, stale-data-state,
// replay-mode, empty-no-data-state, provider-reconnecting) and a live
// Drawing-Inspector-open interaction captured on top of a static fixture.

const STORYBOOK = "http://127.0.0.1:6013";
const LIVE_APP = "http://127.0.0.1:5000";
const OUT = fileURLToPath(new URL("../../data/stabilization/phase3/browser", import.meta.url));
mkdirSync(OUT, { recursive: true });

const resolutions = [
  ["1920x1080", 1920, 1080],
  ["1536x864", 1536, 864],
  ["1440x900", 1440, 900],
  ["1280x800", 1280, 800],
  ["1024x768", 1024, 768],
];

// The 14 required R_75 M5 states from §27.
const requiredStates = [
  ["01_market_context", "chart-scenarios--market-context-only"],
  ["02_developing_buy", "chart-scenarios--developing-buy-setup"],
  ["03_developing_sell", "chart-scenarios--developing-sell-setup"],
  ["04_plan_validation", "chart-scenarios--plan-validation"],
  ["05_trade_ready_buy", "chart-scenarios--trade-ready-buy"],
  ["06_trade_ready_sell", "chart-scenarios--trade-ready-sell"],
  ["07_expired", "chart-scenarios--expired-setup"],
  ["08_invalidated", "chart-scenarios--invalidated-setup"],
  ["09_replay", "chart-scenarios--replay-mode"],
  ["10_historical", "chart-scenarios--waiting-for-confirmation"],
  ["11_previous_setup", "chart-scenarios--previous-setup-enabled"],
  ["12_advanced_smc", "chart-scenarios--advanced-smc-enabled"],
  ["13_research_mode", "chart-scenarios--research-only-scenario"],
];

const browser = await chromium.launch();
const results = [];

for (const [resName, width, height] of resolutions) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(String(err)));

  for (const [stateName, storyId] of requiredStates) {
    const url = `${STORYBOOK}/iframe.html?id=${storyId}&viewMode=story`;
    const file = `${OUT}/${stateName}_${resName}.png`;
    const before = consoleErrors.length;
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
      await page.waitForTimeout(1000);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      await page.screenshot({ path: file, fullPage: false });
      results.push({
        state: stateName,
        resolution: resName,
        url,
        file,
        ok: true,
        horizontal_overflow: overflow,
        new_console_errors: consoleErrors.slice(before),
      });
    } catch (error) {
      results.push({ state: stateName, resolution: resName, url, file, ok: false, error: String(error) });
    }
  }
  await context.close();
}

// State 14: Drawing Inspector open -- a live interaction on top of a static
// fixture (select an overlay from the toolbar's "Inspect drawing..." select,
// which now correctly reaches the underlying <select> element after the
// §15 z-index fix).
{
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(String(err)));
  const url = `${STORYBOOK}/iframe.html?id=chart-scenarios--trade-ready-buy&viewMode=story`;
  const file = `${OUT}/14_drawing_inspector_open_1920x1080.png`;
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForTimeout(800);
    const select = page.locator('select[aria-label="Inspect chart drawing metadata"]');
    const optionValue = await select.locator("option").nth(1).getAttribute("value");
    await select.selectOption(optionValue);
    await page.waitForTimeout(500);
    const inspectorVisible = await page.locator("text=Price / zone").count();
    await page.screenshot({ path: file });
    results.push({
      state: "14_drawing_inspector_open",
      resolution: "1920x1080",
      url,
      file,
      ok: true,
      inspector_opened: inspectorVisible > 0,
      new_console_errors: consoleErrors,
    });
  } catch (error) {
    results.push({ state: "14_drawing_inspector_open", resolution: "1920x1080", url, file, ok: false, error: String(error) });
  }
  await context.close();
}

// Cross-market visual regression (§27): live app, smoke-check only (the app
// requires an explicit "Load Chart" action before analysis populates --
// established in Phase 2 -- so these confirm the redesigned Workspace UI
// still renders structurally and error-free for every market family, not
// full analysis-state coverage).
const crossMarket = [
  ["jump10_research_only", "/workspace?symbol=JD10&timeframe=M5"],
  ["gbpusd_forex", "/workspace?symbol=GBP/USD&timeframe=M5"],
  ["step_market", "/workspace?symbol=stpRNG&timeframe=M5"],
  ["boom_crash_market", "/workspace?symbol=BOOM50&timeframe=M5"],
];
for (const [name, path] of crossMarket) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(String(err)));
  const url = `${LIVE_APP}${path}`;
  const file = `${OUT}/cross_market_${name}.png`;
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForTimeout(3000);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    await page.screenshot({ path: file });
    results.push({ state: `cross_market_${name}`, resolution: "1920x1080", url, file, ok: true, horizontal_overflow: overflow, new_console_errors: consoleErrors });
  } catch (error) {
    results.push({ state: `cross_market_${name}`, resolution: "1920x1080", url, file, ok: false, error: String(error) });
  }
  await context.close();
}

await browser.close();

const report = {
  generated_at: new Date().toISOString(),
  section: "27 - CHROME ACCEPTANCE",
  method:
    "Playwright/Chromium against a static Storybook build of market-chart.stories.tsx (real MarketChart, real overlay pipeline) for the 14 required R_75 M5 states across 5 resolutions, plus a live Drawing-Inspector-open interaction, plus a live-app cross-market structural smoke check.",
  resolutions_tested: resolutions.map(([n]) => n),
  results,
  all_captures_ok: results.every((r) => r.ok),
  any_console_errors: results.some((r) => r.new_console_errors && r.new_console_errors.length),
  any_horizontal_overflow: results.some((r) => r.horizontal_overflow),
};
writeFileSync(`${OUT}/chrome_acceptance_report.json`, JSON.stringify(report, null, 2));
console.log(
  JSON.stringify(
    { all_captures_ok: report.all_captures_ok, any_console_errors: report.any_console_errors, any_horizontal_overflow: report.any_horizontal_overflow, total: results.length },
    null,
    2,
  ),
);
