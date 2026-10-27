import test from "node:test";
import assert from "node:assert/strict";
import worker from "./launcher.mjs";
import { artifactKey } from "./release-keys.mjs";
import launcher from "../launcher-release.json" with { type: "json" };

test("direct binary GET and HEAD use only the pinned object, with download headers", async () => {
  const keys = [];
  const object = {
    body: new Uint8Array([77, 90]),
    size: 2,
    httpEtag: '"binary"',
  };
  const env = {
    LAUNCHER_RELEASES: {
      get: async (key) => {
        keys.push(key);
        return object;
      },
      head: async (key) => {
        keys.push(key);
        return object;
      },
    },
  };
  for (const method of ["GET", "HEAD"]) {
    const response = await worker.fetch(
      new Request("https://app.test/launcher/download?key=secret", { method }),
      env,
    );
    assert.equal(response.status, 200);
    assert.equal(
      response.headers.get("Content-Disposition"),
      'attachment; filename="PokeApp-Launcher-Setup.exe"',
    );
    assert.equal(
      response.headers.get("Content-Type"),
      "application/octet-stream",
    );
    assert.equal(response.headers.get("Content-Length"), "2");
    assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
    assert.equal(
      (await response.arrayBuffer()).byteLength,
      method === "GET" ? 2 : 0,
    );
  }
  assert.deepEqual(keys, [artifactKey, artifactKey]);
  assert.equal(
    artifactKey,
    `windows/${launcher.version}/PokeApp-Launcher-Setup.exe`,
  );
});
test("no exposed bucket browser or upload route; unavailable binary fails closed", async () => {
  const env = {
    ASSETS: { fetch: async () => new Response("static") },
    LAUNCHER_RELEASES: { get: async () => null },
  };
  assert.equal(
    await (
      await worker.fetch(new Request("https://app.test/saves"), env)
    ).text(),
    "static",
  );
  assert.equal(
    (
      await worker.fetch(
        new Request("https://app.test/launcher/download", { method: "POST" }),
        env,
      )
    ).status,
    405,
  );
  const missing = await worker.fetch(
    new Request("https://app.test/launcher/download"),
    env,
  );
  assert.equal(missing.status, 503);
  assert.equal(missing.headers.get("cache-control"), "no-store");
});
test("update channel: signed feed and versioned installers, nothing else", async () => {
  const keys = [];
  const object = { body: new Uint8Array([123, 125]), size: 2, httpEtag: '"e"' };
  const env = {
    ASSETS: { fetch: async () => new Response("static") },
    LAUNCHER_RELEASES: {
      get: async (key) => (keys.push(key), object),
      head: async (key) => (keys.push(key), object),
    },
  };
  const get = (path, method = "GET") =>
    worker.fetch(new Request("https://app.test" + path, { method }), env);
  const feed = await get("/launcher/updates/stable.json");
  assert.equal(feed.status, 200);
  assert.equal(feed.headers.get("Content-Type"), "application/json");
  assert.equal(feed.headers.get("Cache-Control"), "no-store");
  const installer = await get("/launcher/updates/stable/0.27.0.exe");
  assert.equal(
    installer.headers.get("Content-Disposition"),
    'attachment; filename="PokeApp-Launcher-Setup.exe"',
  );
  assert.match(installer.headers.get("Cache-Control"), /immutable/);
  await get("/launcher/updates/private.json");
  await get("/launcher/updates/private/0.27.0-rc.1.exe", "HEAD");
  assert.deepEqual(keys, [
    "updates/stable.json",
    "windows/0.27.0/PokeApp-Launcher-Setup.exe",
    "updates/private.json",
    "private/0.27.0-rc.1/PokeApp-Launcher-Private-Setup.exe",
  ]);
  keys.length = 0;
  for (const path of [
    "/launcher/updates/beta.json",
    "/launcher/updates/stable/../secret.exe",
    "/launcher/updates/stable/%2e%2e%2fkeys.exe",
    "/launcher/updates/stable/0.27.0/x.exe",
    "/launcher/updates/stable/latest.exe",
    "/launcher/updates/",
  ])
    assert.equal((await get(path)).status, 404, path);
  assert.equal((await get("/launcher/updates/stable.json", "PUT")).status, 405);
  assert.deepEqual(keys, []);
});
test("a channel without a published feed answers 404, a missing installer 503", async () => {
  const env = {
    ASSETS: { fetch: async () => new Response("static") },
    LAUNCHER_RELEASES: { get: async () => null },
  };
  const feed = await worker.fetch(
    new Request("https://app.test/launcher/updates/stable.json"),
    env,
  );
  assert.equal(feed.status, 404);
  const binary = await worker.fetch(
    new Request("https://app.test/launcher/updates/stable/0.27.0.exe"),
    env,
  );
  assert.equal(binary.status, 503);
});
