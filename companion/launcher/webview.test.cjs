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

test("the preview origin exists only in private -WebPreview packages", () => {
  const preview = {
    pokeappPrivateCandidate: true,
    pokeappWebPreview: w.PREVIEW_ORIGIN,
  };
  assert.equal(w.webOrigin(true, {}, preview), w.PREVIEW_ORIGIN);
  for (const metadata of [
    {},
    { pokeappWebPreview: w.PREVIEW_ORIGIN },
    { pokeappPrivateCandidate: false, pokeappWebPreview: w.PREVIEW_ORIGIN },
    { pokeappPrivateCandidate: true, pokeappWebPreview: "http://127.0.0.1:9" },
    { pokeappPrivateCandidate: true, pokeappWebPreview: "https://evil.test" },
  ])
    assert.equal(w.webOrigin(true, {}, metadata), w.PRODUCTION_WEB);
  // A run-time variable can never redirect a packaged build.
  assert.equal(
    w.webOrigin(true, { POKEAPP_WEB_ORIGIN: w.PREVIEW_ORIGIN }, {}),
    w.PRODUCTION_WEB,
  );
  assert.notEqual(
    w.webPreferences(w.PREVIEW_ORIGIN).partition,
    w.webPreferences(w.PRODUCTION_WEB).partition,
  );
  assert.equal(
    w.decide("http://127.0.0.1:4174/x", w.PREVIEW_ORIGIN).action,
    "block",
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

test("only the web's own desktop routes open a native panel, from a fixed list", () => {
  const o = w.PRODUCTION_WEB;
  assert.deepEqual(w.desktopPanel(o + "/escritorio/partida", o), {
    panel: "partida",
  });
  for (const panel of w.DESKTOP_PANELS)
    assert.equal(w.desktopPanel(`${o}/escritorio/${panel}/`, o).panel, panel);
  // URLs are normalised first, exactly as the browser navigates them.
  assert.deepEqual(w.desktopPanel(o + "/escritorio/partida/../nube", o), {
    panel: "nube",
  });
  assert.deepEqual(w.desktopPanel(o + "/escritorio/objetos/rare_candy", o), {
    panel: "objetos",
    item: "rare_candy",
  });
  for (const url of [
    o + "/liga",
    o + "/escritorio",
    o + "/escritorio/admin",
    o + "/escritorio/objetos/master_ball",
    o + "/escritorio/partida/rare_candy",
    "https://evil.test/escritorio/partida",
    "http://pokeapp-web.pokeapp-v2.workers.dev/escritorio/partida",
    "not a url",
  ])
    assert.equal(w.desktopPanel(url, o), null, url);
});

test("the panel edge accepts only a plausible sidebar width", () => {
  assert.equal(w.panelLeft(228, 1280), 228);
  for (const value of [0, -5, 228.5, "228", null, undefined, 900, 700])
    assert.equal(w.panelLeft(value, 1280), 0, String(value));
  assert.equal(w.panelLeft(228, 400), 0); // phone width: sidebar is a drawer
});
