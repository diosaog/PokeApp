// Headless check of the real Launcher page with a test preload. Not packaged.
const { app, BrowserWindow } = require("electron");
const path = require("node:path");
const page = path.resolve(__dirname, "../../companion/launcher/index.html");
const script = `(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const out = [];
  const check = (ok, label) => out.push([Boolean(ok), label]);
  await sleep(1500);
  const row = document.querySelector('[data-item="rare_candy"]');
  const input = row.querySelector(".quick-input"), plus = row.querySelector(".quick-plus"),
    minus = row.querySelector(".quick-minus"), add = row.querySelector(".quick-add");
  const type = (v) => { input.focus(); input.value = v; input.dispatchEvent(new Event("input")); };
  check(input.value === "1" && /Tienes 5/.test(row.querySelector(".quick-count").textContent), "initial value and count");
  plus.click(); plus.click(); minus.click();
  check(input.value === "2", "plus/minus share one value");
  type(""); check(add.disabled && /Escribe una cantidad/.test(row.querySelector(".quick-error").textContent), "cleared field cannot confirm");
  type("250"); plus.click(); check(input.value === "251", "buttons continue from typed value");
  type("-1.5"); check(input.value === "15", "only digits kept");
  type("995"); check(add.disabled && /máximo que cabe ahora es 994/.test(row.querySelector(".quick-error").textContent), "above real maximum refused");
  type("994");
  check(!add.disabled && !document.getElementById("quick-emulator-closed"), "no «he cerrado el emulador» checkbox: a valid value enables Añadir");
  add.click(); await sleep(200);
  check(document.getElementById("confirm-dialog").open && JSON.stringify(window.launcher.__calls()) === JSON.stringify([["begin", "quick-item", "rare_candy:994"]]), "one in-app confirmation first, nothing applied yet");
  document.getElementById("confirm-go").click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["rare_candy", 994, "t:quick-item:rare_candy:994"]), "exact ticketed request sent once");
  window.launcher.__set({ quick_item_seq: 1, quick_item_result: { item: "rare_candy", quantity: 994, game: "Y", at: 1 } }); await sleep(1300);
  check(/994 × Caramelo Raro añadidos/.test(document.getElementById("toasts").textContent) && window.launcher.__calls().some((c) => c[0] === "webEvent" && c[1] === "items-changed"), "verified result is confirmed on top and the web refreshes");
  window.launcher.__set({ quick_item_seq: 2, quick_item_result: null, quick_item_error: "El emulador está abierto: ciérralo (y el juego) y vuelve a pulsar «Añadir a la bolsa». Tu partida no ha cambiado." }); await sleep(1300);
  check(/El emulador está abierto/.test(document.getElementById("toasts").textContent), "a refusal shows its real cause on top");
  window.launcher.__unset(["quick_item_seq", "quick_item_result", "quick_item_error"]);
  const full = document.querySelector('[data-item="heart_scale"]');
  check(full.querySelector(".quick-add").disabled && /No cabe/.test(full.querySelector(".quick-error").textContent), "full stack cannot add");
  check(!document.getElementById("update-banner").hidden && !document.getElementById("update-open").hidden && /0\.23\.0/.test(document.getElementById("update-text").textContent), "update offered discreetly in the strip");
  check(/v0.22.0-rc.3/.test(document.getElementById("launcher-version").textContent), "installed version shown");
  check(/Lime3DS/.test(document.getElementById("emulator-state").textContent) && document.querySelectorAll("#discovered-saves button").length === 1, "Lime3DS state and discovered save");
  const card = (id) => document.querySelector('.transfer-card[data-id="' + id.repeat(36) + '"]');
  const kinds = (id) => [...card(id).querySelectorAll("button")].map((b) => b.dataset.kind).join(",");
  check(kinds("a") === "cancel,refresh" && /Has solicitado/.test(card("a").textContent) && /Caja 2, posición 5/.test(card("a").textContent), "requester waits for source: only cancel/refresh");
  check(kinds("b") === "apply,refresh" && /Te van a robar/.test(card("b").textContent) && /Pikachu · Caja 1, posición 2/.test(card("b").textContent), "victim sees own role, Pokémon and turn; no cancel");
  const applyNow = card("b").querySelector('[data-kind="apply"]');
  check(!applyNow.disabled && !document.getElementById("transfer-emulator-closed"), "own action available without a checkbox (the core checks the emulator)");
  applyNow.click(); await sleep(100);
  check(document.getElementById("confirm-dialog").open && /Aplicar tu parte del robo/.test(document.getElementById("confirm-message").textContent) && window.launcher.__calls().at(-1)[0] !== "transfer", "in-app confirmation first, nothing sent yet");
  document.getElementById("confirm-go").click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["transfer", "apply", "b".repeat(36), true, "t:transfer:apply:" + "b".repeat(36)]), "exact own-leg action sent");
  check(/Reanudar mi parte/.test(card("c").textContent) && /NO es definitivo/.test(card("c").textContent), "local application distinguished from final robbery");
  check(/Necesitas asistencia/.test(card("d").textContent) && kinds("d") === "refresh", "blocked operation asks for assistance, no unsafe action");
  check(/Robo completado y registrado/.test(card("e").textContent), "completed only on COMMITTED");
  check(/Sincronización obligatoria/.test(document.getElementById("transfer-summary").textContent) && kinds("1") === "fulfil,refresh" && /Aplicar retirada obligatoria/.test(card("1").textContent) && /antes de cualquier otra sincronización/.test(card("1").textContent), "27A: decided robbery shows the victim's mandatory removal, no cancel or veto");
  check(kinds("2") === "fulfil,refresh" && /Pendiente de recepción/.test(card("2").textContent) && /es definitivo/.test(card("2").textContent), "27A: robber sees adjudicated but not yet usable");
  const backupRows = [...document.querySelectorAll("#backup-list p")];
  check(backupRows.length === 2 && /Original/.test(backupRows[0].textContent) && backupRows[0].querySelectorAll("button").length === 2 && /Copia diaria del 25.10.2026/.test(backupRows[1].textContent) && /Se conserva 30 días/.test(backupRows[1].textContent) && backupRows[1].querySelectorAll("button").length === 1, "daily point listed with date and game, copy only (no restore)");
  // Restore: in-app dialog, safety checks, closed emulator and the exact word.
  backupRows[0].querySelectorAll("button")[1].click(); await sleep(100);
  const confirm = document.getElementById("restore-confirm"), word = document.getElementById("restore-word");
  const typeWord = (v) => { word.value = v; word.dispatchEvent(new Event("input")); };
  typeWord("Confirmo");
  check(document.getElementById("restore-dialog").open && /desde main/.test(document.getElementById("restore-summary").textContent) && confirm.disabled && /✕ Sin entregas de robo pendientes/.test(document.getElementById("restore-checks").textContent), "pending robbery blocks restore");
  window.launcher.__set({ cloud: { data: { transfers: [] } } }); await sleep(1300);
  typeWord("confirmo"); check(confirm.disabled, "restore word is exact (case)");
  typeWord("Confirmo "); check(confirm.disabled, "restore word is exact (spaces)");
  typeWord("Confirmo"); check(!confirm.disabled && !document.getElementById("restore-closed"), "checks and Confirmo enable restore, no checkbox");
  word.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
  check(document.getElementById("restore-dialog").open && !window.launcher.__calls().some((c) => c[0] === "restore"), "Enter never restores");
  confirm.click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["restore", "f".repeat(36), true, "Confirmo", "t:restore:" + "f".repeat(36)]) && !document.getElementById("restore-dialog").open, "restore sends the operation, the typed word and its ticket once");
  window.launcher.__unset(["cloud"]);
  document.getElementById("web-tab").click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["web", true, true]) && document.getElementById("save-view").hidden, "PokeApp tab shows the full web below the navigation");
  window.launcher.__navigate("heart_scale"); await sleep(200);
  check(!document.getElementById("save-view").hidden && document.activeElement === document.querySelector('[data-item="heart_scale"] .quick-input') && JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["web", false, false]), "web inventory link opens the native Heart Scale input");
  window.launcher.__disable(); await sleep(1300);
  check(/aún no aplica cambios/.test(document.getElementById("transfer-summary").textContent) && [...document.querySelectorAll("#transfer-list button")].every((b) => b.disabled), "no capability: robbery visible but every action disabled");
  check(add.disabled && /no puede añadir objetos/.test(document.getElementById("quick-state").textContent), "disabled capability blocks with explanation");
  // Sync status chip: discreet, from the core's state only.
  const chip = () => document.getElementById("sync-chip").textContent;
  check(chip() === "Sin cuenta", "no account: no sync claimed");
  window.launcher.__set({ principal: { display_name: "Test" }, cloud_sync: true, outbox: { pending: 0 }, cloud_receipt: { status: "registered", is_current: true }, last_synced: Date.now() / 1000 - 120 }); await sleep(1300);
  check(chip() === "Sincronizado" && /hace 2 min/.test(document.getElementById("sync-detail").textContent), "synced with last sync time");
  window.launcher.__set({ cloud: { data: { season: { id: "s", name: "Prueba" }, season_link: { status: "BOUND", game: "SN", identity: { game: "SN", trainer: { name: "Otro" } } }, transfers: [] } } }); await sleep(1300);
  check(/La Liga «Prueba» usa tu partida de Pokémon Sol/.test(document.getElementById("season-line").textContent) && /perfil, Mi PC y Entrenadores/.test(document.getElementById("season-line").textContent), "a season bound to another game is explained, never silent");
  window.launcher.__set({ cloud: { data: { season: { id: "s", name: "Prueba" }, season_link: { status: "NOT_PARTICIPANT" }, transfers: [] } } }); await sleep(1300);
  check(/No participas en la Liga «Prueba»/.test(document.getElementById("season-line").textContent), "not enrolled: the save still goes to the profile");
  window.launcher.__set({ cloud_receipt: null, syncing: true, outbox: { pending: 1 } }); await sleep(1300);
  check(chip() === "Sincronizando" && /● Online/.test(document.getElementById("connection").textContent), "sending shows on the card; connection stays Online");
  window.launcher.__set({ syncing: false, error: "SAVE_READBACK_PENDING" }); await sleep(1300);
  check(chip() === "Comprobando" && !/No se pudo sincronizar/.test(document.getElementById("notices").textContent), "a pending server check is not an error");
  window.launcher.__set({ error: "SAVE_REJECTED", error_detail: "CORRUPT_SAVE" }); await sleep(1300);
  check(chip() === "Error" && /parece dañada/.test(document.getElementById("notices").textContent), "a rejection shows its real cause");
  window.launcher.__set({ error: null, error_detail: null });
  window.launcher.__set({ cloud_status: "OFFLINE", outbox: { pending: 2 } }); await sleep(1300);
  check(chip() === "Sin conexión" && /2 cambio/.test(document.getElementById("sync-detail").textContent), "offline keeps changes queued");
  // Saves y Launcher hub and dialogs over the web.
  window.launcher.__navigateTo({ view: "panel", panel: "saves", tab: "copias" }); await sleep(100);
  check(document.body.dataset.mode === "panel" && !document.getElementById("backups-view").hidden && document.getElementById("save-view").hidden && getComputedStyle(document.getElementById("web-tab")).display === "none" && /Saves y Launcher/.test(document.getElementById("panel-title").textContent), "hub opens on the requested tab, beside the web");
  window.launcher.__setUpdate({ status: "DISABLED", current: "0.22.0-rc.3", channel: "private", reason: "UPDATES_NOT_CONFIGURED" });
  window.launcher.__navigateTo({ view: "modal", panel: "update" }); await sleep(200);
  check(document.body.dataset.mode === "modal" && document.getElementById("update-dialog").open && /no tiene activado un canal/.test(document.getElementById("update-message").textContent) && document.getElementById("update-go").hidden, "update popup is honest when no channel is configured");
  document.querySelector("#update-dialog [data-close]").click(); await sleep(100);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["closePanel"]), "closing the last dialog hands the window back to the web");
  window.launcher.__navigateTo({ view: "modal", panel: "objetos", item: "rare_candy" }); await sleep(100);
  check(document.getElementById("sheet-dialog").open && document.getElementById("sheet-body").contains(document.getElementById("quick-article")) && document.getElementById("sheet-body").contains(document.getElementById("write-article")), "items open as a sheet with the confirmation step");
  document.querySelector("#sheet-dialog [data-close]").click(); await sleep(50);
  check(document.getElementById("save-view").contains(document.getElementById("quick-article")) && document.getElementById("save-view").contains(document.getElementById("write-article")), "sheet sections return home on close");
  // Several saves and none chosen: the selector opens by itself, once.
  window.launcher.__navigateTo({ view: "strip" });
  window.launcher.__set({ selected_save: null, save_choice: { status: "CHOOSE", count: 2 }, emulator_saves: [{ path: "C:/fx/Lime3DS/sdmc/Nintendo 3DS/a/b/title/00040000/00055e00/data/00000001/main", emulator: "Lime3DS", game: "Y", modified: Math.floor(Date.now() / 1000) - 30 }, { path: "C:/fx/Azahar/sdmc/Nintendo 3DS/a/b/title/00040000/00175e00/data/00000001/main", emulator: "Azahar", game: "MN", modified: null }] }); await sleep(1300);
  const options = [...document.querySelectorAll("#selector-list .save-option")];
  check(document.getElementById("selector-dialog").open && options.length === 2 && /Pokémon Y/.test(options[0].textContent) && /Lime3DS · modificada hace un momento/.test(options[0].textContent) && /Pokémon Luna/.test(options[1].textContent) && /fecha no disponible/.test(options[1].textContent), "selector lists game, emulator and last change");
  check(/Hemos encontrado varias partidas/.test(document.getElementById("notices").textContent), "choice also stays as a notice");
  options[1].click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["select", "C:/fx/Azahar/sdmc/Nintendo 3DS/a/b/title/00040000/00175e00/data/00000001/main"]), "choosing sends exactly that save");
  // Search: the answer itself fills the selector; nothing found says why.
  shut(document.getElementById("selector-dialog"));
  window.launcher.__discover({ status: "DONE", count: 0, auto_selected: false, saves: [], save_choice: { status: "NONE", count: 0 }, discovery: { found: 0, at: 5, checked: [{ emulator: "Citra", location: "appdata", saves: 0, other_titles: 2, error: null }] } });
  document.getElementById("discover-saves").click(); await sleep(400);
  check(document.getElementById("selector-dialog").open && /no admite/.test(document.getElementById("selector-empty").textContent) && /Citra \\(instalación normal\\): solo juegos no admitidos/.test(document.getElementById("selector-report").textContent) && /no admite/.test(document.getElementById("toasts").textContent), "nothing found: selector opens and explains why, with what was checked");
  shut(document.getElementById("selector-dialog"));
  window.launcher.__discover({ status: "DONE", count: 2, auto_selected: false, save_choice: { status: "KEPT", count: 1 }, saves: [{ path: "C:/p/main", emulator: "Azahar", location: "portable", game: "Y", modified: null }, { path: "C:/q/main", emulator: "Lime3DS", location: "appdata", game: "SN", modified: null }], discovery: { found: 2, at: 6, checked: [] } });
  document.getElementById("discover-primary").click(); await sleep(400);
  const found = [...document.querySelectorAll("#selector-list .save-option")];
  check(document.getElementById("selector-dialog").open && found.length === 2 && /Azahar \\(versión portable\\)/.test(found[0].textContent) && /Hemos encontrado 2 partidas/.test(document.getElementById("toasts").textContent), "results appear at once, even before the next state poll");
  shut(document.getElementById("selector-dialog"));
  // Updates: the popup opens by itself once per version, «Más tarde» is kept,
  // «Actualizar» goes through a main ticket, progress and errors are shown.
  const ud = document.getElementById("update-dialog"), uq = (id) => document.getElementById(id);
  const offer = { status: "AVAILABLE", current: "0.26.0", version: "0.27.0", channel: "private", prompt: true, size: 160 * 1024 * 1024, notes: "- Selector de partidas\\n- Copias de seguridad" };
  shut(ud); window.launcher.__navigateTo({ view: "strip" });
  window.launcher.__setUpdate(offer); await sleep(1300);
  check(ud.open && /Hay una versión nueva/.test(uq("update-message").textContent) && /Versión 0\.27\.0 · tienes 0\.26\.0/.test(uq("update-versions").textContent) && document.querySelectorAll("#update-notes li").length === 2 && !uq("update-go").hidden && uq("update-go").textContent.trim() === "Actualizar" && uq("update-later").textContent.trim() === "Más tarde" && /160 MB/.test(uq("update-facts").textContent), "a newer version opens the popup by itself with version, notes and size");
  uq("update-later").click(); await sleep(200);
  check(!ud.open && window.launcher.__calls().some((c) => c[0] === "postpone"), "«Más tarde» postpones that version");
  await sleep(1300);
  check(!ud.open && uq("update-banner").hidden, "no repeated popup or banner for a postponed version");
  window.launcher.__navigateTo({ view: "modal", panel: "update" }); await sleep(300);
  check(ud.open && uq("update-go").textContent.trim() === "Actualizar", "a manual check still shows the postponed version");
  uq("update-go").click(); await sleep(300);
  check(JSON.stringify(window.launcher.__calls().slice(-2)) === JSON.stringify([["begin", "update", "0.27.0"], ["apply", "t:update:0.27.0"]]), "«Actualizar» asks main for a ticket bound to that version");
  window.launcher.__setUpdate({ ...offer, prompt: false, status: "DOWNLOADING", progress: { received: 80 * 1024 * 1024, total: 160 * 1024 * 1024 } }); await sleep(600);
  check(!uq("update-progress-box").hidden && /80 MB de 160 MB · 50 %/.test(uq("update-progress-text").textContent) && uq("update-later").hidden, "download progress is shown; no «Más tarde» once accepted");
  window.launcher.__setUpdate({ ...offer, prompt: false, status: "ERROR", reason: "SIGNATURE_INVALID" }); await sleep(1300);
  check(/verificación de firma/.test(uq("update-message").textContent) && uq("update-go").textContent.trim() === "Reintentar", "a forged update is refused and explained");
  window.launcher.__setUpdate({ status: "UP_TO_DATE", current: "0.27.0", channel: "private" }); await sleep(1300);
  check(/Estás utilizando la última versión/.test(uq("update-message").textContent) && uq("update-go").hidden, "no update: «Estás utilizando la última versión»");
  shut(ud);
  // Friend's Launcher: a core that is restarting is not «Sin conexión» and
  // never looks like a signed-out account; it recovers without a restart.
  const textOf = (id) => document.getElementById(id).textContent;
  window.launcher.__set({ principal: { display_name: "Amigo", trainer_id: "t" }, auth_status: "VERIFIED", cloud_status: "ONLINE", last_online: Date.now() / 1000, error: null, error_cause: null }); await sleep(1300);
  check(/● Online/.test(textOf("connection")) && textOf("launcher-core") === "Disponible" && /Amigo · Cuenta verificada/.test(textOf("identity")), "ready core: core, connection and account each on their own line");
  window.launcher.__core({ status: "RESTARTING", reason: "LAUNCHER_ALREADY_RUNNING", message: "Otra ventana de PokeApp Launcher, o una sesión anterior que todavía se está cerrando, está usando tus datos locales. Lo reintentamos solo.", next_attempt_in: 12 }); await sleep(1300);
  check(/Reconectando con el núcleo/.test(textOf("connection")) && !/Sin conexión/.test(textOf("connection")), "a restarting core is not shown as «Sin conexión»");
  check(/Amigo · Cuenta guardada en este equipo/.test(textOf("identity")) && /no hace falta volver a iniciar sesión/.test(textOf("identity")) && document.getElementById("login").hidden, "the account stays; no new sign-in is asked");
  check(/sesión anterior/.test(textOf("launcher-core")) && /Próximo intento en 12 s/.test(textOf("launcher-core")) && /sesión anterior/.test(textOf("message")) && !document.getElementById("core-restart").hidden, "the real reason, the next attempt and «Reintentar ahora»");
  document.getElementById("core-restart").click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["coreRestart"]), "«Reintentar ahora» asks main to start the core at once");
  window.launcher.__core({ status: "READY", message: "" }); await sleep(1300);
  check(/● Online/.test(textOf("connection")) && textOf("launcher-core") === "Disponible" && document.getElementById("core-restart").hidden && textOf("message") === "" && /Amigo · Cuenta verificada/.test(textOf("identity")), "back without restarting the Launcher: same account, online, message cleared");
  window.launcher.__core({ status: "READY", message: "El núcleo del Launcher está terminando una operación en tu partida. Espera unos segundos y no abras el emulador.", stalled: true }); await sleep(1300);
  check(/terminando una operación en tu partida/.test(textOf("launcher-core")) && /no abras el emulador/.test(textOf("message")), "a core finishing a save operation is waited for and said so");
  window.launcher.__core({ status: "READY", message: "" });
  window.launcher.__set({ selected_save: "C:/fixture/main", cloud_sync: true, cloud_status: "OFFLINE", error: "BACKEND_UNAVAILABLE", error_cause: "TLS_UNTRUSTED", outbox: { pending: 0 } }); await sleep(1300);
  check(/antivirus o un proxy/.test(textOf("launcher-connection")) && /antivirus o un proxy/.test(textOf("sync-detail")), "an intercepted secure connection is named, not a generic offline");
  document.getElementById("copy-diagnostics").click(); await sleep(300);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["copyDiagnostics"]) && /Diagnóstico copiado/.test(textOf("toasts")), "«Copiar diagnóstico» copies a safe summary");
  return out;
})()`;
app.whenReady().then(async () => {
  const win = new BrowserWindow({
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      sandbox: false,
    },
  });
  await win.loadFile(page);
  if (process.env.POKEAPP_LAUNCHER_SHOT) {
    // Optional design review capture (27B): the native screen before checks.
    win.setContentSize(1280, 1600);
    await new Promise((r) => setTimeout(r, 1500));
    const image = await win.webContents.capturePage();
    require("node:fs").writeFileSync(
      process.env.POKEAPP_LAUNCHER_SHOT,
      image.toPNG(),
    );
  }
  const result = await win.webContents.executeJavaScript(script);
  for (const [ok, label] of result)
    console.log((ok ? "PASS " : "FAIL ") + label);
  app.exit(result.every(([ok]) => ok) ? 0 : 1);
});
