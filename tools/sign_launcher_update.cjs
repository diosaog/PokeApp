// Release-side signer for Launcher update manifests (Ed25519).
// The private key is read from a file OUTSIDE the repository and the build
// output; it is never printed, logged, copied or embedded. Only the public key
// is baked into a build. The stable channel additionally requires a valid
// Authenticode signature on the installer: no stable manifest without it.
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const repo = path.resolve(__dirname, "..");

function inside(file, folder) {
  const a = path.resolve(file).toLowerCase();
  const b = path.resolve(folder).toLowerCase();
  return a === b || a.startsWith(b + path.sep);
}

function generate(directory) {
  if (inside(directory, repo))
    throw new Error("KEY_DIRECTORY_INSIDE_REPOSITORY");
  fs.mkdirSync(directory, { recursive: true });
  const privateFile = path.join(directory, "pokeapp-update-private.pem");
  const publicFile = path.join(directory, "pokeapp-update-public.pem");
  if (fs.existsSync(privateFile) || fs.existsSync(publicFile))
    throw new Error("KEY_ALREADY_EXISTS");
  const keys = crypto.generateKeyPairSync("ed25519");
  fs.writeFileSync(
    privateFile,
    keys.privateKey.export({ type: "pkcs8", format: "pem" }),
    {
      mode: 0o600,
      flag: "wx",
    },
  );
  fs.writeFileSync(
    publicFile,
    keys.publicKey.export({ type: "spki", format: "pem" }),
    {
      flag: "wx",
    },
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
  buildRoot,
}) {
  if (!["private", "stable"].includes(channel))
    throw new Error("INVALID_CHANNEL");
  if (inside(keyFile, repo) || (buildRoot && inside(keyFile, buildRoot)))
    throw new Error("KEY_INSIDE_REPOSITORY_OR_BUILD");
  if (channel === "stable" && authenticode !== "Valid")
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
  const key = crypto.createPrivateKey(fs.readFileSync(keyFile));
  const signature = crypto.sign(null, body, key);
  // Self-check against the derived public key before anything is written.
  if (!crypto.verify(null, body, crypto.createPublicKey(key), signature))
    throw new Error("SIGNATURE_SELF_CHECK_FAILED");
  const envelope = {
    manifest: body.toString("base64"),
    signature: signature.toString("base64"),
  };
  fs.writeFileSync(out, JSON.stringify(envelope));
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
      const files = generate(args["generate-key"]);
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

module.exports = { generate, sign };
