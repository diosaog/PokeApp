// Test double for window.launcher: fixed state, records requested actions.
const { contextBridge } = require("electron");
const calls = [];
let enabled = true;
let navigate = null;
let overrides = {};
let discoverReply = { status: "DONE", count: 1 };
let updateInfo = {
  status: "AVAILABLE",
  current: "0.22.0-rc.3",
  version: "0.23.0",
  notes: "Prueba",
  channel: "private",
  prompt: true,
};
const base = () => ({
  local_status: "READY",
  selected_save: "C:/fixture/main",
  cloud_status: "ONLINE",
  auth_status: "VERIFIED",
  principal: null,
  receipt_id: "r1",
  observation: {
    game: "Y",
    generation: 6,
    trainer: { name: "Test", tid: 1 },
    party: [],
    boxes: [{ slots: [null, { nickname: "Pikachu", species_id: 25 }] }],
  },
  cloud: {
    data: {
      transfers: [
        {
          authorization_id: "a".repeat(36),
          side: "destination",
          status: "PENDING_SOURCE",
          planned: true,
          claimed: true,
          apply_started: false,
          verified: false,
          location: { box: 2, slot: 5 },
        },
        {
          authorization_id: "b".repeat(36),
          side: "source",
          status: "PENDING_SOURCE",
          planned: true,
          claimed: true,
          apply_started: false,
          verified: false,
          location: { box: 1, slot: 2 },
        },
        {
          authorization_id: "c".repeat(36),
          side: "source",
          status: "VERIFYING_SOURCE",
          planned: true,
          claimed: true,
          apply_started: true,
          verified: false,
          location: { box: 1, slot: 2 },
        },
        {
          authorization_id: "d".repeat(36),
          side: "destination",
          status: "BLOCKED_UNCERTAIN",
          planned: true,
          claimed: true,
          apply_started: true,
          verified: false,
          location: null,
        },
        {
          authorization_id: "e".repeat(36),
          side: "destination",
          status: "COMMITTED",
          planned: false,
          claimed: true,
          apply_started: true,
          verified: true,
          location: null,
        },
        {
          authorization_id: "1".repeat(36),
          side: "source",
          status: "COMPETITIVELY_ADJUDICATED",
          obligation: "DONOR_PHYSICAL_PENDING",
          mandatory: true,
          planned: true,
          claimed: false,
          apply_started: false,
          verified: false,
          location: { box: 1, slot: 2 },
        },
        {
          authorization_id: "2".repeat(36),
          side: "destination",
          status: "COMPETITIVELY_ADJUDICATED",
          obligation: "RECIPIENT_PHYSICAL_PENDING",
          mandatory: false,
          planned: true,
          claimed: false,
          apply_started: false,
          verified: false,
          location: { box: 3, slot: 1 },
        },
      ],
    },
  },
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
  // 072: paid Shop objects waiting for the bag of a Pokémon Y save.
  deliveries: {
    save_game: "Y",
    league_game: "Y",
    application_enabled: enabled,
    items: [
      {
        purchase_id: "c0000000-0000-4000-8000-000000000001",
        name: "Objeto Evolutivo",
        mode: "choice",
        state: "READY",
        options: [
          { code: "fire_stone", name: "Piedra Fuego", compatible: true },
          { code: "ice_stone", name: "Piedra Hielo", compatible: false },
          { code: "dusk_stone", name: "Piedra Noche", compatible: true },
        ],
      },
      {
        purchase_id: "c0000000-0000-4000-8000-000000000002",
        name: "Chapa Plateada",
        mode: "bag",
        state: "READY",
        options: [{ code: "bottle_cap", name: "Chapa Plateada", compatible: false }],
      },
      {
        purchase_id: "c0000000-0000-4000-8000-000000000003",
        name: "Lupa",
        mode: "bag",
        state: "READY",
        options: [{ code: "zoom_lens", name: "Telescopio", compatible: true }],
      },
      {
        purchase_id: "c0000000-0000-4000-8000-000000000004",
        name: "Restos",
        mode: "bag",
        state: "ELSEWHERE",
        options: [{ code: "leftovers", name: "Restos", compatible: true }],
      },
    ],
  },
  write: {
    status: "IDLE",
    busy: false,
    backups: [
      {
        operation_id: "f".repeat(36),
        role: "original",
        game: "Y",
        created_at: "2026-10-26T10:00:00+00:00",
        verified: true,
        status: "APPLIED_VERIFIED",
        beside_save: "REMOVED",
        can_restore: true,
      },
      {
        operation_id: "9".repeat(36),
        role: "daily",
        date: "2026-10-25",
        game: "Y",
        created_at: "2026-10-25T08:00:00+00:00",
        verified: true,
        status: "DAILY",
        beside_save: null,
        can_restore: false,
      },
    ],
    can_confirm: false,
    can_reconcile: false,
    transfer_application_enabled: enabled,
  },
});
const state = () => ({ ...base(), ...overrides });
// The supervised core's own status; while it is not READY, state() fails
// like the real IPC does.
let core = { status: "READY", message: "", stalled: false };
contextBridge.exposeInMainWorld("launcher", {
  state: async () => {
    if (core.status !== "READY") throw new Error(core.message);
    return state();
  },
  core: async () => core,
  coreRestart: async () => (calls.push(["coreRestart"]), core),
  copyDiagnostics: async () => (
    calls.push(["copyDiagnostics"]),
    { copied: true }
  ),
  __core: (snapshot) => {
    core = { stalled: false, ...snapshot };
  },
  quickItems: async () => ({ status: "QUEUED" }),
  deliveries: async () => (calls.push(["deliveries"]), { status: "QUEUED" }),
  addDelivery: async (...args) => (
    calls.push(["delivery", ...args]),
    { status: "QUEUED" }
  ),
  addQuickItem: async (...args) => (calls.push(args), { status: "QUEUED" }),
  transfer: async (...args) => (
    calls.push(["transfer", ...args]),
    { status: "QUEUED" }
  ),
  // Like the core: the search updates its own state before it answers.
  discoverSaves: async () => {
    if (discoverReply.saves)
      overrides = { ...overrides, emulator_saves: discoverReply.saves, discovery: discoverReply.discovery };
    return discoverReply;
  },
  __discover: (reply) => {
    discoverReply = reply;
  },
  webEvent: async (type) => (calls.push(["webEvent", type]), { sent: true }),
  chooseSave: async () => ({ status: "CANCELLED" }),
  retry: async () => ({ status: "QUEUED" }),
  selectDiscovered: async (p) => (
    calls.push(["select", p]),
    { status: "QUEUED" }
  ),
  showWeb: async (show, top) => (
    calls.push(["web", show, top > 0]),
    { shown: show }
  ),
  onNavigate: (callback) => {
    navigate = callback;
  },
  __navigate: (item) => navigate && navigate({ view: "quick-items", item }),
  __navigateTo: (message) => navigate && navigate(message),
  __set: (patch) => {
    overrides = { ...overrides, ...patch };
  },
  restoreBackup: async (...args) => (
    calls.push(["restore", ...args]),
    { status: "QUEUED" }
  ),
  backups: async () => ({ status: "QUEUED" }),
  // Main issues one ticket per action; here it simply names what it binds.
  confirmBegin: async (kind, target) => (
    calls.push(["begin", kind, target]),
    {
      ticket: "t:" + kind + ":" + target,
      title: "Confirmar",
      message:
        kind === "transfer:apply" ? "Aplicar tu parte del robo" : "Confirmar",
      detail: "",
      go: "Confirmar",
      facts: [["Juego", "Y (desde main)"]],
    }
  ),
  checkUpdate: async () => updateInfo,
  __setUpdate: (info) => {
    updateInfo = info;
  },
  __unset: (keys) => {
    overrides = Object.fromEntries(
      Object.entries(overrides).filter(([key]) => !keys.includes(key)),
    );
  },
  closePanel: async () => (calls.push(["closePanel"]), { closed: true }),
  present: async (view) => (calls.push(["present", view]), { shown: true }),
  openHub: async (tab) => (calls.push(["openHub", tab]), { shown: true }),
  updateState: async () => updateInfo,
  postponeUpdate: async () => (
    calls.push(["postpone"]),
    (updateInfo = { ...updateInfo, prompt: false })
  ),
  applyUpdate: async (ticket) => (
    calls.push(["apply", ticket]),
    { ...updateInfo, status: "DOWNLOADING" }
  ),
  __calls: () => calls.map((c) => [...c]),
  __disable: () => {
    enabled = false;
  },
  __enable: () => {
    enabled = true;
  },
});
