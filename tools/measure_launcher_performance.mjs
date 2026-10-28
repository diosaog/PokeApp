// Launcher performance (packaged app, isolated profile): time to a usable
// window, memory of the whole process tree, and CPU while idle.
// The app runs straight from a build's win-unpacked folder (no installer), so
// nothing relaunches it with the real environment; LOCALAPPDATA/APPDATA point
// into a scratch folder that is removed afterwards.
//
//   node tools/measure_launcher_performance.mjs <win-unpacked dir> <output.json> [runs]
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";

const [dir, out, runsArg = "3"] = process.argv.slice(2);
const exe = path.join(path.resolve(dir), "PokeApp Launcher.exe");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ps = (c) => execFileSync("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", c], { encoding: "utf8" }).trim();
// Every process started from the unpacked folder (Electron, renderers, GPU, core).
const tree = () =>
  JSON.parse(
    ps(`@(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith('${path.resolve(dir).replace(/'/g, "''")}', 'OrdinalIgnoreCase') } | ForEach-Object { [pscustomobject]@{ id = $_.ProcessId; ws = $_.WorkingSetSize; private = $_.PrivatePageCount; cpu = ($_.KernelModeTime + $_.UserModeTime) } }) | ConvertTo-Json -Compress`) || "[]",
  );
const list = (v) => (Array.isArray(v) ? v : v ? [v] : []);
const results = [];
for (let run = 0; run < Number(runsArg); run++) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-perf-"));
  const env = { ...process.env, LOCALAPPDATA: path.join(root, "local"), APPDATA: path.join(root, "roaming") };
  // An editor-hosted shell may export ELECTRON_RUN_AS_NODE: the app would start as Node.
  delete env.ELECTRON_RUN_AS_NODE;
  fs.mkdirSync(env.LOCALAPPDATA, { recursive: true });
  fs.mkdirSync(env.APPDATA, { recursive: true });
  const port = 9470 + run;
  const t0 = performance.now();
  const child = spawn(exe, [`--remote-debugging-port=${port}`], { env, stdio: "ignore" });
  let browser;
  for (let i = 0; i < 120 && !browser; i++) {
    try {
      browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
    } catch {
      await sleep(500);
    }
  }
  if (!browser) throw new Error("the Launcher did not open its debugging port in 60 s");
  let page;
  for (let i = 0; i < 300 && !page; i++) {
    page = browser.contexts().flatMap((c) => c.pages()).find((p) => p.url().includes("shell=unified"));
    if (!page) await sleep(50);
  }
  // Usable: the shell is up and the native core has answered its first state.
  for (let i = 0; i < 600; i++) {
    const ready = await page.evaluate(async () => Boolean(window.launcher && (await window.launcher.state()))).catch(() => false);
    if (ready) break;
    await sleep(50);
  }
  const usable = performance.now() - t0;
  await sleep(10000); // settle: web view loaded, first discovery done
  const a = list(tree());
  const cpu0 = a.reduce((s, p) => s + Number(p.cpu), 0);
  const w0 = performance.now();
  await sleep(30000);
  const b = list(tree());
  const cpu1 = b.reduce((s, p) => s + Number(p.cpu), 0);
  const idleCpu = ((cpu1 - cpu0) / 1e4 / (performance.now() - w0)) * 100 / os.cpus().length; // 100-ns ticks → % of the machine
  results.push({
    usable_ms: Math.round(usable),
    processes: b.length,
    working_set_mb: Math.round(b.reduce((s, p) => s + Number(p.ws), 0) / 1048576),
    private_mb: Math.round(b.reduce((s, p) => s + Number(p.private), 0) / 1048576),
    idle_cpu_percent_of_machine: Math.round(idleCpu * 100) / 100,
  });
  console.log(JSON.stringify(results.at(-1)));
  await browser.close().catch(() => {});
  try {
    execFileSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  } catch {}
  for (let i = 0; i < 60 && list(tree()).length; i++) await sleep(500);
  fs.rmSync(root, { recursive: true, force: true, maxRetries: 20, retryDelay: 500 });
}
const median = (k) => results.map((r) => r[k]).sort((x, y) => x - y)[Math.floor(results.length / 2)];
const summary = Object.fromEntries(Object.keys(results[0]).map((k) => [k, median(k)]));
fs.writeFileSync(out, JSON.stringify({ build: path.resolve(dir), cpus: os.cpus().length, runs: results, median: summary }, null, 2) + "\n");
console.log("median", JSON.stringify(summary));
