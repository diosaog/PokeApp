// Publish a stable Launcher release to R2 — guarded, dry-run by default.
//
// Refuses unless every condition holds, so a stable manifest can never go out
// with an unsigned or mismatched installer:
//   * the installer's Authenticode status is Valid (Windows' own check), or
//     NotSigned under the owner's stated private-distribution policy
//     (--unsigned-policy private-distribution); a broken signature never passes;
//   * the package audit of that build root passed and is a public, stable
//     build (no private candidate, HTTPS stable feed);
//   * the signed manifest verifies with the public key embedded in that very
//     build, is channel "stable", names the build's version and binds the
//     installer's exact size and SHA-512 at the stable route for that version;
//   * R2 has no object yet for that version (published versions are immutable).
// With --apply --owner-authorized it uploads the installer FIRST, reads it back
// through the public route and compares SHA-512, and only then uploads the
// manifest (the switch players see). The web card is deployed afterwards.
//
//   node tools/publish_launcher_release.mjs --build <build root> --manifest <stable.json>
//        [--unsigned-policy private-distribution] [--apply --owner-authorized]
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const updater = require("../companion/launcher/updater.cjs");
const { UNSIGNED_POLICY } = require("./sign_launcher_update.cjs");
const asar = require("../companion/launcher/node_modules/@electron/asar");
const argv = process.argv.slice(2);
const arg = (name) => {
  const i = argv.indexOf("--" + name);
  return i >= 0 ? argv[i + 1] : undefined;
};
const flag = (name) => argv.includes("--" + name);
const WEB = "https://pokeapp-web.pokeapp-v2.workers.dev";
const BUCKET = "pokeapp-launcher-releases";
const build = path.resolve(arg("build") || "");
const installer = path.join(build, "release", "PokeApp-Launcher-Setup.exe");
const problems = [];
const need = (ok, problem) => ok || problems.push(problem);

need(fs.existsSync(installer), "no public installer in the build root");
const bytes = fs.existsSync(installer)
  ? fs.readFileSync(installer)
  : Buffer.alloc(0);
const status = fs.existsSync(installer)
  ? execFileSync("powershell", ["-NoProfile", "-Command",
      `(Get-AuthenticodeSignature -LiteralPath '${installer.replace(/'/g, "''")}').Status`],
      { encoding: "utf8" }).trim() // prettier-ignore
  : "Missing";
const unsignedPolicy = arg("unsigned-policy");
need(
  status === "Valid" ||
    (status === "NotSigned" && unsignedPolicy === UNSIGNED_POLICY),
  `installer Authenticode is ${status}: only Valid, or NotSigned under --unsigned-policy ${UNSIGNED_POLICY}`,
);
const auditFile = path.join(build, "package-audit.json");
const audit = fs.existsSync(auditFile)
  ? JSON.parse(fs.readFileSync(auditFile, "utf8"))
  : {};
need(audit.status === "PASS", "package audit missing or not PASS");
need(
  audit.private_candidate === false,
  "a private candidate is never published as stable",
);
const pkg = fs.existsSync(path.join(build, "release", "win-unpacked", "resources", "app.asar"))
  ? JSON.parse(asar.extractFile(path.join(build, "release", "win-unpacked", "resources", "app.asar"), "package.json").toString("utf8"))
  : {}; // prettier-ignore
const embedded = pkg.pokeappUpdate || {};
need(embedded.publicKey && embedded.feed?.stable === `${WEB}/launcher/updates/stable.json`,
  "the build does not embed the stable key and the stable feed"); // prettier-ignore
let manifest;
try {
  const envelope = JSON.parse(
    fs.readFileSync(path.resolve(arg("manifest") || ""), "utf8"),
  );
  const body = Buffer.from(envelope.manifest, "base64");
  // The signature, with the key embedded in this very build.
  if (
    !crypto.verify(
      null,
      body,
      crypto.createPublicKey(embedded.publicKey),
      Buffer.from(envelope.signature, "base64"),
    )
  )
    throw Object.assign(new Error("SIGNATURE_INVALID"), {
      code: "SIGNATURE_INVALID",
    });
  manifest = JSON.parse(body.toString("utf8"));
  need(
    manifest.channel === "stable",
    "the manifest is not for the stable channel",
  );
  // And the shipped updater, as a client at the minimum version would read it
  // (a bridge manifest names itself as minimum: nobody installs it, it says
  // «última versión» to the bridge).
  if (updater.compareVersions(manifest.minimum_version, manifest.version) < 0)
    updater.verifyManifest(envelope, embedded.publicKey, {
      channel: "stable",
      currentVersion: manifest.minimum_version,
    });
} catch (error) {
  manifest = undefined;
  problems.push(
    `manifest refused by the shipped updater: ${error.code || error.message}`,
  );
}
if (manifest) {
  need(
    manifest.version === pkg.version,
    `manifest ${manifest.version} is not the build's ${pkg.version}`,
  );
  need(manifest.installer.size === bytes.length &&
    manifest.installer.sha512 === crypto.createHash("sha512").update(bytes).digest("base64"),
    "manifest does not bind this installer's size and SHA-512"); // prettier-ignore
  need(manifest.installer.url === `${WEB}/launcher/updates/stable/${manifest.version}.exe`,
    "manifest URL is not the stable route for its version"); // prettier-ignore
}
const key =
  manifest && `windows/${manifest.version}/PokeApp-Launcher-Setup.exe`;
if (key) {
  const head = await fetch(
    `${WEB}/launcher/updates/stable/${manifest.version}.exe`,
    { method: "HEAD" },
  );
  need(
    head.status !== 200,
    `R2 already serves ${key}: published versions are never overwritten`,
  );
}
const plan = {
  version: manifest?.version ?? null,
  installer: {
    bytes: bytes.length,
    sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
  },
  authenticode: status,
  authenticode_policy: status === "Valid" ? "signed" : unsignedPolicy || null,
  steps: key ? [`upload ${key}`, "read back through the public route and compare SHA-512",
    "upload updates/stable.json (last)", "deploy the web with web/launcher-release.json = " + manifest.version] : [], // prettier-ignore
  problems,
};
console.log(JSON.stringify(plan, null, 2));
if (!flag("apply")) process.exit(problems.length ? 1 : 0);
if (!flag("owner-authorized"))
  throw new Error(
    "--apply needs the owner's explicit authorization (--owner-authorized)",
  );
if (problems.length) throw new Error("refused: " + problems.join("; "));
const wrangler = path.resolve("web/node_modules/wrangler/bin/wrangler.js");
const put = (objectKey, file, type) =>
  execFileSync(process.execPath, [wrangler, "r2", "object", "put", `${BUCKET}/${objectKey}`, "--file", file,
    "--remote", ...(type ? ["--content-type", type] : [])], { cwd: "web", stdio: "inherit" }); // prettier-ignore
put(key, installer);
const served = Buffer.from(
  await (await fetch(manifest.installer.url)).arrayBuffer(),
);
if (
  crypto.createHash("sha512").update(served).digest("base64") !==
  manifest.installer.sha512
)
  throw new Error("read-back SHA-512 differs: the manifest was NOT published");
put("updates/stable.json", path.resolve(arg("manifest")), "application/json");
console.log(`published ${manifest.version}: installer verified, then manifest`);
