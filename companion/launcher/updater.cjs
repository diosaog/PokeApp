// Launcher updates: an Ed25519-signed manifest under a PINNED public key is the
// only authority. A hash served by the same origin is never trusted on its own:
// the installer's SHA-512 and size are bound by that signature. Disabled until a
// release key is configured; nothing here publishes, uploads or holds secrets.
// Private candidates may use a loopback feed (http://127.0.0.1) for rehearsal;
// public builds accept HTTPS only.
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const CHANNELS = ["stable", "private"];
const FIELDS = [
  "channel",
  "version",
  "minimum_version",
  "notes",
  "installer",
  "released_at",
];

class UpdateError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

function parseVersion(value) {
  const match =
    /^(\d{1,4})\.(\d{1,4})\.(\d{1,4})(?:-([0-9A-Za-z.]{1,32}))?$/.exec(
      value || "",
    );
  if (!match) throw new UpdateError("MANIFEST_INVALID");
  return {
    core: match.slice(1, 4).map(Number),
    pre: match[4] ? match[4].split(".") : [],
  };
}

function compareVersions(a, b) {
  const x = parseVersion(a),
    y = parseVersion(b);
  for (let i = 0; i < 3; i++)
    if (x.core[i] !== y.core[i]) return x.core[i] < y.core[i] ? -1 : 1;
  if (!x.pre.length || !y.pre.length)
    return x.pre.length === y.pre.length ? 0 : x.pre.length ? -1 : 1;
  for (let i = 0; i < Math.max(x.pre.length, y.pre.length); i++) {
    if (x.pre[i] === undefined) return -1;
    if (y.pre[i] === undefined) return 1;
    const n = /^\d+$/.test(x.pre[i]),
      m = /^\d+$/.test(y.pre[i]);
    if (x.pre[i] === y.pre[i]) continue;
    if (n && m) return Number(x.pre[i]) < Number(y.pre[i]) ? -1 : 1;
    if (n !== m) return n ? -1 : 1;
    return x.pre[i] < y.pre[i] ? -1 : 1;
  }
  return 0;
}

// A loopback HTTP URL is accepted only when the build allows rehearsal feeds.
function secureUrl(value, allowLoopback = false) {
  let url;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  if (url.username || url.password) return false;
  if (url.protocol === "https:") return true;
  return (
    allowLoopback &&
    url.protocol === "http:" &&
    ["127.0.0.1", "localhost"].includes(url.hostname)
  );
}

// envelope = { manifest: base64(JSON bytes), signature: base64(Ed25519 over those bytes) }
function verifyManifest(
  envelope,
  publicKeyPem,
  { channel, currentVersion, allowLoopback = false },
) {
  if (!publicKeyPem) throw new UpdateError("UPDATES_NOT_CONFIGURED");
  if (
    !envelope ||
    typeof envelope.manifest !== "string" ||
    envelope.manifest.length > 16384
  )
    throw new UpdateError("MANIFEST_INVALID");
  if (typeof envelope.signature !== "string" || !envelope.signature)
    throw new UpdateError("SIGNATURE_MISSING");
  const bytes = Buffer.from(envelope.manifest, "base64");
  const signature = Buffer.from(envelope.signature, "base64");
  let valid = false;
  try {
    valid =
      signature.length === 64 &&
      crypto.verify(
        null,
        bytes,
        crypto.createPublicKey(publicKeyPem),
        signature,
      );
  } catch {
    valid = false;
  }
  if (!valid) throw new UpdateError("SIGNATURE_INVALID");
  let manifest;
  try {
    manifest = JSON.parse(bytes.toString("utf8"));
  } catch {
    throw new UpdateError("MANIFEST_INVALID");
  }
  const installer = manifest && manifest.installer;
  if (
    !manifest ||
    typeof manifest !== "object" ||
    Object.keys(manifest).sort().join() !== [...FIELDS].sort().join() ||
    !CHANNELS.includes(manifest.channel) ||
    typeof manifest.notes !== "string" ||
    manifest.notes.length > 2000 ||
    !installer ||
    Object.keys(installer).sort().join() !== "sha512,size,url" ||
    !/^[A-Za-z0-9+/]{86}==$/.test(installer.sha512) ||
    !Number.isInteger(installer.size) ||
    installer.size < 1 ||
    installer.size > 512 * 1024 * 1024
  )
    throw new UpdateError("MANIFEST_INVALID");
  if (!secureUrl(installer.url, allowLoopback))
    throw new UpdateError("INSECURE_URL");
  parseVersion(manifest.minimum_version);
  if (manifest.channel !== channel) throw new UpdateError("CHANNEL_MISMATCH");
  const order = compareVersions(manifest.version, currentVersion);
  if (order < 0) throw new UpdateError("DOWNGRADE_REJECTED");
  if (order === 0) return null; // already current: no update
  if (compareVersions(manifest.minimum_version, currentVersion) > 0)
    throw new UpdateError("INCOMPATIBLE_VERSION");
  return manifest;
}

// The runtime state is the authority on active physical/journal/sync work.
function installBlocker(state) {
  if (!state) return "STATE_UNAVAILABLE";
  const write = state.write || {};
  if (write.busy) return "WRITE_IN_PROGRESS";
  if (write.restart_blocked_by_recovery || write.status === "RECOVERY_REQUIRED")
    return "RECOVERY_PENDING";
  if (["PREPARED", "AWAITING_CONFIRMATION"].includes(write.status))
    return "WRITE_PENDING";
  if (state.cloud_status === "SYNCING") return "SYNC_IN_PROGRESS";
  const transfers =
    (state.cloud && state.cloud.data && state.cloud.data.transfers) || [];
  if (transfers.some((t) => !["COMMITTED", "CANCELLED"].includes(t.status)))
    return "TRANSFER_IN_PROGRESS";
  return null;
}

// The verified installer for this exact manifest, if it is already on disk:
// a repeated «Actualizar» never downloads twice.
function readyInstaller(directory, manifest) {
  const pending = readPending(directory);
  if (
    !pending ||
    pending.version !== manifest.version ||
    pending.sha512 !== manifest.installer.sha512
  )
    return null;
  try {
    return verifiedInstaller(directory).file;
  } catch {
    return null;
  }
}

async function download(fetchImpl, manifest, directory, onProgress = () => {}) {
  fs.mkdirSync(directory, { recursive: true });
  const ready = readyInstaller(directory, manifest);
  if (ready) return ready;
  const final = path.join(
    directory,
    `PokeApp-Launcher-${manifest.version}.exe`,
  );
  const partial = final + ".partial";
  fs.rmSync(partial, { force: true });
  const hash = crypto.createHash("sha512");
  let size = 0;
  try {
    const response = await fetchImpl(manifest.installer.url, {
      redirect: "error",
    });
    if (!response.ok || !response.body)
      throw new UpdateError("DOWNLOAD_FAILED");
    const out = fs.openSync(partial, "wx");
    try {
      for await (const chunk of response.body) {
        size += chunk.length;
        if (size > manifest.installer.size)
          throw new UpdateError("INTEGRITY_FAILED");
        hash.update(chunk);
        fs.writeSync(out, chunk);
        onProgress(size, manifest.installer.size);
      }
    } finally {
      fs.closeSync(out);
    }
    if (size !== manifest.installer.size)
      throw new UpdateError("DOWNLOAD_INTERRUPTED");
    if (hash.digest("base64") !== manifest.installer.sha512)
      throw new UpdateError("INTEGRITY_FAILED");
    // An older verified installer is superseded by this one.
    const previous = readPending(directory);
    if (previous && previous.file !== path.basename(final))
      fs.rmSync(path.join(directory, previous.file), { force: true });
    fs.rmSync(final, { force: true });
    fs.renameSync(partial, final);
  } catch (error) {
    fs.rmSync(partial, { force: true });
    throw error instanceof UpdateError
      ? error
      : new UpdateError("DOWNLOAD_INTERRUPTED");
  }
  fs.writeFileSync(
    path.join(directory, "pending.json"),
    JSON.stringify({
      version: manifest.version,
      file: path.basename(final),
      sha512: manifest.installer.sha512,
    }),
  );
  return final;
}

// Re-hash immediately before launch: the file on disk must still be the signed one.
function verifiedInstaller(directory) {
  const pending = readPending(directory);
  if (!pending) throw new UpdateError("NOTHING_TO_INSTALL");
  const file = path.join(directory, pending.file);
  const digest = crypto
    .createHash("sha512")
    .update(fs.readFileSync(file))
    .digest("base64");
  if (digest !== pending.sha512) {
    fs.rmSync(file, { force: true });
    fs.rmSync(path.join(directory, "pending.json"), { force: true });
    throw new UpdateError("INTEGRITY_FAILED");
  }
  return { file, version: pending.version };
}

function readPending(directory) {
  try {
    const pending = JSON.parse(
      fs.readFileSync(path.join(directory, "pending.json"), "utf8"),
    );
    parseVersion(pending.version);
    if (path.basename(pending.file) !== pending.file) return null;
    return pending;
  } catch {
    return null;
  }
}

// On start: an installed target clears the leftovers; an older running version
// means the previous install did not finish, so the verified file is kept.
function reconcileStartup(directory, currentVersion) {
  const pending = readPending(directory);
  if (!pending) return { status: "IDLE" };
  if (compareVersions(currentVersion, pending.version) >= 0) {
    fs.rmSync(path.join(directory, pending.file), { force: true });
    fs.rmSync(path.join(directory, "pending.json"), { force: true });
    return { status: "INSTALLED", version: pending.version };
  }
  return { status: "INSTALL_INCOMPLETE", version: pending.version };
}

// «Más tarde» is remembered per version: no popup again for that version at
// start; a manual check still shows it, and a newer version asks again.
function postpone(directory, version) {
  parseVersion(version);
  fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(
    path.join(directory, "postponed.json"),
    JSON.stringify({ version }),
  );
}

function postponed(directory) {
  try {
    const { version } = JSON.parse(
      fs.readFileSync(path.join(directory, "postponed.json"), "utf8"),
    );
    parseVersion(version);
    return version;
  } catch {
    return null;
  }
}

module.exports = {
  UpdateError,
  secureUrl,
  readyInstaller,
  postpone,
  postponed,
  compareVersions,
  verifyManifest,
  installBlocker,
  download,
  verifiedInstaller,
  reconcileStartup,
};
