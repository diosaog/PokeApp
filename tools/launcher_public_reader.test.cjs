const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"),
  path = require("node:path"),
  os = require("node:os"),
  crypto = require("node:crypto");
const {
  createSSHReader,
  parseProof,
  loadConfig,
} = require("./launcher_public_reader.cjs");
const URL =
  "https://pokeapp-web.pokeapp-v2.workers.dev/launcher/updates/stable/0.26.9.exe";
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-reader-test-"));
  t.after(() => {
    assert(path.resolve(root).startsWith(path.resolve(os.tmpdir()) + path.sep));
    fs.rmSync(root, { recursive: true, force: true });
  });
  const key = path.join(root, "identity"),
    known = path.join(root, "known_hosts"),
    configFile = path.join(root, "reader.json");
  fs.writeFileSync(key, "isolated test key marker, never executed");
  const pub = Buffer.concat([
    Buffer.from([0, 0, 0, 11]),
    Buffer.from("ssh-ed25519"),
    Buffer.from([0, 0, 0, 32]),
    crypto.randomBytes(32),
  ]);
  fs.writeFileSync(
    known,
    `ssh.railway.com ssh-ed25519 ${pub.toString("base64")}\n`,
  );
  const config = {
    provider: "railway-ssh",
    host: "ssh.railway.com",
    user: "pokeapp-api-production.up.railway.app",
    identity_file: key,
    known_hosts_file: known,
    host_key_sha256:
      "SHA256:" +
      crypto
        .createHash("sha256")
        .update(pub)
        .digest("base64")
        .replace(/=+$/, ""),
  };
  fs.writeFileSync(configFile, JSON.stringify(config));
  return {
    root,
    key,
    known,
    configFile,
    config,
    save: (value) => fs.writeFileSync(configFile, JSON.stringify(value)),
  };
}
test("reader accepts only explicit fixed provider/service and host key pin outside repo/build", (t) => {
  const f = fixture(t);
  assert.equal(loadConfig(f.configFile).host, "ssh.railway.com");
  for (const value of [
    { ...f.config, host: "evil.test" },
    { ...f.config, user: "root@evil.test" },
    { ...f.config, extra: "anything" },
    { ...f.config, host_key_sha256: "SHA256:" + "f".repeat(43) },
  ]) {
    f.save(value);
    assert.throws(() => loadConfig(f.configFile));
  }
  f.save(f.config);
  assert.throws(() => loadConfig(f.configFile, f.root), /LOCATION_INVALID/);
  fs.appendFileSync(f.known, "ssh.railway.com ssh-ed25519 YQ==\n");
  assert.throws(() => loadConfig(f.configFile), /HOST_PIN_INVALID/);
});
test("proof must match exact URL/method, HTTP status, bounded byte count and SHA-512 format", () => {
  const proof = {
    url: URL,
    method: "GET",
    status: 200,
    size: 159427247,
    sha512: "A".repeat(86) + "==",
  };
  assert.deepEqual(parseProof(JSON.stringify(proof), URL, "GET"), proof);
  for (const value of [
    { ...proof, url: "https://evil.test/x.exe" },
    { ...proof, method: "HEAD" },
    { ...proof, status: 0 },
    { ...proof, size: 0.5 },
    { ...proof, size: 513 * 1024 * 1024 },
    { ...proof, sha512: null },
    { ...proof, ignored: true },
    [proof],
  ])
    assert.throws(() => parseProof(JSON.stringify(value), URL, "GET"));
  assert.throws(() =>
    parseProof("progress\n" + JSON.stringify(proof), URL, "GET"),
  );
  assert.deepEqual(
    parseProof(
      JSON.stringify({ ...proof, status: 503, size: 0, sha512: null }),
      URL,
      "GET",
    ),
    { ...proof, status: 503, size: 0, sha512: null },
  );
});
test("SSH uses pinned known_hosts, exact identity, no agent/config/proxy and bounded output", async (t) => {
  const f = fixture(t);
  let invocation;
  const proof = {
    url: URL,
    method: "GET",
    status: 200,
    size: 12,
    sha512: "A".repeat(86) + "==",
  };
  const reader = createSSHReader(f.configFile, {
    execute: (exe, args, options) => {
      invocation = { exe, args, options };
      return JSON.stringify(proof);
    },
  });
  assert.deepEqual(await reader(URL, "GET"), proof);
  for (const option of [
    "BatchMode=yes",
    "IdentitiesOnly=yes",
    "StrictHostKeyChecking=yes",
    "HostKeyAlgorithms=ssh-ed25519",
    "ForwardAgent=no",
    "ClearAllForwardings=yes",
    "PermitLocalCommand=no",
    "UserKnownHostsFile=" + f.known,
  ])
    assert(invocation.args.includes(option));
  assert.equal(invocation.options.timeout, 60000);
  assert.equal(invocation.options.maxBuffer, 16384);
  assert.equal(
    invocation.args.at(-2),
    "pokeapp-api-production.up.railway.app@ssh.railway.com",
  );
  assert(invocation.args.includes(f.key));
  const encoded = /b64decode\("([A-Za-z0-9+/=]+)"\)/.exec(
    invocation.args.at(-1),
  )[1];
  const remote = Buffer.from(encoded, "base64").toString();
  assert(remote.includes("response.read(1024*1024)"));
  assert(remote.includes("hashlib.sha512()"));
  assert(remote.includes(URL));
  assert(
    !remote.includes("os.environ") &&
      !remote.includes("open(" + JSON.stringify(f.key)),
  );
  f.save({ ...f.config, identity_file: f.known });
  await assert.rejects(reader(URL, "HEAD"), /CONFIG_CHANGED/);
});
test("arbitrary destinations, commands and failed SSH cannot produce accepted proof", async (t) => {
  const f = fixture(t);
  let called = false;
  const reader = createSSHReader(f.configFile, {
    execute: () => {
      called = true;
      throw new Error("sensitive details never forwarded");
    },
  });
  for (const url of [
    "https://evil.test/x.exe",
    URL + "?redirect=evil",
    URL + ";id",
    URL.replace("https:", "http:"),
  ])
    await assert.rejects(reader(url, "GET"), /REQUEST_INVALID/);
  await assert.rejects(reader(URL, "POST"), /REQUEST_INVALID/);
  assert.equal(called, false);
  await assert.rejects(reader(URL, "GET"), /^Error: PUBLIC_READER_SSH_FAILED$/);
});
