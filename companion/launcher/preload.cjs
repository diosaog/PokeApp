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
  updateState: () => ipcRenderer.invoke("launcher:update-state"),
  downloadUpdate: () => ipcRenderer.invoke("launcher:update-download"),
  installUpdate: () => ipcRenderer.invoke("launcher:update-install"),
});
