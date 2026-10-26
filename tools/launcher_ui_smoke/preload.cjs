// Test double for window.launcher: fixed state, records requested actions.
const { contextBridge } = require("electron");
const calls = [];
let enabled = true;
let navigate = null;
const state = () => ({
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
contextBridge.exposeInMainWorld("launcher", {
  state: async () => state(),
  quickItems: async () => ({ status: "QUEUED" }),
  addQuickItem: async (...args) => (calls.push(args), { status: "QUEUED" }),
  transfer: async (...args) => (
    calls.push(["transfer", ...args]),
    { status: "QUEUED" }
  ),
  discoverSaves: async () => ({ status: "DONE", count: 1 }),
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
  updateState: async () => ({
    status: "AVAILABLE",
    current: "0.22.0-rc.3",
    version: "0.23.0",
    notes: "Prueba",
    channel: "private",
  }),
  downloadUpdate: async () => ({ status: "DOWNLOADING" }),
  installUpdate: async () => ({
    status: "DOWNLOADED",
    deferred: "WRITE_IN_PROGRESS",
  }),
  __calls: () => calls.map((c) => [...c]),
  __disable: () => {
    enabled = false;
  },
});
