// Real public-channel check of the stable Launcher, in an isolated profile.
//
// Uses the PUBLIC installers and the HOSTED stable feed — the definitive
// mechanism and configuration — but never the owner's data: LOCALAPPDATA and
// APPDATA point into the output folder for every process (the Launcher keeps
// its profile, Electron data and core state under LOCALAPPDATA; the core finds
// saves under APPDATA), and the app is installed into that folder. Only one
// synthetic save exists there. It refuses to run if the stable Launcher is
// installed for this Windows user.
//
//   transition: install 0.25.0, let it set up its profile, install the bridge
//               over it by hand, prove everything kept, then the bridge reads
//               the hosted feed («última versión»).
//   update:     with a higher version published, the installed bridge finds
//               it, «Actualizar» downloads, verifies, installs, restarts as the
//               new version; everything kept; then the sandbox is removed.
//
//   node tools/validate_launcher_public_update.mjs transition --legacy <0.25.0 setup> --bridge <setup> --va <v> --out <dir>
//   node tools/validate_launcher_public_update.mjs update --vb <v> --out <dir>
import { spawn, execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";

const require = createRequire(import.meta.url);
const asar = require("../companion/launcher/node_modules/@electron/asar");
const [phase, ...rest] = process.argv.slice(2);
const args = Object.fromEntries(
  rest.reduce(
    (p, v, i, all) =>
      v.startsWith("--") ? [...p, [v.slice(2), all[i + 1]]] : p,
    [],
  ),
);
const out = path.resolve(args.out);
const sandbox = path.join(out, "sandbox");
const install = path.join(sandbox, "install");
const exe = path.join(install, "PokeApp Launcher.exe");
const local = path.join(sandbox, "localappdata");
const roaming = path.join(sandbox, "appdata");
const profile = path.join(local, "PokeApp", "Launcher");
const stateFile = path.join(out, "public-update-state.json");
const reportFile = path.join(out, `public-update-${phase}.json`);
const env = { ...process.env, LOCALAPPDATA: local, APPDATA: roaming };
for (const name of [
  "ELECTRON_RUN_AS_NODE",
  "POKEAPP_LAUNCHER_PROFILE",
  "POKEAPP_WEB_ORIGIN",
])
  delete env[name];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const sha = (file) =>
  crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const report = { phase, checks: [], status: "RUNNING" };
const check = (pass, label) => {
  report.checks.push({ pass: Boolean(pass), label });
  console.log(pass ? "PASS" : "FAIL", label);
  if (!pass) throw new Error("FAIL " + label);
};
async function until(fn, ms = 30000, step = 250) {
  const end = Date.now() + ms;
  for (;;) {
    try {
      const v = await fn();
      if (v) return v;
    } catch {}
    if (Date.now() > end) throw new Error("timed out");
    await sleep(step);
  }
}
const ps = (command) =>
  execFileSync(
    "powershell.exe",
    ["-NoProfile", "-NonInteractive", "-Command", command],
    { encoding: "utf8" },
  ).trim();
const running = () =>
  ps(`Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith('${install.replace(/'/g, "''")}', 'OrdinalIgnoreCase') } | ForEach-Object { $_.ProcessId }`)
    .split(/\s+/).filter(Boolean).map(Number); // prettier-ignore
const kill = () => {
  for (const pid of running())
    try {
      execFileSync("taskkill", ["/PID", String(pid), "/T", "/F"], {
        stdio: "ignore",
      });
    } catch {}
};
const uninstallEntries = () =>
  // The installer registers "PokeApp Launcher <version>"; the UpdateTest and
  // Private variants have their own names and never count.
  Number(
    ps(
      "@(Get-ChildItem 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall' | Where-Object { (Get-ItemProperty $_.PSPath).DisplayName -match '^PokeApp Launcher( [0-9].*)?$' }).Count",
    ),
  );
// @electron/asar caches an archive's header by path: after an install replaces
// app.asar, a cached header would read the new file at the old offsets.
const installedVersion = () => {
  asar.uncacheAll();
  return JSON.parse(
    asar
      .extractFile(path.join(install, "resources", "app.asar"), "package.json")
      .toString("utf8"),
  ).version;
};
// NSIS relaunches installers and uninstallers from a temporary copy.
const nsisBusy = () =>
  ps(
    "@(Get-Process | Where-Object { $_.ProcessName -match '^(Un|Au)_[A-Z]$' }).Count",
  ) !== "0";
// Everything that must survive, by content.
function snapshot(saveFile) {
  const files = {};
  for (const name of [
    "config.json",
    "known-saves.json",
    "session.dpapi",
    path.join("backups", "phase32-marker.bin"),
  ]) {
    const file = path.join(profile, name);
    files[name] = fs.existsSync(file) ? sha(file) : null;
  }
  return { files, save: sha(saveFile) };
}
let browser = null,
  tools = null;
async function start(port) {
  spawn(exe, [`--remote-debugging-port=${port}`], {
    env,
    stdio: "ignore",
    detached: false,
  });
  browser = await until(
    () => chromium.connectOverCDP(`http://127.0.0.1:${port}`),
    60000,
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
async function stop() {
  await browser?.close().catch(() => {});
  browser = null;
  kill();
  await until(async () => running().length === 0, 30000, 500);
}
const updateState = () => tools.evaluate(() => window.launcher.updateState());
const settled = () =>
  until(async () => {
    const u = await updateState();
    return !["CHECKING", "IDLE"].includes(u.status) && u;
  }, 60000);

try {
  if (phase === "transition") {
    if (uninstallEntries() !== 0)
      throw new Error(
        "a PokeApp Launcher is installed for this user: refusing to touch it",
      );
    if (fs.existsSync(sandbox)) throw new Error("sandbox already exists");
    const saveDir = path.join(roaming, "Lime3DS", "sdmc", "Nintendo 3DS", "0".repeat(32), "0".repeat(32),
      "title", "00040000", "00055e00", "data", "00000001"); // prettier-ignore
    fs.mkdirSync(saveDir, { recursive: true });
    const saveFile = path.join(saveDir, "main");
    fs.writeFileSync(saveFile, Buffer.alloc(4096, 9));
    fs.mkdirSync(path.join(profile, "backups"), { recursive: true });
    // The player had chosen this save in 0.25.0 (its own config format).
    fs.writeFileSync(path.join(profile, "config.json"), JSON.stringify({ schema_version: 1,
      selected_save: saveFile, folders: [], backend_url: null, auto_sync: false, cloud_sync: false,
      poll_seconds: 5.0, debounce_seconds: 1.0 }, null, 2)); // prettier-ignore
    fs.writeFileSync(
      path.join(profile, "backups", "phase32-marker.bin"),
      crypto.randomBytes(512),
    );
    // A DPAPI session bound to another origin: kept, never used or sent.
    execFileSync(path.resolve(".venv-api/Scripts/python.exe"), ["-c",
      "import json,sys;from pathlib import Path;from app.launcher.secrets import protect;Path(sys.argv[1]).write_bytes(protect(json.dumps({'origin':'https://acceptance.invalid','tokens':{},'principal':{}}).encode()))",
      path.join(profile, "session.dpapi")]); // prettier-ignore

    execFileSync(args.legacy, ["/S", `/D=${install}`], { env });
    await until(async () => !nsisBusy() && fs.existsSync(exe), 120000, 1000);
    check(
      fs.existsSync(exe) && installedVersion() === "0.25.0",
      "public 0.25.0 installed in the sandbox",
    );
    spawn(exe, [], { env, stdio: "ignore" });
    await until(
      () =>
        fs.existsSync(path.join(profile, "launcher.lock")) ||
        fs.existsSync(path.join(profile, "shell")),
      120000,
      1000,
    );
    await sleep(20000); // let it read the selection and settle its profile
    kill();
    await until(async () => running().length === 0, 30000, 500);
    const before = snapshot(saveFile);
    check(before.files["config.json"] && before.files["session.dpapi"] && fs.existsSync(path.join(profile, "shell")),
      "0.25.0 ran on its profile: selected save, encrypted session, backups"); // prettier-ignore

    const t0 = Date.now();
    execFileSync(args.bridge, ["/S"], { env });
    // The installer removes 0.25.0 with its own uninstaller, then extracts.
    await until(async () => {
      const v = (() => { try { return installedVersion(); } catch { return "-"; } })();
      if ((Date.now() - t0) % 15000 < 1000) console.log(`  installing… ${Math.round((Date.now() - t0) / 1000)}s version ${v} entries ${uninstallEntries()}`);
      return v === args.va;
    }, 300000, 1000); // prettier-ignore
    kill(); // a silent install may start the app
    await until(async () => running().length === 0, 30000, 500);
    check(
      installedVersion() === args.va && fs.existsSync(exe),
      `the ${args.va} installer replaced 0.25.0 in the same folder`,
    );
    check(
      uninstallEntries() === 1,
      "one installed PokeApp Launcher (no side-by-side copy)",
    );
    const after = snapshot(saveFile);
    check(
      JSON.stringify(after.files) === JSON.stringify(before.files),
      "the installer kept the profile byte for byte: configuration, known saves, encrypted session, backups",
    );
    check(
      after.save === before.save,
      "the game save is untouched by the transition",
    );

    await start(9451);
    const selected = (await tools.evaluate(() => window.launcher.state()))
      .selected_save;
    check(
      selected && path.resolve(selected) === path.resolve(saveFile),
      `${args.va} keeps the save chosen in 0.25.0`,
    );
    const u = await settled();
    check(
      u.status === "UP_TO_DATE" && u.current === args.va,
      `${args.va} reads the hosted stable feed: «Estás utilizando la última versión»`,
    );
    await tools.evaluate(() =>
      localStorage.setItem("phase32-marker", "kept-across-update"),
    );
    await tools
      .screenshot({ path: path.join(out, "bridge-up-to-date.png") })
      .catch(() => {});
    await stop();
    // The baseline for the update is the bridge's own profile.
    fs.writeFileSync(
      stateFile,
      JSON.stringify(
        { va: args.va, saveFile, selected, snapshot: snapshot(saveFile) },
        null,
        2,
      ),
    );
  } else if (phase === "update") {
    // After an update NSIS relaunches the app through Explorer, with the
    // user's real environment: the restarted Launcher opens the REAL profile.
    // Right for a player, wrong for an isolated test (found 2026-10-28, when
    // it briefly opened the owner's profile). Only on a machine without one.
    const realProfile = path.join(
      process.env.LOCALAPPDATA,
      "PokeApp",
      "Launcher",
    );
    if (fs.existsSync(realProfile))
      throw new Error(
        "a real Launcher profile exists on this machine: the post-update relaunch would use it; run this phase on a clean Windows user",
      );
    const state = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    await start(9452);
    let u = await settled();
    if (u.status === "UP_TO_DATE")
      u = await tools.evaluate(() => window.launcher.checkUpdate());
    check(
      ["AVAILABLE", "READY"].includes(u.status) && u.version === args.vb,
      `${state.va} finds ${args.vb} on the hosted stable feed`,
    );
    await tools
      .screenshot({ path: path.join(out, "update-available.png") })
      .catch(() => {});
    await tools.evaluate(() => present("update", { check: false }));
    await until(() =>
      tools.evaluate(
        () =>
          document.querySelector("#update-dialog").open &&
          !document.querySelector("#update-go").hidden,
      ),
    );
    await sleep(300);
    await tools.evaluate(() => document.querySelector("#update-go").click());
    const seen = new Set();
    await until(
      async () => {
        try {
          const s = await updateState();
          seen.add(s.status);
          return s.status === "INSTALLING";
        } catch {
          return true; // the Launcher closed for the installer
        }
      },
      600000,
      200,
    );
    check(
      true,
      "download verified (Ed25519 manifest, SHA-512 installer) and installation started: " +
        [...seen].join(" → "),
    );
    await browser.close().catch(() => {});
    browser = null;
    await until(
      async () => installedVersion() === args.vb && running().length > 0,
      300000,
      1000,
    );
    check(true, `silent install done; ${args.vb} restarted by itself`);
    const updates = path.join(profile, "updates");
    await until(
      async () =>
        !fs.existsSync(updates) ||
        !fs.readdirSync(updates).some((f) => f.endsWith(".exe")),
      120000,
      1000,
    );
    check(true, "the restarted version cleared the downloaded installer");
    kill();
    await until(async () => running().length === 0, 30000, 500);
    await start(9453);
    u = await settled();
    check(
      u.status === "UP_TO_DATE" && u.current === args.vb,
      `running ${args.vb}; the hosted feed is now «última versión»`,
    );
    const now = snapshot(state.saveFile);
    check(now.files["session.dpapi"] === state.snapshot.files["session.dpapi"] &&
      execFileSync(path.resolve(".venv-api/Scripts/python.exe"), ["-c",
        "import json,sys;from pathlib import Path;from app.launcher.secrets import protect;print(json.loads(protect(Path(sys.argv[1]).read_bytes(),decrypt=True))['origin'])",
        path.join(profile, "session.dpapi")], { encoding: "utf8" }).trim() === "https://acceptance.invalid",
      "encrypted session kept and still decryptable"); // prettier-ignore
    check(
      (await tools.evaluate(() => window.launcher.state())).selected_save ===
        state.selected,
      "selected save kept",
    );
    check(now.files["config.json"] === state.snapshot.files["config.json"] &&
      now.files["known-saves.json"] === state.snapshot.files["known-saves.json"] &&
      now.files[path.join("backups", "phase32-marker.bin")] === state.snapshot.files[path.join("backups", "phase32-marker.bin")],
      "configuration, known saves and backups kept byte for byte"); // prettier-ignore
    check(
      now.save === state.snapshot.save,
      "the game save is untouched by the update",
    );
    check(
      (await tools.evaluate(() => localStorage.getItem("phase32-marker"))) ===
        "kept-across-update",
      "Launcher app data (Electron profile) kept",
    );
    await stop();
  } else throw new Error("phase must be transition or update");
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.error = String(error?.stack || error).slice(0, 1500);
  console.error(report.error);
} finally {
  await browser?.close().catch(() => {});
  if (phase === "update" || report.status === "FAIL") {
    kill();
    const uninstaller = path.join(install, "Uninstall PokeApp Launcher.exe");
    if (fs.existsSync(uninstaller)) {
      try {
        execFileSync(uninstaller, ["/currentuser", "/S"], { env });
      } catch {}
      for (let i = 0; i < 120 && (fs.existsSync(exe) || nsisBusy()); i++)
        await sleep(1000);
      await sleep(3000);
    }
    report.cleanup = { uninstall_entries_left: uninstallEntries() };
    fs.rmSync(sandbox, {
      recursive: true,
      force: true,
      maxRetries: 20,
      retryDelay: 500,
    });
    report.cleanup.sandbox_removed = !fs.existsSync(sandbox);
  }
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(reportFile, JSON.stringify(report, null, 2) + "\n");
  console.log(
    `${report.status} ${report.checks.filter((c) => c.pass).length}/${report.checks.length}`,
  );
  process.exit(report.status === "PASS" ? 0 : 1);
}
