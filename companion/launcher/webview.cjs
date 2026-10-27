// The real PokeApp web inside the Launcher. It is treated as untrusted remote
// content: no preload, no IPC, sandboxed, its own persistent session, and every
// navigation pinned to the web origin. The only bridge is one same-origin link
// (/__launcher/quick-items/<item>) that the Launcher intercepts to open its own
// native panel; it carries an item code, never data or a command.
const PRODUCTION_WEB = "https://pokeapp-web.pokeapp-v2.workers.dev";
// Owner preview of an undeployed web (27B): ONE exact loopback origin, honoured
// only by private-candidate packages built with -WebPreview. Never configurable
// at run time, never in public builds, and never sharing the real web session.
const PREVIEW_ORIGIN = "http://127.0.0.1:4173";
const QUICK_ITEMS = ["rare_candy", "heart_scale"];
// One app: the web's own routes open native Launcher views. The web never
// sends a command: the Launcher only observes its URL and maps it to this
// fixed list.
// - /saves (Saves y Launcher) is the native hub, beside the web's sidebar.
// - Infinite items and robbery deliveries open as dialogs over the web.
// - The 27C /escritorio/<panel> links keep working and land in the same views.
const HUB_TABS = ["partidas", "copias", "launcher"];
const MODALS = ["objetos", "robos"];
const LEGACY = { partida: "partidas", copias: "copias", nube: "launcher" };
// Kept for older webs and tests that list the 27C panel names.
const DESKTOP_PANELS = ["partida", "objetos", "robos", "copias", "nube"];

function desktopPanel(url, origin) {
  let target;
  try {
    target = new URL(url);
  } catch {
    return null;
  }
  if (target.origin !== origin) return null;
  if (/^\/saves\/?$/.test(target.pathname)) return { panel: "saves" };
  const match = /^\/escritorio\/([a-z]+)(?:\/([a-z_]+))?\/?$/.exec(
    target.pathname,
  );
  if (!match) return null;
  const [, name, item] = match;
  if (LEGACY[name] && !item) return { panel: "saves", tab: LEGACY[name] };
  if (name === "robos" && !item) return { panel: "robos", modal: true };
  if (name === "objetos" && !item) return { panel: "objetos", modal: true };
  if (name === "objetos" && QUICK_ITEMS.includes(item))
    return { panel: "objetos", item, modal: true };
  return null;
}

// The web's sidebar edge, read from the page as a plain number: anything else
// (or a hidden phone-width sidebar) means the panel covers the whole width.
function panelLeft(value, width) {
  return Number.isInteger(value) &&
    value > 0 &&
    value <= Math.min(480, width / 2)
    ? value
    : 0;
}

function webOrigin(packaged, env, metadata = {}) {
  if (packaged)
    return metadata.pokeappPrivateCandidate === true &&
      metadata.pokeappWebPreview === PREVIEW_ORIGIN
      ? PREVIEW_ORIGIN
      : PRODUCTION_WEB;
  const override = env.POKEAPP_WEB_ORIGIN;
  if (!override) return PRODUCTION_WEB;
  const url = new URL(override);
  const local = ["127.0.0.1", "localhost"].includes(url.hostname);
  if (!(url.protocol === "https:" || (url.protocol === "http:" && local)))
    throw new Error("Web origin must be HTTPS (or local HTTP for tests)");
  return url.origin;
}

function webPreferences(origin = PRODUCTION_WEB) {
  return {
    sandbox: true,
    contextIsolation: true,
    nodeIntegration: false,
    nodeIntegrationInSubFrames: false,
    webSecurity: true,
    webviewTag: false,
    partition:
      origin === PRODUCTION_WEB
        ? "persist:pokeapp-web"
        : "persist:pokeapp-web-preview",
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
    // Session bridge codes: no data travels; the Launcher acts on its own.
    const bare = !target.search && !target.hash;
    if (bare && target.pathname === "/__launcher/session")
      return { action: "session" };
    if (bare && target.pathname === "/__launcher/logout")
      return { action: "logout" };
    if (target.pathname.startsWith("/__launcher/")) return { action: "block" };
    return { action: "allow" };
  }
  if (target.protocol === "https:" && !target.username && !target.password)
    return { action: "external", url: target.href };
  return { action: "block" };
}

function attach(
  view,
  {
    origin,
    version,
    onQuickItems,
    openExternal,
    onSession = () => {},
    onLogout = () => {},
  },
) {
  const contents = view.webContents;
  contents.setUserAgent(
    `${contents.getUserAgent()} PokeAppLauncher/${version}`,
  );
  const route = (url) => {
    const decision = decide(url, origin);
    if (decision.action === "quick-items") onQuickItems(decision.item);
    if (decision.action === "external") openExternal(decision.url);
    if (decision.action === "session") onSession();
    if (decision.action === "logout") onLogout();
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

module.exports = {
  PRODUCTION_WEB,
  PREVIEW_ORIGIN,
  DESKTOP_PANELS,
  HUB_TABS,
  MODALS,
  webOrigin,
  webPreferences,
  decide,
  desktopPanel,
  panelLeft,
  attach,
};
