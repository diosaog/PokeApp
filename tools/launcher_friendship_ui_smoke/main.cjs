// «Felicidad máxima» dialog (2026-11-12): the party and every PC box, grouped,
// filterable and searchable; one confirmation bound to the exact place and
// bytes. Real renderer, test double for window.launcher: no account, save,
// network or write. Optional evidence: POKEAPP_FRIENDSHIP_UI_EVIDENCE=<dir>.
const { app, BrowserWindow, ipcMain } = require("electron");
const fs = require("node:fs"),
  path = require("node:path"),
  os = require("node:os");
app.setPath(
  "userData",
  fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-friendship-ui-")),
);
const script = `(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms)), results = [];
  const check = (ok, label) => { results.push([Boolean(ok), label]); if (!ok) throw new Error(label); };
  const h = c => c.repeat(64);
  const fixture = {
    application_enabled: true, game: 'Y', source_sha256: h('0'),
    party: [
      { slot_index: 0, species: 445, form: 0, nickname: 'Tiburón', level: 52, friendship: 70, eligible: true, pokemon_sha256: h('1') },
      { slot_index: 1, species: 25, form: 0, nickname: 'Pikachu', level: 30, friendship: 255, eligible: true, pokemon_sha256: h('2') },
      { slot_index: 2, species: 175, form: 0, nickname: '', level: 0, friendship: 0, eligible: false, pokemon_sha256: h('3') },
    ],
    boxes: [
      { box_index: 0, slot_index: 0, species: 448, form: 0, nickname: 'Aura', level: 40, friendship: 50, eligible: true, pokemon_sha256: h('4') },
      { box_index: 0, slot_index: 3, species: 6, form: 0, nickname: 'Charizard', level: 45, friendship: 120, eligible: true, pokemon_sha256: h('5') },
      { box_index: 0, slot_index: 7, species: 175, form: 0, nickname: '', level: 0, friendship: 0, eligible: false, pokemon_sha256: h('6') },
      { box_index: 4, slot_index: 17, species: 149, form: 0, nickname: 'Lejos', level: 61, friendship: 33, eligible: true, pokemon_sha256: h('7') },
      { box_index: 30, slot_index: 29, species: 133, form: 0, nickname: 'Eevee', level: 12, friendship: 255, eligible: true, pokemon_sha256: h('8') },
    ],
  };
  const q = id => document.getElementById(id);
  const rows = () => [...q('friendship-party').querySelectorAll('.friendship-row')];
  const groups = () => [...q('friendship-party').querySelectorAll('.friendship-group')].map(g => g.firstChild.textContent);
  const rowFor = name => rows().find(r => r.querySelector('strong').textContent === name);
  const filter = (id, value) => { const el = q(id); if (el.type === 'checkbox') el.checked = value; else el.value = value; el.dispatchEvent(new Event(el.tagName === 'SELECT' || el.type === 'checkbox' ? 'change' : 'input')); };
  await sleep(1200);
  window.launcher.__setUpdate({ status: 'UP_TO_DATE', current: '0.26.15', channel: 'stable', prompt: false });
  closeDialogs();
  window.launcher.__set({ friendship: fixture, friendship_seq: 1, friendship_error: null, friendship_result: null, write: { status: 'IDLE', busy: false, idle: true, can_confirm: false, backups: [] } });
  await sleep(1300);
  window.launcher.__navigateTo({ view: 'modal', panel: 'felicidad' }); await sleep(1300);
  check(q('sheet-dialog').open && q('sheet-title').textContent === 'Felicidad máxima', 'Inventory route opens the Felicidad máxima sheet');
  check(window.launcher.__calls().some(c => c[0] === 'friendship'), 'opening the sheet reads the party and the boxes');
  check(rows().length === 6, 'six eligible Pokémon: two eggs are never offered');
  check(JSON.stringify(groups()) === JSON.stringify(['Equipo', 'Caja 1', 'Caja 5', 'Caja 31']), 'grouped by place: party first, then every box in order');
  check(/Aura/.test(rowFor('Aura').textContent) && /Lucario · Nv\\. 40/.test(rowFor('Aura').textContent) && /Caja 1 · 1/.test(rowFor('Aura').textContent) && /Felicidad 50/.test(rowFor('Aura').textContent) && rowFor('Aura').querySelector('img.friendship-sprite').src.endsWith('/pokemon/448.png'), 'a Box 1 Pokémon shows sprite, nickname, species, level, place and friendship');
  check(/Caja 5 · 18/.test(rowFor('Lejos').textContent) && /Caja 31 · 30/.test(rowFor('Eevee').textContent) && /Equipo · 1/.test(rowFor('Tiburón').textContent), 'later boxes and the party name their exact place');
  check(rowFor('Eevee').querySelector('button').disabled && /Ya está al máximo/.test(rowFor('Eevee').textContent) && !rowFor('Lejos').querySelector('button').disabled, 'a Pokémon already at 255 cannot be chosen; the others can');
  check(/6 Pokémon en tu equipo y tus cajas/.test(q('friendship-count').textContent), 'the count covers party and boxes');
  check([...q('friendship-place').options].map(o => o.textContent).join('|') === 'Equipo y cajas (6)|Equipo (2)|Caja 1 (2)|Caja 5 (1)|Caja 31 (1)', 'the place filter lists the party and each box with Pokémon');
  await window.launcher.__friendshipCapture('friendship-all');
  filter('friendship-place', 'box:4');
  check(rows().length === 1 && rowFor('Lejos') && JSON.stringify(groups()) === '["Caja 5"]', 'filter by one box');
  filter('friendship-place', 'party');
  check(rows().length === 2 && JSON.stringify(groups()) === '["Equipo"]', 'filter by the party');
  filter('friendship-place', 'all'); filter('friendship-search', 'lucario');
  check(rows().length === 1 && rowFor('Aura'), 'search by species name');
  filter('friendship-search', 'TIBURON');
  check(rows().length === 1 && rowFor('Tiburón'), 'search by nickname ignores case and accents');
  filter('friendship-search', 'mew');
  check(rows().length === 0 && /Ningún Pokémon coincide/.test(q('friendship-party').textContent) && /Mostrando 0 de 6/.test(q('friendship-count').textContent), 'no match explains itself');
  filter('friendship-search', ''); filter('friendship-hide-max', true);
  check(rows().length === 4 && !rowFor('Eevee') && !rowFor('Pikachu'), 'hide the ones already at 255');
  filter('friendship-hide-max', false);
  rowFor('Lejos').querySelector('button').click(); await sleep(300);
  check(window.launcher.__calls().some(c => c[0] === 'begin' && c[1] === 'friendship' && c[2] === 'box:4:17:' + h('7')), 'confirmation is bound to Box 5 slot 18 and that Pokémon\\'s exact bytes');
  check(q('confirm-dialog').open, 'the in-app confirmation opens');
  q('confirm-go').click(); await sleep(300);
  const applied = window.launcher.__calls().filter(c => c[0] === 'friendship-apply');
  check(applied.length === 1 && JSON.stringify(applied[0].slice(1)) === JSON.stringify(['box', 4, 17, h('7'), 't:friendship:box:4:17:' + h('7')]), 'one application for that box Pokémon, never moved to the party');
  check(/Subiendo la felicidad/.test(q('friendship-state').textContent) && rows().every(r => r.querySelector('button').disabled), 'while it applies every button waits');
  const raised = { ...fixture, boxes: fixture.boxes.map(m => m.box_index === 4 ? { ...m, friendship: 255, pokemon_sha256: h('9') } : m) };
  window.launcher.__set({ friendship: raised, friendship_seq: 2, friendship_result: { location: 'box', box_index: 4, slot_index: 17, friendship: 255, readback_verified: true, game: 'Y', at: 100 } });
  await sleep(1800);
  check(/felicidad 255 comprobada/.test(q('friendship-state').textContent) && /Felicidad 255/.test(rowFor('Lejos').textContent) && rowFor('Lejos').querySelector('button').disabled, 'the verified re-read shows 255 in the same box');
  await window.launcher.__friendshipCapture('friendship-done');
  rowFor('Tiburón').querySelector('button').click(); await sleep(300);
  check(window.launcher.__calls().some(c => c[0] === 'begin' && c[2] === 'party:0:' + h('1')), 'a party Pokémon is confirmed by its party slot');
  q('confirm-dialog').querySelector('[data-close]')?.click(); await sleep(200);
  check(window.launcher.__calls().filter(c => c[0] === 'friendship-apply').length === 1, 'stepping back writes nothing');
  closeDialogs();
  return results;
})()`;
app.whenReady().then(async () => {
  const win = new BrowserWindow({
    show: false,
    width: 1000,
    height: 900,
    webPreferences: {
      preload: path.resolve(__dirname, "../launcher_ui_smoke/preload.cjs"),
      contextIsolation: true,
      sandbox: false,
      backgroundThrottling: false,
      offscreen: true,
    },
  });
  const errors = [];
  // Sprites come from the repository's own public assets, never the network.
  win.webContents.session.protocol.handle("https", (request) => {
    const match =
      /^https:\/\/pokeapp-web\.pokeapp-v2\.workers\.dev\/visuals\/v1\/pokemon\/(\d+)\.png$/.exec(
        request.url,
      );
    const file =
      match &&
      path.resolve(
        __dirname,
        `../../web/public/visuals/v1/pokemon/${match[1]}.png`,
      );
    if (!file || !fs.existsSync(file))
      return new Response(null, { status: 404 });
    return new Response(fs.readFileSync(file), {
      headers: { "content-type": "image/png" },
    });
  });
  ipcMain.handle("smoke:friendship-capture", async (event, label) => {
    if (
      event.sender !== win.webContents ||
      !["friendship-all", "friendship-done"].includes(label)
    )
      throw new Error("Invalid fixture capture");
    if (!process.env.POKEAPP_FRIENDSHIP_UI_EVIDENCE) return;
    fs.mkdirSync(process.env.POKEAPP_FRIENDSHIP_UI_EVIDENCE, {
      recursive: true,
    });
    await new Promise((resolve) => {
      win.webContents.once("paint", resolve);
      win.webContents.invalidate();
      setTimeout(resolve, 1500);
    });
    fs.writeFileSync(
      path.join(process.env.POKEAPP_FRIENDSHIP_UI_EVIDENCE, label + ".png"),
      (await win.webContents.capturePage()).toPNG(),
    );
  });
  win.webContents.on("console-message", (_event, _level, message) => {
    if (message.startsWith("Uncaught")) errors.push(message);
  });
  try {
    await win.loadFile(
      path.resolve(__dirname, "../../companion/launcher/index.html"),
    );
    const results = await win.webContents.executeJavaScript(script);
    results.push([errors.length === 0, "no uncaught renderer errors"]);
    for (const [pass, label] of results)
      console.log((pass ? "PASS " : "FAIL ") + label);
    app.exit(results.every(([pass]) => pass) ? 0 : 1);
  } catch (error) {
    console.error(error);
    app.exit(1);
  }
});
