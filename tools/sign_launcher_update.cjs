// Release-side signer for Launcher update manifests (Ed25519).
// The private key is read from a file OUTSIDE the repository and the build
// output; it is never printed, logged, copied or embedded. Only the public key
// is baked into a build. A ".dpapi" key file holds the PEM encrypted for this
// Windows user (DPAPI, purpose-bound entropy) and is decrypted in memory only.
// The stable channel requires a valid Authenticode signature on the installer,
// unless the owner's private-distribution policy is stated explicitly: then an
// installer that is NOT signed at all is accepted and recorded as such. A
// broken or untrusted signature is refused in every case.
const { execFileSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

// Owner decision 2026-10-28: PokeApp is distributed privately among friends,
// without a commercial code-signing certificate.
const UNSIGNED_POLICY = "private-distribution";
const ENTROPY = Buffer.from("PokeApp Launcher update signing key v1").toString(
  "base64",
);

// DPAPI (CurrentUser) through Windows PowerShell; bytes travel base64 over
// stdin/stdout, never through a file or an argument.
function dpapi(operation, bytes) {
  const script =
    "Add-Type -AssemblyName System.Security;" +
    "$b=[Convert]::FromBase64String([Console]::In.ReadToEnd().Trim());" +
    `$e=[Convert]::FromBase64String('${ENTROPY}');` +
    `$o=[System.Security.Cryptography.ProtectedData]::${operation}($b,$e,'CurrentUser');` +
    "[Console]::Out.Write([Convert]::ToBase64String($o))";
  try {
    const out = execFileSync(
      "powershell",
      ["-NoProfile", "-NonInteractive", "-Command", script],
      {
        input: bytes.toString("base64"),
        encoding: "utf8",
        windowsHide: true,
        stdio: ["pipe", "pipe", "ignore"],
      },
    );
    return Buffer.from(out.trim(), "base64");
  } catch {
    throw new Error("KEY_PROTECTION_FAILED");
  }
}

function readPrivateKey(keyFile) {
  const raw = fs.readFileSync(keyFile);
  return crypto.createPrivateKey(
    keyFile.endsWith(".dpapi") ? dpapi("Unprotect", raw) : raw,
  );
}

// Owner + SYSTEM only on the key folder (no inherited access).
function restrict(directory) {
  execFileSync(
    "icacls",
    [directory, "/inheritance:r", "/grant:r",
      `${process.env.USERNAME}:(OI)(CI)F`, "SYSTEM:(OI)(CI)F"],
    { stdio: "ignore" },
  ); // prettier-ignore
}

const repo = path.resolve(__dirname, "..");

function inside(file, folder) {
  const a = path.resolve(file).toLowerCase();
  const b = path.resolve(folder).toLowerCase();
  return a === b || a.startsWith(b + path.sep);
}

function generate(directory, { protect = false } = {}) {
  if (inside(directory, repo))
    throw new Error("KEY_DIRECTORY_INSIDE_REPOSITORY");
  fs.mkdirSync(directory, { recursive: true });
  const privateFile = path.join(
    directory,
    "pokeapp-update-private.pem" + (protect ? ".dpapi" : ""),
  );
  const publicFile = path.join(directory, "pokeapp-update-public.pem");
  const names = [
    "pokeapp-update-private.pem",
    "pokeapp-update-private.pem.dpapi",
    "pokeapp-update-public.pem",
  ];
  if (names.some((name) => fs.existsSync(path.join(directory, name))))
    throw new Error("KEY_ALREADY_EXISTS");
  if (protect) restrict(directory);
  const keys = crypto.generateKeyPairSync("ed25519");
  const pem = Buffer.from(
    keys.privateKey.export({ type: "pkcs8", format: "pem" }),
  );
  fs.writeFileSync(privateFile, protect ? dpapi("Protect", pem) : pem, {
    mode: 0o600,
    flag: "wx",
  });
  pem.fill(0);
  fs.writeFileSync(
    publicFile,
    keys.publicKey.export({ type: "spki", format: "pem" }),
    {
      flag: "wx",
    },
  );
  return { privateFile, publicFile };
}

// Recovery copy: the key as PKCS#8 encrypted with the owner's passphrase
// (AES-256), for offline storage; the passphrase comes from the owner's own
// environment (POKEAPP_KEY_BACKUP_PASSPHRASE), never from an argument.
function exportKey(keyFile, to, passphrase) {
  if (!passphrase || passphrase.length < 16)
    throw new Error("PASSPHRASE_TOO_SHORT");
  if (inside(to, repo)) throw new Error("KEY_INSIDE_REPOSITORY_OR_BUILD");
  const pem = readPrivateKey(keyFile).export({
    type: "pkcs8",
    format: "pem",
    cipher: "aes-256-cbc",
    passphrase,
  });
  fs.writeFileSync(to, pem, { mode: 0o600, flag: "wx" });
}

// Back from a recovery copy into a DPAPI-protected key folder.
function importKey(backup, directory, passphrase) {
  if (inside(directory, repo))
    throw new Error("KEY_DIRECTORY_INSIDE_REPOSITORY");
  const key = crypto.createPrivateKey({
    key: fs.readFileSync(backup),
    passphrase,
  });
  const privateFile = path.join(directory, "pokeapp-update-private.pem.dpapi");
  const publicFile = path.join(directory, "pokeapp-update-public.pem");
  if (fs.existsSync(privateFile) || fs.existsSync(publicFile))
    throw new Error("KEY_ALREADY_EXISTS");
  fs.mkdirSync(directory, { recursive: true });
  restrict(directory);
  const pem = Buffer.from(key.export({ type: "pkcs8", format: "pem" }));
  fs.writeFileSync(privateFile, dpapi("Protect", pem), { flag: "wx" });
  pem.fill(0);
  fs.writeFileSync(
    publicFile,
    crypto.createPublicKey(key).export({ type: "spki", format: "pem" }),
    { flag: "wx" },
  );
  return { privateFile, publicFile };
}

function sign({
  installer,
  version,
  channel,
  minimum,
  notes,
  url,
  keyFile,
  out,
  authenticode,
  unsignedPolicy,
  buildRoot,
}) {
  if (!["private", "stable"].includes(channel))
    throw new Error("INVALID_CHANNEL");
  if (inside(keyFile, repo) || (buildRoot && inside(keyFile, buildRoot)))
    throw new Error("KEY_INSIDE_REPOSITORY_OR_BUILD");
  const unsignedAccepted =
    authenticode === "NotSigned" && unsignedPolicy === UNSIGNED_POLICY;
  if (channel === "stable" && authenticode !== "Valid" && !unsignedAccepted)
    throw new Error("STABLE_REQUIRES_VALID_AUTHENTICODE");
  // HTTPS only; a loopback rehearsal URL is accepted on the private channel.
  const loopback = /^http:\/\/127\.0\.0\.1:\d{2,5}\//.test(url || "");
  if (!/^https:\/\//.test(url || "") && !(loopback && channel === "private"))
    throw new Error("DOWNLOAD_URL_MUST_BE_HTTPS");
  const semver = /^\d{1,4}\.\d{1,4}\.\d{1,4}(-[0-9A-Za-z.]{1,32})?$/;
  if (!semver.test(version || "") || !semver.test(minimum || ""))
    throw new Error("INVALID_VERSION");
  const bytes = fs.readFileSync(installer);
  const manifest = {
    channel,
    version,
    minimum_version: minimum,
    notes: notes || "",
    installer: {
      url,
      sha512: crypto.createHash("sha512").update(bytes).digest("base64"),
      size: bytes.length,
    },
    released_at: new Date().toISOString(),
  };
  const body = Buffer.from(JSON.stringify(manifest));
  const key = readPrivateKey(keyFile);
  const signature = crypto.sign(null, body, key);
  // Self-check against the derived public key before anything is written.
  if (!crypto.verify(null, body, crypto.createPublicKey(key), signature))
    throw new Error("SIGNATURE_SELF_CHECK_FAILED");
  const envelope = {
    manifest: body.toString("base64"),
    signature: signature.toString("base64"),
  };
  fs.writeFileSync(out, JSON.stringify(envelope));
  // What was signed, and under which Authenticode status/policy (audit trail).
  const record = {
    channel,
    version,
    minimum_version: minimum,
    installer_sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
    installer_bytes: bytes.length,
    authenticode,
    authenticode_policy:
      authenticode === "Valid"
        ? "signed"
        : unsignedAccepted
          ? UNSIGNED_POLICY
          : "not required on the private channel",
    public_key_sha256: crypto
      .createHash("sha256")
      .update(
        crypto.createPublicKey(key).export({ type: "spki", format: "der" }),
      )
      .digest("hex"),
    signed_at: manifest.released_at,
  };
  fs.writeFileSync(
    out.replace(/\.json$/, "") + ".release.json",
    JSON.stringify(record, null, 2) + "\n",
  );
  return envelope;
}

if (require.main === module) {
  const args = Object.fromEntries(
    process.argv.slice(2).reduce((pairs, value, index, all) => {
      if (value.startsWith("--")) pairs.push([value.slice(2), all[index + 1]]);
      return pairs;
    }, []),
  );
  try {
    if (args["generate-key"]) {
      const files = generate(args["generate-key"], {
        protect: process.argv.includes("--protect"),
      });
      console.log("Public key: " + files.publicFile);
    } else if (args["export-key"]) {
      exportKey(
        args["export-key"],
        args.to,
        process.env.POKEAPP_KEY_BACKUP_PASSPHRASE,
      );
      console.log("Encrypted backup written");
    } else if (args["import-key"]) {
      const files = importKey(
        args["import-key"],
        args.to,
        process.env.POKEAPP_KEY_BACKUP_PASSPHRASE,
      );
      console.log("Public key: " + files.publicFile);
    } else {
      sign({
        installer: args.installer,
        version: args.version,
        channel: args.channel,
        minimum: args.minimum,
        notes: args.notes,
        url: args.url,
        keyFile: args["key-file"],
        out: args.out,
        authenticode: args.authenticode,
        unsignedPolicy: args["unsigned-policy"],
        buildRoot: args["build-root"],
      });
      console.log("Signed manifest: " + args.out);
    }
  } catch (error) {
    // Error codes only: never echo key material or paths' contents.
    console.error("SIGNING_FAILED " + error.message);
    process.exit(1);
  }
}

module.exports = { generate, sign, exportKey, importKey, UNSIGNED_POLICY };
