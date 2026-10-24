import test from "node:test";
import assert from "node:assert/strict";
import worker, { artifactKey } from "./launcher.mjs";
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
