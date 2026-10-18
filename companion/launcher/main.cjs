const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { createInterface } = require("node:readline");

const root = path.resolve(__dirname, "../..");
const entry = pathToFileURL(path.join(__dirname, "index.html")).href;
// User data survives per-user installation upgrades and uninstallation.
const profile =
  process.env.POKEAPP_LAUNCHER_PROFILE ||
  path.join(
    process.env.LOCALAPPDATA || app.getPath("appData"),
    "PokeApp",
    "Launcher",
  );
app.setPath("userData", path.join(profile, "shell"));
app.setAppUserModelId("app.pokeapp.launcher");
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
        { name: "Save Pokémon (incluye main de X/Y, ORAS y Sol/Luna/Ultrasol/Ultraluna)", extensions: ["*"] },
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
