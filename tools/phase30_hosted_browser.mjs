// Phase 30 hosted acceptance, browser part without a session: the public
// sign-in screen at 1440 and 390 px — no console or page errors, no failed
// same-origin or API request, no horizontal scroll. Read-only: it never types
// a PIN or submits a form.
// Run: node tools/phase30_hosted_browser.mjs <output dir>
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";

// Playwright lives in the web package.
const { chromium } = createRequire(
  new URL("../web/package.json", import.meta.url),
)("@playwright/test");

const WEB = "https://pokeapp-web.pokeapp-v2.workers.dev";
const out = process.argv[2] || "hosted-browser";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ channel: "msedge" });
const results = [];
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    const problems = [];
    page.on(
      "console",
      (m) => m.type() === "error" && problems.push("console: " + m.text()),
    );
    page.on("pageerror", (e) => problems.push("page: " + e.message));
    page.on("response", (r) => {
      const url = new URL(r.url());
      // This machine's Edge adds same-origin GUID-path requests (local security
      // software); only the web's own assets and the API count.
      const ours = url.origin === WEB && !/^\/[0-9A-F]{8}-/.test(url.pathname);
      if ((ours || url.hostname.endsWith("railway.app")) && r.status() >= 400)
        problems.push(`http ${r.status()} ${url.pathname}`);
    });
    await page.goto(WEB + "/", { waitUntil: "load" });
    await page
      .getByRole("button", { name: /entrar|iniciar/i })
      .first()
      .waitFor({ timeout: 30000 });
    const scroll = await page.evaluate(
      () => document.documentElement.scrollWidth - innerWidth,
    );
    await page.screenshot({ path: join(out, `login-${width}.png`) });
    results.push({
      width,
      horizontal_overflow_px: scroll,
      problems,
      pass: scroll <= 0 && !problems.length,
    });
    await page.close();
  }
} finally {
  await browser.close();
}
writeFileSync(
  join(out, "hosted-browser.json"),
  JSON.stringify(results, null, 2) + "\n",
);
console.log(JSON.stringify(results));
process.exit(results.every((r) => r.pass) ? 0 : 1);
