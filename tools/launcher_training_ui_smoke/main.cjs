// Focused native wizard, no accounts/saves/network mutations; real renderer.
const { app, BrowserWindow, ipcMain } = require("electron");
const fs = require("node:fs"),
  path = require("node:path"),
  os = require("node:os");
app.setPath(
  "userData",
  fs.mkdtempSync(path.join(os.tmpdir(), "pokeapp-training-ui-")),
);
const script = `(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms)), results = [];
  const check = (ok, label) => { results.push([Boolean(ok), label]); if (!ok) throw new Error(label); };
  const purchase = 'a0000000-0000-4000-8000-000000000001', entity = 'b0000000-0000-4000-8000-000000000001';
  const mint = { purchase_id: purchase, item_code: 'menta_naturaleza', name: 'Menta de Naturaleza', effect: 'nature' };
  const silver = { purchase_id: 'a0000000-0000-4000-8000-000000000002', item_code: 'chapa_plateada', name: 'Chapa Plateada', effect: 'iv' };
  const gold = { purchase_id: 'a0000000-0000-4000-8000-000000000003', item_code: 'chapa_dorada', name: 'Chapa Dorada', effect: 'ivs' };
  const target = { pokemon_entity_id: entity, source_sha256: 'a'.repeat(64), game: 'Y', source: 'party', slot_number: 1, pokemon: { species: 'Pokémon #25', species_id: 25, nickname: 'Chispa', level: 14, nature_id: 0, ivs: { hp: 31, atk: 14, defense: 4, spa: 13, spd: 12, spe: 29 }, form: 0 } };
  let seq = 0;
  const fixture = { application_enabled: true, items: [mint, silver, gold], targets: [target], operations: [] };
  const q = id => document.getElementById(id);
  const buttons = () => [...q('training-body').querySelectorAll('button')];
  const choose = name => buttons().find(b => b.querySelector('strong')?.textContent === name);
  const applied = () => window.launcher.__calls().filter(c => c[0] === 'training-apply');
  const open = async code => { window.launcher.__navigateTo({ view: 'modal', panel: 'entrenamiento', item: code }); await sleep(150); };
  await sleep(1200);
  window.launcher.__setUpdate({ status: 'UP_TO_DATE', current: '0.26.9', channel: 'stable', prompt: false });
  closeDialogs();
  window.launcher.__set({ principal: { trainer_id: 'fixture-user', display_name: 'Prueba' }, training: fixture, training_seq: seq, training_error: null, write: { status: 'IDLE', busy: false, idle: true, can_confirm: false, backups: [] } });
  await sleep(1300);
  await open('menta_naturaleza');
  check(q('training-dialog').open && /1 · Elige/.test(q('training-step').textContent), 'Inventory Mint route opens directly at Pokémon selection');
  check(/Chispa/.test(q('training-body').textContent) && /Pikachu · Nv. 14/.test(q('training-body').textContent) && /Fuerte/.test(q('training-body').textContent) && q('training-body').querySelector('img').src.endsWith('/pokemon/25.png'), 'target shows actual nickname, species, level, nature and sprite');
  buttons()[0].click();
  check(buttons().length === 25 && choose('Fuerte').disabled && /Neutra/.test(choose('Dócil').textContent), 'all 25 natures, neutral included, current nature disabled');
  choose('Firme').click(); await sleep(150);
  check(/Fuerte → Firme/.test(q('training-body').textContent) && /naturaleza real/.test(q('training-body').textContent) && !q('training-confirm').disabled && applied().length === 0, 'Mint preview gives exact nature change and writes nothing');
  await window.launcher.__trainingCapture('mint-confirmation');
  q('training-back').click();
  check(buttons().length === 25 && applied().length === 0, 'Back returns to nature selection without consuming or writing');
  choose('Modesta').click(); await sleep(150); q('training-cancel').click();
  check(!q('training-dialog').open && applied().length === 0, 'Cancel final preview sends no application');
  await open('menta_naturaleza'); buttons()[0].click(); choose('Firme').click(); await sleep(150);
  q('training-confirm').click(); q('training-confirm').click(); await sleep(150);
  check(applied().length === 1 && applied()[0][1].purchase_id === purchase && applied()[0][1].pokemon_entity_id === entity && applied()[0][1].source_sha256 === target.source_sha256 && applied()[0][1].change.nature_id === 3, 'final double click dispatches exactly one bound Mint application');
  window.launcher.__set({ training_seq: ++seq, training_result: { status: 'APPLIED', purchase_id: purchase, at: 100 } }); await sleep(1500);
  check(window.launcher.__calls().some(c => c[0] === 'webEvent' && c[1] === 'items-changed') && window.launcher.__calls().some(c => c[0] === 'webEvent' && c[1] === 'save-changed'), 'verified success refreshes inventory and Pokémon views');
  q('training-cancel').click(); await open('chapa_plateada'); buttons()[0].click();
  check(buttons().length === 6 && choose('PS').disabled && /31 · Ya está al máximo/.test(choose('PS').textContent) && /14 → 31/.test(choose('Ataque').textContent), 'Silver lists six actual IVs and disables maxed IV');
  choose('Ataque').click(); await sleep(150);
  check(/Ataque: 14 → 31/.test(q('training-body').textContent) && /Poder Oculto/.test(q('training-body').textContent) && q('training-body').querySelectorAll('tbody tr').length === 6, 'Silver final preview names one IV and warns about Hidden Power');
  await window.launcher.__trainingCapture('silver-confirmation');
  q('training-confirm').click(); await sleep(150);
  check(applied().length === 2 && JSON.stringify(applied()[1][1].change) === JSON.stringify({ kind: 'iv', stat: 'atk' }), 'Silver confirms only the selected stat');
  window.launcher.__set({ training_seq: ++seq, training_result: { status: 'APPLIED', at: 101 } }); await sleep(1500);
  q('training-cancel').click(); await open('chapa_dorada'); buttons()[0].click(); await sleep(150);
  check(q('training-body').querySelectorAll('tbody tr').length === 6 && !q('training-confirm').hidden && applied().length === 2, 'Gold goes from Pokémon to six-IV confirmation without a write');
  await window.launcher.__trainingCapture('gold-confirmation');
  q('training-back').click(); check(/1 · Elige/.test(q('training-step').textContent), 'Gold Back returns to Pokémon selection');
  buttons()[0].click(); await sleep(150); q('training-confirm').click(); await sleep(150);
  check(applied().length === 3 && JSON.stringify(applied()[2][1].change) === JSON.stringify({ kind: 'ivs' }), 'Gold confirms exactly all-six-IV effect');
  window.launcher.__set({ training_seq: ++seq, training_result: { status: 'PENDING', at: 102 }, training_error: 'La compra sigue reservada hasta verificar la operación.' }); await sleep(1500);
  check(/reservada/.test(q('training-error').textContent) && /pendiente de comprobar/.test(q('toasts').textContent), 'uncertain operation stays pending with explicit reserved-purchase message');
  const itemEvents = () => window.launcher.__calls().filter(c => c[0] === 'webEvent' && c[1] === 'items-changed').length;
  const beforeRecovery = itemEvents();
  window.launcher.__set({ training_seq: ++seq, training_error: null }); await sleep(1300);
  check(itemEvents() === beforeRecovery + 1, 'later reconciliation refreshes inventory without replaying application');
  const beforeBackground = itemEvents();
  window.launcher.__set({ training_result: { status: 'APPLIED', purchase_id: gold.purchase_id, at: 103 } }); await sleep(1300);
  check(itemEvents() === beforeBackground + 1, 'background recovery result refreshes web even when training_seq stays unchanged');
  window.launcher.__set({ training: { ...fixture, targets: [{ ...target, pokemon: { ...target.pokemon, ivs: { hp: 31, atk: 31, defense: 31, spa: 31, spd: 31, spe: 31 } } }] } }); await sleep(1300);
  q('training-cancel').click(); await open('chapa_dorada');
  check(buttons()[0].disabled && /seis IV ya/.test(q('training-body').textContent), 'perfect Pokémon cannot consume a redundant Gold Cap');
  q('training-cancel').click();
  window.launcher.__set({ training: fixture }); await sleep(1300);
  await open('menta_naturaleza'); buttons()[0].click(); choose('Firme').click(); await sleep(150);
  window.launcher.__set({ principal: { trainer_id: 'different-fixture-user', display_name: 'Otra cuenta' }, training: null }); await sleep(1300);
  check(!q('training-body').textContent.includes('Chispa') && q('training-confirm').hidden && /cuenta o la partida ha cambiado/.test(q('training-error').textContent), 'account switch clears previous Pokémon, draft and final confirmation');
  q('training-cancel').click();
  return results;
})()`;
app.whenReady().then(async () => {
  const win = new BrowserWindow({
    show: false,
    width: 1100,
    height: 850,
    webPreferences: {
      preload: path.resolve(__dirname, "../launcher_ui_smoke/preload.cjs"),
      contextIsolation: true,
      sandbox: false,
      backgroundThrottling: false,
      offscreen: true,
    },
  });
  const errors = [];
  win.webContents.session.protocol.handle("https", (request) => {
    if (
      request.url !==
      "https://pokeapp-web.pokeapp-v2.workers.dev/visuals/v1/pokemon/25.png"
    )
      return new Response(null, { status: 404 });
    return new Response(
      fs.readFileSync(
        path.resolve(__dirname, "../../web/public/visuals/v1/pokemon/25.png"),
      ),
      { headers: { "content-type": "image/png" } },
    );
  });
  ipcMain.handle("smoke:training-capture", async (event, label) => {
    if (
      event.sender !== win.webContents ||
      ![
        "mint-confirmation",
        "silver-confirmation",
        "gold-confirmation",
      ].includes(label)
    )
      throw new Error("Invalid fixture capture");
    if (!process.env.POKEAPP_TRAINING_UI_EVIDENCE) return;
    fs.mkdirSync(process.env.POKEAPP_TRAINING_UI_EVIDENCE, { recursive: true });
    await new Promise((resolve) => {
      win.webContents.once("paint", resolve);
      win.webContents.invalidate();
      setTimeout(resolve, 1500);
    });
    fs.writeFileSync(
      path.join(process.env.POKEAPP_TRAINING_UI_EVIDENCE, label + ".png"),
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
