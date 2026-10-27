const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const u = require("./updater.cjs");

// Two disposable private versions: running 0.22.0-rc.3, offered 0.23.0.
const keys = crypto.generateKeyPairSync("ed25519");
const other = crypto.generateKeyPairSync("ed25519");
const PUBLIC = keys.publicKey.export({ type: "spki", format: "pem" });
const INSTALLER = crypto.randomBytes(4096);
const CURRENT = "0.22.0-rc.3";

function manifest(fields = {}) {
  return {
    channel: "private",
    version: "0.23.0",
    minimum_version: "0.22.0-rc.1",
    notes: "Objetos rápidos y robos conectados.",
    released_at: "2026-10-25T00:00:00Z",
    installer: {
      url: "https://updates.invalid/PokeApp-Launcher-Private-Setup.exe",
      sha512: crypto.createHash("sha512").update(INSTALLER).digest("base64"),
      size: INSTALLER.length,
    },
    ...fields,
  };
}
function envelope(value, key = keys.privateKey) {
  const bytes = Buffer.from(JSON.stringify(value));
  return {
    manifest: bytes.toString("base64"),
    signature: crypto.sign(null, bytes, key).toString("base64"),
  };
}
const verify = (env, extra = {}) =>
  u.verifyManifest(env, PUBLIC, {
    channel: "private",
    currentVersion: CURRENT,
    ...extra,
  });
const code = (fn) => {
  try {
    fn();
  } catch (error) {
    return error.code;
  }
  return "OK";
};
const fetchOf =
  (chunks, { ok = true, fail = false } = {}) =>
  async () => ({
    ok,
    body: (async function* () {
      for (const c of chunks) yield c;
      if (fail) throw new Error("socket closed");
    })(),
  });
const temp = () => fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-update-"));

test("detects a newer signed version and reports none when current", () => {
  assert.equal(verify(envelope(manifest())).version, "0.23.0");
  assert.equal(verify(envelope(manifest({ version: CURRENT }))), null);
  assert.equal(u.compareVersions("0.22.0", "0.22.0-rc.3"), 1);
  assert.equal(u.compareVersions("0.22.0-rc.10", "0.22.0-rc.9"), 1);
});

test("rejects missing, invalid or foreign signatures and tampered manifests", () => {
  const good = envelope(manifest());
  assert.equal(
    code(() => verify({ manifest: good.manifest })),
    "SIGNATURE_MISSING",
  );
  assert.equal(
    code(() =>
      verify({ ...good, signature: Buffer.alloc(64).toString("base64") }),
    ),
    "SIGNATURE_INVALID",
  );
  assert.equal(
    code(() => verify(envelope(manifest(), other.privateKey))),
    "SIGNATURE_INVALID",
  );
  const tampered = Buffer.from(
    JSON.stringify(manifest({ notes: "otra" })),
  ).toString("base64");
  assert.equal(
    code(() => verify({ ...good, manifest: tampered })),
    "SIGNATURE_INVALID",
  );
  assert.equal(
    code(() =>
      u.verifyManifest(good, null, {
        channel: "private",
        currentVersion: CURRENT,
      }),
    ),
    "UPDATES_NOT_CONFIGURED",
  );
});

test("separates channels, refuses downgrade, insecure URL and incompatible jumps", () => {
  assert.equal(
    code(() => verify(envelope(manifest()), { channel: "stable" })),
    "CHANNEL_MISMATCH",
  );
  assert.equal(
    code(() => verify(envelope(manifest({ channel: "stable" })))),
    "CHANNEL_MISMATCH",
  );
  assert.equal(
    code(() => verify(envelope(manifest({ version: "0.21.9" })))),
    "DOWNGRADE_REJECTED",
  );
  const insecure = manifest();
  insecure.installer = {
    ...insecure.installer,
    url: "http://updates.invalid/setup.exe",
  };
  assert.equal(
    code(() => verify(envelope(insecure))),
    "INSECURE_URL",
  );
  assert.equal(
    code(() => verify(envelope(manifest({ minimum_version: "0.22.1" })))),
    "INCOMPATIBLE_VERSION",
  );
  assert.equal(
    code(() => verify(envelope({ ...manifest(), extra: 1 }))),
    "MANIFEST_INVALID",
  );
});

test("interrupted or manipulated downloads leave nothing installable", async () => {
  const m = manifest();
  const dir = temp();
  await assert.rejects(
    u.download(fetchOf([INSTALLER.subarray(0, 100)], { fail: true }), m, dir),
    { code: "DOWNLOAD_INTERRUPTED" },
  );
  await assert.rejects(
    u.download(fetchOf([INSTALLER.subarray(0, 100)]), m, dir),
    { code: "DOWNLOAD_INTERRUPTED" },
  );
  const bad = Buffer.from(INSTALLER);
  bad[7] ^= 1;
  await assert.rejects(u.download(fetchOf([bad]), m, dir), {
    code: "INTEGRITY_FAILED",
  });
  await assert.rejects(
    u.download(fetchOf([INSTALLER, Buffer.from("x")]), m, dir),
    { code: "INTEGRITY_FAILED" },
  );
  await assert.rejects(u.download(fetchOf([], { ok: false }), m, dir), {
    code: "DOWNLOAD_FAILED",
  });
  assert.deepEqual(fs.readdirSync(dir), []);
  assert.equal(
    code(() => u.verifiedInstaller(dir)),
    "NOTHING_TO_INSTALL",
  );
});

test("verified download is re-hashed before launch; tampering after download is caught", async () => {
  const dir = temp();
  const file = await u.download(
    fetchOf([INSTALLER.subarray(0, 1000), INSTALLER.subarray(1000)]),
    manifest(),
    dir,
  );
  assert.equal(u.verifiedInstaller(dir).file, file);
  fs.appendFileSync(file, "x");
  assert.equal(
    code(() => u.verifiedInstaller(dir)),
    "INTEGRITY_FAILED",
  );
  assert.deepEqual(fs.readdirSync(dir), []);
});

test("installation is deferred while any physical, journal, transfer or sync work is active", () => {
  const idle = {
    write: { status: "IDLE", busy: false, restart_blocked_by_recovery: false },
    cloud_status: "ONLINE",
    cloud: { data: { transfers: [{ status: "COMMITTED" }] } },
  };
  assert.equal(u.installBlocker(idle), null);
  assert.equal(u.installBlocker(null), "STATE_UNAVAILABLE");
  assert.equal(
    u.installBlocker({ ...idle, write: { ...idle.write, busy: true } }),
    "WRITE_IN_PROGRESS",
  );
  assert.equal(
    u.installBlocker({
      ...idle,
      write: { ...idle.write, status: "AWAITING_CONFIRMATION" },
    }),
    "WRITE_PENDING",
  );
  assert.equal(
    u.installBlocker({
      ...idle,
      write: { ...idle.write, restart_blocked_by_recovery: true },
    }),
    "RECOVERY_PENDING",
  );
  assert.equal(
    u.installBlocker({ ...idle, cloud_status: "SYNCING" }),
    "SYNC_IN_PROGRESS",
  );
  assert.equal(
    u.installBlocker({
      ...idle,
      cloud: { data: { transfers: [{ status: "VERIFYING_SOURCE" }] } },
    }),
    "TRANSFER_IN_PROGRESS",
  );
});

test("restart reconciliation: incomplete install keeps the verified file, success cleans up", async () => {
  const dir = temp();
  await u.download(fetchOf([INSTALLER]), manifest(), dir);
  assert.deepEqual(u.reconcileStartup(dir, CURRENT), {
    status: "INSTALL_INCOMPLETE",
    version: "0.23.0",
  });
  assert.equal(u.verifiedInstaller(dir).version, "0.23.0");
  assert.deepEqual(u.reconcileStartup(dir, "0.23.0"), {
    status: "INSTALLED",
    version: "0.23.0",
  });
  assert.deepEqual(fs.readdirSync(dir), []);
  assert.deepEqual(u.reconcileStartup(dir, "0.23.0"), { status: "IDLE" });
});

test("loopback rehearsal feeds only where the build allows them", () => {
  const local = manifest({
    installer: {
      ...manifest().installer,
      url: "http://127.0.0.1:8766/PokeApp-Launcher-Private-Setup.exe",
    },
  });
  assert.equal(
    code(() => verify(envelope(local))),
    "INSECURE_URL",
  );
  assert.equal(
    verify(envelope(local), { allowLoopback: true }).version,
    "0.23.0",
  );
  for (const url of [
    "http://updates.invalid/x.exe",
    "http://user:pw@127.0.0.1/x.exe",
    "ftp://127.0.0.1/x.exe",
  ])
    assert.equal(
      code(() =>
        verify(
          envelope(manifest({ installer: { ...manifest().installer, url } })),
          { allowLoopback: true },
        ),
      ),
      "INSECURE_URL",
      url,
    );
});

test("progress is reported and a verified installer is never downloaded twice", async () => {
  const dir = temp();
  const seen = [];
  let fetches = 0;
  const fetchOnce = async (...args) => {
    fetches++;
    return fetchOf([INSTALLER.subarray(0, 1000), INSTALLER.subarray(1000)])(
      ...args,
    );
  };
  await u.download(fetchOnce, manifest(), dir, (received, total) =>
    seen.push([received, total]),
  );
  assert.deepEqual(seen, [
    [1000, INSTALLER.length],
    [INSTALLER.length, INSTALLER.length],
  ]);
  await u.download(fetchOnce, manifest(), dir);
  assert.equal(fetches, 1);
  assert.ok(u.readyInstaller(dir, manifest()));
  // Another signed file for the same version is not "ready": it downloads.
  assert.equal(
    u.readyInstaller(
      dir,
      manifest({
        installer: { ...manifest().installer, sha512: "A".repeat(86) + "==" },
      }),
    ),
    null,
  );
});

test("a newer download retires the older verified installer", async () => {
  const dir = temp();
  await u.download(fetchOf([INSTALLER]), manifest(), dir);
  const newer = Buffer.concat([INSTALLER, Buffer.from("v2")]);
  await u.download(
    fetchOf([newer]),
    manifest({
      version: "0.24.0",
      installer: {
        ...manifest().installer,
        sha512: crypto.createHash("sha512").update(newer).digest("base64"),
        size: newer.length,
      },
    }),
    dir,
  );
  assert.deepEqual(fs.readdirSync(dir).sort(), [
    "PokeApp-Launcher-0.24.0.exe",
    "pending.json",
  ]);
});

test("«Más tarde» is remembered per version and rejects junk", () => {
  const dir = temp();
  assert.equal(u.postponed(dir), null);
  u.postpone(dir, "0.23.0");
  assert.equal(u.postponed(dir), "0.23.0");
  assert.throws(() => u.postpone(dir, "../../evil"));
  fs.writeFileSync(path.join(dir, "postponed.json"), "{oops");
  assert.equal(u.postponed(dir), null);
});

test("after an update, a file still in use never stops the start and is retried", async () => {
  const dir = temp();
  await u.download(fetchOf([INSTALLER]), manifest(), dir);
  const rmSync = fs.rmSync;
  fs.rmSync = (target, options) => {
    if (String(target).endsWith(".exe")) {
      const error = new Error("EBUSY");
      error.code = "EBUSY";
      throw error;
    }
    return rmSync(target, options);
  };
  try {
    assert.deepEqual(u.reconcileStartup(dir, "0.23.0"), {
      status: "INSTALLED",
      version: "0.23.0",
      leftover: true,
    });
    // The record stays so the next attempt finishes the cleanup.
    assert.ok(fs.existsSync(path.join(dir, "pending.json")));
  } finally {
    fs.rmSync = rmSync;
  }
  assert.deepEqual(u.reconcileStartup(dir, "0.23.0"), {
    status: "INSTALLED",
    version: "0.23.0",
  });
  assert.deepEqual(fs.readdirSync(dir), []);
});
