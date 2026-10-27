/* All navigation uses this in-memory local DTO. No browser network access. */
const $ = (id) => document.getElementById(id);
let observation = null,
  revision = null,
  boxIndex = 0,
  polling = false,
  pendingWrite = null,
  backupRows = [],
  backupKey = "",
  selectedSave = null,
  exportAvailable = false,
  backupBusy = false,
  lastState = null,
  lastUpdate = null;
const text = (id, value) => {
  $(id).textContent = value;
};
const gameNames = {
  X: "X",
  Y: "Y",
  OR: "Rubí Omega",
  AS: "Zafiro Alfa",
  SN: "Sol",
  MN: "Luna",
  US: "Ultrasol",
  UM: "Ultraluna",
};
// "hace 3 min" for recent moments, a short date otherwise. Seconds since epoch.
function when(seconds) {
  const elapsed = Date.now() / 1000 - seconds;
  if (elapsed < 60) return "hace un momento";
  if (elapsed < 3600) return `hace ${Math.floor(elapsed / 60)} min`;
  return new Date(seconds * 1000).toLocaleString("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  });
}
// A robbery whose physical delivery is not verified yet (main checks the same).
const robberyOpen = (transfers) =>
  (transfers || []).some(
    (t) =>
      t.mandatory ||
      (t.obligation && !t.obligation.endsWith("_VERIFIED")) ||
      (t.apply_started && !["COMMITTED", "CANCELLED"].includes(t.status)),
  );
function details(p, location) {
  text("pokemon-title", p.nickname || `Pokémon #${p.species_id}`);
  $("pokemon-details").replaceChildren();
  const fields = {
    Especie: `#${p.species_id}`,
    Nivel: p.level,
    Ubicación: location,
    Objeto: p.item_id ? `#${p.item_id}` : "Sin objeto",
    Movimientos:
      p.moves
        .filter((m) => m.id)
        .map((m) => `#${m.id} (${m.pp} PP)`)
        .join(", ") || "Sin movimientos",
    Naturaleza: `#${p.nature_id}`,
    Habilidad: `#${p.ability_id}`,
    IV: p.ivs.join(" / "),
    EV: p.evs.join(" / "),
    Estado: p.is_egg ? "Huevo" : p.shiny ? "Variocolor" : "Observado en save",
  };
  for (const [label, value] of Object.entries(fields)) {
    const dt = document.createElement("dt"),
      dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = String(value);
    $("pokemon-details").append(dt, dd);
  }
  $("details").showModal();
}
function slots(id, data, prefix) {
  $(id).replaceChildren();
  data.forEach((p, i) => {
    const el = document.createElement(p ? "button" : "div");
    el.className = "slot" + (p ? "" : " empty");
    if (p) {
      const name = document.createElement("strong"),
        meta = document.createElement("span");
      name.textContent = p.nickname || `Pokémon #${p.species_id}`;
      meta.textContent = `#${p.species_id} · Nv. ${p.level}`;
      el.append(name, meta);
      el.addEventListener("click", () => details(p, `${prefix} · ${i + 1}`));
    } else el.textContent = `Vacío · ${i + 1}`;
    $(id).append(el);
  });
}
function renderBox() {
  const boxes = observation?.boxes || [];
  boxIndex = Math.max(0, Math.min(boxIndex, boxes.length - 1));
  text(
    "box-name",
    boxes.length ? `Caja ${boxIndex + 1} / ${boxes.length}` : "Caja —",
  );
  slots("box", boxes[boxIndex]?.slots || [], `Caja ${boxIndex + 1}`);
  $("previous-box").disabled = boxIndex === 0;
  $("next-box").disabled = boxIndex >= boxes.length - 1;
}
const errorText = {
  LOGIN_REQUIRED: "Vuelve a iniciar sesión para sincronizar.",
  SESSION_REJECTED: "Sesión no válida. Vuelve a conectar.",
  OBSERVATION_REJECTED:
    "PokeApp no ha aceptado este save. Tu lectura local sigue disponible.",
  SAVE_REJECTED:
    "No se pudo registrar el save. Revisa el archivo, la cuenta y la Liga.",
  SAVE_SUPERSEDED:
    "La web tiene otro save actual. Selecciona tu archivo actualizado antes de sincronizar.",
  SAVE_READBACK_PENDING:
    "Falta comprobar el save en la web. Pulsa Reintentar; no se duplicará la subida.",
  SAVE_PARSE_MISMATCH:
    "La lectura local no coincide. Vuelve a abrir el save con el Launcher actualizado.",
  SAVE_CHANGED_DURING_READ:
    "El archivo ha cambiado. Esperando una lectura estable.",
  BACKEND_UNAVAILABLE:
    "Sin conexión con PokeApp. Puedes seguir explorando tu save.",
  SYNC_UNAVAILABLE:
    "No se pudo sincronizar. Puedes seguir explorando y reintentar.",
};
// The five owner-facing sync states, plus "no save" and "no account".
function syncStatus(state) {
  const pending = state.outbox?.pending || 0;
  if (!state.selected_save)
    return ["idle", "Sin partida", "Busca tu partida para empezar."];
  if (state.write?.status === "RECOVERY_REQUIRED")
    return [
      "error",
      "Error",
      "Sincronización en pausa: hay una recuperación pendiente. No abras el emulador.",
    ];
  if (!state.principal)
    return [
      "idle",
      "Sin cuenta",
      "Inicia sesión en PokeApp y esta partida se sincronizará sola.",
    ];
  // Shared PC: another trainer synced from this Launcher before.
  if (!state.cloud_sync)
    return [
      "pending",
      "Pendiente",
      "Confirma que esta partida es tuya con «Sincronizar ahora» (pestaña Launcher).",
    ];
  if (state.cloud_status === "OFFLINE")
    return [
      "offline",
      "Sin conexión",
      pending
        ? `${pending} cambio(s) en cola: se enviarán al volver la conexión.`
        : "Se sincronizará al volver la conexión.",
    ];
  if (
    state.outbox?.paused ||
    (state.error && state.error !== "SAVE_CHANGED_DURING_READ")
  )
    return [
      "error",
      "Error",
      errorText[state.error] || "No se pudo sincronizar. Lo reintentaremos.",
    ];
  if (
    !pending &&
    state.cloud_receipt?.status === "registered" &&
    state.cloud_receipt.is_current
  )
    return [
      "ok",
      "Sincronizado",
      state.last_synced
        ? `Última sincronización: ${when(state.last_synced)}`
        : "Tu partida está al día en PokeApp.",
    ];
  if (pending && state.cloud_status === "SYNCING")
    return ["busy", "Sincronizando", "Enviando tu partida a PokeApp…"];
  return [
    "pending",
    "Pendiente",
    state.local_status === "READY"
      ? "Se enviará en un momento."
      : "Esperando a que el archivo deje de cambiar.",
  ];
}
function render(state) {
  const write = state.write;
  if (pendingWrite !== write?.operation_id)
    $("emulator-closed").checked = false;
  pendingWrite = write?.operation_id || null;
  text(
    "write-state",
    write?.message || "No hay cambios autorizados pendientes.",
  );
  text("write-description", write?.description || "");
  text("write-error", state.write_error || "");
  $("write-confirmation").hidden = !write?.can_confirm;
  $("confirm-write").disabled =
    !write?.can_confirm || !$("emulator-closed").checked;
  if (selectedSave !== state.selected_save) {
    selectedSave = state.selected_save;
    $("backup-emulator-closed").checked = false;
  }
  exportAvailable = Boolean(write?.can_export);
  backupBusy = Boolean(write?.busy);
  $("export-save").disabled =
    !exportAvailable || !$("backup-emulator-closed").checked;
  text("backup-notice", write?.backup_message || "");
  const key = JSON.stringify([write?.backups || [], write?.busy]);
  if (key !== backupKey) {
    backupKey = key;
    backupRows = write?.backups || [];
    renderBackups(Boolean(write?.busy));
  }
  $("reconcile-write").hidden = !write?.can_reconcile;
  const recovery = write?.status === "RECOVERY_REQUIRED";
  $("select-save").disabled = recovery;
  $("selector-manual").disabled = recovery;
  if ("observation" in state) {
    observation = state.observation;
    revision = state.receipt_id;
    text(
      "save-identity",
      observation
        ? `${observation.trainer.name} · ${gameNames[observation.game] || observation.game} · Gen ${observation.generation} · TID ${observation.trainer.tid}`
        : "",
    );
    slots("party", observation?.party || Array(6).fill(null), "Equipo");
    renderBox();
  }
  const local = ["UNSUPPORTED_GAME", "UNSUPPORTED_VERSION"].includes(
    state.local_status,
  )
    ? "Save no compatible. Juegos admitidos: Gen3, Gen4, Gen5, Pokémon X/Y, Rubí Omega/Zafiro Alfa y Sol/Luna/Ultrasol/Ultraluna (save descifrado)."
    : ["CORRUPT_SAVE", "TRUNCATED_SAVE", "AMBIGUOUS_IDENTITY"].includes(
          state.local_status,
        )
      ? "Save incompleto o no válido. No se enviará a la nube; se conserva la última lectura local si existe."
      : state.local_status === "READY"
        ? "Save leído localmente."
        : state.local_status === "CACHED"
          ? "Última lectura guardada; comprobando el archivo…"
          : observation
            ? "No se ha podido actualizar el save. Mostrando la última lectura local."
            : state.selected_save
              ? "Esperando una lectura estable del save seleccionado."
              : "Selecciona tu archivo para empezar. Puedes explorar sin conexión.";
  text("save-state", local);
  text(
    "connection",
    recovery
      ? "● Sincronización pausada"
      : state.cloud_status === "ONLINE"
        ? "● Online"
        : state.cloud_status === "SYNCING"
          ? "● Sincronizando"
          : "● Sin conexión",
  );
  text(
    "identity",
    state.principal
      ? `${state.principal.display_name}${state.auth_status === "VERIFIED" ? " · Cuenta verificada" : " · Identidad guardada, pendiente de verificar"}`
      : "Inicia sesión para conectar tu Launcher.",
  );
  const cached = state.cloud?.data;
  const useLabels = {
    PREPARED: "Aplicación pendiente",
    PENDING_APPLICATION: "Aplicación pendiente",
    APPLIED_VERIFIED: "Aplicación verificada",
    FAILED_RECOVERABLE: "Error recuperable",
    RECOVERY_REQUIRED: "Recuperación necesaria",
    BLOCKED_UNCERTAIN: "Operación bloqueada",
  };
  text(
    "item-use-state",
    cached?.item_uses?.length
      ? cached.item_uses
          .map((use) => useLabels[use.status] || "Estado no disponible")
          .join(" · ")
      : "Aplicación de objetos deshabilitada. No se consume ningún objeto desde este Launcher.",
  );
  // A local application is never the robbery: only COMMITTED is server-confirmed.
  const transferLabels = {
    PREPARING: "Robo pendiente · preparando guardados",
    WAITING_OTHER: "Esperando al otro entrenador",
    PENDING_SOURCE: "Pendiente de la primera parte",
    VERIFYING_SOURCE: "Primera parte aplicada · verificando",
    PENDING_DESTINATION: "Esperando la segunda parte",
    VERIFYING_BOTH: "Segunda parte aplicada · verificando",
    BOTH_VERIFIED_PENDING_IDENTITY: "Verificación en curso",
    COMMITTED: "Robo completado",
    CANCELLED: "Robo cancelado",
    BLOCKED_UNCERTAIN: "Operación bloqueada",
  };
  const transfers = cached?.transfers || [];
  text(
    "transfer-state",
    transfers.length
      ? transfers
          .map(
            (t) =>
              `${t.side === "source" ? "Te roban" : "Robas"}: ${transferLabels[t.status] || "Estado no disponible"}`,
          )
          .join(" · ") +
          (state.write?.transfer_application_enabled
            ? ""
            : " · Este Launcher no aplica robos todavía.")
      : "No hay robos en curso.",
  );

  text(
    "cloud-state",
    cached
      ? `${cached.season?.name || "Sin Liga activa"} · Monedas: ${cached.wallet ?? "Desconocidas"}`
      : "Todavía no hay datos guardados.",
  );
  text(
    "cloud-age",
    state.cloud
      ? `${state.cloud_stale ? "Último estado guardado · Puede estar desactualizado" : "Estado consultado"} · ${new Date(state.cloud.refreshed_at * 1000).toLocaleString()}`
      : "",
  );
  const [tone, label, detail] = syncStatus(state);
  text("receipt", `${label} · ${detail}`);
  $("enable-sync").disabled = recovery || !observation || !state.principal;
  $("login").querySelector("button").disabled =
    state.auth_status === "CHECKING";
  text("message", errorText[state.error] || "");
  renderSaveCard(state, tone, label, detail);
  renderLauncher(state, label);
}

// Saves y Launcher · Mis partidas: the active save at a glance.
function renderSaveCard(state, tone, label, detail) {
  const saves = state.emulator_saves || [];
  const current = saves.find((s) => s.path === state.selected_save);
  const game = observation?.game || current?.game;
  $("save-card").dataset.empty = String(!state.selected_save);
  $("save-card").dataset.game = game || "";
  text("save-card-badge", game || "?");
  text(
    "save-card-title",
    !state.selected_save
      ? "Aún no hay partida"
      : observation
        ? `${observation.trainer.name} · Pokémon ${gameNames[observation.game] || observation.game}`
        : game
          ? `Pokémon ${gameNames[game] || game} · leyendo…`
          : "Leyendo tu partida…",
  );
  text(
    "save-card-meta",
    !state.selected_save
      ? "Busca tu partida en el emulador y PokeApp la sincronizará sola, sin modificar el archivo."
      : [
          current?.emulator || "Archivo elegido a mano",
          observation ? `TID ${observation.trainer.tid}` : null,
          current?.modified ? `Modificada ${when(current.modified)}` : null,
        ]
          .filter(Boolean)
          .join(" · "),
  );
  $("sync-chip").dataset.tone = tone;
  text("sync-chip", label);
  text("sync-detail", detail);
  $("choose-save").hidden = !state.selected_save;
  $("choose-save").disabled = state.write?.status === "RECOVERY_REQUIRED";
  const choice = state.save_choice || {};
  const others = state.selected_save
    ? saves.filter((s) => s.path !== state.selected_save).length
    : 0;
  $("other-saves").hidden = !others;
  text(
    "other-saves",
    choice.new
      ? "Hay una partida nueva en este equipo. Tu partida activa no cambia: pulsa «Cambiar partida» si quieres usar la nueva."
      : `${others === 1 ? "Hay otra partida" : `Hay ${others} partidas más`} en este equipo. Puedes cambiar cuando quieras.`,
  );
}

// Saves y Launcher · Launcher: version, account, automatic sync.
function renderLauncher(state, label) {
  text(
    "launcher-account",
    state.principal
      ? `${state.principal.display_name} · ${state.auth_status === "VERIFIED" ? "verificada" : "pendiente de verificar"}`
      : "Sin vincular: inicia sesión en PokeApp",
  );
  text(
    "launcher-sync",
    !state.principal
      ? "Se activa al iniciar sesión"
      : state.cloud_sync
        ? `Automática · ${label}`
        : "En pausa",
  );
  $("login").hidden = Boolean(state.principal);
  $("logout").hidden = !state.principal;
}

// Contextual notices above the web: choices and incidents, never silent.
const dismissed = new Set();
let noticeKey = "";
function renderNotices(state) {
  const notices = [];
  const choice = state.save_choice || {};
  if (choice.status === "CHOOSE" && !state.selected_save)
    notices.push([
      "choose",
      "info",
      "Hemos encontrado varias partidas. Elige cuál quieres sincronizar.",
      "Elegir partida",
      () => present("selector"),
    ]);
  if (choice.new && state.selected_save)
    notices.push([
      "new-save",
      "info",
      "Hay una partida nueva en este equipo. Tu partida activa no cambia.",
      "Ver partidas",
      () => present("selector"),
    ]);
  if (robberyOpen(state.cloud?.data?.transfers))
    notices.push([
      "robbery",
      "gold",
      state.cloud?.data?.mandatory_sync
        ? "Sincronización obligatoria: PokeApp ha decidido un robo sobre tu partida."
        : "Tienes una entrega de robo pendiente en tu partida.",
      "Ver entrega",
      () => present("robos"),
    ]);
  if (state.write?.status === "RECOVERY_REQUIRED")
    notices.push([
      "recovery",
      "danger",
      "Recuperación pendiente: no abras el emulador hasta resolverla.",
      "Ver detalles",
      () => openHub("partidas"),
    ]);
  else if (state.principal && state.outbox?.paused)
    notices.push([
      "sync-error",
      "danger",
      "No se pudo sincronizar tu partida. Lo reintentaremos.",
      "Ver detalles",
      () => openHub("partidas"),
    ]);
  const shown = notices.filter(([id]) => !dismissed.has(id));
  const key = JSON.stringify(shown.map(([id, , message]) => [id, message]));
  if (key === noticeKey) return;
  noticeKey = key;
  const box = $("notices");
  box.hidden = !shown.length;
  box.replaceChildren(
    ...shown.map(([id, tone, message, label, go]) => {
      const row = document.createElement("p"),
        span = document.createElement("span"),
        button = document.createElement("button"),
        close = document.createElement("button");
      row.className = "notice";
      row.dataset.tone = tone;
      row.dataset.id = id;
      span.textContent = message;
      button.type = close.type = "button";
      button.textContent = label;
      button.onclick = go;
      close.className = "icon-close";
      close.textContent = "×";
      close.setAttribute("aria-label", "Ocultar aviso");
      close.onclick = () => {
        dismissed.add(id);
        renderNotices(lastState || state);
      };
      row.append(span, button, close);
      return row;
    }),
  );
  reportStrip();
}

// Owner rule: several saves and none chosen → the selector opens by itself, once.
let autoPresented = false;
function autoChoose(state) {
  if (
    autoPresented ||
    state.save_choice?.status !== "CHOOSE" ||
    state.selected_save
  )
    return;
  autoPresented = true;
  present("selector");
}

function renderBackups(busy) {
  const list = $("backup-list");
  list.replaceChildren();
  if (!backupRows.length) {
    list.textContent = lastState?.selected_save
      ? "Todavía no hay copias de esta partida. PokeApp crea una antes de cada cambio y una diaria."
      : "Elige tu partida para ver sus copias.";
    return;
  }
  for (const backup of backupRows) {
    const row = document.createElement("p"),
      label = document.createElement("span"),
      title = document.createElement("strong"),
      meta = document.createElement("span"),
      actions = document.createElement("span"),
      copy = document.createElement("button");
    row.className = "backup-row";
    row.dataset.verified = String(Boolean(backup.verified));
    label.className = "backup-label";
    actions.className = "backup-actions";
    const daily = backup.role === "daily";
    title.textContent = daily
      ? `${backup.game} · Copia diaria del ${new Date(`${backup.date}T12:00:00`).toLocaleDateString("es-ES")}`
      : `${backup.game} · ${backup.created_at ? new Date(backup.created_at).toLocaleString("es-ES") : "Fecha no disponible"}`;
    meta.textContent = daily
      ? " · Estado antes de la primera modificación del día · Verificada · Se conserva 30 días "
      : ` · ${backup.role === "before_restore" ? "Antes de restaurar" : "Original"} · ${backup.verified ? "Verificada" : "Inválida o ilegible"} · ${["RECOVERY_REQUIRED", "PREPARED"].includes(backup.status) ? "Recuperación pendiente" : "Conservada"}${backup.beside_save === "REMOVED" ? " · Sin restos junto a la partida" : backup.beside_save === "KEPT_CHANGED" ? " · Copia junto a la partida conservada: cambió fuera de PokeApp" : backup.beside_save?.startsWith("KEPT_") || backup.beside_save === "REMOVAL_INTENT" ? " · Copia junto a la partida conservada por seguridad" : ""} `;
    label.append(title, meta);
    copy.textContent = "Exportar copia…";
    copy.disabled = !backup.verified || busy;
    copy.onclick = () =>
      action(() =>
        window.launcher.saveBackup(backup.operation_id, backup.role),
      );
    actions.append(copy);
    if (backup.can_restore) {
      const restore = document.createElement("button");
      restore.textContent = "Restaurar…";
      restore.className = "danger-soft";
      restore.disabled = busy;
      restore.onclick = () => openRestore(backup);
      actions.append(restore);
    }
    row.append(label, actions);
    list.append(row);
  }
}
async function action(fn) {
  try {
    const result = await fn();
    if (result?.status === "BUSY")
      text("message", "Hay una operación pendiente.");
    return result;
  } catch (error) {
    // Main's own refusals are sentences meant for the trainer; codes are not.
    const reason = String(error?.message || "")
      .split("Error: ")
      .pop();
    text(
      "message",
      /^[A-ZÁÉÍÓÚ¿¡].* /.test(reason)
        ? reason
        : "No se pudo contactar con el núcleo local del Launcher.",
    );
  }
}

// Sections: the PokeApp web (classic window only) and the three hub tabs.
const sections = {
  partidas: ["save-view", "save-tab"],
  copias: ["backups-view", "backups-tab"],
  launcher: ["cloud-view", "cloud-tab"],
};
let hubTab = "partidas";
function showSection(name) {
  for (const [key, [view, button]] of Object.entries(sections)) {
    $(view).hidden = key !== name;
    $(button).setAttribute("aria-pressed", String(key === name));
  }
  $("web-tab").setAttribute("aria-pressed", String(name === "web"));
  if (name in sections) hubTab = name;
  if (name === "copias" && lastState?.selected_save)
    void action(() => window.launcher.backups());
}
function tab(name) {
  name = { save: "partidas", cloud: "launcher" }[name] || name;
  showSection(name);
  // Unified shell: the web stays beside the hub; it is never toggled here.
  if (document.body.dataset.mode === "panel") return;
  const web = name === "web";
  const top = Math.ceil(
    document.querySelector("nav").getBoundingClientRect().bottom,
  );
  void action(() => window.launcher.showWeb(web, web ? top : 0));
}
$("web-tab").onclick = () => tab("web");
$("save-tab").onclick = () => tab("partidas");
$("backups-tab").onclick = () => tab("copias");
$("cloud-tab").onclick = () => tab("launcher");
// Unified shell: loaded as the Launcher's tools view, this page is the
// «Saves y Launcher» hub beside the web's sidebar, a dialog over the web, or,
// between those, just the strip of notices. Opened on its own it keeps the
// classic tabs.
const unified = new URLSearchParams(location.search).get("shell") === "unified";
function mode(name) {
  document.body.dataset.mode = name;
  document.documentElement.dataset.mode = name;
  $("offline-note").hidden = name !== "offline";
  reportStrip();
}
let stripHeight = -1;
function reportStrip() {
  if (!unified || document.body.dataset.mode !== "strip") return;
  const shown = [$("update-banner"), $("notices")].filter((el) => !el.hidden);
  const height = shown.length
    ? Math.min(
        160,
        Math.ceil(
          Math.max(...shown.map((el) => el.getBoundingClientRect().bottom)),
        ),
      )
    : 0;
  if (height === stripHeight) return;
  stripHeight = height;
  void action(() => window.launcher.layout(height));
}
function openHub(name) {
  const current = document.body.dataset.mode;
  if (unified && (current === "strip" || current === "modal"))
    return void action(() => window.launcher.openHub(name || hubTab));
  if (current === "panel") return showSection(name || hubTab);
  tab(name || hubTab);
}
function enterHub(name) {
  closeDialogs();
  mode("panel");
  text("panel-title", "Saves y Launcher");
  showSection(name || hubTab);
  window.scrollTo(0, 0);
  $("panel-title").focus();
}
$("panel-back").onclick = () => action(() => window.launcher.closePanel());

// Dialogs. Over the web (modal mode) the window is only the dialog: closing
// the last one hands the window back to the web.
const dialogIds = {
  selector: "selector-dialog",
  update: "update-dialog",
  restore: "restore-dialog",
  objetos: "sheet-dialog",
  robos: "sheet-dialog",
};
const anyOpen = () => document.querySelector("dialog[open]") !== null;
// The update popup re-checks the feed when the trainer opens it; opened by
// the updater itself (or from the strip) it shows the offer already verified.
let updateCheckOnOpen = true;
function present(view, { check = true } = {}) {
  if (view === "update") updateCheckOnOpen = check;
  if (unified && document.body.dataset.mode === "strip")
    return void action(() => window.launcher.present(view));
  openDialog(view);
}
function openDialog(view, item) {
  if (view === "objetos" || view === "robos") fillSheet(view, item);
  if (view === "selector") renderSelector(lastState, true);
  if (view === "update") {
    if (updateCheckOnOpen || !lastUpdate) void checkForUpdates();
    else fillUpdateDialog(lastUpdate);
    updateCheckOnOpen = true;
  }
  const dialog = $(dialogIds[view]);
  if (!dialog.open) dialog.showModal();
  if (view === "objetos") focusItem(item);
}
// Every close goes through here, synchronously: the dialog "close" event is
// queued and is not delivered while the window is not painting.
function shut(dialog, quiet = false) {
  if (!dialog.open) return;
  dialog.close();
  if (dialog.id === "sheet-dialog") returnSheet();
  dialog.dispatchEvent(new Event("shut"));
  if (!quiet && document.body.dataset.mode === "modal" && !anyOpen())
    void action(() => window.launcher.closePanel());
}
function closeDialogs() {
  for (const dialog of document.querySelectorAll("dialog[open]"))
    shut(dialog, true);
}
for (const dialog of document.querySelectorAll("dialog")) {
  dialog.addEventListener("click", (event) => {
    if (event.target.closest("[data-close]")) shut(dialog);
  });
  // Escape closes like «Cerrar», through the same path.
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    shut(dialog);
  });
}

// In-app confirmation (replaces native message boxes). Main writes the text
// from the core's state and issues a single-use ticket for this action only;
// the dialog hands that ticket back, or null when the trainer steps back.
async function confirmWith(kind, target) {
  const offer = await action(() => window.launcher.confirmBegin(kind, target));
  if (!offer?.ticket) return null;
  return (await confirmDialog(offer)) ? offer.ticket : null;
}
function confirmDialog({ title, message, detail, go, danger }) {
  const dialog = $("confirm-dialog");
  text("confirm-title", title);
  text("confirm-message", message);
  text("confirm-detail", detail || "");
  text("confirm-go", go);
  $("confirm-go").className = danger ? "danger" : "primary";
  return new Promise((resolve) => {
    let ok = false;
    $("confirm-go").onclick = () => {
      ok = true;
      shut(dialog);
    };
    dialog.addEventListener("shut", () => resolve(ok), { once: true });
    dialog.showModal();
    $("confirm-go").focus();
  });
}

// Objetos ∞ and Robos y entregas open as sheets: the same native sections,
// moved into the dialog and returned when it closes.
const sheets = {
  objetos: ["Objetos ∞", ["quick-article", "write-article"]],
  robos: ["Robos y entregas", ["transfer-article", "write-article"]],
};
const homes = new Map();
function fillSheet(view) {
  returnSheet();
  const [title, ids] = sheets[view];
  text("sheet-title", title);
  $("sheet-dialog").dataset.sheet = view;
  for (const id of ids) {
    const section = $(id),
      mark = document.createComment(id);
    section.before(mark);
    homes.set(section, mark);
    $("sheet-body").append(section);
  }
  if (view === "objetos" && lastState?.selected_save && !lastState.quick_items)
    void action(() => window.launcher.quickItems());
}
function returnSheet() {
  for (const [section, mark] of homes) mark.replaceWith(section);
  homes.clear();
}
function focusItem(item) {
  const input = item
    ? document.querySelector(`.quick-item[data-item="${item}"] .quick-input`)
    : null;
  if (input && !input.disabled) input.focus();
}

window.launcher.onNavigate(({ view, panel, item, tab: hub }) => {
  if (view === "panel") return enterHub(hub);
  if (view === "modal") {
    closeDialogs();
    mode("modal");
    return openDialog(panel, item);
  }
  if (view === "strip" || view === "offline") {
    closeDialogs();
    mode(view);
    if (view === "offline") tab("partidas");
    return;
  }
  // Classic tabs: "Añadir a mi partida" opens the native quick items.
  tab("partidas");
  $("quick-title").scrollIntoView();
  focusItem(item);
});
if (unified) mode("strip");
$("previous-box").onclick = () => {
  boxIndex--;
  renderBox();
};
$("next-box").onclick = () => {
  boxIndex++;
  renderBox();
};
$("close-details").onclick = () => $("details").close();
$("select-save").onclick = () => action(() => window.launcher.chooseSave());
$("selector-manual").onclick = () =>
  action(async () => {
    const result = await window.launcher.chooseSave();
    if (result?.status !== "CANCELLED") shut($("selector-dialog"));
    return result;
  });
$("export-save").onclick = async () => {
  const ticket = await confirmWith("export", "current");
  if (ticket)
    void action(() =>
      window.launcher.exportSave($("backup-emulator-closed").checked, ticket),
    );
};
$("refresh-backups").onclick = () => action(() => window.launcher.backups());
$("backup-emulator-closed").onchange = () => {
  $("export-save").disabled =
    !exportAvailable || !$("backup-emulator-closed").checked;
};
$("retry").onclick = () => action(() => window.launcher.retry());
$("logout").onclick = () => action(() => window.launcher.logout());
$("enable-sync").onclick = () => action(() => window.launcher.sync());
$("emulator-closed").onchange = () => {
  $("confirm-write").disabled = !pendingWrite || !$("emulator-closed").checked;
};
$("confirm-write").onclick = async () => {
  const operation = pendingWrite;
  const ticket = await confirmWith("write", operation);
  if (ticket)
    void action(() =>
      window.launcher.confirmWrite(
        operation,
        $("emulator-closed").checked,
        ticket,
      ),
    );
};
$("reconcile-write").onclick = () =>
  action(() => window.launcher.reconcileWrite());
$("login").onsubmit = (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget),
    trainer = String(form.get("trainer")),
    pin = String(form.get("pin"));
  event.currentTarget.elements.pin.value = "";
  void action(() => window.launcher.login(trainer, pin));
};

// Save selector: every candidate with what is known before reading it.
function renderSelector(state, force) {
  const found = state?.emulator_saves || [];
  const list = $("selector-list");
  const key = JSON.stringify([found, state?.selected_save, observation?.game]);
  if (!force && list.dataset.key === key) return;
  list.dataset.key = key;
  $("selector-empty").hidden = found.length > 0;
  list.replaceChildren(
    ...found.map((save) => {
      const current = save.path === state.selected_save;
      const button = document.createElement("button"),
        badge = document.createElement("span"),
        body = document.createElement("span"),
        title = document.createElement("strong"),
        meta = document.createElement("span"),
        where = document.createElement("span"),
        status = document.createElement("span");
      button.type = "button";
      button.className = "save-option";
      button.dataset.current = String(current);
      badge.className = "save-option-badge";
      badge.textContent = save.game || "?";
      body.className = "save-option-body";
      title.textContent = `Pokémon ${gameNames[save.game] || "partida"}${current && observation ? ` · ${observation.trainer.name}` : ""}`;
      meta.textContent = [
        save.emulator || "Emulador",
        save.modified
          ? `modificada ${when(save.modified)}`
          : "fecha no disponible",
      ].join(" · ");
      // Only the tail of the path: enough to tell saves apart, no user name.
      where.className = "save-option-path";
      where.textContent = `…/${save.path.split(/[\\/]/).slice(-6, -3).join("/")}`;
      status.className = "save-option-status";
      status.textContent = current
        ? state.local_status === "READY"
          ? "Elegida · validada"
          : "Elegida"
        : save.game
          ? "Compatible · se valida al elegirla"
          : "Juego sin identificar · se valida al elegirla";
      body.append(title, meta, where);
      button.append(badge, body, status);
      button.onclick = () =>
        action(async () => {
          if (!current) await window.launcher.selectDiscovered(save.path);
          shut($("selector-dialog"));
        });
      return button;
    }),
  );
}
$("selector-rescan").onclick = () => action(discover);
$("choose-save").onclick = () => present("selector");
$("discover-primary").onclick = () => action(discover);
async function discover() {
  const result = await window.launcher.discoverSaves();
  if (result?.count === 0)
    text(
      "message",
      "No se han encontrado partidas compatibles en los emuladores de este equipo.",
    );
  else if (result?.count > 1 && !result.auto_selected) {
    // Wait for the core to publish the list, then let the trainer choose.
    await poll();
    present("selector");
  }
  return result;
}

// Restore: a summary, the safety checks, closed emulator and "Confirmo".
let restoreTarget = null;
function restoreChecks(state) {
  const write = state?.write || {};
  return [
    [Boolean(restoreTarget?.verified), "Copia verificada por su huella"],
    [
      !robberyOpen(state?.cloud?.data?.transfers) &&
        !state?.cloud?.data?.mandatory_sync,
      "Sin entregas de robo pendientes",
    ],
    [
      !write.busy && write.status !== "RECOVERY_REQUIRED",
      "Ninguna otra operación en curso",
    ],
  ];
}
let restoreTicket = null;
// Main describes this backup of this save and issues the ticket that the
// typed "Confirmo" is bound to; a stale or other backup is refused by main.
async function openRestore(backup) {
  const offer = await action(() =>
    window.launcher.confirmBegin("restore", backup.operation_id),
  );
  if (!offer?.ticket) return;
  restoreTarget = backup;
  restoreTicket = offer.ticket;
  $("restore-summary").replaceChildren();
  for (const [label, value] of offer.facts || []) {
    const dt = document.createElement("dt"),
      dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    $("restore-summary").append(dt, dd);
  }
  $("restore-closed").checked = false;
  $("restore-word").value = "";
  updateRestore();
  present("restore");
  $("restore-closed").focus();
}
function updateRestore() {
  if (!restoreTarget) return;
  const checks = restoreChecks(lastState);
  $("restore-checks").replaceChildren(
    ...checks.map(([ok, label]) => {
      const li = document.createElement("li");
      li.dataset.ok = String(ok);
      li.textContent = `${ok ? "✓" : "✕"} ${label}`;
      return li;
    }),
  );
  $("restore-confirm").disabled = !(
    checks.every(([ok]) => ok) &&
    $("restore-closed").checked &&
    $("restore-word").value === "Confirmo"
  );
}
$("restore-closed").onchange = updateRestore;
$("restore-word").oninput = updateRestore;
// Enter never confirms: the button is the only way.
$("restore-word").onkeydown = (event) => {
  if (event.key === "Enter") event.preventDefault();
};
$("restore-confirm").onclick = () => {
  const operation = restoreTarget?.operation_id,
    typed = $("restore-word").value,
    ticket = restoreTicket;
  if (!operation || !ticket || $("restore-confirm").disabled) return;
  restoreTicket = null;
  shut($("restore-dialog"));
  void action(() =>
    window.launcher.restoreBackup(operation, true, typed, ticket),
  );
};

// Robbery actions: only this trainer's own leg; no peer data, no second logic.
const transferProgress = {
  REQUESTED: "Robo solicitado. PokeApp está comprobando que es válido.",
  ELIGIBILITY_VERIFIED: "Robo válido. PokeApp lo está adjudicando.",
  COMPETITIVELY_ADJUDICATED:
    "Robo adjudicado por PokeApp: es definitivo. Falta la entrega física en las partidas.",
  RECONCILED:
    "Robo completado: decisión y entrega física verificadas en las dos partidas.",
  PREPARING: "Ninguna copia preparada todavía.",
  WAITING_OTHER: "Una copia preparada; falta la del otro entrenador.",
  PENDING_SOURCE:
    "Las dos copias están preparadas; falta retirar el Pokémon de la partida de origen.",
  VERIFYING_SOURCE:
    "La partida de origen ya está modificada; PokeApp la está verificando.",
  PENDING_DESTINATION:
    "Origen verificado; falta añadir el Pokémon en la partida de destino.",
  VERIFYING_BOTH:
    "La partida de destino ya está modificada; PokeApp la está verificando.",
  BOTH_VERIFIED_PENDING_IDENTITY:
    "Las dos partidas están verificadas; PokeApp está registrando la propiedad.",
  COMMITTED: "Robo completado y registrado por PokeApp.",
  CANCELLED: "Robo cancelado antes de aplicar. No se ha consumido el objeto.",
  BLOCKED_UNCERTAIN: "Operación bloqueada.",
};
const obligationText = {
  DONOR_PHYSICAL_PENDING:
    "Sincronización obligatoria: PokeApp debe retirar este Pokémon de tu partida antes de cualquier otra sincronización.",
  DONOR_RECOVERY_REQUIRED:
    "No se pudo preparar la retirada sobre tu partida actual. Cierra el juego y vuelve a intentarlo.",
  DONOR_VERIFIED: "Retirada verificada en tu partida.",
  DONOR_ABSENT_VERIFIED: "Tu partida ya no tenía ese Pokémon: verificado.",
  DONOR_BLOCKED_UNCERTAIN:
    "Retirada bloqueada: necesitas recuperación asistida.",
  RECIPIENT_PHYSICAL_PENDING:
    "Pendiente de recepción: el Pokémon aún no está en tu partida y no puedes usarlo.",
  RECIPIENT_RECOVERY_REQUIRED:
    "No se pudo preparar la entrega en tu partida actual (¿cajas llenas?). Libera un hueco y vuelve a intentarlo.",
  RECIPIENT_VERIFIED: "Pokémon recibido y verificado en tu partida.",
  RECIPIENT_BLOCKED_UNCERTAIN:
    "Entrega bloqueada: necesitas recuperación asistida.",
};
function transferActions(t) {
  const open = [
    "DONOR_PHYSICAL_PENDING",
    "DONOR_RECOVERY_REQUIRED",
    "RECIPIENT_PHYSICAL_PENDING",
    "RECIPIENT_RECOVERY_REQUIRED",
  ].includes(t.obligation);
  if (t.obligation)
    // Decided robbery: only this side's physical obligation, never a veto.
    return { fulfil: open, refresh: true };
  return {
    prepare:
      t.planned &&
      !t.claimed &&
      ["PREPARING", "WAITING_OTHER"].includes(t.status),
    apply:
      (t.side === "source" &&
        ["PENDING_SOURCE", "VERIFYING_SOURCE"].includes(t.status)) ||
      (t.side === "destination" &&
        ["PENDING_DESTINATION", "VERIFYING_BOTH"].includes(t.status)),
    cancel:
      t.side === "destination" &&
      !t.apply_started &&
      ["PREPARING", "WAITING_OTHER", "PENDING_SOURCE"].includes(t.status),
    refresh: true,
  };
}
function renderTransfers(state) {
  const items = state.cloud?.data?.transfers || [];
  const write = state.write || {};
  const enabled = Boolean(write.transfer_application_enabled);
  const closed = $("transfer-emulator-closed").checked;
  text(
    "transfer-summary",
    !items.length
      ? "No hay robos en curso."
      : !enabled
        ? "Puedes consultar tus robos, pero este Launcher aún no aplica cambios: falta la certificación con Lime3DS."
        : items.some((t) => t.mandatory)
          ? "Sincronización obligatoria: PokeApp ya ha decidido un robo sobre tu partida. Tu sincronización normal está en pausa hasta retirar ese Pokémon."
          : "Sigue los pasos de cada robo. Solo puedes confirmar lo que te corresponde.",
  );
  const key = JSON.stringify([
    items,
    enabled,
    write.busy,
    write.status,
    closed,
    state.selected_save,
    revision,
  ]);
  const list = $("transfer-list");
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  list.replaceChildren(
    ...items.map((t) => {
      const card = document.createElement("div");
      card.className = "transfer-card";
      card.dataset.id = t.authorization_id;
      const line = (value, cls) => {
        const p = document.createElement("p");
        p.textContent = value;
        if (cls) p.className = cls;
        card.append(p);
      };
      line(
        t.side === "source"
          ? "Te van a robar un Pokémon: tu partida es la de origen."
          : "Has solicitado este robo: tu partida es la de destino.",
        "transfer-role",
      );
      const where = t.location;
      const pokemon =
        where && t.side === "source"
          ? where.party
            ? observation?.party?.[where.slot - 1]
            : observation?.boxes?.[where.box - 1]?.slots?.[where.slot - 1]
          : null;
      if (where)
        line(
          t.side === "source"
            ? `Pokémon: ${pokemon ? pokemon.nickname || `#${pokemon.species_id}` : "el indicado por PokeApp"} · ${where.party ? "Equipo" : `Caja ${where.box}`}, posición ${where.slot}.`
            : `Llegará a tu partida en la Caja ${where.box}, posición ${where.slot}.`,
        );
      line(`Partida: ${state.selected_save || "sin seleccionar"}`, "muted");
      line(
        transferProgress[t.status] || "Estado no disponible.",
        "transfer-progress",
      );
      if (t.obligation)
        line(
          obligationText[t.obligation] || "Estado no disponible.",
          t.mandatory ? "transfer-help" : "transfer-progress",
        );
      if (t.apply_started && !t.obligation && t.status !== "COMMITTED")
        line(
          "Tu parte ya está aplicada en tu partida, pero el robo NO es definitivo hasta que PokeApp verifique las dos partidas.",
        );
      if (
        t.status === "BLOCKED_UNCERTAIN" ||
        write.status === "RECOVERY_REQUIRED"
      )
        line(
          "Necesitas asistencia: no abras el emulador, conserva las copias y contacta con el administrador. No restaures la partida por tu cuenta.",
          "transfer-help",
        );
      const actions = transferActions(t);
      if (enabled && (actions.prepare || actions.apply || actions.fulfil))
        line(
          "Cierra el juego y el emulador y marca la casilla antes de continuar.",
        );
      const labels = {
        prepare: "Preparar copia",
        apply: t.apply_started ? "Reanudar mi parte" : "Aplicar mi parte",
        fulfil:
          t.side === "source"
            ? "Aplicar retirada obligatoria"
            : "Recibir el Pokémon",
        cancel: "Cancelar robo",
        refresh: "Comprobar estado",
      };
      for (const kind of ["prepare", "apply", "fulfil", "cancel", "refresh"]) {
        if (!actions[kind]) continue;
        const button = document.createElement("button");
        button.textContent = labels[kind];
        button.dataset.kind = kind;
        button.disabled =
          !enabled ||
          write.busy ||
          (["prepare", "apply", "fulfil"].includes(kind) && !closed);
        button.onclick = async () => {
          // Main says what this step does to the local file before it runs.
          const ticket =
            kind === "refresh"
              ? null
              : await confirmWith("transfer:" + kind, t.authorization_id);
          if (kind === "refresh" || ticket)
            void action(() =>
              window.launcher.transfer(
                kind,
                t.authorization_id,
                closed,
                ticket,
              ),
            );
        };
        card.append(button);
      }
      return card;
    }),
  );
}
$("transfer-emulator-closed").onchange = () =>
  lastState && renderTransfers(lastState);

// Quick items: ONE text state per item, shared by keyboard, + and −.
const quantities = { rare_candy: "1", heart_scale: "1" };
function renderQuick(state) {
  const write = state.write || {};
  const view = state.quick_items;
  const enabled = Boolean(view?.application_enabled);
  const adding = (write.description || "").startsWith("Añadir");
  text(
    "quick-state",
    !state.selected_save
      ? "Selecciona tu partida para ver tus objetos."
      : write.status === "RECOVERY_REQUIRED"
        ? "Recuperación necesaria. Conserva las copias y no abras el emulador."
        : write.busy
          ? "Preparando copia, aplicando o verificando. Mantén el juego cerrado."
          : write.status === "AWAITING_CONFIRMATION" && adding
            ? "Esperando cierre del emulador: marca la casilla y confirma en «Cambios en tu partida»."
            : write.status === "APPLIED_VERIFIED" && adding
              ? "Aplicado correctamente: la partida se ha releído y verificado."
              : state.quick_item_error
                ? "Error recuperable: " + state.quick_item_error
                : !view
                  ? "Pulsa «Leer objetos de la partida» para ver tus cantidades."
                  : !enabled
                    ? "Operación bloqueada: añadir objetos se activará tras la certificación real con Lime3DS. Puedes consultar tus cantidades."
                    : "Listo para añadir.",
  );
  for (const row of document.querySelectorAll(".quick-item")) {
    const item = row.dataset.item;
    const info = view?.items?.[item];
    const input = row.querySelector(".quick-input");
    if (document.activeElement !== input && input.value !== quantities[item])
      input.value = quantities[item];
    const parsed = PokeQuantity.parse(quantities[item], info?.addable ?? 0);
    row.querySelector(".quick-count").textContent = info
      ? `Tienes ${info.count} · máximo ${info.max}`
      : "";
    row.querySelector(".quick-error").textContent =
      info && parsed.error ? parsed.error : "";
    const blocked =
      !enabled ||
      !info ||
      write.busy ||
      ["RECOVERY_REQUIRED", "AWAITING_CONFIRMATION", "PREPARED"].includes(
        write.status,
      );
    for (const name of [".quick-minus", ".quick-plus", ".quick-input"])
      row.querySelector(name).disabled = blocked;
    row.querySelector(".quick-add").disabled =
      blocked || parsed.value === null || !$("quick-emulator-closed").checked;
  }
}
for (const row of document.querySelectorAll(".quick-item")) {
  const item = row.dataset.item;
  const input = row.querySelector(".quick-input");
  const max = () => lastState?.quick_items?.items?.[item]?.addable ?? 0;
  const update = (value) => {
    quantities[item] = value;
    if (input.value !== value) input.value = value;
    if (lastState) renderQuick(lastState);
  };
  input.oninput = () => update(PokeQuantity.clean(input.value));
  row.querySelector(".quick-minus").onclick = () =>
    update(PokeQuantity.step(quantities[item], -1, max()));
  row.querySelector(".quick-plus").onclick = () =>
    update(PokeQuantity.step(quantities[item], 1, max()));
  row.querySelector(".quick-add").onclick = () => {
    const parsed = PokeQuantity.parse(quantities[item], max());
    if (parsed.value === null) return update(quantities[item]);
    action(() =>
      window.launcher.addQuickItem(
        item,
        parsed.value,
        $("quick-emulator-closed").checked,
      ),
    );
  };
}
$("quick-emulator-closed").onchange = () => lastState && renderQuick(lastState);
$("quick-refresh").onclick = () => action(() => window.launcher.quickItems());

function renderEmulator(state) {
  text(
    "emulator-state",
    `Emulador principal: ${state.emulator?.primary_candidate || "Lime3DS"} · compatibilidad pendiente de certificar. Cierra siempre el juego y el emulador antes de un cambio.`,
  );
  const list = $("discovered-saves");
  const found = state.emulator_saves || [];
  const key = JSON.stringify([found, state.selected_save]);
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  list.replaceChildren(
    ...found.map((save) => {
      const button = document.createElement("button");
      const current = save.path === state.selected_save;
      button.textContent = `${current ? "Activa · " : "Usar "}Pokémon ${gameNames[save.game] || "partida"} · ${save.emulator}`;
      button.dataset.current = String(current);
      button.disabled = current;
      button.onclick = () =>
        action(() => window.launcher.selectDiscovered(save.path));
      return button;
    }),
  );
}
$("discover-saves").onclick = () => action(discover);

// Updates. Main checks the signed feed at start and on «Buscar actualizaciones»;
// a newer version opens this popup by itself once (never again after «Más
// tarde» for that version). «Actualizar» downloads, verifies, installs and
// restarts; nothing is forced and nothing is shown done before it is.
const megabytes = (bytes) =>
  `${(bytes / 1024 / 1024).toLocaleString("es-ES", { maximumFractionDigits: 1 })} MB`;
const updateBusy = ["DOWNLOADING", "VERIFYING", "WAITING", "INSTALLING"];
const blockerText = {
  WRITE_IN_PROGRESS: "un cambio en tu partida",
  WRITE_PENDING: "un cambio pendiente de confirmar",
  RECOVERY_PENDING: "una recuperación pendiente",
  SYNC_IN_PROGRESS: "la sincronización",
  TRANSFER_IN_PROGRESS: "una entrega de robo",
  STATE_UNAVAILABLE: "el núcleo del Launcher",
};
const updateErrors = {
  SIGNATURE_INVALID:
    "La actualización no supera la verificación de firma. No se instalará.",
  SIGNATURE_MISSING: "La actualización no viene firmada. No se instalará.",
  INTEGRITY_FAILED:
    "El archivo descargado no coincide con el firmado. Se ha descartado.",
  DOWNLOAD_INTERRUPTED:
    "Se perdió la conexión durante la descarga. Puedes reintentarlo.",
  DOWNLOAD_FAILED: "No se pudo descargar ahora mismo. Puedes reintentarlo.",
  DOWNGRADE_REJECTED: "Se ha ignorado una versión anterior a la tuya.",
  INCOMPATIBLE_VERSION:
    "Esta versión no se instala sobre la tuya: descárgala desde la web de PokeApp.",
  CHANNEL_MISMATCH: "La versión ofrecida es de otro canal. Se ha ignorado.",
  INSECURE_URL: "La descarga no usa una conexión segura. Se ha ignorado.",
  MANIFEST_INVALID:
    "La información de la versión no es válida. Se ha ignorado.",
  UPDATE_CHECK_FAILED:
    "No se pudo comprobar ahora mismo. Tu Launcher sigue funcionando.",
};
let updateAutoShown = new Set(),
  updateWatch = null;
async function renderUpdate() {
  const u = await window.launcher.updateState().catch(() => null);
  if (!u) return;
  lastUpdate = u;
  const version = `v${u.current}${u.channel === "private" ? " · canal privado" : ""}`;
  text("launcher-version", version);
  text("launcher-version-detail", version);
  const dialogOpen = $("update-dialog").open;
  // Discreet strip: an offer not postponed, or an update running unseen.
  const offer = ["AVAILABLE", "READY"].includes(u.status) && u.prompt;
  const running = updateBusy.includes(u.status);
  $("update-banner").hidden = dialogOpen || !(offer || running);
  text(
    "update-text",
    running
      ? `Actualizando PokeApp Launcher ${u.version}…${u.progress ? ` ${percent(u.progress)} %` : ""}`
      : offer
        ? `Nueva versión ${u.version} de PokeApp Launcher.`
        : "",
  );
  $("update-open").hidden = $("update-banner").hidden;
  if (dialogOpen) fillUpdateDialog(u);
  // Once per version, over the web only: never over another dialog, the hub
  // in use or the offline tools.
  if (
    offer &&
    !updateAutoShown.has(u.version) &&
    !anyOpen() &&
    document.body.dataset.mode === "strip"
  ) {
    updateAutoShown.add(u.version);
    present("update", { check: false });
  }
  reportStrip();
}
const percent = ({ received, total }) =>
  total ? Math.floor((received / total) * 100) : 0;
function fillUpdateDialog(u) {
  const busy = updateBusy.includes(u.status);
  const versions = u.version
    ? `Versión ${u.version} · tienes ${u.current}`
    : `PokeApp Launcher ${u.current}`;
  const message = {
    CHECKING: "Buscando actualizaciones…",
    IDLE: "Buscando actualizaciones…",
    UP_TO_DATE: "Estás utilizando la última versión.",
    AVAILABLE: "Hay una versión nueva de PokeApp Launcher.",
    READY: u.deferred
      ? `Lista para instalar. Esperando a que termine ${blockerText[u.deferred] || "una operación en curso"}.`
      : "La nueva versión está descargada y verificada.",
    DOWNLOADING: `Descargando la versión ${u.version}…`,
    VERIFYING: "Verificando la firma y la integridad…",
    WAITING: `Esperando a que termine ${blockerText[u.deferred] || "una operación en curso"}…`,
    INSTALLING:
      "Instalando. PokeApp Launcher se reiniciará solo; tu sesión, tu partida y tus copias se conservan.",
    ERROR:
      updateErrors[u.reason] ||
      "No se pudo completar la actualización. Tu Launcher sigue funcionando.",
    DISABLED:
      "Este Launcher no tiene activado un canal de actualizaciones automáticas. Cuando haya una versión nueva, descárgala desde la web de PokeApp («Descargar Launcher»).",
  }[u.status];
  $("update-hero").dataset.tone =
    u.status === "ERROR"
      ? "error"
      : ["AVAILABLE", "READY"].includes(u.status) || busy
        ? "new"
        : "idle";
  $("update-hero").querySelector(".update-badge").textContent =
    u.status === "ERROR"
      ? "!"
      : u.status === "UP_TO_DATE"
        ? "✓"
        : ["CHECKING", "IDLE"].includes(u.status)
          ? "↻"
          : "↑";
  text(
    "update-title",
    u.version && u.status !== "UP_TO_DATE"
      ? "Actualización disponible"
      : "Actualizaciones",
  );
  text("update-message", message || "Estado de actualización no disponible.");
  text("update-versions", versions);
  // Novedades: one line per change, as signed in the manifest.
  const notes =
    ["AVAILABLE", "READY"].includes(u.status) && u.notes
      ? u.notes.split(/\n+/).filter((line) => line.trim())
      : [];
  $("update-notes").replaceChildren(
    ...notes.map((line) => {
      const li = document.createElement("li");
      li.textContent = line.replace(/^[-•]\s*/, "");
      return li;
    }),
  );
  const facts = [];
  if (u.size && ["AVAILABLE", "READY", "DOWNLOADING"].includes(u.status))
    facts.push(["Tamaño", megabytes(u.size)]);
  if (["AVAILABLE", "READY"].includes(u.status) || busy)
    facts.push([
      "Seguridad",
      "Versión firmada; el instalador se comprueba (SHA-512 y tamaño) antes de ejecutarse",
    ]);
  if (["AVAILABLE", "READY"].includes(u.status))
    facts.push(["Se conserva", "Sesión, partida elegida, copias y ajustes"]);
  $("update-facts").hidden = !facts.length;
  $("update-facts").replaceChildren(
    ...facts.flatMap(([label, value]) => {
      const dt = document.createElement("dt"),
        dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = value;
      return [dt, dd];
    }),
  );
  $("update-progress-box").hidden = !busy;
  const progress = u.progress || { received: 0, total: u.size || 0 };
  $("update-progress").value =
    u.status === "DOWNLOADING" ? percent(progress) : busy ? 100 : 0;
  text(
    "update-progress-text",
    u.status === "DOWNLOADING"
      ? `${megabytes(progress.received)} de ${megabytes(progress.total)} · ${percent(progress)} %`
      : u.status === "VERIFYING"
        ? "Comprobando…"
        : u.status === "INSTALLING"
          ? "Reiniciando…"
          : "",
  );
  const canApply =
    ["AVAILABLE", "READY"].includes(u.status) ||
    (u.status === "ERROR" && Boolean(u.version));
  $("update-go").hidden = !(canApply || u.status === "ERROR");
  text(
    "update-go",
    u.status === "READY"
      ? "Instalar ahora"
      : u.status === "ERROR"
        ? "Reintentar"
        : "Actualizar",
  );
  $("update-later").hidden = busy;
  text(
    "update-later",
    ["AVAILABLE", "READY"].includes(u.status) ? "Más tarde" : "Cerrar",
  );
}
// While something runs, follow it closely (progress), then stop.
function watchUpdate() {
  if (updateWatch) return;
  updateWatch = setInterval(async () => {
    const u = await window.launcher.updateState().catch(() => null);
    if (!u) return;
    lastUpdate = u;
    if ($("update-dialog").open) fillUpdateDialog(u);
    if (!updateBusy.includes(u.status)) {
      clearInterval(updateWatch);
      updateWatch = null;
    }
  }, 250);
}
async function checkForUpdates() {
  if (lastUpdate) fillUpdateDialog({ ...lastUpdate, status: "CHECKING" });
  const u = await window.launcher.checkUpdate().catch(() => null);
  if (u) {
    lastUpdate = u;
    fillUpdateDialog(u);
  } else
    text(
      "update-message",
      "No se pudo comprobar ahora mismo. Inténtalo más tarde.",
    );
}
async function applyUpdate() {
  const u = lastUpdate;
  if (!u) return;
  if (u.status === "ERROR" && !u.version) return checkForUpdates();
  // The popup is the confirmation; main binds it to this signed offer.
  const offer = await action(() =>
    window.launcher.confirmBegin("update", String(u.version)),
  );
  if (!offer?.ticket) return;
  const started = await action(() => window.launcher.applyUpdate(offer.ticket));
  if (started) {
    lastUpdate = { ...u, ...started };
    fillUpdateDialog(lastUpdate);
    watchUpdate();
  }
}
$("check-update").onclick = () => present("update");
$("update-go").onclick = () => void applyUpdate();
$("update-later").onclick = async () => {
  if (["AVAILABLE", "READY"].includes(lastUpdate?.status))
    await action(() => window.launcher.postponeUpdate());
  shut($("update-dialog"));
};
$("update-open").onclick = () => present("update", { check: false });

async function poll() {
  if (polling) return;
  polling = true;
  try {
    const state = await window.launcher.state(revision);
    lastState = state;
    render(state);
    renderQuick(state);
    renderTransfers(state);
    renderEmulator(state);
    renderNotices(state);
    if ($("selector-dialog").open) renderSelector(state);
    if ($("restore-dialog").open) updateRestore();
    autoChoose(state);
    void renderUpdate();
  } catch {
    text(
      "message",
      "Núcleo local no disponible. La lectura ya cargada sigue accesible.",
    );
  } finally {
    polling = false;
  }
}
slots("party", Array(6).fill(null), "Equipo");
renderBox();
void poll();
setInterval(poll, 1000);
