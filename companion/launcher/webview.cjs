// The real PokeApp web inside the Launcher. It is treated as untrusted remote
// content: no preload, no IPC, sandboxed, its own persistent session, and every
// navigation pinned to the web origin. The only bridge is one same-origin link
// (/__launcher/quick-items/<item>) that the Launcher intercepts to open its own
// native panel; it carries an item code, never data or a command.
const PRODUCTION_WEB = "https://pokeapp-web.pokeapp-v2.workers.dev";
const QUICK_ITEMS = ["rare_candy", "heart_scale"];

function webOrigin(packaged, env) {
  const override = env.POKEAPP_WEB_ORIGIN;
  if (packaged || !override) return PRODUCTION_WEB;
  const url = new URL(override);
  const local = ["127.0.0.1", "localhost"].includes(url.hostname);
  if (!(url.protocol === "https:" || (url.protocol === "http:" && local)))
    throw new Error("Web origin must be HTTPS (or local HTTP for tests)");
  return url.origin;
}

function webPreferences() {
  return {
    sandbox: true,
    contextIsolation: true,
    nodeIntegration: false,
    nodeIntegrationInSubFrames: false,
    webSecurity: true,
    webviewTag: false,
    partition: "persist:pokeapp-web",
    spellcheck: false,
  };
}

function decide(url, origin) {
  let target;
  try {
    target = new URL(url);
  } catch {
    return { action: "block" };
  }
  if (target.origin === origin) {
    const match = /^\/__launcher\/quick-items\/([a-z_]+)$/.exec(
      target.pathname,
    );
    if (match && QUICK_ITEMS.includes(match[1]))
      return { action: "quick-items", item: match[1] };
    if (target.pathname.startsWith("/__launcher/")) return { action: "block" };
    return { action: "allow" };
  }
  if (target.protocol === "https:" && !target.username && !target.password)
    return { action: "external", url: target.href };
  return { action: "block" };
}

function attach(view, { origin, version, onQuickItems, openExternal }) {
  const contents = view.webContents;
  contents.setUserAgent(
    `${contents.getUserAgent()} PokeAppLauncher/${version}`,
  );
  const route = (url) => {
    const decision = decide(url, origin);
    if (decision.action === "quick-items") onQuickItems(decision.item);
    if (decision.action === "external") openExternal(decision.url);
    return decision.action === "allow";
  };
  contents.setWindowOpenHandler(({ url }) => {
    route(url);
    return { action: "deny" };
  });
  contents.on("will-navigate", (event, url) => {
    if (!route(url)) event.preventDefault();
  });
  contents.on("will-redirect", (event, url) => {
    if (decide(url, origin).action !== "allow") event.preventDefault();
  });
  contents.on("will-attach-webview", (event) => event.preventDefault());
  contents.session.setPermissionRequestHandler((_c, _p, callback) =>
    callback(false),
  );
  return contents.loadURL(origin + "/");
}

module.exports = { PRODUCTION_WEB, webOrigin, webPreferences, decide, attach };
