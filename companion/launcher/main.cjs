const { app, BrowserWindow, ipcMain, dialog } = require("electron");
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
  sequence = 0;
const pending = new Map();
function request(command, args = {}) {
  if (!worker || worker.killed || pending.size >= 8)
    return Promise.reject(new Error("Launcher no disponible"));
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
function authorize(event) {
  if (
    !win ||
    event.sender !== win.webContents ||
    event.senderFrame !== win.webContents.mainFrame ||
    event.senderFrame.url !== entry
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
      title: "Guardar copia original",
      buttonLabel: "Guardar copia",
      defaultPath: `PokeApp-${backup.game}-${operationId.slice(0, 8)}-${role}.sav`,
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
  win = new BrowserWindow({
    show: process.env.POKEAPP_LAUNCHER_HEADLESS_TEST !== "1",
    width: 1120,
    height: 820,
    minWidth: 720,
    minHeight: 600,
    backgroundColor: "#101916",
    icon: path.join(__dirname, "assets/icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event) => event.preventDefault());
  win.webContents.session.setPermissionRequestHandler(
    (_webContents, _permission, callback) => callback(false),
  );
  win.loadFile(path.join(__dirname, "index.html"));
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
