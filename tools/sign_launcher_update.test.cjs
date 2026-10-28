const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {
  generate,
  sign,
  exportKey,
  importKey,
  UNSIGNED_POLICY,
} = require("./sign_launcher_update.cjs");
const updater = require("../companion/launcher/updater.cjs");

// Every folder holds a freshly generated private key: none outlives the run.
const made = [];
const temp = () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-sign-"));
  made.push(dir);
  return dir;
};
test.after(() => {
  for (const dir of made) fs.rmSync(dir, { recursive: true, force: true });
});
const repo = path.resolve(__dirname, "..");
const URL = "https://updates.invalid/PokeApp-Launcher-Private-Setup.exe";

function release() {
  const dir = temp();
  const keys = generate(path.join(dir, "keys"));
  const installer = path.join(dir, "setup.exe");
  fs.writeFileSync(installer, Buffer.alloc(2048, 7));
  return { dir, keys, installer };
}
const base = (r, extra = {}) => ({
  installer: r.installer,
  version: "0.22.0-rc.91",
  channel: "private",
  minimum: "0.22.0-rc.1",
  notes: "Prueba privada",
  url: URL,
  keyFile: r.keys.privateFile,
  out: path.join(r.dir, "private.json"),
  authenticode: "NotSigned",
  ...extra,
});

test("key generation stays outside the repository and never overwrites", () => {
  const dir = temp();
  generate(dir);
  assert.throws(() => generate(dir), /KEY_ALREADY_EXISTS/);
  assert.throws(
    () => generate(path.join(repo, "keys")),
    /KEY_DIRECTORY_INSIDE_REPOSITORY/,
  );
  assert.match(
    fs.readFileSync(path.join(dir, "pokeapp-update-public.pem"), "utf8"),
    /PUBLIC KEY/,
  );
});

test("signed private manifest verifies with the shipped updater and binds the installer", async () => {
  const r = release();
  const envelope = sign(base(r));
  const manifest = updater.verifyManifest(
    envelope,
    fs.readFileSync(r.keys.publicFile, "utf8"),
    {
      channel: "private",
      currentVersion: "0.22.0-rc.90",
    },
  );
  assert.equal(manifest.installer.size, 2048);
  const data = fs.readFileSync(r.installer);
  const file = await updater.download(
    async () => ({ ok: true, body: [data] }),
    manifest,
    path.join(r.dir, "dl"),
  );
  assert.equal(updater.verifiedInstaller(path.join(r.dir, "dl")).file, file);
  assert.ok(
    !fs
      .readFileSync(path.join(r.dir, "private.json"), "utf8")
      .includes("PRIVATE"),
  );
});

test("stable requires valid Authenticode; key placement and HTTPS enforced", () => {
  const r = release();
  assert.throws(
    () => sign(base(r, { channel: "stable" })),
    /STABLE_REQUIRES_VALID_AUTHENTICODE/,
  );
  assert.throws(
    () => sign(base(r, { channel: "stable", authenticode: "UnknownError" })),
    /STABLE_REQUIRES_VALID_AUTHENTICODE/,
  );
  assert.throws(
    () => sign(base(r, { url: "http://updates.invalid/x.exe" })),
    /DOWNLOAD_URL_MUST_BE_HTTPS/,
  );
  assert.throws(
    () => sign(base(r, { keyFile: path.join(repo, "x.pem") })),
    /KEY_INSIDE_REPOSITORY_OR_BUILD/,
  );
  assert.throws(
    () => sign(base(r, { buildRoot: r.dir })),
    /KEY_INSIDE_REPOSITORY_OR_BUILD/,
  );
  assert.throws(() => sign(base(r, { channel: "beta" })), /INVALID_CHANNEL/);
});

test("private distribution: an unsigned stable installer is accepted only by stated policy and recorded", () => {
  const r = release();
  const stable = (extra) =>
    base(r, {
      channel: "stable",
      url: "https://updates.invalid/s.exe",
      ...extra,
    });
  assert.throws(
    () => sign(stable({ authenticode: "NotSigned" })),
    /STABLE_REQUIRES_VALID_AUTHENTICODE/,
  );
  assert.throws(
    () => sign(stable({ authenticode: "NotSigned", unsignedPolicy: "yes" })),
    /STABLE_REQUIRES_VALID_AUTHENTICODE/,
  );
  // A broken or untrusted signature is never waved through.
  for (const authenticode of ["HashMismatch", "NotTrusted", "UnknownError"])
    assert.throws(
      () => sign(stable({ authenticode, unsignedPolicy: UNSIGNED_POLICY })),
      /STABLE_REQUIRES_VALID_AUTHENTICODE/,
    );
  const envelope = sign(
    stable({ authenticode: "NotSigned", unsignedPolicy: UNSIGNED_POLICY }),
  );
  const manifest = updater.verifyManifest(
    envelope,
    fs.readFileSync(r.keys.publicFile, "utf8"),
    { channel: "stable", currentVersion: "0.22.0-rc.90" },
  );
  assert.equal(manifest.channel, "stable");
  const record = JSON.parse(
    fs.readFileSync(path.join(r.dir, "private.release.json"), "utf8"),
  );
  assert.equal(record.authenticode, "NotSigned");
  assert.equal(record.authenticode_policy, UNSIGNED_POLICY);
});

test("DPAPI key: never plain on disk, signs, survives a new process, backs up and restores", async () => {
  const dir = temp();
  const keys = generate(path.join(dir, "stable"), { protect: true });
  assert.match(keys.privateFile, /\.dpapi$/);
  const blob = fs.readFileSync(keys.privateFile);
  assert.ok(!blob.includes("PRIVATE KEY") && !blob.includes("MC4CAQ"));
  assert.throws(() => generate(path.join(dir, "stable")), /KEY_ALREADY_EXISTS/);
  const installer = path.join(dir, "setup.exe");
  fs.writeFileSync(installer, Buffer.alloc(1024, 3));
  const out = path.join(dir, "stable.json");
  const args = { installer, version: "1.0.1", channel: "stable", minimum: "1.0.0",
    notes: "", url: "https://updates.invalid/1.0.1.exe", out,
    authenticode: "NotSigned", unsignedPolicy: UNSIGNED_POLICY }; // prettier-ignore
  // A separate process: the key is usable after this one ends.
  const { execFileSync } = require("node:child_process");
  execFileSync(process.execPath, [path.join(__dirname, "sign_launcher_update.cjs"),
    "--installer", installer, "--version", "1.0.1", "--channel", "stable", "--minimum", "1.0.0",
    "--notes", "x", "--url", args.url, "--key-file", keys.privateFile, "--authenticode", "NotSigned",
    "--unsigned-policy", UNSIGNED_POLICY, "--out", out], { stdio: "ignore" }); // prettier-ignore
  const publicKey = fs.readFileSync(keys.publicFile, "utf8");
  updater.verifyManifest(JSON.parse(fs.readFileSync(out, "utf8")), publicKey, {
    channel: "stable",
    currentVersion: "1.0.0",
  });
  const backup = path.join(dir, "backup.pem");
  assert.throws(
    () => exportKey(keys.privateFile, backup, "short"),
    /PASSPHRASE_TOO_SHORT/,
  );
  exportKey(keys.privateFile, backup, "correct horse battery staple");
  assert.match(fs.readFileSync(backup, "utf8"), /ENCRYPTED PRIVATE KEY/);
  const restored = importKey(
    backup,
    path.join(dir, "restored"),
    "correct horse battery staple",
  );
  assert.equal(fs.readFileSync(restored.publicFile, "utf8"), publicKey);
  sign({
    ...args,
    keyFile: restored.privateFile,
    out: path.join(dir, "again.json"),
  });
  updater.verifyManifest(JSON.parse(fs.readFileSync(path.join(dir, "again.json"), "utf8")), publicKey,
    { channel: "stable", currentVersion: "1.0.0" }); // prettier-ignore
});

function config(env) {
  const file = path.join(repo, "companion/launcher/electron-builder.cjs");
  const saved = { ...process.env };
  Object.assign(
    process.env,
    { POKEAPP_PACKAGE_STAGE: "stage", POKEAPP_PACKAGE_OUTPUT: "out" },
    env,
  );
  try {
    delete require.cache[require.resolve(file)];
    return require(file);
  } finally {
    for (const k of Object.keys(process.env))
      if (!(k in saved)) delete process.env[k];
    Object.assign(process.env, saved);
  }
}

test("builds embed only the public key and an HTTPS feed, together", () => {
  const r = release();
  const pub = fs.readFileSync(r.keys.publicFile, "utf8");
  const feed = "https://updates.invalid/private.json";
  const built = config({
    POKEAPP_PRIVATE_CANDIDATE: "1",
    POKEAPP_UPDATE_PUBLIC_KEY_FILE: r.keys.publicFile,
    POKEAPP_UPDATE_FEED: feed,
    POKEAPP_BUILD_VERSION: "0.22.0-rc.91",
  });
  assert.equal(built.extraMetadata.pokeappUpdate.publicKey, pub);
  assert.deepEqual(built.extraMetadata.pokeappUpdate.feed, {
    stable: null,
    private: feed,
  });
  assert.equal(built.extraMetadata.version, "0.22.0-rc.91");
  assert.equal(
    config({ POKEAPP_PRIVATE_CANDIDATE: "0" }).extraMetadata.pokeappUpdate,
    undefined,
  );
  assert.throws(
    () =>
      config({
        POKEAPP_UPDATE_PUBLIC_KEY_FILE: r.keys.privateFile,
        POKEAPP_UPDATE_FEED: feed,
      }),
    /private key/,
  );
  assert.throws(
    () =>
      config({
        POKEAPP_UPDATE_PUBLIC_KEY_FILE: r.keys.publicFile,
        POKEAPP_UPDATE_FEED: "http://x/feed",
      }),
    /HTTPS/,
  );
  assert.throws(
    () => config({ POKEAPP_UPDATE_PUBLIC_KEY_FILE: r.keys.publicFile }),
    /together/,
  );
  assert.throws(
    () =>
      config({
        POKEAPP_PRIVATE_CANDIDATE: "0",
        POKEAPP_BUILD_VERSION: "9.9.9",
      }),
    /private candidates/,
  );
});
