// NSIS installation/update of exact release payloads under the disposable
// UpdateTest app identity. Does not install the owner's stable app identity.
import { spawn, execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import crypto from "node:crypto";
import assert from "node:assert/strict";
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";

const require = createRequire(import.meta.url);
const asar = require("../companion/launcher/node_modules/@electron/asar");
const { sign } = require("./sign_launcher_update.cjs");
const [a, b, key, outArg, fixture] = process.argv.slice(2);
assert(
  a && b && key && outArg && fixture,
  "a b private-key out synthetic-fixture required",
);
const out = path.resolve(outArg),
  install = path.join(out, "install");
const buildVersion = (root) => JSON.parse(asar.extractFile(
  path.join(root, "release/win-unpacked/resources/app.asar"), "package.json",
).toString()).version;
const va = buildVersion(a), vb = buildVersion(b);
assert.notEqual(va, vb, "the update must change version");
assert(!fs.existsSync(out), "use a fresh evidence directory");
const product = "PokeApp Launcher UpdateTest";
const exe = path.join(install, product + ".exe");
const profile = path.join(out, "profile");
const setup = (root) =>
  path.join(root, "release/PokeApp-Launcher-UpdateTest-Setup.exe");
const ps = (command) =>
  execFileSync(
    "powershell.exe",
    ["-NoProfile", "-NonInteractive", "-Command", command],
    { encoding: "utf8", windowsHide: true },
  ).trim();
const registrations = () =>
  JSON.parse(
    ps(
      "$r=@(Get-ChildItem 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall' | Get-ItemProperty | Where-Object { $_.DisplayName -match '^PokeApp Launcher UpdateTest( [0-9].*)?$' } | Select-Object DisplayName,UninstallString); ConvertTo-Json -InputObject $r -Compress",
    ),
  );
assert.equal(registrations().length, 0, "no existing UpdateTest installation");
fs.mkdirSync(profile, { recursive: true });
const report = {
  status: "RUNNING",
  from_version: va,
  to_version: vb,
  checks: [],
  boundary:
    "Exact stable code/runtime payloads repackaged with disposable UpdateTest identity and temporary update key. No owner installation or real account.",
};
const pass = (label) => {
  report.checks.push(label);
  console.log("PASS", label);
};
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(fn, ms = 30000) {
  const end = Date.now() + ms;
  do {
    const value = await fn().catch(() => null);
    if (value) return value;
    await pause(250);
  } while (Date.now() < end);
  throw new Error("test deadline exceeded");
}
const hash = (file) =>
  crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const version = () => {
  asar.uncacheAll();
  return JSON.parse(
    asar
      .extractFile(path.join(install, "resources/app.asar"), "package.json")
      .toString(),
  ).version;
};
const env = {
  ...process.env,
  LOCALAPPDATA: path.join(out, "localappdata"),
  APPDATA: path.join(out, "appdata"),
  POKEAPP_LAUNCHER_PROFILE: profile,
  POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
};
delete env.ELECTRON_RUN_AS_NODE;
let child, browser, shell, server;
async function start(port) {
  const started = Date.now();
  child = spawn(exe, [`--remote-debugging-port=${port}`], {
    env,
    windowsHide: true,
    stdio: "ignore",
  });
  // A failed public web load can delay CDP target attachment even while the
  // installed core is already READY. Keep attachment separate from the actual
  // core/observation deadline and bound every connection attempt.
  browser = await until(() =>
    chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 5000 }),
  120000);
  const attached = Date.now();
  shell = await until(async () =>
    browser
      .contexts()
      .flatMap((c) => c.pages())
      .find((p) => p.url().includes("shell=unified")),
  );
  await until(() =>
    shell.evaluate(async () => {
      const c = await window.launcher.core();
      if (c.status !== "READY") return null;
      const s = await window.launcher.state();
      return s.observation && s;
    }),
  );
  (report.startups ??= []).push({
    version: version(),
    cdp_attachment_ms: attached - started,
    core_observation_ms: Date.now() - attached,
  });
}
async function stop() {
  if (browser) {
    const session = await browser.newBrowserCDPSession();
    await Promise.race([
      session.send("Browser.close").catch(() => {}),
      pause(1500),
    ]);
    await browser.close().catch(() => {});
    browser = null;
  }
  if (child) {
    try {
      await until(async () => child.exitCode !== null);
    } catch (error) {
      // CDP can fail before we obtain a browser object. Cleanup is restricted
      // to the process tree we spawned from this disposable installation.
      // Preserve the failure; forced cleanup never makes the gate pass.
      if (child.exitCode === null) {
        execFileSync("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], {
          windowsHide: true,
          stdio: "ignore",
        });
        await until(async () => child.exitCode !== null, 10000);
      }
      throw error;
    }
  }
  await pause(1200);
}
try {
  // Independent protected session marker: wrong origin, never used or sent.
  execFileSync(
    path.resolve(".venv-api/Scripts/python.exe"),
    [
      "-c",
      "import json,sys;from pathlib import Path;from app.launcher.secrets import protect;Path(sys.argv[1]).write_bytes(protect(json.dumps({'origin':'https://acceptance.invalid','tokens':{},'principal':{}}).encode()))",
      path.join(profile, "session.dpapi"),
    ],
    { windowsHide: true },
  );
  const save = path.join(out, "save", "main");
  fs.mkdirSync(path.dirname(save), { recursive: true });
  fs.copyFileSync(fixture, save);
  fs.writeFileSync(
    path.join(profile, "config.json"),
    JSON.stringify({
      schema_version: 1,
      selected_save: save,
      folders: [],
      backend_url: null,
      auto_sync: false,
      cloud_sync: false,
      poll_seconds: 5,
      debounce_seconds: 1,
    }),
  );
  fs.mkdirSync(path.join(profile, "backups"));
  fs.writeFileSync(
    path.join(profile, "backups/marker.bin"),
    crypto.randomBytes(1024),
  );
  const markers = [
    save,
    path.join(profile, "session.dpapi"),
    path.join(profile, "backups/marker.bin"),
  ];
  const before = markers.map(hash);
  execFileSync(setup(a), ["/S", `/D=${install}`], { env, windowsHide: true });
  await until(async () => fs.existsSync(exe) && version() === va, 120000);
  assert.equal(registrations().length, 1);
  pass(`clean NSIS per-user install of ${va} under disposable identity`);
  await start(9465);
  assert.equal(
    (await shell.evaluate(() => window.launcher.state())).selected_save,
    save,
  );
  await shell.evaluate(() =>
    localStorage.setItem("delivery-release-marker", "preserved"),
  );
  pass(
    `installed ${va} starts with selected synthetic save and isolated encrypted session marker`,
  );
  const updaterFile = path.join(out, "shipped-updater.cjs");
  fs.writeFileSync(
    updaterFile,
    asar.extractFile(path.join(install, "resources/app.asar"), "updater.cjs"),
  );
  const updater = require(updaterFile);
  await stop();
  const newBytes = fs.readFileSync(setup(b));
  const feedFile = path.join(out, "private.json");
  sign({
    installer: setup(b),
    version: vb,
    channel: "private",
    minimum: va,
    notes: "Ensayo aislado",
    url: "http://127.0.0.1:8766/b.exe",
    keyFile: key,
    out: feedFile,
    authenticode: "NotSigned",
  });
  const feed = JSON.parse(fs.readFileSync(feedFile));
  server = http.createServer((req, res) => {
    if (req.url === "/private.json")
      return res
        .writeHead(200, { "content-type": "application/json" })
        .end(JSON.stringify(feed));
    if (req.url === "/b.exe")
      return res
        .writeHead(200, { "content-length": newBytes.length })
        .end(newBytes);
    return res.writeHead(404).end();
  });
  await new Promise((resolve) => server.listen(8766, "127.0.0.1", resolve));
  const oldPackage = JSON.parse(
    asar
      .extractFile(path.join(install, "resources/app.asar"), "package.json")
      .toString(),
  );
  const manifest = updater.verifyManifest(
    await (await fetch("http://127.0.0.1:8766/private.json")).json(),
    oldPackage.pokeappUpdate.publicKey,
    { channel: "private", currentVersion: va, allowLoopback: true },
  );
  const updates = path.join(profile, "updates");
  await updater.download(fetch, manifest, updates);
  const verified = updater.verifiedInstaller(updates);
  assert(verified);
  pass(
    `shipped ${va} updater verifies Ed25519 offer, downloads and rechecks installer SHA-512`,
  );
  execFileSync(verified.file, ["/S"], { env, windowsHide: true });
  await until(async () => version() === vb, 120000);
  assert.equal(registrations().length, 1);
  pass(`real NSIS ${vb} update replaces ${va} in same per-user install`);
  assert.deepEqual(markers.map(hash), before);
  pass(
    "installer preserves encrypted session marker, chosen save and backup bytes",
  );
  await start(9466);
  const state = await shell.evaluate(() => window.launcher.state());
  assert.equal(state.selected_save, save);
  assert.equal(state.observation.game, "X");
  assert.equal(
    await shell.evaluate(() => localStorage.getItem("delivery-release-marker")),
    "preserved",
  );
  assert(!fs.existsSync(path.join(updates, "pending.json")));
  pass(
    "updated package restarts, retains selection and Electron data, reconciles pending update",
  );
  await stop();
  assert.deepEqual(markers.map(hash), before);
  pass("session marker, save and backup still intact after updated runtime");
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.error = String(error?.stack || error);
  console.error(report.error);
} finally {
  try {
    await stop().catch((error) => {
      report.status = "FAIL";
      report.stop_error = String(error?.stack || error);
    });
    server?.close();
    const uninstaller = path.join(install, `Uninstall ${product}.exe`);
    if (fs.existsSync(uninstaller)) {
      const rows = registrations();
      assert.equal(rows.length, 1);
      assert(
        rows[0].UninstallString.startsWith('"' + uninstaller + '"'),
        "only uninstall this run's registered target",
      );
      execFileSync(uninstaller, ["/S", "/currentuser", `_?=${install}`], {
        env,
        windowsHide: true,
      });
      await until(
        async () => !fs.existsSync(exe) && registrations().length === 0,
        120000,
      );
      pass(
        "disposable installation uninstalled; no UpdateTest registration remains",
      );
    }
  } catch (error) {
    report.status = "FAIL";
    report.cleanup_error = String(error?.stack || error);
    console.error(report.cleanup_error);
  }
  fs.writeFileSync(
    path.join(out, "installed-update.json"),
    JSON.stringify(report, null, 2),
  );
  console.log(`${report.status} ${report.checks.length} checks`);
}
process.exitCode = report.status === "PASS" ? 0 : 1;
