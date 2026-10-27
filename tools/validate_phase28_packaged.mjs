// Phase 28 private packaged acceptance (0.26.0-preview.x with -WebPreview).
// The packaged Launcher runs with an isolated profile AND an isolated APPDATA
// holding two synthetic emulator files, against the local design preview
// (http://127.0.0.1:4173, synthetic API on :4174). No real account, no owner
// save, no installer run, no owner profile access.
//   node tools/validate_phase28_packaged.mjs <win-unpacked exe> <output dir>
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";

const [exe, output] = process.argv.slice(2);
assert(exe && output);
const origin = "http://127.0.0.1:4173";
const version = "0.26.0-preview.1";
const profile = path.resolve(output, "isolated-profile");
const appdata = path.resolve(output, "isolated-appdata");
const ids = "0".repeat(32);
for (const [emulator, title] of [
  ["Lime3DS", "00055e00"],
  ["Azahar", "00175e00"],
]) {
  const dir = path.join(
    appdata,
    emulator,
    "sdmc",
    "Nintendo 3DS",
    ids,
    ids,
    "title",
    "00040000",
    title,
    "data",
    "00000001",
  );
  await mkdir(dir, { recursive: true });
  // Synthetic bytes: discovery lists them; they are never a real save.
  await writeFile(path.join(dir, "main"), Buffer.alloc(4096, 7));
}
const env = {
  ...process.env,
  APPDATA: appdata,
  POKEAPP_LAUNCHER_PROFILE: profile,
  POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
};
delete env.ELECTRON_RUN_AS_NODE;
const child = spawn(exe, ["--remote-debugging-port=9338"], {
  env,
  windowsHide: true,
  stdio: "ignore",
});
const report = {
  version,
  status: "RUNNING",
  checks: [],
  boundaries:
    "Packaged real core and UI; isolated profile and APPDATA with synthetic files; local preview web with synthetic API; no real accounts or saves.",
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// A hidden window may not paint: captures are best effort, never a check.
let shot = async () => {};
function check(ok, label) {
  report.checks.push({ pass: Boolean(ok), label });
  assert(ok, label);
  console.log("PASS " + label);
}
async function until(fn, tries = 150) {
  for (let i = 0; i < tries; i++) {
    if (await fn().catch(() => false)) return;
    await sleep(100);
  }
  throw new Error("state deadline exceeded");
}
let browser;
try {
  for (let i = 0; i < 60 && !browser; i++) {
    await sleep(500);
    browser = await chromium
      .connectOverCDP("http://127.0.0.1:9338")
      .catch(() => null);
  }
  check(browser, "packaged app starts with isolated profile and APPDATA");
  const pages = () => browser.contexts().flatMap((c) => c.pages());
  await until(
    async () =>
      pages().some((p) => p.url().startsWith(origin)) &&
      pages().some((p) => p.url().includes("shell=unified")),
  );
  const web = pages().find((p) => p.url().startsWith(origin));
  const tools = pages().find((p) => p.url().includes("shell=unified"));
  shot = (name) =>
    tools
      .screenshot({ path: path.join(output, name + ".png"), timeout: 4000 })
      .catch(() => {});
  const errors = [];
  web.on("pageerror", (e) => errors.push("web: " + e.message));
  tools.on("pageerror", (e) => errors.push("tools: " + e.message));
  const state = () =>
    tools.evaluate(() => ({
      mode: document.body.dataset.mode,
      title: document.querySelector("#panel-title").textContent,
      open: [...document.querySelectorAll("dialog[open]")].map((d) => d.id),
      offline: !document.querySelector("#offline-note").hidden,
    }));
  const core = () => tools.evaluate(() => window.launcher.state());
  const navigate = async (route) =>
    web.evaluate((route) => {
      history.pushState({}, "", route);
      dispatchEvent(new PopStateEvent("popstate"));
    }, route);

  // 1. Several synthetic saves and none chosen: the selector opens by itself.
  await until(async () => (await state()).open.includes("selector-dialog"));
  const choice = (await core()).save_choice;
  const options = await tools.locator("#selector-list .save-option").count();
  check(
    choice.status === "CHOOSE" && choice.count === 2 && options === 2,
    "two candidates: selector opens over the web, nothing selected",
  );
  check(!(await core()).selected_save, "no save chosen without the trainer");
  await shot("selector");
  await tools.locator("#selector-dialog [data-close]").first().click();
  await until(async () => (await state()).mode === "strip");
  check(true, "closing the selector hands the window back to the web");

  const isolated = await web.evaluate(() => ({
    node: typeof require,
    process: typeof process,
    bridge: typeof window.launcher,
    marker: navigator.userAgent.includes("PokeAppLauncher/"),
  }));
  check(
    isolated.node === "undefined" &&
      isolated.process === "undefined" &&
      isolated.bridge === "undefined" &&
      isolated.marker,
    "web has no Node, preload or IPC bridge",
  );
  await web.getByRole("button", { name: "Entrar a PokeApp" }).waitFor();
  await web.getByLabel("Entrenador", { exact: true }).fill("Synthetic 28");
  await web.getByLabel("PIN", { exact: true }).fill("1234");
  await web.getByRole("button", { name: "Entrar a PokeApp" }).click();
  await web
    .getByRole("heading", { name: "A por la siguiente, Antonio." })
    .waitFor();
  check(true, "preview web signs in with its synthetic API");
  const native = await core();
  check(
    native.auth_status === "LOGIN_REQUIRED" && native.cloud_sync === false,
    "a preview sign-in never reaches the core (different API: no forwarding)",
  );
  check(
    native.write?.production_operations_enabled === false,
    "production physical operations disabled",
  );
  const groups = await web
    .getByRole("navigation", { name: "Principal" })
    .locator(".nav-group-label")
    .allTextContents();
  check(!groups.includes("ESCRITORIO"), "same sidebar as the browser");

  // 2. Saves y Launcher opens the native hub beside the sidebar.
  const nav = web.getByRole("navigation", { name: "Principal" });
  await nav
    .getByRole("link", { name: "Saves y Launcher", exact: true })
    .click();
  await until(async () => {
    const s = await state();
    return s.mode === "panel" && s.title === "Saves y Launcher";
  });
  check(true, "Saves y Launcher opens the native hub");
  await shot("hub");
  for (const [tab, view] of [
    ["backups-tab", "backups-view"],
    ["cloud-tab", "cloud-view"],
    ["save-tab", "save-view"],
  ]) {
    await tools.locator("#" + tab).click();
    check(
      await tools.locator("#" + view).isVisible(),
      `hub tab ${tab} shows its section`,
    );
  }
  await tools.locator("#cloud-tab").click();
  await tools.locator("#check-update").click();
  await until(async () => (await state()).open.includes("update-dialog"));
  check(
    /no tiene activado un canal/.test(
      await tools.locator("#update-message").textContent(),
    ) && (await tools.locator("#update-go").isHidden()),
    "Buscar actualizaciones is honest: no channel, nothing offered",
  );
  await shot("update");
  await tools.locator("#update-dialog [data-close]").first().click();
  check((await state()).mode === "panel", "closing a dialog keeps the hub");
  await tools.getByRole("button", { name: /Volver a PokeApp/ }).click();
  await until(async () => (await state()).mode === "strip");
  check(true, "Volver a PokeApp closes the hub");

  // 3. Infinite items open the native popup over the profile.
  await navigate("/entrenadores/10000000-0000-4000-8000-000000000002");
  await web.getByText("Objetos ilimitados").waitFor();
  const hrefs = await web
    .getByRole("link", { name: "Añadir a la bolsa" })
    .evaluateAll((els) => els.map((e) => e.getAttribute("href")));
  check(
    hrefs.join() ===
      "/escritorio/objetos/rare_candy,/escritorio/objetos/heart_scale",
    "inventory doors name only approved items",
  );
  await web.getByRole("link", { name: "Añadir a la bolsa" }).first().click();
  await until(async () => (await state()).open.includes("sheet-dialog"));
  check(
    (await state()).mode === "modal" &&
      (await tools.locator("#sheet-title").textContent()) === "Objetos ∞",
    "item popup opens over the web",
  );
  await shot("items");
  await tools.locator("#sheet-dialog [data-close]").first().click();
  await until(
    async () =>
      (await state()).mode === "strip" && web.url().includes("/entrenadores/"),
  );
  check(true, "closing the popup returns to the profile");

  // 4. IPC refuses confirmations that main did not issue for that action.
  const refusals = await tools.evaluate(async () => {
    const out = [];
    for (const call of [
      () => window.launcher.confirmBegin("restore", "not-a-backup"),
      () => window.launcher.confirmBegin("delete-everything", "x"),
      () =>
        window.launcher.restoreBackup(
          "not-a-backup",
          true,
          "Confirmo",
          "forged",
        ),
      () => window.launcher.confirmWrite("op", true, "forged"),
      () => window.launcher.applyUpdate("forged"),
    ])
      out.push(
        await call().then(
          (r) => (r?.status === "DISABLED" ? "refused" : "accepted"),
          () => "refused",
        ),
      );
    return out;
  });
  check(
    refusals.every((r) => r === "refused"),
    "forged or stale confirmations are refused by main",
  );

  // 5. Bridge codes: data-free only; nothing else reaches main.
  const before = web.url();
  for (const code of [
    "/__launcher/session?token=stolen",
    "/__launcher/session/x",
    "/__launcher/pin",
  ]) {
    await web.evaluate((c) => location.assign(c), code).catch(() => {});
    await sleep(400);
  }
  check(web.url() === before, "malformed bridge codes are blocked in place");
  await navigate("/escritorio/admin");
  await sleep(600);
  check((await state()).mode === "strip", "non-allowlisted route ignored");
  await web.evaluate(() => {
    for (let i = 0; i < 30; i++) {
      history.pushState({}, "", i % 2 ? "/liga" : "/saves");
      dispatchEvent(new PopStateEvent("popstate"));
    }
  });
  await sleep(900);
  await until(async () => (await state()).mode === "strip");
  check(web.url().endsWith("/liga"), "30 rapid transitions: latest wins");

  // 6. Logout, foreign navigation, offline fallback.
  // The sign-out also navigates to /__launcher/logout, which the Launcher
  // cancels: do not wait for a navigation that never completes.
  await web
    .getByRole("button", { name: "Cerrar sesión" })
    .click({ noWaitAfter: true });
  // Read the DOM: Playwright keeps waiting for the cancelled navigation.
  await until(() =>
    web.evaluate(() =>
      [...document.querySelectorAll("button")].some((b) =>
        b.textContent.includes("Entrar a PokeApp"),
      ),
    ),
  );
  check(
    (await state()).mode === "strip" &&
      (await core()).auth_status === "LOGIN_REQUIRED",
    "web logout: login shown, core signed out",
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
  check(
    (await state()).offline && (await tools.locator("#save-view").isVisible()),
    "offline: local tools with the same tabs",
  );
  await shot("offline");
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
  check(true, "online recovery returns to the web");
  check(
    errors.length === 0,
    "no web/tools JavaScript errors " + errors.join(" | "),
  );
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.error = String(error.message).slice(0, 1200);
  console.error(report.error);
} finally {
  // Close only this spawned test instance. No owner process is touched.
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
