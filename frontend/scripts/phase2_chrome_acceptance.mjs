import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";

// Phase 2 checkpoint 16: Chrome acceptance for the R_75 M5 golden path.
//
// The 11 required states are exercised via the same Storybook fixture
// surface used by Milestone 3's visual regression stories
// (frontend/src/components/chart/market-chart.stories.tsx) -- these render
// the real MarketChart component against the real overlay pipeline
// (selectVisibleOverlays -> applyDensity -> style registry), fed by
// synthetic-but-structurally-real NormalizedDecision fixtures, not a mocked
// chart. This is the only practical way to force rare/terminal states
// (trade-ready, expired, invalidated) deterministically in a live 24/7
// synthetic-index feed. A live-app smoke pass (state #12 below) additionally
// confirms the actual running app renders without console errors.

const STORYBOOK = "http://127.0.0.1:6006";
const LIVE_APP = "http://127.0.0.1:5000";
const OUT = fileURLToPath(new URL("../../data/stabilization/phase2/browser", import.meta.url));
mkdirSync(OUT, { recursive: true });

const resolutions = [
  ["1920x1080", 1920, 1080],
  ["1536x864", 1536, 864],
  ["1440x900", 1440, 900],
  ["1280x800", 1280, 800],
];

const requiredStates = [
  ["01_market_context", "chart-scenarios--market-context-only"],
  ["02_developing_buy", "chart-scenarios--developing-buy-setup"],
  ["03_developing_sell", "chart-scenarios--developing-sell-setup"],
  ["04_waiting_for_confirmation", "chart-scenarios--waiting-for-confirmation"],
  ["05_plan_validation", "chart-scenarios--plan-validation"],
  ["06_trade_ready_buy", "chart-scenarios--trade-ready-buy"],
  ["07_trade_ready_sell", "chart-scenarios--trade-ready-sell"],
  ["08_expired", "chart-scenarios--expired-setup"],
  ["09_invalidated", "chart-scenarios--invalidated-setup"],
  ["10_previous_setup_enabled", "chart-scenarios--previous-setup-enabled"],
  ["11_advanced_smc_enabled", "chart-scenarios--advanced-smc-enabled"],
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
      await page.waitForTimeout(1200);
      await page.screenshot({ path: file, fullPage: false });
      results.push({
        state: stateName,
        resolution: resName,
        url,
        file,
        ok: true,
        new_console_errors: consoleErrors.slice(before),
      });
    } catch (error) {
      results.push({ state: stateName, resolution: resName, url, file, ok: false, error: String(error) });
    }
  }
  await context.close();
}

// State 12: the actual running app at R_75 M5, whatever its live organic
// state is right now -- confirms the real deployed app (not just fixtures)
// renders cleanly with no console errors.
{
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(String(err)));
  const url = `${LIVE_APP}/workspace?symbol=R_75&timeframe=M5`;
  const file = `${OUT}/12_live_app_current_state_1920x1080.png`;
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForTimeout(4000);
    await page.screenshot({ path: file, fullPage: false });
    results.push({ state: "12_live_app_current_state", resolution: "1920x1080", url, file, ok: true, console_errors: consoleErrors });
  } catch (error) {
    results.push({ state: "12_live_app_current_state", resolution: "1920x1080", url, file, ok: false, error: String(error) });
  }
  await context.close();
}

await browser.close();

const report = {
  generated_at: new Date().toISOString(),
  section: "16 - CHROME ACCEPTANCE",
  method: "Playwright/Chromium against a static Storybook build of frontend/src/components/chart/market-chart.stories.tsx (real MarketChart component, real overlay pipeline, synthetic fixture decisions) for the 11 required states, plus one live-app smoke check.",
  resolutions_tested: resolutions.map(([n]) => n),
  results,
  all_captures_ok: results.every((r) => r.ok),
  any_console_errors: results.some((r) => (r.new_console_errors && r.new_console_errors.length) || (r.console_errors && r.console_errors.length)),
};
writeFileSync(`${OUT}/chrome_acceptance_report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify({ all_captures_ok: report.all_captures_ok, any_console_errors: report.any_console_errors, total: results.length }, null, 2));
