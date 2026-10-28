// Headless renderer + actual Python stdio/native parser. Never controls the desktop.
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { createServer } from "node:http";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const root = process.cwd(),
  evidence = process.argv[2],
  fixture = process.argv[3],
  game = process.argv[4] || "B2",
  xy = ["X", "Y"].includes(game),
  generation = xy ? 6 : 5;
if (!evidence || !fixture)
  throw new Error("Provide private evidence directory and synthetic save");
await mkdir(evidence, { recursive: true });
const profile = await mkdtemp(path.join(evidence, "ui-profile-"));
const trainer = "11111111-1111-4111-8111-111111111111",
  season = "22222222-2222-4222-8222-222222222222";
const principal = {
  trainer_id: trainer,
  display_name: "Fixture",
  is_admin: false,
  globally_enabled: true,
};
let mode = "offline",
  slowStarted = false,
  putCount = 0,
  getCount = 0,
  accepted = null,
  lastBody = null;
const sort = (value) =>
  Array.isArray(value)
    ? value.map(sort)
    : value && typeof value === "object"
      ? Object.fromEntries(
          Object.keys(value)
            .sort()
            .map((k) => [k, sort(value[k])]),
        )
      : value;
const server = createServer(async (req, res) => {
  if (mode === "offline") {
    res.writeHead(503);
    res.end("{}");
    return;
  }
  if (mode === "slow") {
    slowStarted = true;
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const payload = Buffer.concat(chunks).toString();
  let value;
  if (req.url === "/health") value = { status: "ok", service: "pokeapp-api" };
  else if (req.url === "/v1/auth/pin-login") {
    assert.equal(JSON.parse(payload).pin, "0000");
    value = {
      trainer_id: trainer,
      auth_user_id: trainer,
      session: {
        user_id: trainer,
        access_token: "fixture-access",
        refresh_token: "fixture-refresh",
        expires_at: Math.floor(Date.now() / 1000) + 3600,
      },
    };
  } else if (req.url === "/v1/me") value = principal;
  else if (req.url === "/v1/read/seasons")
    value = {
      items: [{ id: season, name: "Local fixture", status: "active" }],
    };
  else if (req.url?.endsWith("/shop")) value = { balance: "8.4" };
  else if (req.url?.includes("/observations/")) {
    assert.equal(req.headers.authorization, "Bearer fixture-access");
    if (req.method === "PUT") {
      putCount++;
      lastBody = JSON.parse(payload);
      accepted = {
        id: req.url.split("/").at(-1),
        trainer_id: trainer,
        season_id: season,
        payload_digest: createHash("sha256")
          // Match Python's ensure_ascii canonical envelope, including nicknames.
          .update(
            JSON.stringify(sort(lastBody)).replace(
              /[\u007f-\uffff]/g,
              (char) =>
                "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0"),
            ),
          )
          .digest("hex"),
        received_at: new Date().toISOString(),
        trust: "client_observed",
        competitive_authority: false,
      };
      req.socket.destroy();
      return; // accepted, response lost; must reconcile, never duplicate PUT
    }
    getCount++;
    if (!accepted) {
      res.writeHead(404);
      res.end("{}");
      return;
    }
    value = accepted;
  } else {
    res.writeHead(404);
    res.end("{}");
    return;
  }
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify(value));
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const originalHash = createHash("sha256")
  .update(await readFile(fixture))
  .digest("hex");
let worker,
  sequence = 0,
  pending = new Map(),
  browser;
function request(command, args = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence,
      timeout = setTimeout(() => {
        pending.delete(id);
        reject(new Error("stdio timeout"));
      }, 10000);
    pending.set(id, { resolve, reject, timeout });
    worker.stdin.write(JSON.stringify({ id, command, args }) + "\n");
  });
}
function start() {
  worker = spawn(
    path.join(root, ".venv-api/Scripts/python.exe"),
    [
      "-m",
      "app.launcher.stdio",
      "--profile",
      profile,
      "--parser",
      path.join(
        root,
        "companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe",
      ),
      "--backend",
      origin,
    ],
    {
      cwd: root,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, DOTNET_ROOT: "C:\\Program Files\\dotnet" },
    },
  );
  createInterface({ input: worker.stdout }).on("line", (line) => {
    const msg = JSON.parse(line),
      task = pending.get(msg.id);
    if (!task) return;
    pending.delete(msg.id);
    clearTimeout(task.timeout);
    if (msg.error) task.reject(new Error(msg.error));
    else task.resolve(msg.result);
  });
  worker.on("exit", () => {
    for (const t of pending.values()) {
      clearTimeout(t.timeout);
      t.reject(new Error("worker exited"));
    }
    pending.clear();
  });
}
async function stop() {
  if (!worker || worker.exitCode !== null) return;
  const closed = new Promise((resolve) => worker.once("exit", resolve));
  worker.stdin.end();
  await closed;
}
async function until(predicate) {
  const deadline = Date.now() + 20000;
  do {
    if (await predicate()) return;
    await new Promise((r) => setTimeout(r, 100));
  } while (Date.now() < deadline);
  throw new Error("Timed out waiting for expected state");
}
try {
  start();
  const started = performance.now();
  await request("select", { path: fixture });
  browser = await chromium.launch({ channel: "msedge", headless: true });
  const page = await browser.newPage({
      viewport: { width: 1120, height: 820 },
    }),
    errors = [],
    network = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (req) => {
    if (req.url().startsWith("http")) network.push(req.url());
  });
  await page.exposeFunction("pipe", async (command, args) =>
    request(command, args),
  );
  await page.addInitScript(() => {
    window.launcher = {
      state: (known_receipt) => window.pipe("state", { known_receipt }),
      chooseSave: () => Promise.resolve({ status: "CANCELLED" }),
      login: (trainer, pin) => window.pipe("login", { trainer, pin }),
      logout: () => window.pipe("logout"),
      retry: () => window.pipe("retry"),
      sync: () => window.pipe("sync"),
    };
  });
  await page.goto(
    pathToFileURL(path.join(root, "companion/launcher/index.html")).href,
  );
  await page.locator("#party button").first().waitFor();
  const startup = performance.now() - started;
  assert.equal(await page.locator("#party .slot").count(), 6);
  // Owner decision 2026-10-28: «Saves y Launcher» shows the team only; the
  // boxes are read for «Mi PC» and robberies, not browsed here.
  assert.equal(await page.locator("#box, #box-name, #next-box").count(), 0);
  if (xy) {
    assert.match(
      await page.locator("#save-identity").innerText(),
      new RegExp(`${game} · Gen 6`),
    );
  }
  async function navigation() {
    // Opening a team member's details is the remaining local navigation.
    return await page.evaluate(async () => {
      const samples = [];
      for (let i = 0; i < 20; i++) {
        const begin = performance.now();
        document.querySelectorAll("#party button")[i % 6]?.click();
        await new Promise(requestAnimationFrame);
        document.getElementById("close-details")?.click();
        samples.push(performance.now() - begin);
      }
      return samples;
    });
  }
  const offline = await navigation();
  await page.locator("#party button").first().click();
  await page.locator("#details[open]").waitFor();
  assert.match(await page.locator("#pokemon-details").innerText(), /IV/);
  await page.locator("#close-details").click();
  await page.screenshot({ path: path.join(evidence, "local-offline.png") });
  mode = "slow";
  await request("retry");
  await until(async () => slowStarted);
  const slow = await navigation();
  mode = "online";
  await request("login", { trainer: "fixture", pin: "0000" });
  await until(
    async () => (await request("state")).cloud?.data?.wallet === "8.4",
  );
  await request("sync");
  const syncStart = performance.now();
  await request("retry");
  await until(async () => putCount === 1);
  await request("retry");
  await until(async () => Boolean((await request("state")).cloud_receipt));
  const syncMs = performance.now() - syncStart;
  assert.equal(putCount, 1);
  assert.ok(getCount >= 2);
  assert.equal(lastBody.observation.generation, generation);
  assert.equal(lastBody.observation.game, game);
  if (xy) assert.equal(lastBody.observation.progress, null);
  else
    assert.equal(
      lastBody.observation.progress.regions[0].badge_flags.filter(Boolean)
        .length,
      0,
    );
  mode = "offline";
  await stop();
  const restarted = performance.now();
  start();
  const cached = await request("state");
  const cachedMs = performance.now() - restarted;
  assert.equal(cached.observation.generation, generation);
  assert.equal(cached.observation.game, game);
  assert.equal(cached.cloud.data.wallet, "8.4");
  assert.equal(cached.cloud_stale, true);
  assert.equal(cached.auth_status, "STALE");
  assert.equal(
    createHash("sha256")
      .update(await readFile(fixture))
      .digest("hex"),
    originalHash,
  );
  assert.deepEqual(network, []);
  assert.deepEqual(errors, []);
  assert.ok(
    Math.max(...offline, ...slow) < 200,
    "Local navigation unexpectedly blocked",
  );
  if (xy) {
    const unsupported = Buffer.alloc(0x76000);
    unsupported.writeUInt32LE(0x42454546, unsupported.length - 0x1f0);
    const invalidPath = path.join(evidence, "unsupported.sav");
    await writeFile(invalidPath, unsupported);
    await request("select", { path: invalidPath });
    await until(
      async () => (await request("state")).local_status === "UNSUPPORTED_GAME",
    );
    await until(async () =>
      (await page.locator("#save-state").innerText()).includes(
        "Juegos admitidos",
      ),
    );
    assert.equal(putCount, 1, "Unsupported input cannot become an upload");
    assert.equal((await request("state")).observation, null);
  }
  const result = {
    status: "PASS",
    game,
    generation,
    startup_useful_ui_ms: startup,
    cached_restart_state_ms: cachedMs,
    offline_team_navigation_ms: offline,
    three_second_network_team_navigation_ms: slow,
    background_sync_with_lost_response_ms: syncMs,
    receipt_gets: getCount,
    put_count: putCount,
    local_party_slots: 6,
    visible_box_slots: 30,
    source_unchanged: true,
    renderer_network_requests: network.length,
    page_errors: errors.length,
    boundary:
      "Headless Edge renders real local UI with actual Python stdio/native parser; shell IPC/native file dialog statically checked, not visibly launched.",
  };
  await writeFile(
    path.join(evidence, "ui.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result));
} finally {
  if (browser) await browser.close();
  await stop();
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
}
