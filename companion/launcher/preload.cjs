const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("launcher", {
  state: (revision) => ipcRenderer.invoke("launcher:state", revision),
  chooseSave: () => ipcRenderer.invoke("launcher:select"),
  login: (trainer, pin) => ipcRenderer.invoke("launcher:login", trainer, pin),
  logout: () => ipcRenderer.invoke("launcher:logout"),
  retry: () => ipcRenderer.invoke("launcher:retry"),
  sync: () => ipcRenderer.invoke("launcher:sync"),
  confirmBegin: (kind, target) =>
    ipcRenderer.invoke("launcher:confirm-begin", kind, target),
  confirmWrite: (operationId, emulatorClosed, ticket) =>
    ipcRenderer.invoke(
      "launcher:write-confirm",
      operationId,
      emulatorClosed,
      ticket,
    ),
  reconcileWrite: () => ipcRenderer.invoke("launcher:write-reconcile"),
  exportSave: (emulatorClosed, ticket) =>
    ipcRenderer.invoke("launcher:export", emulatorClosed, ticket),
  backups: () => ipcRenderer.invoke("launcher:backups"),
  saveBackup: (operationId, role) =>
    ipcRenderer.invoke("launcher:backup-copy", operationId, role),
  restoreBackup: (operationId, emulatorClosed, typed, ticket) =>
    ipcRenderer.invoke(
      "launcher:backup-restore",
      operationId,
      emulatorClosed,
      typed,
      ticket,
    ),
  quickItems: () => ipcRenderer.invoke("launcher:quick-items"),
  addQuickItem: (item, quantity, emulatorClosed) =>
    ipcRenderer.invoke(
      "launcher:quick-item-add",
      item,
      quantity,
      emulatorClosed,
    ),
  transfer: (kind, authorizationId, emulatorClosed, ticket) =>
    ipcRenderer.invoke(
      "launcher:transfer",
      kind,
      authorizationId,
      emulatorClosed,
      ticket,
    ),
  discoverSaves: () => ipcRenderer.invoke("launcher:discover"),
  selectDiscovered: (savePath) =>
    ipcRenderer.invoke("launcher:select-discovered", savePath),
  showWeb: (show, top) => ipcRenderer.invoke("launcher:show-web", show, top),
  // Unified shell (27C): the strip height this page needs, and the way back.
  layout: (height) => ipcRenderer.invoke("launcher:layout", height),
  closePanel: () => ipcRenderer.invoke("launcher:panel-close"),
  present: (view) => ipcRenderer.invoke("launcher:present", view),
  openHub: (tab) => ipcRenderer.invoke("launcher:open-hub", tab),
  checkUpdate: () => ipcRenderer.invoke("launcher:update-check"),
  onNavigate: (callback) =>
    ipcRenderer.on("launcher:navigate", (_event, message) => {
      // Only a known view, panel and item code ever reach the page.
      const items = ["rare_candy", "heart_scale"];
      const panels = ["saves"];
      const tabs = ["partidas", "copias", "launcher"];
      const modals = ["objetos", "robos", "selector", "update", "restore"];
      if (message?.view === "quick-items" && items.includes(message.item))
        callback({ view: "quick-items", item: message.item });
      else if (message?.view === "panel" && panels.includes(message.panel))
        callback({
          view: "panel",
          panel: message.panel,
          tab: tabs.includes(message.tab) ? message.tab : undefined,
        });
      else if (message?.view === "modal" && modals.includes(message.panel))
        callback({
          view: "modal",
          panel: message.panel,
          item: items.includes(message.item) ? message.item : undefined,
        });
      else if (message?.view === "strip" || message?.view === "offline")
        callback({ view: message.view });
    }),
  updateState: () => ipcRenderer.invoke("launcher:update-state"),
  downloadUpdate: () => ipcRenderer.invoke("launcher:update-download"),
  installUpdate: (ticket) =>
    ipcRenderer.invoke("launcher:update-install", ticket),
});
