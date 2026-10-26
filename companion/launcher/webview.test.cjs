const test = require("node:test");
const assert = require("node:assert/strict");
const w = require("./webview.cjs");

const O = "https://pokeapp-web.pokeapp-v2.workers.dev";
test("navigation stays on the web origin; only the quick-item bridge is special", () => {
  assert.deepEqual(w.decide(O + "/tienda", O), { action: "allow" });
  assert.deepEqual(w.decide(O + "/__launcher/quick-items/rare_candy", O), {
    action: "quick-items",
    item: "rare_candy",
  });
  assert.deepEqual(w.decide(O + "/__launcher/quick-items/heart_scale", O), {
    action: "quick-items",
    item: "heart_scale",
  });
  assert.deepEqual(w.decide(O + "/__launcher/quick-items/master_ball", O), {
    action: "block",
  });
  assert.deepEqual(w.decide(O + "/__launcher/restore", O), { action: "block" });
  assert.deepEqual(w.decide("https://example.org/x", O), {
    action: "external",
    url: "https://example.org/x",
  });
  for (const bad of [
    "http://evil.test/",
    "file:///C:/x",
    "javascript:alert(1)",
    "pokeapp-launcher://x",
    "https://u:p@example.org/",
    "nonsense",
  ])
    assert.equal(
      w.decide(bad, O).action === "allow" ||
        w.decide(bad, O).action === "quick-items",
      false,
      bad,
    );
});

test("packaged builds always use the production web; dev override only local or HTTPS", () => {
  assert.equal(
    w.webOrigin(true, { POKEAPP_WEB_ORIGIN: "http://127.0.0.1:9" }),
    w.PRODUCTION_WEB,
  );
  assert.equal(w.webOrigin(false, {}), w.PRODUCTION_WEB);
  assert.equal(
    w.webOrigin(false, { POKEAPP_WEB_ORIGIN: "http://127.0.0.1:5173/x" }),
    "http://127.0.0.1:5173",
  );
  assert.throws(() =>
    w.webOrigin(false, { POKEAPP_WEB_ORIGIN: "http://evil.test" }),
  );
});

test("the web view has no preload and is sandboxed in its own session", () => {
  const p = w.webPreferences();
  assert.equal(p.preload, undefined);
  assert.equal(
    p.sandbox && p.contextIsolation && !p.nodeIntegration && p.webSecurity,
    true,
  );
  assert.equal(p.partition, "persist:pokeapp-web");
});
