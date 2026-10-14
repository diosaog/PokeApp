// Real local API/PG and real Launcher stdio/native parser. No API interception.
import {
  chromium,
  expect,
} from "../web/node_modules/@playwright/test/index.mjs";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { once } from "node:events";
import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import path from "node:path";
import assert from "node:assert/strict";

const out = path.resolve(process.argv[2]);
const fixture = JSON.parse(
  await readFile(path.join(out, "browser-input.json"), "utf8"),
);
assert.equal(new URL(fixture.api).hostname, "127.0.0.1");
const root = process.cwd();
const vite = spawn(
  process.execPath,
  [
    "node_modules/vite/bin/vite.js",
    "--host",
    "127.0.0.1",
    "--port",
    "5173",
    "--strictPort",
  ],
  {
    cwd: path.join(root, "web"),
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, VITE_API_BASE_URL: fixture.api },
  },
);
let core,
  browser,
  sequence = 0;
const pending = new Map(),
  errors = [],
  responses = [];
function request(command, args = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error("stdio timeout"));
    }, 10000);
    pending.set(id, { resolve, reject, timer });
    core.stdin.write(JSON.stringify({ id, command, args }) + "\n");
  });
}
try {
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch("http://127.0.0.1:5173")).ok) break;
    } catch {}
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await chromium.launch({ channel: "msedge", headless: true });
  const page = await browser.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => {
    if (r.url().startsWith(fixture.api))
      responses.push({ path: new URL(r.url()).pathname, status: r.status() });
  });
  async function login() {
    await page.getByLabel("Entrenador", { exact: true }).fill("phase16d-alia");
    await page.getByLabel("PIN", { exact: true }).fill(fixture.pin);
    await page.getByRole("button", { name: "Entrar a PokeApp" }).click();
  }
  // Auth is intentionally memory-only: reload requires login again, then resolves same save.
  await page.goto("http://127.0.0.1:5173/saves");
  await login();
  await expect(page.getByText("Registrado el", { exact: false })).toBeVisible({
    timeout: 30000,
  });
  await page.reload();
  await login();
  await expect(page.getByText("Registrado el", { exact: false })).toBeVisible({
    timeout: 30000,
  });
  await page.getByRole("link", { name: "Mi PC", exact: true }).first().click();
  await expect(
    page.getByRole("heading", {
      name: "Siempre hay un próximo equipo.",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("Sparky", { exact: true }).first()).toBeVisible({
    timeout: 30000,
  });
  await page
    .getByRole("link", { name: "Entrenadores", exact: true })
    .first()
    .click();
  await page
    .getByRole("link", { name: /16D Alia/ })
    .first()
    .click();
  await expect(
    page.getByText("Save registrado y disponible en Mi PC."),
  ).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: path.join(out, "own-trainer.png") });
  // Use SPA navigation for rival profile without losing in-memory authentication.
  await page
    .getByRole("link", { name: "Entrenadores", exact: true })
    .first()
    .click();
  await page
    .getByRole("link", { name: /16D Bruno/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "16D Bruno", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Mi save actual" }),
  ).toHaveCount(0);
  await expect(
    page.getByText("No hay un equipo fijado disponible.", { exact: false }),
  ).toBeVisible({ timeout: 30000 });
  assert(!responses.some((r) => r.status >= 400));
  // Actual launcher UI + local worker, against the same native-byte/API/PG path.
  core = spawn(
    path.join(root, ".venv-api/Scripts/python.exe"),
    [
      "-m",
      "app.launcher.stdio",
      "--profile",
      path.join(out, "launcher-profile"),
      "--parser",
      fixture.parser,
      "--backend",
      fixture.api,
    ],
    { cwd: root, windowsHide: true, stdio: ["pipe", "pipe", "pipe"] },
  );
  createInterface({ input: core.stdout }).on("line", (line) => {
    const msg = JSON.parse(line),
      item = pending.get(msg.id);
    if (!item) return;
    pending.delete(msg.id);
    clearTimeout(item.timer);
    if (msg.error) item.reject(new Error(msg.error));
    else item.resolve(msg.result);
  });
  await request("select", { path: fixture.fixture });
  const launcher = await browser.newPage();
  launcher.on("pageerror", (e) => errors.push(e.message));
  await launcher.exposeFunction("pipe", request);
  await launcher.addInitScript(() => {
    window.launcher = {
      state: (known_receipt) => window.pipe("state", { known_receipt }),
      chooseSave: async () => ({ status: "CANCELLED" }),
      login: (trainer, pin) => window.pipe("login", { trainer, pin }),
      logout: () => window.pipe("logout"),
      sync: () => window.pipe("sync"),
      retry: () => window.pipe("retry"),
    };
  });
  await launcher.goto(
    pathToFileURL(path.join(root, "companion/launcher/index.html")).href,
  );
  await expect(launcher.locator("#party button").first()).toBeVisible({
    timeout: 30000,
  });
  await request("login", { trainer: "phase16d-alia", pin: fixture.pin });
  for (let i = 0; i < 100; i++) {
    if ((await request("state")).auth_status === "VERIFIED") break;
    await new Promise((r) => setTimeout(r, 100));
  }
  await request("sync");
  await request("retry");
  await expect(launcher.locator("#receipt")).toHaveText("Sincronizado", {
    timeout: 45000,
  });
  const state = await request("state");
  assert.equal(state.cloud_receipt.status, "registered");
  assert.equal(state.cloud_receipt.is_current, true);
  assert.equal(state.observation.game, "B2");
  await page.goto("http://127.0.0.1:5173/saves");
  await login();
  await expect(page.getByText("Registrado el", { exact: false })).toBeVisible({
    timeout: 30000,
  });
  const pcResponse = page.waitForResponse(
    (r) =>
      r.url() === `${fixture.api}/v1/read/seasons/${fixture.season}/pc` &&
      r.ok(),
  );
  await page.reload();
  await login();
  assert.equal(
    (await (await pcResponse).json()).save.id,
    state.cloud_receipt.save_id,
  );
  assert.deepEqual(errors, []);
  const report = {
    status: "PASS",
    real_api_responses: responses.length,
    no_api_interception: true,
    reload_save_pc_own_trainer: true,
    rival_private_pc_not_requested: true,
    launcher_raw_receipt_pc_readback: true,
    page_errors: errors,
  };
  await writeFile(
    path.join(out, "browser.json"),
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report));
} finally {
  if (browser) await browser.close();
  if (core && core.exitCode === null) {
    const end = once(core, "exit");
    core.stdin.end();
    await end;
  }
  for (const item of pending.values()) clearTimeout(item.timer);
  if (vite.exitCode === null) {
    const end = once(vite, "exit");
    vite.kill();
    await end;
  }
}
