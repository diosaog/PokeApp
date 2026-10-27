const {
  app,
  BrowserWindow,
  WebContentsView,
  ipcMain,
  dialog,
  shell,
  net,
} = require("electron");
const webview = require("./webview.cjs");
const {
  createConfirmations,
  describe,
  fingerprint,
  restorable,
  robberyOpen,
} = require("./confirmations.cjs");
const { spawn } = require("node:child_process");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { createInterface } = require("node:readline");
const metadata = require("./package.json");
const privateCandidate = metadata.pokeappPrivateCandidate === true;
// Update rehearsal builds (private only) keep their own profile and never see
// the real emulator folders.
const rehearsal = privateCandidate && metadata.pokeappVariant === "updatetest";

const root = path.resolve(__dirname, "../..");
const entry = pathToFileURL(path.join(__dirname, "index.html")).href;
// User data survives per-user installation upgrades and uninstallation.
const profile =
  process.env.POKEAPP_LAUNCHER_PROFILE ||
  path.join(
    process.env.LOCALAPPDATA || app.getPath("appData"),
    "PokeApp",
    rehearsal
      ? "Launcher-UpdateTest"
      : privateCandidate
        ? "Launcher-Private"
        : "Launcher",
  );
app.setPath("userData", path.join(profile, "shell"));
app.setAppUserModelId(
  privateCandidate ? "app.pokeapp.launcher.private" : "app.pokeapp.launcher",
);
// In-app confirmations: main writes the summary from the core's state and
// issues a single-use ticket bound to that action, target and state.
const confirmations = createConfirmations();
let worker,
  win,
  tools,
  sequence = 0,
  installing = false;
const pending = new Map();
function request(command, args = {}) {
  if (!worker || worker.killed || pending.size >= 8)
    return Promise.reject(new Error("Launcher no disponible"));
  // Once an update install is confirmed, no new local operation may start.
  if (installing && command !== "state")
    return Promise.reject(new Error("Actualización en curso"));
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error("Launcher no disponible"));
    }, 5000);
    pending.set(id, { resolve, reject, timer });
    worker.stdin.write(JSON.stringify({ id, command, args }) + "\n");
  });
}
// Only the Launcher's own page (the native tools view) may call the core.
function authorize(event) {
  const from = event.senderFrame && new URL(event.senderFrame.url);
  if (from) from.search = "";
  if (
    !tools ||
    event.sender !== tools.webContents ||
    event.senderFrame !== tools.webContents.mainFrame ||
    from?.href !== entry
  )
    throw new Error("Solicitud no permitida");
}
app.whenReady().then(() => {
  const python = app.isPackaged
    ? path.join(process.resourcesPath, "runtime/core/PokeApp.Core.exe")
    : process.env.POKEAPP_LAUNCHER_PYTHON ||
      path.join(root, ".venv-api/Scripts/python.exe");
  const parser = app.isPackaged
    ? path.join(process.resourcesPath, "runtime/parser/PokeApp.Parser.exe")
    : process.env.POKEAPP_LAUNCHER_PARSER ||
      path.join(
        root,
        "companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe",
      );
  const args = app.isPackaged ? [] : ["-m", "app.launcher.stdio"];
  args.push("--parser", parser, "--profile", profile);
  worker = spawn(python, args, {
    cwd: app.isPackaged ? process.resourcesPath : root,
    env: rehearsal
      ? { ...process.env, APPDATA: path.join(profile, "sandbox-appdata") }
      : process.env,
    windowsHide: true,
    stdio: ["pipe", "pipe", "ignore"],
  });
  const rejectPending = () => {
    for (const task of pending.values()) {
      clearTimeout(task.timer);
      task.reject(new Error("Launcher no disponible"));
    }
    pending.clear();
  };
  worker.on("error", rejectPending);
  worker.on("exit", rejectPending);
  worker.stdin.on("error", rejectPending);
  createInterface({ input: worker.stdout }).on("line", (line) => {
    try {
      const msg = JSON.parse(line),
        task = pending.get(msg.id);
      if (!task) return;
      pending.delete(msg.id);
      clearTimeout(task.timer);
      if (msg.error)
        task.reject(new Error("No se pudo completar la solicitud local"));
      else task.resolve(msg.result);
    } catch {
      rejectPending();
    }
  });
  ipcMain.handle("launcher:state", (event, revision) => {
    authorize(event);
    return request("state", {
      known_receipt: typeof revision === "string" ? revision : null,
    });
  });
  ipcMain.handle("launcher:select", async (event) => {
    authorize(event);
    const result = await dialog.showOpenDialog(win, {
      properties: ["openFile"],
      filters: [
        {
          name: "Save Pokémon (incluye main de X/Y, ORAS y Sol/Luna/Ultrasol/Ultraluna)",
          extensions: ["*"],
        },
        { name: "Save con extensión", extensions: ["sav", "dsv", "srm"] },
      ],
    });
    return result.canceled
      ? { status: "CANCELLED" }
      : request("select", { path: result.filePaths[0] });
  });
  ipcMain.handle("launcher:login", (event, trainer, pin) => {
    authorize(event);
    if (
      typeof trainer !== "string" ||
      typeof pin !== "string" ||
      trainer.length > 128 ||
      pin.length > 32
    )
      throw new Error("Datos no válidos");
    return request("login", { trainer, pin });
  });
  for (const name of ["logout", "retry", "sync"])
    ipcMain.handle("launcher:" + name, (event) => {
      authorize(event);
      return request(name);
    });
  ipcMain.handle(
    "launcher:write-confirm",
    async (event, operationId, emulatorClosed, ticket) => {
      authorize(event);
      if (
        typeof operationId !== "string" ||
        operationId.length > 128 ||
        emulatorClosed !== true
      )
        throw new Error("Confirma que el juego y el emulador están cerrados.");
      const state = await request("state");
      describe("write", operationId, state);
      confirmations.redeem(
        ticket,
        "write",
        operationId,
        fingerprint("write", operationId, state),
      );
      return request("write_confirm", {
        operation_id: operationId,
        closed_emulator_confirmed: true,
      });
    },
  );
  ipcMain.handle("launcher:write-reconcile", (event) => {
    authorize(event);
    return request("write_reconcile");
  });
  ipcMain.handle("launcher:backups", (event) => {
    authorize(event);
    return request("backup_list");
  });
  ipcMain.handle("launcher:backup-copy", async (event, operationId, role) => {
    authorize(event);
    const state = await request("state");
    const backup = state.write?.backups?.find(
      (b) => b.operation_id === operationId && b.role === role && b.verified,
    );
    if (!backup || state.write.busy)
      throw new Error("La copia no está verificada. Actualiza el historial.");
    const chosen = await dialog.showSaveDialog(win, {
      title:
        role === "daily" ? "Guardar copia diaria" : "Guardar copia original",
      buttonLabel: "Guardar copia",
      defaultPath:
        role === "daily"
          ? `PokeApp-${backup.game}-diaria-${backup.date}.sav`
          : `PokeApp-${backup.game}-${operationId.slice(0, 8)}-${role}.sav`,
      filters: [{ name: "Copia de partida", extensions: ["sav"] }],
    });
    if (chosen.canceled || !chosen.filePath) return { status: "CANCELLED" };
    return request("backup_export", {
      operation_id: operationId,
      role,
      destination: chosen.filePath,
    });
  });
  ipcMain.handle(
    "launcher:backup-restore",
    async (event, operationId, emulatorClosed, typed, ticket) => {
      authorize(event);
      if (typeof operationId !== "string" || operationId.length > 128)
        throw new Error("Restauración no disponible.");
      if (emulatorClosed !== true)
        throw new Error("Confirma que el juego y el emulador están cerrados.");
      if (typed !== "Confirmo")
        throw new Error("Escribe Confirmo para restaurar.");
      const state = await request("state");
      // The ticket was issued for this backup of this save, in this state.
      confirmations.redeem(
        ticket,
        "restore",
        operationId,
        fingerprint("restore", operationId, state),
      );
      if (!restorable(state, operationId) || state.write.busy)
        throw new Error("Restauración no disponible.");
      // Pending robbery deliveries could duplicate or lose a Pokémon.
      if (
        state.cloud?.data?.mandatory_sync ||
        robberyOpen(state.cloud?.data?.transfers) ||
        state.write.status === "RECOVERY_REQUIRED"
      )
        throw new Error(
          "Hay operaciones pendientes: resuélvelas antes de restaurar.",
        );
      return request("backup_restore", {
        operation_id: operationId,
        closed_emulator_confirmed: true,
        restore_confirmed: true,
      });
    },
  );
  ipcMain.handle("launcher:export", async (event, emulatorClosed, ticket) => {
    authorize(event);
    if (emulatorClosed !== true)
      throw new Error("Confirma que el juego y el emulador están cerrados.");
    const state = await request("state");
    describe("export", "current", state);
    confirmations.redeem(
      ticket,
      "export",
      "current",
      fingerprint("export", "current", state),
    );
    const result = await dialog.showOpenDialog(win, {
      title: "Elegir carpeta para la copia del save",
      properties: ["openDirectory", "createDirectory"],
      buttonLabel: "Elegir carpeta",
    });
    if (result.canceled || !result.filePaths[0]) return { status: "CANCELLED" };
    return request("export_prepare", {
      destination: result.filePaths[0],
      intent: state.write.export_intent,
      closed_emulator_confirmed: true,
    });
  });
  // Window: an empty base; the web view and the native tools view stack on it.
  win = new BrowserWindow({
    show: process.env.POKEAPP_LAUNCHER_HEADLESS_TEST !== "1",
    width: 1120,
    height: 820,
    minWidth: 720,
    minHeight: 600,
    backgroundColor: "#0a0d22",
    icon: path.join(__dirname, "assets/icon.ico"),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event) => event.preventDefault());
  void win.loadURL("about:blank");
  // Native tools: this Launcher's own page, the only holder of the preload.
  tools = new WebContentsView({
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  tools.setBackgroundColor("#00000000");
  tools.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  tools.webContents.on("will-navigate", (event) => event.preventDefault());
  tools.webContents.session.setPermissionRequestHandler(
    (_webContents, _permission, callback) => callback(false),
  );
  // One app (27C): the real PokeApp web fills the window and stays the base of
  // the experience. The Launcher's own page (tools) opens as a panel over the
  // web content, beside the web's sidebar, whenever the web navigates to one
  // of its /escritorio routes; otherwise only a strip of it shows, and only
  // while an update notice needs it. If the web cannot load, the tools take
  // the whole window so the local save tools keep working offline.
  const webAt = webview.webOrigin(
    app.isPackaged,
    process.env,
    require("./package.json"),
  );
  const web = new WebContentsView({
    webPreferences: webview.webPreferences(webAt),
  });
  let strip = 0,
    modal = false,
    panel = null,
    panelFromUrl = false,
    left = 0,
    offline = false,
    turn = 0; // the latest open/close wins; a slower earlier open is dropped
  const layout = () => {
    const [width, height] = win.getContentSize();
    web.setBounds({
      x: 0,
      y: strip,
      width,
      height: Math.max(0, height - strip),
    });
    // Dialogs cover the whole window; the hub sits beside the web's sidebar.
    const x = offline || modal ? 0 : left;
    tools.setBounds(
      offline || panel
        ? { x, y: 0, width: Math.max(0, width - x), height }
        : { x: 0, y: 0, width, height: strip },
    );
    tools.setVisible(Boolean(offline || panel || strip));
  };
  // The web's sidebar edge, read in an isolated world as a plain number.
  const sidebarEdge = () =>
    web.webContents
      .executeJavaScriptInIsolatedWorld(999, [
        {
          code: `(() => { const s = document.querySelector(".sidebar"); const r = s && s.getBoundingClientRect(); return r && r.left === 0 && r.width > 0 ? Math.round(r.right) : 0; })()`,
        },
      ])
      .then(
        (value) => webview.panelLeft(value, win.getContentSize()[0]),
        () => 0,
      );
  const openPanel = async (target, fromUrl) => {
    const mine = ++turn;
    panel = target.panel;
    panelFromUrl = fromUrl;
    const edge = target.modal ? 0 : await sidebarEdge();
    if (mine !== turn) return;
    modal = Boolean(target.modal);
    left = edge;
    layout();
    tools.webContents.focus();
    tools.webContents.send("launcher:navigate", {
      view: modal ? "modal" : "panel",
      panel: target.panel,
      item: target.item,
      tab: target.tab,
    });
  };
  const closePanel = () => {
    turn++;
    panel = null;
    modal = false;
    layout();
    tools.webContents.send("launcher:navigate", { view: "strip" });
  };
  const followWeb = (url) => {
    const target = webview.desktopPanel(url, webAt);
    if (target) void openPanel(target, true);
    else if (panel && panelFromUrl) closePanel();
  };
  web.webContents.on("did-navigate-in-page", (_event, url, isMainFrame) => {
    if (isMainFrame) followWeb(url);
  });
  web.webContents.on("did-navigate", (_event, url) => {
    if (offline) {
      offline = false;
      layout();
      tools.webContents.send("launcher:navigate", { view: "strip" });
    }
    followWeb(url);
  });
  web.webContents.on(
    "did-fail-load",
    (_event, code, _description, _url, isMainFrame) => {
      // -3 is a navigation this Launcher cancelled itself.
      if (!isMainFrame || code === -3) return;
      offline = true;
      layout();
      tools.webContents.send("launcher:navigate", { view: "offline" });
    },
  );
  win.on("resize", () => {
    if (!panel) return layout();
    void sidebarEdge().then((edge) => {
      left = edge;
      layout();
    });
  });
  const shareApi = (async () => {
    try {
      const config = await (
        await net.fetch(webAt + "/build-config.json")
      ).json();
      const state = await request("state");
      const api = new URL(config.api_base_url).origin;
      return api === state.backend_origin ? api : null;
    } catch {
      return null;
    }
  })();
  const onWebOrigin = () => {
    try {
      return new URL(web.webContents.getURL()).origin === webAt;
    } catch {
      return false;
    }
  };
  const pushSession = async () => {
    if (!(await shareApi)) return;
    for (let attempt = 0; attempt < 8; attempt++) {
      if (!onWebOrigin()) return;
      const reply = await request("web_session").catch(() => null);
      if (!reply || reply.status === "LOGIN_REQUIRED") return;
      if (reply.status === "OK") {
        const session = JSON.stringify({
          access_token: reply.access_token,
          expires_at: reply.expires_at,
          trainer_id: reply.trainer_id,
        });
        await web.webContents
          .executeJavaScript(
            `window.__pokeappLauncherSession && window.__pokeappLauncherSession(${session})`,
          )
          .catch(() => {});
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
  };
  // One sign-in: when the web signs in successfully, the core signs in with
  // the same credentials, which pass through memory only (never stored).
  void shareApi.then((api) => {
    if (!api) return;
    const pending = new Map();
    const filter = { urls: [api + "/v1/auth/pin-login"] };
    const webRequest = web.webContents.session.webRequest;
    webRequest.onBeforeRequest(filter, (details, callback) => {
      try {
        if (details.method === "POST" && details.uploadData?.[0]?.bytes) {
          const body = JSON.parse(details.uploadData[0].bytes.toString("utf8"));
          if (
            typeof body.trainer_identifier === "string" &&
            typeof body.pin === "string"
          )
            pending.set(details.id, {
              trainer: body.trainer_identifier,
              pin: body.pin,
            });
        }
      } catch {
        // Not a login body this Launcher understands: nothing to forward.
      }
      callback({});
    });
    webRequest.onCompleted(filter, async (details) => {
      const login = pending.get(details.id);
      pending.delete(details.id);
      if (!login || details.statusCode !== 200) return;
      const state = await request("state").catch(() => null);
      const linked = state?.principal?.display_name;
      if (
        !linked ||
        linked.toLocaleLowerCase() !== login.trainer.toLocaleLowerCase()
      )
        await request("login", login).catch(() => {});
    });
    webRequest.onErrorOccurred(filter, (details) => pending.delete(details.id));
  });
  web.webContents.on("did-finish-load", () => void pushSession());
  void webview.attach(web, {
    origin: webAt,
    version: app.getVersion(),
    openExternal: (url) => shell.openExternal(url),
    onSession: () => void pushSession(),
    // Signing out of PokeApp also unlinks this Launcher and stops its sync.
    onLogout: () => void request("logout").catch(() => {}),
    // Older webs link "Añadir a mi partida" to /__launcher/quick-items/<item>.
    onQuickItems: (item) => void openPanel({ panel: "objetos", item }, false),
  });
  ipcMain.handle("launcher:present", (event, view) => {
    authorize(event);
    if (!["selector", "update", "robos", "objetos", "restore"].includes(view))
      throw new Error("Vista no válida");
    void openPanel({ panel: view, modal: true }, false);
    return { shown: true };
  });
  ipcMain.handle("launcher:open-hub", (event, tab) => {
    authorize(event);
    if (!["partidas", "copias", "launcher"].includes(tab))
      throw new Error("Vista no válida");
    void openPanel({ panel: "saves", tab }, false);
    return { shown: true };
  });
  ipcMain.handle("launcher:layout", (event, height) => {
    authorize(event);
    if (!Number.isInteger(height) || height < 0 || height > 160)
      throw new Error("Vista no válida");
    strip = height;
    layout();
  });
  // "Volver a PokeApp": the web goes back to where it was before the panel.
  ipcMain.handle("launcher:panel-close", (event) => {
    authorize(event);
    if (offline) {
      web.webContents.reload();
      return { offline: true };
    }
    const history = web.webContents.navigationHistory;
    if (panelFromUrl && history.canGoBack()) history.goBack();
    closePanel();
    return { offline: false };
  });
  // Classic tab bar (used when the web is unreachable): "PokeApp" retries it.
  ipcMain.handle("launcher:show-web", (event, show, top) => {
    authorize(event);
    if (
      typeof show !== "boolean" ||
      !Number.isInteger(top) ||
      top < 0 ||
      top > 400
    )
      throw new Error("Vista no válida");
    if (show && offline) web.webContents.reload();
    else if (show) closePanel();
    return { shown: show, origin: webAt };
  });
  win.contentView.addChildView(web);
  win.contentView.addChildView(tools);
  layout();
  ipcMain.handle("launcher:quick-items", (event) => {
    authorize(event);
    return request("quick_items_refresh");
  });
  ipcMain.handle(
    "launcher:quick-item-add",
    (event, item, quantity, emulatorClosed) => {
      authorize(event);
      if (
        !["rare_candy", "heart_scale"].includes(item) ||
        !Number.isInteger(quantity) ||
        quantity < 1 ||
        quantity > 9999 ||
        emulatorClosed !== true
      )
        throw new Error(
          "Revisa el objeto, la cantidad y el cierre del emulador.",
        );
      // Only prepares; the existing write confirmation still applies it.
      return request("quick_item_offer", {
        item,
        quantity,
        closed_emulator_confirmed: true,
      });
    },
  );
  // Robbery: only this trainer's listed leg; runtime and server recheck all.
  // The tools page explains the LOCAL effect in its own dialog and passes an
  // explicit confirmation; completion is the server's verdict.
  ipcMain.handle(
    "launcher:transfer",
    async (event, kind, authorizationId, emulatorClosed, ticket) => {
      authorize(event);
      if (
        !["prepare", "apply", "fulfil", "cancel", "refresh"].includes(kind) ||
        typeof authorizationId !== "string" ||
        authorizationId.length !== 36
      )
        throw new Error("Operación de robo no válida");
      const state = await request("state");
      const transfer = (state.cloud?.data?.transfers || []).find(
        (t) => t.authorization_id === authorizationId,
      );
      if (!transfer) throw new Error("La operación ya no está pendiente.");
      const args = { authorization_id: authorizationId };
      if (kind === "refresh") return request("transfer_refresh", args);
      const step = "transfer:" + kind;
      describe(step, authorizationId, state);
      confirmations.redeem(
        ticket,
        step,
        authorizationId,
        fingerprint(step, authorizationId, state),
      );
      if (kind === "cancel") return request("transfer_cancel", args);
      if (emulatorClosed !== true)
        throw new Error("Confirma que el juego y el emulador están cerrados.");
      if (kind === "fulfil") {
        return request("transfer_fulfil", {
          ...args,
          closed_emulator_confirmed: true,
        });
      }
      return request(
        kind === "prepare" ? "transfer_prepare" : "transfer_apply",
        {
          ...args,
          closed_emulator_confirmed: true,
        },
      );
    },
  );
  ipcMain.handle("launcher:discover", (event) => {
    authorize(event);
    return request("discover_saves");
  });
  ipcMain.handle("launcher:select-discovered", (event, savePath) => {
    authorize(event);
    if (typeof savePath !== "string" || savePath.length > 4096)
      throw new Error("Partida no válida");
    return request("select_discovered", { path: savePath });
  });

  const updates = require("./updater.cjs");
  const updateConfig = require("./package.json").pokeappUpdate || {};
  const channel = privateCandidate ? "private" : "stable";
  const updateDir = path.join(profile, "updates");
  const feed = updateConfig.feed && updateConfig.feed[channel];
  // Rehearsal feeds on loopback exist only in private candidates.
  const allowLoopback = privateCandidate;
  const configured = Boolean(
    updateConfig.publicKey &&
    typeof feed === "string" &&
    updates.secureUrl(feed, allowLoopback),
  );
  const current = app.getVersion();
  // Never let the updater's own housekeeping stop the Launcher from starting.
  const reconcile = () => {
    try {
      return updates.reconcileStartup(updateDir, current);
    } catch {
      return { status: "IDLE" };
    }
  };
  const recovered = configured ? reconcile() : { status: "IDLE" };
  // The installer that restarted us may still hold its file: retry shortly.
  if (recovered.leftover) setTimeout(reconcile, 60000).unref();
  let update = configured
    ? {
        status: recovered.status === "INSTALL_INCOMPLETE" ? "READY" : "IDLE",
        current,
        channel,
        recovered,
        version:
          recovered.status === "INSTALL_INCOMPLETE"
            ? recovered.version
            : undefined,
      }
    : {
        status: "DISABLED",
        current,
        channel,
        reason: "UPDATES_NOT_CONFIGURED",
      };
  let offered = null,
    checking = null,
    applying = null;
  const busy = () =>
    ["DOWNLOADING", "VERIFYING", "WAITING", "INSTALLING"].includes(
      update.status,
    );
  // `prompt`: the popup opens by itself at most once per version, and never
  // for a version the trainer postponed (a manual check still shows it).
  const checkFeed = ({ manual = false } = {}) => {
    if (!configured || busy()) return Promise.resolve();
    if (checking) return checking;
    update = { ...update, status: "CHECKING", reason: undefined };
    checking = fetch(feed, { redirect: "error" })
      .then((response) =>
        response.ok ? response.json() : Promise.reject(new Error("feed")),
      )
      .then((envelope) => {
        offered = updates.verifyManifest(envelope, updateConfig.publicKey, {
          channel,
          currentVersion: current,
          allowLoopback,
        });
        update = offered
          ? {
              ...update,
              status: updates.readyInstaller(updateDir, offered)
                ? "READY"
                : "AVAILABLE",
              version: offered.version,
              notes: offered.notes,
              size: offered.installer.size,
              prompt:
                !manual && updates.postponed(updateDir) !== offered.version,
            }
          : {
              ...update,
              status: "UP_TO_DATE",
              version: undefined,
              prompt: false,
            };
      })
      .catch((error) => {
        offered = null;
        // A verified file left by an unfinished install can still be offered.
        const left = recovered.status === "INSTALL_INCOMPLETE";
        update = {
          ...update,
          status: left ? "READY" : "ERROR",
          reason: error.code || "UPDATE_CHECK_FAILED",
          prompt: false,
        };
      })
      .finally(() => {
        checking = null;
      });
    return checking;
  };
  void checkFeed();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  // The core must be gone before the installer replaces its files.
  const stopCore = () =>
    new Promise((resolve) => {
      if (!worker || worker.exitCode !== null) return resolve();
      const child = worker;
      child.once("exit", () => resolve());
      child.stdin.end();
      setTimeout(() => {
        if (child.exitCode === null) child.kill();
      }, 15000).unref();
    });
  // Download (once) → verify → wait for critical work → stop the core →
  // run the verified installer silently → it restarts the Launcher.
  const applyUpdate = async () => {
    try {
      if (offered) {
        update = {
          ...update,
          status: "DOWNLOADING",
          progress: { received: 0, total: offered.installer.size },
          reason: undefined,
          deferred: undefined,
        };
        await updates.download(fetch, offered, updateDir, (received, total) => {
          update = { ...update, progress: { received, total } };
        });
      }
      update = { ...update, status: "VERIFYING" };
      const installer = updates.verifiedInstaller(updateDir);
      if (
        installer.version !== update.version ||
        updates.compareVersions(installer.version, current) <= 0
      )
        throw new updates.UpdateError("DOWNGRADE_REJECTED");
      // Sync settles by itself: wait for it. Other work defers the install.
      for (let wait = 0; ; wait++) {
        const blocker = updates.installBlocker(
          await request("state").catch(() => null),
        );
        if (!blocker) break;
        if (blocker !== "SYNC_IN_PROGRESS" || wait >= 60) {
          update = { ...update, status: "READY", deferred: blocker };
          return;
        }
        update = { ...update, status: "WAITING", deferred: blocker };
        await sleep(1000);
      }
      update = { ...update, status: "INSTALLING", deferred: undefined };
      installing = true;
      await stopCore();
      // Re-hash at the last moment: the file run is the file signed.
      const final = updates.verifiedInstaller(updateDir);
      spawn(final.file, ["/S", "--updated", "--force-run"], {
        detached: true,
        stdio: "ignore",
        windowsHide: true,
      }).unref();
      app.quit();
    } catch (error) {
      update = {
        ...update,
        status: "ERROR",
        reason: error.code || "UPDATE_FAILED",
        progress: undefined,
      };
      if (installing) {
        // The core was stopped for an install that could not start: come
        // back as before rather than stay without it.
        app.relaunch();
        app.exit(0);
      }
    } finally {
      applying = null;
    }
  };
  ipcMain.handle("launcher:update-state", (event) => {
    authorize(event);
    return update;
  });
  ipcMain.handle("launcher:update-check", async (event) => {
    authorize(event);
    await checkFeed({ manual: true });
    return update;
  });
  ipcMain.handle("launcher:update-postpone", (event) => {
    authorize(event);
    if (
      update.version &&
      ["AVAILABLE", "READY", "ERROR"].includes(update.status)
    )
      updates.postpone(updateDir, update.version);
    update = { ...update, prompt: false };
    return update;
  });
  ipcMain.handle("launcher:update-apply", (event, ticket) => {
    authorize(event);
    if (
      !["AVAILABLE", "READY", "ERROR"].includes(update.status) ||
      !update.version
    )
      throw new Error("No hay ninguna actualización verificada.");
    confirmations.redeem(ticket, "update", update.version, [
      update.version,
      offered?.installer.sha512 ?? null,
    ]);
    if (!applying) applying = applyUpdate();
    return { ...update, status: offered ? "DOWNLOADING" : "VERIFYING" };
  });
  ipcMain.handle("launcher:confirm-begin", async (event, kind, target) => {
    authorize(event);
    if (
      typeof kind !== "string" ||
      typeof target !== "string" ||
      target.length > 128
    )
      throw new Error("Confirmación no válida");
    if (kind === "update") {
      // The popup is the confirmation; the ticket binds it to this signed offer.
      if (
        !["AVAILABLE", "READY", "ERROR"].includes(update.status) ||
        target !== update.version
      )
        throw new Error("No hay ninguna actualización verificada.");
      return {
        ticket: confirmations.issue("update", target, [
          target,
          offered?.installer.sha512 ?? null,
        ]),
      };
    }
    if (
      ![
        "write",
        "export",
        "restore",
        "transfer:prepare",
        "transfer:apply",
        "transfer:fulfil",
        "transfer:cancel",
      ].includes(kind)
    )
      throw new Error("Confirmación no válida");
    const state = await request("state");
    const offer = describe(kind, target, state);
    return {
      ...offer,
      ticket: confirmations.issue(
        kind,
        target,
        fingerprint(kind, target, state),
      ),
    };
  });

  tools.webContents.loadFile(path.join(__dirname, "index.html"), {
    query: { shell: "unified" },
  });
});
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => {
  if (worker) {
    worker.stdin.end();
    const child = worker;
    setTimeout(() => {
      if (child.exitCode === null) child.kill();
    }, 20000).unref();
  }
});
