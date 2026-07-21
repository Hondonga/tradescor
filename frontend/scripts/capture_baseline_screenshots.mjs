import { chromium } from "playwright";
import { mkdirSync } from "fs";

const BASE = "http://127.0.0.1:5000";
const OUT = new URL("../../data/stabilization/baseline/screenshots", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const resolutions = [
  ["1920x1080", 1920, 1080],
  ["1536x864", 1536, 864],
  ["1440x900", 1440, 900],
  ["1280x800", 1280, 800],
];

// Workspace polls live data continuously (react-query refetch + provider stream),
// so it never reaches Playwright's "networkidle" state by design. Use
// domcontentloaded + a fixed settle delay instead.
const pages = [
  ["workspace-volatility75-m5", "/workspace?symbol=R_75&timeframe=M5"],
  ["workspace-jump10-m5", "/workspace?symbol=JD10&timeframe=M5"],
  ["workspace-gbpusd-m5", "/workspace?symbol=GBP/USD&timeframe=M5"],
];

const browser = await chromium.launch();
const results = [];
for (const [resName, width, height] of resolutions) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  for (const [pageName, path] of pages) {
    const url = BASE + path;
    const file = `${OUT}/${pageName}_${resName}.png`;
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
      await page.waitForTimeout(4000); // let charts/query data settle
      await page.screenshot({ path: file, fullPage: false });
      results.push({ page: pageName, resolution: resName, url, file, ok: true });
    } catch (error) {
      results.push({ page: pageName, resolution: resName, url, file, ok: false, error: String(error) });
    }
  }
  await context.close();
}
await browser.close();
console.log(JSON.stringify(results, null, 2));
