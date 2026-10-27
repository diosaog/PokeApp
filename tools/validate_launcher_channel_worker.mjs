// The update channel through the real pokeapp-web Worker, locally.
//
// Runs `wrangler dev --local` on the committed Worker with a disposable local
// R2 (never the remote bucket), seeds it like a release would — installer
// first, signed manifest last — and checks what a Launcher meets: routes,
// headers, cache, methods, unknown and traversal paths, and a manifest signed
// by the release signer, fetched, verified and downloaded by the shipped
// updater through the Worker. Synthetic bytes and a throwaway key only.
//
//   node tools/validate_launcher_channel_worker.mjs --out <dir> [--port 8799]
import { spawn, execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const require = createRequire(import.meta.url);
const { generate, sign } = require("./sign_launcher_update.cjs");
const updater = require("../companion/launcher/updater.cjs");
const launcher = require("../web/launcher-release.json");

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf("--" + name);
  return i >= 0 ? argv[i + 1] : fallback;
};
const out = path.resolve(arg("out", "launcher-channel"));
const port = Number(arg("port", "8799"));
const origin = `http://127.0.0.1:${port}`;
const web = path.resolve(
  path.dirname(new URL(import.meta.url).pathname.slice(1)),
  "../web",
);
const wrangler = path.join(
  web,
  "node_modules",
  "wrangler",
  "bin",
  "wrangler.js",
);
const work = fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-channel-"));
const state = path.join(work, "r2");
const bucket = "pokeapp-launcher-releases";
const checks = [];
const check = (pass, label, observed) => {
  checks.push({
    pass: Boolean(pass),
    label,
    ...(observed === undefined ? {} : { observed }),
  });
  console.log(
    pass ? "PASS" : "FAIL",
    label,
    observed === undefined ? "" : JSON.stringify(observed),
  );
};
const put = (key, file, type) =>
  execFileSync(process.execPath, [wrangler, "r2", "object", "put", `${bucket}/${key}`,
    "--file", file, "--local", "--persist-to", state, ...(type ? ["--content-type", type] : [])],
    { cwd: web, stdio: "pipe" }); // prettier-ignore
const sha = (data, algo = "sha256", encoding = "hex") =>
  crypto.createHash(algo).update(data).digest(encoding);

let dev;
try {
  // Release-shaped objects: the public installer the download card names, a
  // private candidate and its signed manifest.
  const version = "9.0.0-channel.1";
  const keys = generate(path.join(work, "keys"));
  const publicInstaller = path.join(work, "public.exe");
  const privateInstaller = path.join(work, "private.exe");
  fs.writeFileSync(publicInstaller, crypto.randomBytes(300_000));
  fs.writeFileSync(privateInstaller, crypto.randomBytes(400_000));
  put(
    `windows/${launcher.version}/PokeApp-Launcher-Setup.exe`,
    publicInstaller,
  );
  put(
    `private/${version}/PokeApp-Launcher-Private-Setup.exe`,
    privateInstaller,
  );
  const manifestFile = path.join(work, "private.json");
  sign({
    installer: privateInstaller,
    version,
    channel: "private",
    minimum: "0.1.0",
    notes: "- Canal privado servido por el Worker",
    url: `${origin}/launcher/updates/private/${version}.exe`,
    keyFile: keys.privateFile,
    out: manifestFile,
    authenticode: "NotSigned",
  });
  put("updates/private.json", manifestFile, "application/json");

  dev = spawn(process.execPath, [wrangler, "dev", "--local", "--port", String(port), "--ip", "127.0.0.1",
    "--persist-to", state, "--show-interactive-dev-session=false"], { cwd: web, stdio: ["ignore", "pipe", "pipe"] }); // prettier-ignore
  fs.mkdirSync(out, { recursive: true });
  const devLog = fs.createWriteStream(path.join(out, "wrangler-dev.log"));
  dev.stdout.pipe(devLog);
  dev.stderr.pipe(devLog);
  let ready = false;
  for (let i = 0; i < 240 && !ready; i++) {
    await new Promise((r) => setTimeout(r, 500));
    ready = await fetch(origin + "/launcher/updates/beta.json").then(
      () => true,
      () => false,
    );
  }
  check(ready, "wrangler dev serves the committed Worker on loopback");

  const get = (p, init) => fetch(origin + p, { redirect: "manual", ...init });
  const feed = await get("/launcher/updates/private.json");
  const feedBody = Buffer.from(await feed.arrayBuffer());
  check(
    feed.status === 200 &&
      feed.headers.get("content-type") === "application/json" &&
      feed.headers.get("cache-control") === "no-store" &&
      feed.headers.get("x-content-type-options") === "nosniff" &&
      feedBody.equals(fs.readFileSync(manifestFile)),
    "manifest route: exact bytes, JSON, no-store, nosniff",
  );
  const stable = await get("/launcher/updates/stable.json");
  check(
    stable.status === 404 &&
      (await stable.text()) === "Sin versiones publicadas" &&
      stable.headers.get("cache-control") === "no-store",
    "stable feed absent until published: 404, no-store",
  );
  const binary = await get(`/launcher/updates/private/${version}.exe`);
  const bytes = Buffer.from(await binary.arrayBuffer());
  check(
    binary.status === 200 &&
      binary.headers.get("content-type") === "application/octet-stream" &&
      binary.headers.get("cache-control") ===
        "public, max-age=86400, immutable" &&
      binary.headers.get("content-disposition") ===
        'attachment; filename="PokeApp-Launcher-Private-Setup.exe"' &&
      Number(binary.headers.get("content-length")) === bytes.length &&
      sha(bytes) === sha(fs.readFileSync(privateInstaller)),
    "installer route: exact bytes, octet-stream, immutable, private file name",
  );
  const head = await get(`/launcher/updates/private/${version}.exe`, {
    method: "HEAD",
  });
  check(head.status === 200 && Number(head.headers.get("content-length")) === bytes.length,
    "HEAD gives the size without the body"); // prettier-ignore
  const download = await get("/launcher/download");
  const first = Buffer.from(await download.arrayBuffer());
  check(
    download.status === 200 &&
      sha(first) === sha(fs.readFileSync(publicInstaller)) &&
      download.headers.get("cache-control") === "public, max-age=300",
    `/launcher/download serves windows/${launcher.version}/ (the version the card shows)`,
  );
  for (const method of ["POST", "PUT", "DELETE", "PATCH"]) {
    const r = await get(`/launcher/updates/private/${version}.exe`, { method });
    check(
      r.status === 405 && r.headers.get("allow") === "GET, HEAD",
      `${method} refused (405)`,
    );
  }
  for (const p of [
    "/launcher/updates/",
    "/launcher/updates/beta.json",
    "/launcher/updates/private/latest.exe",
    "/launcher/updates/private/..%2F..%2Fwindows%2F0.25.0.exe",
    "/launcher/updates/stable/9.0.0-channel.1/../../x.exe",
    "/launcher/updates/private/9.0.0-channel.1.exe.json",
  ]) {
    const r = await get(p);
    check(r.status === 404 && !/octet-stream/.test(r.headers.get("content-type") || ""),
      `no listing or traversal: ${p}`, r.status); // prettier-ignore
  }
  const missing = await get("/launcher/updates/private/9.9.9.exe");
  check(missing.status === 503 && missing.headers.get("cache-control") === "no-store",
    "unpublished version: 503, no-store, nothing cached"); // prettier-ignore

  // The shipped updater, end to end through the Worker.
  const manifest = updater.verifyManifest(JSON.parse(feedBody), fs.readFileSync(keys.publicFile, "utf8"), {
    channel: "private", currentVersion: "8.0.0", allowLoopback: true,
  }); // prettier-ignore
  const file = await updater.download(fetch, manifest, path.join(work, "dl"));
  check(
    updater.verifiedInstaller(path.join(work, "dl"))?.file === file &&
      sha(fs.readFileSync(file), "sha512", "base64") ===
        manifest.installer.sha512,
    "updater verifies the Worker's manifest (Ed25519) and its download (SHA-512)",
  );
  let wrongChannel = "";
  try {
    updater.verifyManifest(JSON.parse(feedBody), fs.readFileSync(keys.publicFile, "utf8"), {
      channel: "stable", currentVersion: "8.0.0", allowLoopback: true,
    }); // prettier-ignore
  } catch (error) {
    wrongChannel = error.code || error.message;
  }
  check(
    wrongChannel === "CHANNEL_MISMATCH",
    "a stable Launcher refuses the private feed",
    wrongChannel,
  );
} finally {
  // workerd keeps the local R2 files open until its whole tree is gone.
  if (dev?.pid)
    try {
      execFileSync("taskkill", ["/PID", String(dev.pid), "/T", "/F"], {
        stdio: "ignore",
      });
    } catch {}
  await new Promise((r) => setTimeout(r, 1500));
  fs.rmSync(work, {
    recursive: true,
    force: true,
    maxRetries: 20,
    retryDelay: 500,
  });
}
const passed = checks.filter((c) => c.pass).length;
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, "channel-worker.json"),
  JSON.stringify({ worker: "web/worker/launcher.mjs (wrangler dev --local, disposable R2)", passed, total: checks.length, checks }, null, 2) + "\n"); // prettier-ignore
console.log(`${passed}/${checks.length}`);
process.exit(passed === checks.length ? 0 : 1);
