// Real update rehearsal between two packaged private versions.
//
// Installs version A of «PokeApp Launcher UpdateTest» (its own app id, install
// folder and profile — never the owner's Launcher) from its real NSIS
// installer, serves a signed loopback feed with a temporary Ed25519 key, and
// drives the real app over CDP: refusals (forged signature, downgrade,
// incompatible jump, wrong channel, corrupted bytes, dropped connection), the
// popup and «Más tarde», the block during a recovery, an unfinished install
// recovered at the next start, then the real update to version B with its
// silent installer and automatic restart, and the data kept across it.
// Synthetic saves only (in the rehearsal sandbox APPDATA), no account.
//
//   node tools/validate_launcher_update_e2e.mjs --a <build root A> --b <build root B>
//        --va <version A> --vb <version B> --key <rehearsal private key> --out <dir>
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { spawn, execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const { sign } = require("./sign_launcher_update.cjs");
const asar = require("../companion/launcher/node_modules/@electron/asar");
const args = Object.fromEntries(
  process.argv
    .slice(2)
    .reduce(
      (pairs, value, i, all) =>
        value.startsWith("--")
          ? [...pairs, [value.slice(2), all[i + 1]]]
          : pairs,
      [],
    ),
);
for (const name of ["a", "b", "va", "vb", "key", "out"])
  assert(args[name], "missing --" + name);
const out = path.resolve(args.out);
const product = "PokeApp Launcher UpdateTest";
const setup = (root) =>
  path.join(root, "release", "PokeApp-Launcher-UpdateTest-Setup.exe");
const install = path.join(out, "install");
const exe = path.join(install, product + ".exe");
const profile = path.join(
  process.env.LOCALAPPDATA,
  "PokeApp",
  "Launcher-UpdateTest",
);
const PORT = 8766;
const report = {
  versions: { a: args.va, b: args.vb },
  status: "RUNNING",
  checks: [],
  boundaries:
    "Rehearsal app id/profile/install folder, loopback feed, temporary key, synthetic saves; not the owner's Launcher, no account, nothing published.",
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now();
const log = (message) =>
  console.log(`[${((Date.now() - t0) / 1000).toFixed(1)}s] ${message}`);
function check(ok, label) {
  report.checks.push({ pass: Boolean(ok), label });
  assert(ok, label);
  log("PASS " + label);
}
// No single call may hang the rehearsal: each attempt has its own deadline.
const bounded = (promise, ms) =>
  Promise.race([
    promise,
    sleep(ms).then(() => {
      throw new Error("call timed out");
    }),
  ]);
async function until(fn, ms = 30000, step = 200) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const value = await bounded(Promise.resolve().then(fn), 10000).catch(
      () => null,
    );
    if (value) return value;
    await sleep(step);
  }
  throw new Error("deadline exceeded");
}
const ps = (command) =>
  execFileSync(
    "powershell.exe",
    ["-NoProfile", "-NonInteractive", "-Command", command],
    { encoding: "utf8" },
  ).trim();
const running = () =>
  ps(
    `Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith('${install.replace(/'/g, "''")}', 'OrdinalIgnoreCase') } | ForEach-Object { $_.ProcessId }`,
  )
    .split(/\s+/)
    .filter(Boolean)
    .map(Number);
const installedVersion = () =>
  JSON.parse(
    asar
      .extractFile(path.join(install, "resources", "app.asar"), "package.json")
      .toString("utf8"),
  ).version;
const sha = (file) =>
  crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");

// ---- Preconditions: everything disposable, nothing pre-existing.
assert(!fs.existsSync(profile), "rehearsal profile already exists: " + profile);
assert(!fs.existsSync(install), "install folder already exists: " + install);
for (const root of [args.a, args.b]) assert(fs.existsSync(setup(root)));
fs.mkdirSync(out, { recursive: true });

// ---- Signed loopback feed.
const installerB = fs.readFileSync(setup(args.b));
const keyFile = path.resolve(args.key);
const privateKey = crypto.createPrivateKey(fs.readFileSync(keyFile));
const url = `http://127.0.0.1:${PORT}/b.exe`;
const envelopeOf = (manifest, key = privateKey) => {
  const body = Buffer.from(JSON.stringify(manifest));
  return {
    manifest: body.toString("base64"),
    signature: crypto.sign(null, body, key).toString("base64"),
  };
};
// The real offer goes through the release signer itself.
const offerFile = path.join(out, "private.json");
sign({
  installer: setup(args.b),
  version: args.vb,
  channel: "private",
  minimum: args.va,
  notes:
    "- Ensayo de actualización entre dos versiones privadas\n- Descarga verificada con firma Ed25519 y SHA-512",
  url,
  keyFile,
  out: offerFile,
  authenticode: "NotSigned",
});
const offer = JSON.parse(fs.readFileSync(offerFile, "utf8"));
const offerManifest = JSON.parse(
  Buffer.from(offer.manifest, "base64").toString("utf8"),
);
const feeds = {
  offer,
  same: envelopeOf({ ...offerManifest, version: args.va }),
  forged: envelopeOf(
    offerManifest,
    crypto.generateKeyPairSync("ed25519").privateKey,
  ),
  downgrade: envelopeOf({ ...offerManifest, version: "0.25.0" }),
  incompatible: envelopeOf({ ...offerManifest, minimum_version: args.vb }),
  channel: envelopeOf({ ...offerManifest, channel: "stable" }),
};
const scenario = { feed: "same", installer: "ok", served: 0 };
const server = http.createServer((req, res) => {
  if (req.url === "/private.json") {
    if (scenario.feed === "down") return res.writeHead(503).end();
    res.writeHead(200, { "content-type": "application/json" });
    return res.end(JSON.stringify(feeds[scenario.feed]));
  }
  if (req.url !== "/b.exe") return res.writeHead(404).end();
  scenario.served++;
  const bytes =
    scenario.installer === "corrupt"
      ? Buffer.from(installerB).map((b, i) => (i === 4096 ? b ^ 0xff : b))
      : installerB;
  res.writeHead(200, {
    "content-type": "application/octet-stream",
    "content-length": bytes.length,
  });
  // Paced (about 40 MB/s) so the popup can show the progress.
  let offset = 0;
  const cut =
    scenario.installer === "drop" ? Math.floor(bytes.length * 0.3) : Infinity;
  const pump = () => {
    if (offset >= cut) return req.socket.destroy();
    if (offset >= bytes.length) return res.end();
    const end = Math.min(offset + 1024 * 1024, bytes.length, cut);
    res.write(bytes.subarray(offset, end));
    offset = end;
    setTimeout(pump, 25);
  };
  pump();
});
await new Promise((r) => server.listen(PORT, "127.0.0.1", r));

// ---- Environment: the visible app, without test overrides.
const env = { ...process.env };
for (const name of [
  "ELECTRON_RUN_AS_NODE",
  "POKEAPP_LAUNCHER_PROFILE",
  "POKEAPP_LAUNCHER_HEADLESS_TEST",
  "POKEAPP_WEB_ORIGIN",
])
  delete env[name];
let browser = null,
  child = null,
  tools = null;
async function start(port) {
  log("start on port " + port);
  child = spawn(exe, [`--remote-debugging-port=${port}`], {
    env,
    stdio: "ignore",
  });
  browser = await until(
    () => chromium.connectOverCDP(`http://127.0.0.1:${port}`),
    40000,
    500,
  );
  tools = await until(async () =>
    browser
      .contexts()
      .flatMap((c) => c.pages())
      .find((p) => p.url().includes("shell=unified")),
  );
  await until(() => tools.evaluate(() => Boolean(window.launcher)));
}
async function stop({ abrupt = false } = {}) {
  log(abrupt ? "kill" : "close");
  if (abrupt) execFileSync("taskkill", ["/PID", String(child.pid), "/T", "/F"]);
  else {
    const session = await bounded(browser.newBrowserCDPSession(), 5000).catch(
      () => null,
    );
    await bounded(session?.send("Browser.close"), 5000).catch(() => {});
  }
  await bounded(browser?.close(), 5000).catch(() => {});
  browser = null;
  // The core (and anything else from the install folder) must be gone.
  await until(async () => running().length === 0, 30000, 500);
}
const updateState = () => tools.evaluate(() => window.launcher.updateState());
const manualCheck = () => tools.evaluate(() => window.launcher.checkUpdate());
const shot = (name) =>
  tools
    .screenshot({ path: path.join(out, name + ".png"), timeout: 8000 })
    .catch(() => {});
const updatesDir = path.join(profile, "updates");
const files = () =>
  fs.existsSync(updatesDir) ? fs.readdirSync(updatesDir).sort() : [];
// «Actualizar» exactly as a trainer does it: open the popup and click.
// The page polls main every second: act on (or capture) what it shows.
async function synced() {
  const { status, reason } = await updateState();
  await until(() =>
    tools.evaluate(
      ([s, r]) => lastUpdate?.status === s && lastUpdate?.reason === r,
      [status, reason],
    ),
  );
}
async function clickUpdate() {
  await synced();
  await tools.evaluate(() => present("update", { check: false }));
  await until(() =>
    tools.evaluate(
      () =>
        document.querySelector("#update-dialog").open &&
        !document.querySelector("#update-go").hidden,
    ),
  );
  // The button's own handler, as a click delivers it (CDP pointer events on a
  // WebContentsView can misjudge its viewport right after a resize).
  await sleep(300);
  await tools.evaluate(() => document.querySelector("#update-go").click());
}

try {
  // 1. Install version A with its real installer into a disposable folder.
  fs.mkdirSync(profile, { recursive: true });
  const saveDir = path.join(
    profile,
    "sandbox-appdata",
    "Lime3DS",
    "sdmc",
    "Nintendo 3DS",
    "0".repeat(32),
    "0".repeat(32),
    "title",
    "00040000",
    "00055e00",
    "data",
    "00000001",
  );
  fs.mkdirSync(saveDir, { recursive: true });
  fs.writeFileSync(path.join(saveDir, "main"), Buffer.alloc(4096, 9));
  // A protected session bound to another origin: kept, never used or sent.
  execFileSync(path.resolve(".venv-api/Scripts/python.exe"), [
    "-c",
    "import json,sys;from pathlib import Path;from app.launcher.secrets import protect;Path(sys.argv[1]).write_bytes(protect(json.dumps({'origin':'https://rehearsal.invalid','tokens':{},'principal':{}}).encode()))",
    path.join(profile, "session.dpapi"),
  ]);
  execFileSync(setup(args.a), ["/S", `/D=${install}`]);
  check(
    fs.existsSync(exe) && installedVersion() === args.va,
    `real installer: version ${args.va} installed in a disposable folder`,
  );

  // 2. First start: no newer version.
  scenario.feed = "same";
  await start(9441);
  const first = await until(async () => {
    const u = await updateState();
    return ["UP_TO_DATE", "ERROR"].includes(u.status) && u;
  });
  check(first.status === "UP_TO_DATE", "start-up check: nothing newer");
  await tools.evaluate(() => present("update"));
  await until(() =>
    tools.evaluate(() =>
      /última versión/.test(
        document.querySelector("#update-message").textContent,
      ),
    ),
  );
  await shot("popup-up-to-date");
  check(true, "popup says «Estás utilizando la última versión»");
  await tools.evaluate(() => shut(document.querySelector("#update-dialog")));
  const selected = await until(async () => {
    const s = await tools.evaluate(() => window.launcher.state());
    return s.selected_save;
  });
  check(
    selected.includes("sandbox-appdata"),
    "one synthetic save in the sandbox is chosen automatically",
  );
  await tools.evaluate(() =>
    localStorage.setItem("rehearsal-marker", "kept-across-update"),
  );

  // 3. Refusals: nothing downloaded for any of them.
  for (const [feed, reason] of [
    ["forged", "SIGNATURE_INVALID"],
    ["downgrade", "DOWNGRADE_REJECTED"],
    ["incompatible", "INCOMPATIBLE_VERSION"],
    ["channel", "CHANNEL_MISMATCH"],
  ]) {
    scenario.feed = feed;
    const u = await manualCheck();
    check(
      u.status === "ERROR" && u.reason === reason && scenario.served === 0,
      `${feed} manifest refused (${reason}), nothing downloaded`,
    );
  }
  scenario.feed = "forged";
  await manualCheck();
  await synced();
  await tools.evaluate(() => present("update", { check: false }));
  await sleep(500);
  await shot("popup-forged-refused");
  await tools.evaluate(() => shut(document.querySelector("#update-dialog")));

  // 4. Corrupted bytes and a dropped connection: discarded, retry possible.
  scenario.feed = "offer";
  check((await manualCheck()).status === "AVAILABLE", "valid offer detected");
  // Only a ticket main issued for this offer starts it; the web has no bridge.
  const forged = await tools
    .evaluate(() => window.launcher.applyUpdate("forged-ticket"))
    .then(
      () => "accepted",
      () => "refused",
    );
  const web = browser
    .contexts()
    .flatMap((c) => c.pages())
    .find((p) => p.url().startsWith("http://127.0.0.1:4173"));
  check(
    forged === "refused" &&
      scenario.served === 0 &&
      (!web ||
        (await web.evaluate(
          () =>
            typeof window.launcher === "undefined" &&
            typeof require === "undefined",
        ))),
    "IPC: a forged ticket cannot start an update; the web has no native bridge",
  );
  scenario.installer = "corrupt";
  await clickUpdate();
  const corrupt = await until(async () => {
    const u = await updateState();
    return u.status === "ERROR" && u;
  }, 60000);
  check(
    corrupt.reason === "INTEGRITY_FAILED" &&
      files().every((f) => !f.endsWith(".exe") && f !== "pending.json"),
    "corrupted download refused by SHA-512 and removed",
  );
  scenario.installer = "drop";
  await clickUpdate();
  const dropped = await until(async () => {
    const u = await updateState();
    return u.status === "ERROR" && u;
  }, 60000);
  check(
    ["DOWNLOAD_INTERRUPTED", "DOWNLOAD_FAILED"].includes(dropped.reason) &&
      files().every((f) => !f.endsWith(".partial") && !f.endsWith(".exe")),
    "dropped connection: partial file removed, «Reintentar» offered",
  );
  await stop();

  // 5. Popup by itself at start, «Más tarde» remembered for that version.
  scenario.installer = "ok";
  await start(9442);
  await until(
    () => tools.evaluate(() => document.querySelector("#update-dialog").open),
    30000,
  );
  await sleep(600);
  await shot("popup-available");
  check(
    await tools.evaluate(
      () =>
        /Hay una versión nueva/.test(
          document.querySelector("#update-message").textContent,
        ) && document.querySelectorAll("#update-notes li").length === 2,
    ),
    "newer version: popup opens by itself with notes",
  );
  await tools.evaluate(() => document.querySelector("#update-later").click());
  await until(() => fs.existsSync(path.join(updatesDir, "postponed.json")));
  check(true, "«Más tarde» remembered for that version");
  await stop();
  await start(9443);
  await until(async () => (await updateState()).status === "AVAILABLE");
  await sleep(4000);
  check(
    !(await tools.evaluate(
      () => document.querySelector("#update-dialog").open,
    )),
    "no repeated popup at the next start",
  );
  await stop();

  // 6. Critical work blocks the install (real RECOVERY_REQUIRED in the core),
  //    after a full verified download with progress.
  // The engine's own folder is set aside (not deleted) and comes back after.
  const writes = path.join(profile, "writes");
  const aside = path.join(profile, "writes.rehearsal-aside");
  if (fs.existsSync(writes)) fs.renameSync(writes, aside);
  fs.mkdirSync(path.join(out, "writes-target"), { recursive: true });
  execFileSync("cmd", [
    "/c",
    "mklink",
    "/J",
    path.join(profile, "writes"),
    path.join(out, "writes-target"),
  ]);
  await start(9444);
  await until(async () => (await updateState()).status === "AVAILABLE");
  const seen = new Set();
  let progressShot = false;
  const servedBefore6 = scenario.served;
  await clickUpdate();
  // An impatient second click and a direct second request: still one download.
  await tools.evaluate(() => document.querySelector("#update-go").click());
  await tools
    .evaluate(async () => {
      const offer = await window.launcher.confirmBegin(
        "update",
        String(lastUpdate.version),
      );
      return window.launcher.applyUpdate(offer.ticket);
    })
    .catch(() => null);
  const deferred = await until(
    async () => {
      const u = await updateState();
      seen.add(u.status);
      if (
        u.status === "DOWNLOADING" &&
        !progressShot &&
        u.progress?.received > u.progress.total * 0.3
      ) {
        progressShot = true;
        await shot("popup-downloading");
      }
      return u.status === "READY" && u;
    },
    120000,
    100,
  );
  check(
    seen.has("DOWNLOADING") && progressShot,
    "download shows its progress in the popup",
  );
  check(
    scenario.served === servedBefore6 + 1,
    "repeated «Actualizar»: one single download",
  );
  check(
    deferred.deferred === "RECOVERY_PENDING" &&
      files().includes("pending.json") &&
      running().length > 0,
    "pending recovery: verified installer kept, install deferred, Launcher keeps running",
  );
  await shot("popup-deferred");
  // 7. The Launcher dies before installing (power cut, crash).
  await stop({ abrupt: true });
  execFileSync("cmd", ["/c", "rmdir", writes]);
  if (fs.existsSync(aside)) fs.renameSync(aside, writes);

  // 8. Next start, feed unreachable: the unfinished install is offered from
  //    the kept, re-verified file; the real update to B runs.
  scenario.feed = "down";
  const servedBefore = scenario.served;
  const keep = {
    config: sha(path.join(profile, "config.json")),
    session: sha(path.join(profile, "session.dpapi")),
    known: sha(path.join(profile, "known-saves.json")),
  };
  await start(9445);
  const ready = await until(async () => {
    const u = await updateState();
    return u.status === "READY" && u;
  });
  check(
    ready.version === args.vb,
    "unfinished install recovered at start (offline): «Instalar ahora»",
  );
  await clickUpdate();
  const installing = await until(
    async () => {
      try {
        const u = await updateState();
        return u.status === "INSTALLING" && u;
      } catch {
        return { status: "INSTALLING", lost: true };
      }
    },
    60000,
    100,
  );
  check(installing, "installing: the Launcher closes for the installer");
  check(
    scenario.served === servedBefore,
    "nothing downloaded again for the install",
  );
  await browser.close().catch(() => {});
  browser = null;

  // 9. The installer replaces A and restarts the Launcher by itself as B.
  await until(
    async () => installedVersion() === args.vb && running().length > 0,
    240000,
    1000,
  );
  check(true, `silent install done; ${args.vb} restarted by itself`);
  // The installer that restarted the Launcher may still hold its own file:
  // the new version must keep running and clean it up shortly after.
  await until(
    async () =>
      !files().some((f) => f.endsWith(".exe") || f === "pending.json"),
    100000,
    1000,
  );
  check(
    running().length > 0,
    "the restarted version keeps running and clears the downloaded installer",
  );
  for (const pid of running())
    try {
      execFileSync("taskkill", ["/PID", String(pid), "/T", "/F"]);
    } catch {}
  await until(async () => running().length === 0, 30000, 500);

  // 10. Same profile, new version: everything kept.
  scenario.feed = "offer";
  await start(9446);
  const after = await until(async () => {
    const u = await updateState();
    return ["UP_TO_DATE", "ERROR"].includes(u.status) && u;
  });
  check(
    after.current === args.vb && after.status === "UP_TO_DATE",
    `running ${args.vb}; the same feed is now «última versión»`,
  );
  const state = await tools.evaluate(() => window.launcher.state());
  check(state.selected_save === selected, "selected save kept");
  check(
    sha(path.join(profile, "config.json")) === keep.config &&
      sha(path.join(profile, "known-saves.json")) === keep.known,
    "configuration and known saves kept byte for byte",
  );
  check(
    sha(path.join(profile, "session.dpapi")) === keep.session &&
      execFileSync(
        path.resolve(".venv-api/Scripts/python.exe"),
        [
          "-c",
          "import json,sys;from pathlib import Path;from app.launcher.secrets import protect;print(json.loads(protect(Path(sys.argv[1]).read_bytes(),decrypt=True))['origin'])",
          path.join(profile, "session.dpapi"),
        ],
        { encoding: "utf8" },
      ).trim() === "https://rehearsal.invalid",
    "DPAPI-protected session kept and still decryptable",
  );
  check(
    (await tools.evaluate(() => localStorage.getItem("rehearsal-marker"))) ===
      "kept-across-update",
    "Launcher app data (Electron profile) kept",
  );
  await stop();
  report.installed_version = installedVersion();
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.error = String(error?.stack || error).slice(0, 2000);
  console.error(report.error);
} finally {
  await bounded(browser?.close(), 5000).catch(() => {});
  for (const pid of running())
    try {
      execFileSync("taskkill", ["/PID", String(pid), "/T", "/F"]);
    } catch {}
  server.close();
  try {
    // Only the test junction; the engine's own folder goes with the profile.
    if (fs.lstatSync(path.join(profile, "writes")).isSymbolicLink())
      execFileSync("cmd", ["/c", "rmdir", path.join(profile, "writes")]);
  } catch {}
  // Remove the rehearsal install (its own uninstaller) and profile.
  const uninstaller = path.join(install, `Uninstall ${product}.exe`);
  // NSIS relaunches its uninstaller from a temporary copy: wait for it.
  if (fs.existsSync(uninstaller))
    try {
      execFileSync(uninstaller, ["/S"]);
      for (let i = 0; i < 90 && fs.existsSync(exe); i++) await sleep(1000);
      await sleep(3000);
    } catch {}
  report.cleanup = {
    uninstall_entry_left: ps(
      `@(Get-ChildItem 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall' | Where-Object { (Get-ItemProperty $_.PSPath).DisplayName -like '${product}*' }).Count`,
    ),
  };
  for (const folder of [profile, install])
    try {
      fs.rmSync(folder, {
        recursive: true,
        force: true,
        maxRetries: 20,
        retryDelay: 500,
      });
    } catch {}
  report.cleanup.profile_removed = !fs.existsSync(profile);
  report.cleanup.install_removed = !fs.existsSync(install);
  fs.writeFileSync(
    path.join(out, "update-e2e.json"),
    JSON.stringify(report, null, 2),
  );
  console.log(
    `${report.status} ${report.checks.filter((c) => c.pass).length}/${report.checks.length}`,
  );
  // Leave nothing behind, even if a handle stays open.
  process.exit(report.status === "PASS" ? 0 : 1);
}
process.exitCode = report.status === "PASS" ? 0 : 1;
