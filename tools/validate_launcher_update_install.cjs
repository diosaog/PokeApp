// Real installed-update check for two DISPOSABLE private installers (Windows).
// Drives the shipped updater module exactly like main.cjs does after the user
// confirms; the in-app button/dialog path is covered by the UI smoke test.
// Never touches the user's real profiles, publishes nothing, and uninstalls.
const { spawnSync, spawn, execFileSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const https = require("node:https");
const path = require("node:path");
const updater = require("../companion/launcher/updater.cjs");

const [work, oldSetup, newSetup, oldVersion, newVersion] =
  process.argv.slice(2);
const keys = path.join(work, "keys");
const install = path.join(work, "install");
const profile = path.join(work, "profile");
const updates = path.join(profile, "updates");
const exeName = "PokeApp Launcher Private.exe";
const checks = [];
const pass = (label) => (checks.push(label), console.log("PASS " + label));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// Owner's real profiles (private candidate and public Launcher) must not change.
const realProfiles = ["Launcher-Private", "Launcher"].map((p) =>
  path.join(process.env.LOCALAPPDATA, "PokeApp", p),
);

function listing(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { recursive: true })
    .sort()
    .map((f) => {
      const s = fs.statSync(path.join(dir, f));
      return [f, s.size, s.mtimeMs];
    });
}
function digest(dir) {
  return fs
    .readdirSync(dir, { recursive: true })
    .filter((f) => fs.statSync(path.join(dir, f)).isFile())
    .sort()
    .map((f) => [
      f,
      crypto
        .createHash("sha256")
        .update(fs.readFileSync(path.join(dir, f)))
        .digest("hex"),
    ]);
}
function version() {
  const exe = path.join(install, exeName);
  if (!fs.existsSync(exe)) return null;
  // NSIS records the exact semantic version for the per-user install entry.
  return (
    execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        "Get-ChildItem 'HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall' | Get-ItemProperty | Where-Object DisplayName -like 'PokeApp Launcher Private*' | Select-Object -ExpandProperty DisplayVersion",
      ],
      { encoding: "utf8" },
    ).trim() || null
  );
}
function manifest(
  version,
  setup,
  key = path.join(keys, "pokeapp-update-private.pem"),
) {
  const data = fs.readFileSync(setup);
  const body = Buffer.from(
    JSON.stringify({
      channel: "private",
      version,
      minimum_version: "0.22.0-rc.1",
      notes: "Prueba privada desechable",
      installer: {
        url: "https://127.0.0.1:8443/setup.exe",
        sha512: crypto.createHash("sha512").update(data).digest("base64"),
        size: data.length,
      },
      released_at: new Date().toISOString(),
    }),
  );
  return {
    manifest: body.toString("base64"),
    signature: crypto
      .sign(null, body, crypto.createPrivateKey(fs.readFileSync(key)))
      .toString("base64"),
  };
}

(async () => {
  const realBefore = JSON.stringify(realProfiles.map(listing));
  let served = { feed: null, setup: null };
  const server = https.createServer(
    {
      key: fs.readFileSync(path.join(work, "tls-key.pem")),
      cert: fs.readFileSync(path.join(work, "tls-cert.pem")),
    },
    (req, res) => {
      const body =
        req.url === "/private.json"
          ? JSON.stringify(served.feed)
          : req.url === "/setup.exe"
            ? served.setup
            : null;
      if (!body) return res.writeHead(404).end();
      res.writeHead(200).end(body);
    },
  );
  await new Promise((r) => server.listen(8443, "127.0.0.1", r));
  const publicKey = fs.readFileSync(
    path.join(keys, "pokeapp-update-public.pem"),
    "utf8",
  );
  const offered = async () =>
    updater.verifyManifest(
      await (await fetch("https://127.0.0.1:8443/private.json")).json(),
      publicKey,
      { channel: "private", currentVersion: oldVersion },
    );
  try {
    const r = spawnSync(
      oldSetup,
      ["/S", "/D=" + install.replace(/\//g, "\\")],
      { stdio: "ignore" },
    );
    if (r.status !== 0 || version() !== oldVersion)
      throw new Error("old install failed " + r.status + " " + version());
    pass(`installed ${oldVersion} per-user into a disposable folder`);

    fs.mkdirSync(path.join(profile, "writes", "write-backups"), {
      recursive: true,
    });
    fs.writeFileSync(
      path.join(profile, "writes", "physical-writes.sqlite3"),
      crypto.randomBytes(8192),
    );
    fs.writeFileSync(
      path.join(profile, "writes", "write-backups", "original.bin"),
      crypto.randomBytes(4096),
    );
    fs.writeFileSync(
      path.join(profile, "launcher.json"),
      JSON.stringify({ selected_save: null }),
    );
    const seeded =
      JSON.stringify(digest(path.join(profile, "writes"))) +
      fs.readFileSync(path.join(profile, "launcher.json"), "utf8");

    const tampered = Buffer.from(fs.readFileSync(newSetup));
    tampered[4096] ^= 1;
    served = { feed: manifest(newVersion, newSetup), setup: tampered };
    await updater.download(fetch, await offered(), updates).then(
      () => {
        throw new Error("tampered admitted");
      },
      (e) => {
        if (e.code !== "INTEGRITY_FAILED") throw e;
      },
    );
    if (fs.readdirSync(updates).length) throw new Error("tampered leftovers");
    served = {
      feed: manifest("0.22.0-rc.89", oldSetup),
      setup: fs.readFileSync(oldSetup),
    };
    await offered().then(
      () => {
        throw new Error("downgrade admitted");
      },
      (e) => {
        if (e.code !== "DOWNGRADE_REJECTED") throw e;
      },
    );
    const foreign = path.join(work, "foreign.pem");
    fs.writeFileSync(
      foreign,
      crypto
        .generateKeyPairSync("ed25519")
        .privateKey.export({ type: "pkcs8", format: "pem" }),
    );
    served = {
      feed: manifest(newVersion, newSetup, foreign),
      setup: fs.readFileSync(newSetup),
    };
    await offered().then(
      () => {
        throw new Error("foreign key admitted");
      },
      (e) => {
        if (e.code !== "SIGNATURE_INVALID") throw e;
      },
    );
    if (version() !== oldVersion)
      throw new Error("installed version changed by a rejected update");
    pass(
      "over real HTTPS: tampered installer, downgrade and foreign-key manifest rejected; nothing installed",
    );

    served = {
      feed: manifest(newVersion, newSetup),
      setup: fs.readFileSync(newSetup),
    };
    await updater.download(fetch, await offered(), updates);
    const installer = updater.verifiedInstaller(updates);
    const env = {
      ...process.env,
      POKEAPP_LAUNCHER_PROFILE: profile,
      POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
    };
    delete env.ELECTRON_RUN_AS_NODE;
    // main.cjs adds --force-run; NSIS then relaunches through the shell WITHOUT
    // this process's environment, i.e. on the user's real profile. The test
    // installs silently and starts the installed app itself on the disposable one.
    const code = spawnSync(installer.file, ["/S"], { stdio: "ignore" }).status;
    if (code !== 0 || version() !== newVersion)
      throw new Error("upgrade failed " + code + " " + version());
    pass(
      `signed ${newVersion} downloaded, re-hashed and installed over ${oldVersion} (same per-user install)`,
    );
    spawn(path.join(install, exeName), [], {
      env,
      detached: true,
      stdio: "ignore",
    }).unref();

    let relaunched = false;
    for (let i = 0; i < 60 && !relaunched; i++) {
      await sleep(1000);
      relaunched = !fs.existsSync(path.join(updates, "pending.json"));
    }
    if (!relaunched)
      throw new Error("relaunched app did not reconcile pending update");
    const running = execFileSync(
      "tasklist",
      ["/FI", `IMAGENAME eq ${exeName}`],
      { encoding: "utf8" },
    ).includes("PokeApp Launcher");
    pass(
      `installed ${newVersion} restarted${running ? " (process running)" : ""} on the disposable profile and reconciled/removed the pending update`,
    );
    spawnSync("taskkill", ["/F", "/T", "/IM", exeName], { stdio: "ignore" });
    await sleep(3000);
    const after =
      JSON.stringify(digest(path.join(profile, "writes"))) +
      fs.readFileSync(path.join(profile, "launcher.json"), "utf8");
    if (after !== seeded) throw new Error("profile journal/backups changed");
    pass(
      "journal, backups and configuration byte-identical after update and restart",
    );

    const uninstaller = path.join(
      install,
      "Uninstall PokeApp Launcher Private.exe",
    );
    spawnSync(uninstaller, ["/S", "_?=" + install.replace(/\//g, "\\")], {
      stdio: "ignore",
    });
    for (let i = 0; i < 30 && fs.existsSync(path.join(install, exeName)); i++)
      await sleep(1000);
    if (fs.existsSync(path.join(install, exeName)))
      throw new Error("uninstall left the app");
    const kept =
      JSON.stringify(digest(path.join(profile, "writes"))) +
      fs.readFileSync(path.join(profile, "launcher.json"), "utf8");
    if (kept !== seeded) throw new Error("uninstall changed profile data");
    pass("silent uninstall removed the app and kept profile journal/backups");
    if (JSON.stringify(realProfiles.map(listing)) !== realBefore)
      throw new Error("real profile touched");
    pass(
      "owner's real private and public Launcher profiles untouched during this run",
    );
    fs.writeFileSync(
      path.join(work, "result.json"),
      JSON.stringify(
        { status: "PASS", checks, oldVersion, newVersion },
        null,
        2,
      ),
    );
  } finally {
    server.close();
  }
})().catch((error) => {
  console.error("FAIL " + error.message);
  spawnSync("taskkill", ["/F", "/T", "/IM", exeName], { stdio: "ignore" });
  process.exit(1);
});
