// Private packaged acceptance; official deployed web + synthetic browser API.
// No real login, save selection, mutation, installer or owner profile access.
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { fixture } from "../web/e2e/fixtures.ts";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";

const [exe, output] = process.argv.slice(2);
assert(exe && output);
const origin = "https://pokeapp-web.pokeapp-v2.workers.dev";
const api = "https://pokeapp-api-production.up.railway.app";
const profile = path.resolve(output, "isolated-profile");
await mkdir(output, { recursive: true });
const env = {
  ...process.env,
  POKEAPP_LAUNCHER_PROFILE: profile,
  POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
  POKEAPP_WEB_ORIGIN: "http://127.0.0.1:4173",
};
delete env.ELECTRON_RUN_AS_NODE;
const child = spawn(exe, ["--remote-debugging-port=9337"], {
  env,
  windowsHide: true,
  stdio: "ignore",
});
const report = {
  version: "0.24.0-rc.2",
  status: "RUNNING",
  checks: [],
  boundaries:
    "Packaged real core/UI and official assets; synthetic authenticated browser API, no real accounts.",
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function check(ok, label) {
  report.checks.push({ pass: Boolean(ok), label });
  assert(ok, label);
  console.log("PASS " + label);
}
async function until(fn) {
  for (let i = 0; i < 100; i++) {
    if (await fn()) return;
    await sleep(100);
  }
  throw new Error("state deadline exceeded");
}
let browser;
try {
  for (let i = 0; i < 60 && !browser; i++) {
    await sleep(500);
    browser = await chromium
      .connectOverCDP("http://127.0.0.1:9337")
      .catch(() => null);
  }
  check(browser, "packaged app starts with isolated profile");
  const pages = () => browser.contexts().flatMap((c) => c.pages());
  await until(
    () =>
      pages().some((p) => p.url().startsWith(origin)) &&
      pages().some((p) => p.url().includes("shell=unified")),
  );
  const web = pages().find((p) => p.url().startsWith(origin));
  const tools = pages().find((p) => p.url().includes("shell=unified"));
  const errors = [];
  web.on("pageerror", (e) => errors.push(e.message));
  tools.on("pageerror", (e) => errors.push(e.message));
  await web.getByRole("button", { name: "Entrar a PokeApp" }).waitFor();
  const state = () =>
    tools.evaluate(() => ({
      mode: document.body.dataset.mode,
      title: document.querySelector("#panel-title").textContent,
      offline: !document.querySelector("#offline-note").hidden,
    }));
  const navigate = async (route) =>
    web.evaluate((route) => {
      history.pushState({}, "", route);
      dispatchEvent(new PopStateEvent("popstate"));
    }, route);
  check(
    web.url().startsWith(origin),
    "official origin loaded; packaged override ignored",
  );
  const isolated = await web.evaluate(() => ({
    node: typeof require,
    process: typeof process,
    bridge: typeof window.launcher,
    marker: navigator.userAgent.includes("PokeAppLauncher/0.24.0-rc.2"),
  }));
  check(
    isolated.node === "undefined" &&
      isolated.process === "undefined" &&
      isolated.bridge === "undefined" &&
      isolated.marker,
    "web has no Node/preload/IPC bridge and identifies rc.2",
  );
  check((await state()).mode === "strip", "web is initial main surface");
  await web.screenshot({ path: path.join(output, "official-login.png") });
  await navigate("/escritorio/partida");
  await until(
    async () =>
      new URL(web.url()).pathname === "/" && (await state()).mode === "strip",
  );
  check(true, "signed-out route redirect does not leave stale native panel");

  // Intercept before typing any credentials. All auth here is synthetic.
  await fixture(web, false, api);
  await web.reload();
  await web.getByLabel("Entrenador", { exact: true }).fill("Synthetic 27C");
  await web.getByLabel("PIN", { exact: true }).fill("1234");
  await web.getByRole("button", { name: "Entrar a PokeApp" }).click();
  await web
    .getByRole("heading", { name: "A por la siguiente, Antonio." })
    .waitFor();
  check(true, "deployed React navigation works with synthetic session");
  const nav = web.getByRole("navigation", { name: "Principal" });
  for (const [label, title] of [
    ["Mi partida", "Mi partida"],
    ["Objetos ∞", "Objetos ∞"],
    ["Robos y entregas", "Robos y entregas"],
    ["Copias de seguridad", "Copias de seguridad"],
    ["Conexión", "Conexión y sincronización"],
  ]) {
    await nav.getByRole("link", { name: label, exact: true }).click();
    await until(async () => {
      const s = await state();
      return s.mode === "panel" && s.title === title;
    });
    check(true, label + " opens correct native panel");
  }
  const nativeState = await tools.evaluate(() => window.launcher.state());
  check(
    nativeState.auth_status === "LOGIN_REQUIRED" &&
      nativeState.cloud_sync === false &&
      !nativeState.selected_save,
    "web synthetic login does not authenticate native connection or select a save",
  );
  check(
    nativeState.write?.production_operations_enabled === false,
    "production physical operations disabled",
  );
  await tools.screenshot({ path: path.join(output, "connection-panel.png") });
  await tools.getByRole("button", { name: /Volver a PokeApp/ }).click();
  await until(async () => (await state()).mode === "strip");
  check(true, "return to PokeApp closes panel");
  await navigate("/entrenadores/10000000-0000-4000-8000-000000000002");
  await web.getByText("Objetos ilimitados").waitFor();
  const hrefs = await web
    .getByRole("link", { name: "Añadir a mi partida" })
    .evaluateAll((els) => els.map((e) => e.getAttribute("href")));
  check(
    hrefs.join() ===
      "/escritorio/objetos/rare_candy,/escritorio/objetos/heart_scale",
    "infinite inventory links select only approved item panels",
  );
  await web.getByRole("link", { name: "Añadir a mi partida" }).first().click();
  await until(
    async () =>
      (await state()).title === "Objetos ∞" && (await state()).mode === "panel",
  );
  await tools.getByRole("button", { name: /Volver a PokeApp/ }).click();
  await until(async () => (await state()).mode === "strip");
  check(
    await web.getByText("Objetos ilimitados").isVisible(),
    "inventory/session preserved on return",
  );
  await web.evaluate(() => {
    for (let i = 0; i < 30; i++) {
      history.pushState({}, "", i % 2 ? "/liga" : "/escritorio/partida");
      dispatchEvent(new PopStateEvent("popstate"));
    }
  });
  await until(async () => (await state()).mode === "strip");
  await sleep(700);
  check(
    (await state()).mode === "strip" && web.url().endsWith("/liga"),
    "30 rapid transitions: latest close wins",
  );
  await navigate("/escritorio/admin");
  await sleep(700);
  check(
    (await state()).mode === "strip",
    "non-allowlisted native route ignored",
  );
  await nav.getByRole("link", { name: "Conexión", exact: true }).click();
  await until(async () => (await state()).mode === "panel");
  await web.getByRole("button", { name: "Cerrar sesión" }).click();
  await until(
    async () =>
      (await state()).mode === "strip" && new URL(web.url()).pathname === "/",
  );
  check(
    await web.getByRole("button", { name: "Entrar a PokeApp" }).isVisible(),
    "web logout closes open native panel",
  );
  await web
    .evaluate(() => {
      location.href = "http://example.invalid/";
    })
    .catch(() => {});
  await sleep(500);
  check(web.url().startsWith(origin), "foreign navigation blocked");
  const cdp = await web.context().newCDPSession(web);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp.send("Network.emulateNetworkConditions", {
    offline: true,
    latency: 0,
    downloadThroughput: -1,
    uploadThroughput: -1,
  });
  await web.reload({ timeout: 8000 }).catch(() => {});
  await until(async () => (await state()).mode === "offline");
  check((await state()).offline, "offline load falls back to local tools");
  check(
    (await tools.evaluate(() => window.launcher.state())).local_status ===
      "NO_SAVE",
    "packaged core remains available offline",
  );
  await tools.screenshot({ path: path.join(output, "offline.png") });
  await cdp.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 0,
    downloadThroughput: -1,
    uploadThroughput: -1,
  });
  await tools.evaluate(() => window.launcher.closePanel());
  await until(
    async () =>
      (await state()).mode === "strip" && web.url().startsWith(origin),
  );
  check(true, "online recovery returns to web without native credentials");
  check(errors.length === 0, "no web/tools JavaScript errors");
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.error = String(error.message).slice(0, 1200);
  console.error(report.error);
} finally {
  // Close only this spawned test instance. No owner process is enumerated/killed.
  if (browser) {
    try {
      const session = await browser.newBrowserCDPSession();
      await Promise.race([
        session.send("Browser.close").catch(() => {}),
        sleep(1000),
      ]);
    } catch {}
    await browser.close().catch(() => {});
  }
  await sleep(1500);
  if (child.exitCode === null) child.kill();
  await writeFile(
    path.join(output, "acceptance.json"),
    JSON.stringify(report, null, 2),
  );
}
process.exitCode = report.status === "PASS" ? 0 : 1;
