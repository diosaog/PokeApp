const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("launcher", {
  state: (revision) => ipcRenderer.invoke("launcher:state", revision),
  chooseSave: () => ipcRenderer.invoke("launcher:select"),
  login: (trainer, pin) => ipcRenderer.invoke("launcher:login", trainer, pin),
  logout: () => ipcRenderer.invoke("launcher:logout"),
  retry: () => ipcRenderer.invoke("launcher:retry"),
  sync: () => ipcRenderer.invoke("launcher:sync"),
  confirmWrite: (operationId, emulatorClosed) =>
    ipcRenderer.invoke("launcher:write-confirm", operationId, emulatorClosed),
  reconcileWrite: () => ipcRenderer.invoke("launcher:write-reconcile"),
  exportSave: (emulatorClosed) =>
    ipcRenderer.invoke("launcher:export", emulatorClosed),
  backups: () => ipcRenderer.invoke("launcher:backups"),
  saveBackup: (operationId, role) =>
    ipcRenderer.invoke("launcher:backup-copy", operationId, role),
  restoreBackup: (operationId, emulatorClosed) =>
    ipcRenderer.invoke("launcher:backup-restore", operationId, emulatorClosed),
  quickItems: () => ipcRenderer.invoke("launcher:quick-items"),
  addQuickItem: (item, quantity, emulatorClosed) =>
    ipcRenderer.invoke(
      "launcher:quick-item-add",
      item,
      quantity,
      emulatorClosed,
    ),
  transfer: (kind, authorizationId, emulatorClosed) =>
    ipcRenderer.invoke(
      "launcher:transfer",
      kind,
      authorizationId,
      emulatorClosed,
    ),
  discoverSaves: () => ipcRenderer.invoke("launcher:discover"),
  selectDiscovered: (savePath) =>
    ipcRenderer.invoke("launcher:select-discovered", savePath),
  showWeb: (show, top) => ipcRenderer.invoke("launcher:show-web", show, top),
  // Unified shell (27C): the strip height this page needs, and the way back.
  layout: (height) => ipcRenderer.invoke("launcher:layout", height),
  closePanel: () => ipcRenderer.invoke("launcher:panel-close"),
  onNavigate: (callback) =>
    ipcRenderer.on("launcher:navigate", (_event, message) => {
      // Only a known view, panel and item code ever reach the page.
      const items = ["rare_candy", "heart_scale"];
      const panels = ["partida", "objetos", "robos", "copias", "nube"];
      if (message?.view === "quick-items" && items.includes(message.item))
        callback({ view: "quick-items", item: message.item });
      else if (message?.view === "panel" && panels.includes(message.panel))
        callback({
          view: "panel",
          panel: message.panel,
          item: items.includes(message.item) ? message.item : undefined,
        });
      else if (message?.view === "strip" || message?.view === "offline")
        callback({ view: message.view });
    }),
  updateState: () => ipcRenderer.invoke("launcher:update-state"),
  downloadUpdate: () => ipcRenderer.invoke("launcher:update-download"),
  installUpdate: () => ipcRenderer.invoke("launcher:update-install"),
});
