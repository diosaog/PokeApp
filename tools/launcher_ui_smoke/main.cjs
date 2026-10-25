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
  applyNow.click(); await sleep(200);
  check(JSON.stringify(window.launcher.__calls().at(-1)) === JSON.stringify(["transfer", "apply", "b".repeat(36), true]), "exact own-leg action sent");
  check(/Reanudar mi parte/.test(card("c").textContent) && /NO es definitivo/.test(card("c").textContent), "local application distinguished from final robbery");
  check(/Necesitas asistencia/.test(card("d").textContent) && kinds("d") === "refresh", "blocked operation asks for assistance, no unsafe action");
  check(/Robo completado y registrado/.test(card("e").textContent), "completed only on COMMITTED");
  window.launcher.__disable(); await sleep(1300);
  check(/aún no aplica cambios/.test(document.getElementById("transfer-summary").textContent) && [...document.querySelectorAll("#transfer-list button")].every((b) => b.disabled), "no capability: robbery visible but every action disabled");
  check(add.disabled && /Operación bloqueada/.test(document.getElementById("quick-state").textContent), "disabled capability blocks with explanation");
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
  const result = await win.webContents.executeJavaScript(script);
  for (const [ok, label] of result)
    console.log((ok ? "PASS " : "FAIL ") + label);
  app.exit(result.every(([ok]) => ok) ? 0 : 1);
});
