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
});
