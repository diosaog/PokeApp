// Web performance measurement (read-only): first visit with an empty cache,
// a warm reload, and a first visit on a slow link, at 1440 and 390 px.
// Collects TTFB, DOMContentLoaded, load, LCP, CLS, long tasks, requests and
// bytes (total and JavaScript). Never signs in.
//
//   node tools/measure_web_performance.mjs <url> <output.json> [runs]
import { createRequire } from "node:module";
import fs from "node:fs";

const { chromium } = createRequire(new URL("../web/package.json", import.meta.url))("@playwright/test");
const [url = "https://pokeapp-web.pokeapp-v2.workers.dev/", out = "web-performance.json", runsArg = "3"] =
  process.argv.slice(2);
const runs = Number(runsArg);
// Chrome DevTools "Slow 4G"-like profile.
const SLOW = { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 };
const OBSERVE = () => {
  window.__perf = { lcp: 0, cls: 0, long: 0 };
  new PerformanceObserver((l) => l.getEntries().forEach((e) => (window.__perf.lcp = e.startTime))).observe({ type: "largest-contentful-paint", buffered: true });
  new PerformanceObserver((l) => l.getEntries().forEach((e) => { if (!e.hadRecentInput) window.__perf.cls += e.value; })).observe({ type: "layout-shift", buffered: true }); // prettier-ignore
  new PerformanceObserver((l) => l.getEntries().forEach((e) => (window.__perf.long += e.duration))).observe({ type: "longtask", buffered: true });
};

async function visit(context, { width, slow }) {
  const page = await context.newPage();
  await page.setViewportSize({ width, height: 900 });
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  if (slow) await cdp.send("Network.emulateNetworkConditions", SLOW);
  let requests = 0, bytes = 0, js = 0; // prettier-ignore
  const types = new Map();
  // Only PokeApp's own origins count: this machine's security software injects
  // its own scripts into every page.
  const ours = (u) => u.startsWith(new URL(url).origin) || u.includes(".railway.app");
  cdp.on("Network.responseReceived", (e) => ours(e.response.url) && types.set(e.requestId, e.response.mimeType));
  cdp.on("Network.loadingFinished", (e) => {
    if (!types.has(e.requestId)) return;
    requests++;
    bytes += e.encodedDataLength;
    if ((types.get(e.requestId) || "").includes("javascript")) js += e.encodedDataLength;
  });
  await page.addInitScript(OBSERVE);
  const t0 = Date.now();
  await page.goto(url, { waitUntil: "load", timeout: 120000 });
  // The sign-in form is the first useful screen.
  await page.getByRole("button", { name: /entrar|iniciar/i }).first().waitFor({ timeout: 120000 });
  const ready = Date.now() - t0;
  await page.waitForTimeout(1500);
  const nav = await page.evaluate(() => {
    const n = performance.getEntriesByType("navigation")[0];
    return { ttfb: n.responseStart, dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd, ...window.__perf };
  });
  await page.close();
  return { ...nav, ready, requests, bytes, js };
}

const browser = await chromium.launch({ channel: "msedge" });
const results = {};
try {
  for (const width of [1440, 390]) {
    for (const [name, slow, warm] of [["cold", false, false], ["warm", false, true], ["slow-cold", true, false]]) {
      const samples = [];
      for (let i = 0; i < runs; i++) {
        const context = await browser.newContext();
        if (warm) await (await visit(context, { width, slow: false }), Promise.resolve());
        samples.push(await visit(context, { width, slow }));
        await context.close();
      }
      const median = (key) => samples.map((s) => s[key]).sort((a, b) => a - b)[Math.floor(samples.length / 2)];
      results[`${name}-${width}`] = Object.fromEntries(
        ["ttfb", "dcl", "load", "lcp", "cls", "long", "ready", "requests", "bytes", "js"].map((k) => [k, Math.round(median(k) * 1000) / 1000]),
      );
      console.log(name, width, JSON.stringify(results[`${name}-${width}`]));
    }
  }
} finally {
  await browser.close();
}
fs.writeFileSync(out, JSON.stringify({ url, runs, measured_at: new Date().toISOString(), results }, null, 2) + "\n");
