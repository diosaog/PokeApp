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
  type("994"); check(add.disabled, "emulator checkbox required");
  const box = document.getElementById("quick-emulator-closed"); box.click();
  check(!add.disabled, "valid value and confirmation enable Añadir");
  add.click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls()) === JSON.stringify([["rare_candy", 994, true]]), "exact request sent once");
  const full = document.querySelector('[data-item="heart_scale"]');
  check(full.querySelector(".quick-add").disabled && /No cabe/.test(full.querySelector(".quick-error").textContent), "full stack cannot add");
  check(!document.getElementById("update-banner").hidden && !document.getElementById("update-download").hidden, "update offered with download button");
  check(/v0.22.0-rc.3/.test(document.getElementById("launcher-version").textContent), "installed version shown");
  check(/Lime3DS/.test(document.getElementById("emulator-state").textContent) && document.querySelectorAll("#discovered-saves button").length === 1, "Lime3DS state and discovered save");
  const card = (id) => document.querySelector('.transfer-card[data-id="' + id.repeat(36) + '"]');
  const kinds = (id) => [...card(id).querySelectorAll("button")].map((b) => b.dataset.kind).join(",");
  check(kinds("a") === "cancel,refresh" && /Has solicitado/.test(card("a").textContent) && /Caja 2, posición 5/.test(card("a").textContent), "requester waits for source: only cancel/refresh");
  check(kinds("b") === "apply,refresh" && /Te van a robar/.test(card("b").textContent) && /Pikachu · Caja 1, posición 2/.test(card("b").textContent), "victim sees own role, Pokémon and turn; no cancel");
  const apply = card("b").querySelector('[data-kind="apply"]');
  check(apply.disabled, "apply needs emulator-closed confirmation");
  document.getElementById("transfer-emulator-closed").click(); await sleep(50);
  const applyNow = card("b").querySelector('[data-kind="apply"]');
  check(!applyNow.disabled, "confirmation enables own action");
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
  document.getElementById("restore-closed").click(); typeWord("Confirmo");
  check(document.getElementById("restore-dialog").open && /desde main/.test(document.getElementById("restore-summary").textContent) && confirm.disabled && /✕ Sin entregas de robo pendientes/.test(document.getElementById("restore-checks").textContent), "pending robbery blocks restore");
  window.launcher.__set({ cloud: { data: { transfers: [] } } }); await sleep(1300);
  typeWord("confirmo"); check(confirm.disabled, "restore word is exact (case)");
  typeWord("Confirmo "); check(confirm.disabled, "restore word is exact (spaces)");
  typeWord("Confirmo"); check(!confirm.disabled, "checks, closed emulator and Confirmo enable restore");
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
  check(add.disabled && /Operación bloqueada/.test(document.getElementById("quick-state").textContent), "disabled capability blocks with explanation");
  // Sync status chip: discreet, from the core's state only.
  const chip = () => document.getElementById("sync-chip").textContent;
  check(chip() === "Sin cuenta", "no account: no sync claimed");
  window.launcher.__set({ principal: { display_name: "Test" }, cloud_sync: true, outbox: { pending: 0 }, cloud_receipt: { status: "registered", is_current: true }, last_synced: Date.now() / 1000 - 120 }); await sleep(1300);
  check(chip() === "Sincronizado" && /hace 2 min/.test(document.getElementById("sync-detail").textContent), "synced with last sync time");
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
