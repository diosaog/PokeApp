// Screenshots of «Saves y Launcher» and every Launcher popup with synthetic
// data (2026-11-18 redesign). Real renderer, test preload; nothing is written
// to any save, account or server. Run with Electron (ELECTRON_RUN_AS_NODE unset):
//   electron tools/launcher_popups_preview/main.cjs <output dir>
const { app, BrowserWindow } = require("electron");
const fs = require("node:fs"),
  path = require("node:path"),
  os = require("node:os");
app.setPath(
  "userData",
  fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-popups-preview-")),
);
const out = path.resolve(process.argv.at(-1));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const mon = (species, nickname, level, extra = {}) => ({
  species,
  species_id: species,
  form: 0,
  nickname,
  level,
  ...extra,
});
const party = [
  mon(530, "Terremoto", 44),
  mon(36, "Leffa", 45),
  mon(73, "Pulpo Pol", 44),
  mon(350, "=(", 44),
  mon(711, "Jalowin", 44),
  mon(675, "Tripon", 44),
];
const fixture = {
  principal: { trainer_id: "fixture", display_name: "Anto" },
  auth_status: "VERIFIED",
  cloud_sync: true,
  observation: {
    game: "Y",
    generation: 6,
    trainer: { name: "Anto", tid: 12345 },
    party,
    boxes: [],
  },
  training: {
    application_enabled: true,
    items: [
      { purchase_id: "a0000000-0000-4000-8000-000000000001", item_code: "menta_naturaleza", name: "Menta de Naturaleza", effect: "nature" },
      { purchase_id: "a0000000-0000-4000-8000-000000000002", item_code: "chapa_plateada", name: "Chapa Plateada", effect: "iv" },
    ],
    targets: party.slice(0, 5).map((p, i) => ({
      pokemon_entity_id: `b0000000-0000-4000-8000-00000000000${i}`,
      source_sha256: "a".repeat(64),
      game: "Y",
      source: "party",
      slot_number: i + 1,
      pokemon: { ...p, nature_id: [0, 15, 3, 13, 10][i], ivs: { hp: 31, atk: 14, defense: 4, spa: 13, spd: 12, spe: 29 } },
    })),
    operations: [],
  },
  training_seq: 1,
  friendship: {
    application_enabled: true,
    party: party.map((p, i) => ({ slot_index: i, ...p, friendship: [70, 255, 120, 33, 200, 90][i], eligible: true, pokemon_sha256: String(i).repeat(64) })),
    boxes: [
      { box_index: 0, slot_index: 0, ...mon(448, "Aura", 40), friendship: 50, eligible: true, pokemon_sha256: "7".repeat(64) },
      { box_index: 0, slot_index: 3, ...mon(6, "", 45), friendship: 120, eligible: true, pokemon_sha256: "8".repeat(64) },
    ],
  },
  friendship_seq: 1,
  revive: {
    application_enabled: true,
    in_sync: true,
    free_slot: true,
    purchases: ["d0000000-0000-4000-8000-000000000001"],
    dead_box_number: 7,
    candidates: [
      { pokemon_entity_id: "e1", ...mon(530, "Terremoto", 44), slot_number: 1 },
      { pokemon_entity_id: "e2", ...mon(149, "Dragoncito", 52), slot_number: 2 },
      { pokemon_entity_id: "e3", ...mon(94, "", 40), slot_number: 3 },
    ],
  },
  revive_seq: 1,
  write: { status: "IDLE", busy: false, idle: true, can_confirm: false, backups: [], transfer_application_enabled: true },
};
const steps = [
  ["hub", `window.launcher.__navigateTo({ view: 'panel', tab: 'partidas' });`],
  ["hub-launcher-tab", `document.getElementById('cloud-tab').click();`],
  ["training-pokemon", `document.getElementById('save-tab').click(); window.launcher.__navigateTo({ view: 'modal', panel: 'entrenamiento', item: 'menta_naturaleza' });`],
  ["training-natures", `[...document.getElementById('training-body').querySelectorAll('button')][0].click();`],
  ["training-nature-confirm", `[...document.querySelectorAll('.training-nature')].find(b => b.querySelector('strong').textContent === 'Modesta').click();`],
  ["training-ivs", `closeDialogs(); window.launcher.__navigateTo({ view: 'modal', panel: 'entrenamiento', item: 'chapa_plateada' });`, `[...document.getElementById('training-body').querySelectorAll('button')][0].click();`],
  ["felicidad", `closeDialogs(); window.launcher.__navigateTo({ view: 'modal', panel: 'felicidad' });`],
  ["revivir", `closeDialogs(); window.launcher.__navigateTo({ view: 'modal', panel: 'revivir' });`],
  ["objetos", `closeDialogs(); window.launcher.__navigateTo({ view: 'modal', panel: 'objetos' });`],
  ["robos", `closeDialogs(); window.launcher.__navigateTo({ view: 'modal', panel: 'robos' });`],
];
app.whenReady().then(async () => {
  const win = new BrowserWindow({
    show: false,
    width: 1280,
    height: 860,
    webPreferences: {
      preload: path.resolve(__dirname, "../launcher_ui_smoke/preload.cjs"),
      contextIsolation: true,
      sandbox: false,
      backgroundThrottling: false,
      offscreen: true,
    },
  });
  win.webContents.session.protocol.handle("https", (request) => {
    const match = /\/visuals\/v1\/pokemon\/([0-9a-z-]+\.png)$/.exec(request.url);
    const file = match && path.resolve(__dirname, "../../web/public/visuals/v1/pokemon", match[1]);
    if (!file || !fs.existsSync(file)) return new Response(null, { status: 404 });
    return new Response(fs.readFileSync(file), { headers: { "content-type": "image/png" } });
  });
  const errors = [];
  win.webContents.on("console-message", (_e, _l, message) => {
    if (message.startsWith("Uncaught")) errors.push(message);
  });
  try {
    fs.mkdirSync(out, { recursive: true });
    await win.loadFile(path.resolve(__dirname, "../../companion/launcher/index.html"));
    await sleep(1200);
    await win.webContents.executeJavaScript(
      `window.launcher.__setUpdate({ status: 'UP_TO_DATE', current: '0.26.17', channel: 'stable', prompt: false }); closeDialogs(); window.launcher.__set(${JSON.stringify(fixture)}); true`,
    );
    await sleep(1400);
    for (const [label, ...codes] of steps) {
      for (const code of codes) {
        await win.webContents.executeJavaScript(`${code}; true`);
        await sleep(700);
      }
      await sleep(600);
      win.webContents.invalidate();
      await sleep(300);
      fs.writeFileSync(path.join(out, `${label}.png`), (await win.webContents.capturePage()).toPNG());
      console.log("captured", label);
    }
    console.log(errors.length ? "ERRORS " + errors.join(" | ") : "no renderer errors");
    app.exit(errors.length ? 1 : 0);
  } catch (error) {
    console.error(error);
    app.exit(1);
  }
});
