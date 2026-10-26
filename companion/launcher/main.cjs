const {
  app,
  BrowserWindow,
  WebContentsView,
  ipcMain,
  dialog,
  shell,
} = require("electron");
const webview = require("./webview.cjs");
const { spawn } = require("node:child_process");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { createInterface } = require("node:readline");
const privateCandidate =
  require("./package.json").pokeappPrivateCandidate === true;

const root = path.resolve(__dirname, "../..");
const entry = pathToFileURL(path.join(__dirname, "index.html")).href;
// User data survives per-user installation upgrades and uninstallation.
const profile =
  process.env.POKEAPP_LAUNCHER_PROFILE ||
  path.join(
    process.env.LOCALAPPDATA || app.getPath("appData"),
    "PokeApp",
    privateCandidate ? "Launcher-Private" : "Launcher",
  );
app.setPath("userData", path.join(profile, "shell"));
app.setAppUserModelId(
  privateCandidate ? "app.pokeapp.launcher.private" : "app.pokeapp.launcher",
);
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
    async (event, operationId, emulatorClosed) => {
      authorize(event);
      if (
        typeof operationId !== "string" ||
        operationId.length > 128 ||
        emulatorClosed !== true
      )
        throw new Error("Confirma que el juego y el emulador están cerrados.");
      const state = await request("state");
      if (
        !state.write?.can_confirm ||
        state.write.operation_id !== operationId ||
        !state.write.description
      )
        throw new Error("La acción ya no está pendiente de confirmación.");
      const confirmation = await dialog.showMessageBox(win, {
        type: "warning",
        title: "Confirmar cambio local",
        message: `${state.write.game} · ${state.write.description}`,
        detail: `${state.selected_save}\n\nEl juego y el emulador deben permanecer cerrados. Se conservará una copia del archivo original. No se consume ningún artículo.`,
        buttons: ["Cancelar", "Confirmar cambio"],
        defaultId: 0,
        cancelId: 0,
        noLink: true,
      });
      if (confirmation.response !== 1) return { status: "CANCELLED" };
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
    async (event, operationId, emulatorClosed) => {
      authorize(event);
      if (emulatorClosed !== true)
        throw new Error("Confirma que el juego y el emulador están cerrados.");
      const state = await request("state");
      const backup = state.write?.backups?.find(
        (b) =>
          b.operation_id === operationId &&
          b.role === "original" &&
          b.can_restore &&
          b.verified,
      );
      if (!backup || state.write.busy)
        throw new Error("Restauración no disponible.");
      const confirmation = await dialog.showMessageBox(win, {
        type: "warning",
        title: "Restaurar copia original",
        message: `${backup.game} · Recuperar los bytes originales`,
        detail:
          "Mantén el juego y el emulador cerrados hasta terminar. Un archivo externo distinto se conservará y bloqueará la restauración. Recuperar bytes no revierte compras ni recompensas.",
        buttons: ["Cancelar", "Restaurar copia"],
        defaultId: 0,
        cancelId: 0,
        noLink: true,
      });
      if (confirmation.response !== 1) return { status: "CANCELLED" };
      return request("backup_restore", {
        operation_id: operationId,
        closed_emulator_confirmed: true,
        restore_confirmed: true,
      });
    },
  );
  ipcMain.handle("launcher:export", async (event, emulatorClosed) => {
    authorize(event);
    if (emulatorClosed !== true)
      throw new Error("Confirma que el juego y el emulador están cerrados.");
    const state = await request("state");
    if (!state.write?.can_export || !state.write?.export_intent) {
      throw new Error("No hay una operación de exportación autorizada.");
    }
    const result = await dialog.showOpenDialog(win, {
      title: "Elegir carpeta para la copia del save",
      properties: ["openDirectory", "createDirectory"],
      buttonLabel: "Elegir carpeta",
    });
    if (result.canceled || !result.filePaths[0]) return { status: "CANCELLED" };
    const confirmation = await dialog.showMessageBox(win, {
      type: "warning",
      title: "Exportar copia validada",
      message:
        "Se creará un archivo nuevo y se conservará la partida original.",
      detail: `${state.selected_save}\n\nLa exportación no aplica cambios al archivo original ni consume recursos de Liga.`,
      buttons: ["Cancelar", "Exportar copia"],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
    });
    return confirmation.response !== 1
      ? { status: "CANCELLED" }
      : request("export_prepare", {
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
    panel = null,
    panelFromUrl = false,
    left = 0,
    offline = false;
  const layout = () => {
    const [width, height] = win.getContentSize();
    web.setBounds({
      x: 0,
      y: strip,
      width,
      height: Math.max(0, height - strip),
    });
    const x = offline ? 0 : left;
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
    panel = target.panel;
    panelFromUrl = fromUrl;
    left = await sidebarEdge();
    layout();
    tools.webContents.focus();
    tools.webContents.send("launcher:navigate", { view: "panel", ...target });
  };
  const closePanel = () => {
    panel = null;
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
  void webview.attach(web, {
    origin: webAt,
    version: app.getVersion(),
    openExternal: (url) => shell.openExternal(url),
    // Older webs link "Añadir a mi partida" to /__launcher/quick-items/<item>.
    onQuickItems: (item) => void openPanel({ panel: "objetos", item }, false),
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
  // The dialog explains the LOCAL effect; completion is the server's verdict.
  ipcMain.handle(
    "launcher:transfer",
    async (event, kind, authorizationId, emulatorClosed) => {
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
      if (kind === "cancel") {
        if (transfer.side !== "destination" || transfer.apply_started)
          throw new Error(
            "Solo quien solicitó el robo puede cancelarlo, y solo antes de aplicar.",
          );
        const answer = await dialog.showMessageBox(win, {
          type: "question",
          title: "Cancelar robo",
          message: "¿Cancelar este robo antes de aplicar ningún cambio?",
          detail:
            "No se modifica ninguna partida y el objeto no se consume. Las copias se conservan.",
          buttons: ["Volver", "Cancelar robo"],
          defaultId: 0,
          cancelId: 0,
          noLink: true,
        });
        if (answer.response !== 1) return { status: "NOT_CONFIRMED" };
        return request("transfer_cancel", args);
      }
      if (emulatorClosed !== true)
        throw new Error("Confirma que el juego y el emulador están cerrados.");
      if (kind === "fulfil") {
        if (!transfer.obligation)
          throw new Error("PokeApp aún no ha decidido.");
        const victim = transfer.side === "source";
        const answer = await dialog.showMessageBox(win, {
          type: "warning",
          title: victim ? "Sincronización obligatoria" : "Recibir Pokémon",
          message: victim
            ? "Retirar de tu partida el Pokémon robado"
            : "Añadir a tu partida el Pokémon robado",
          detail: `${state.selected_save}\n\nEl robo ya está decidido por PokeApp. ${victim ? "Se retirará el Pokémon de tu partida actual" : "Se añadirá el Pokémon a tu partida actual"} con copia verificada, confirmación y verificación independiente. Si tu partida cambió desde la decisión, PokeApp recalculará tu parte sin modificar nada todavía.\n\nMantén el juego y el emulador cerrados hasta que termine.`,
          buttons: ["Cancelar", victim ? "Retirar ahora" : "Recibir ahora"],
          defaultId: 0,
          cancelId: 0,
          noLink: true,
        });
        if (answer.response !== 1) return { status: "NOT_CONFIRMED" };
        return request("transfer_fulfil", {
          ...args,
          closed_emulator_confirmed: true,
        });
      }
      const where = transfer.location
        ? `Caja ${transfer.location.box}, posición ${transfer.location.slot}`
        : "la posición indicada por PokeApp";
      const effect =
        kind === "prepare"
          ? "Se creará y comprobará una copia completa de tu partida. Todavía no se modifica nada."
          : transfer.side === "source"
            ? `Se retirará de tu partida el Pokémon de la ${where}.`
            : `Se añadirá a tu partida el Pokémon robado en la ${where}.`;
      const answer = await dialog.showMessageBox(win, {
        type: "warning",
        title:
          kind === "prepare"
            ? "Preparar copia para el robo"
            : "Aplicar tu parte",
        message:
          kind === "prepare"
            ? "Preparar copia verificada"
            : "Aplicar tu parte del robo",
        detail: `${state.selected_save}\n\n${effect} El robo solo es definitivo cuando PokeApp verifica las dos partidas.\n\nMantén el juego y el emulador cerrados hasta que termine.`,
        buttons: [
          "Cancelar",
          kind === "prepare" ? "Preparar copia" : "Aplicar mi parte",
        ],
        defaultId: 0,
        cancelId: 0,
        noLink: true,
      });
      if (answer.response !== 1) return { status: "NOT_CONFIRMED" };
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
  let update = {
    status: "DISABLED",
    current: app.getVersion(),
    channel,
    reason: "UPDATES_NOT_CONFIGURED",
  };
  let offered = null;
  if (
    updateConfig.publicKey &&
    typeof feed === "string" &&
    feed.startsWith("https://")
  ) {
    const recovered = updates.reconcileStartup(updateDir, app.getVersion());
    update = {
      status:
        recovered.status === "INSTALL_INCOMPLETE" ? "DOWNLOADED" : "CHECKING",
      current: app.getVersion(),
      channel,
      recovered,
    };
    fetch(feed, { redirect: "error" })
      .then((response) =>
        response.ok ? response.json() : Promise.reject(new Error("feed")),
      )
      .then((envelope) => {
        offered = updates.verifyManifest(envelope, updateConfig.publicKey, {
          channel,
          currentVersion: app.getVersion(),
        });
        if (update.status !== "DOWNLOADED")
          update = offered
            ? {
                ...update,
                status: "AVAILABLE",
                version: offered.version,
                notes: offered.notes,
              }
            : { ...update, status: "UP_TO_DATE" };
      })
      .catch((error) => {
        update = {
          ...update,
          status: "ERROR",
          reason: error.code || "UPDATE_CHECK_FAILED",
        };
      });
  }
  ipcMain.handle("launcher:update-state", (event) => {
    authorize(event);
    return update;
  });
  ipcMain.handle("launcher:update-download", async (event) => {
    authorize(event);
    if (!offered || update.status !== "AVAILABLE") return update;
    update = { ...update, status: "DOWNLOADING" };
    try {
      await updates.download(fetch, offered, updateDir);
      update = { ...update, status: "DOWNLOADED" };
    } catch (error) {
      update = {
        ...update,
        status: "AVAILABLE",
        reason: error.code || "DOWNLOAD_FAILED",
      };
    }
    return update;
  });
  ipcMain.handle("launcher:update-install", async (event) => {
    authorize(event);
    if (update.status !== "DOWNLOADED") return update;
    const blocker = updates.installBlocker(
      await request("state").catch(() => null),
    );
    if (blocker) return { ...update, deferred: blocker };
    const installer = updates.verifiedInstaller(updateDir);
    const confirmation = await dialog.showMessageBox(win, {
      type: "info",
      title: "Instalar actualización",
      message: `PokeApp Launcher ${installer.version}`,
      detail:
        "El Launcher se cerrará, se instalará la nueva versión y volverá a abrirse. Tus copias, sesión y operaciones se conservan.",
      buttons: ["Más tarde", "Instalar y reiniciar"],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
    });
    if (confirmation.response !== 1) return update;
    const last = updates.installBlocker(
      await request("state").catch(() => null),
    );
    if (last) return { ...update, deferred: last };
    installing = true;
    spawn(installer.file, ["/S", "--force-run"], {
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    }).unref();
    app.quit();
    return { ...update, status: "INSTALLING" };
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
