// Test double for window.launcher: fixed state, records requested actions.
const { contextBridge } = require("electron");
const calls = [];
let enabled = true;
const state = () => ({
  local_status: "READY",
  selected_save: "C:/fixture/main",
  cloud_status: "ONLINE",
  auth_status: "VERIFIED",
  principal: null,
  cloud: null,
  emulator: { primary_candidate: "Lime3DS" },
  emulator_saves: [{ path: "C:/fixture/main", emulator: "Lime3DS", game: "Y" }],
  quick_items: {
    application_enabled: enabled,
    items: {
      rare_candy: { count: 5, max: 999, addable: 994, name: "Caramelo Raro" },
      heart_scale: { count: 999, max: 999, addable: 0, name: "Escama Corazón" },
    },
  },
  quick_item_error: null,
  write: { status: "IDLE", busy: false, backups: [], can_confirm: false, can_reconcile: false },
});
contextBridge.exposeInMainWorld("launcher", {
  state: async () => state(),
  quickItems: async () => ({ status: "QUEUED" }),
  addQuickItem: async (...args) => (calls.push(args), { status: "QUEUED" }),
  discoverSaves: async () => ({ status: "DONE", count: 1 }),
  selectDiscovered: async (p) => (calls.push(["select", p]), { status: "QUEUED" }),
  updateState: async () => ({ status: "AVAILABLE", current: "0.22.0-rc.3", version: "0.23.0", notes: "Prueba", channel: "private" }),
  downloadUpdate: async () => ({ status: "DOWNLOADING" }),
  installUpdate: async () => ({ status: "DOWNLOADED", deferred: "WRITE_IN_PROGRESS" }),
  __calls: () => calls.map((c) => [...c]),
  __disable: () => {
    enabled = false;
  },
});
