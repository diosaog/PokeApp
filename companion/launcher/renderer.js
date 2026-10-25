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
  backupBusy = false;
const text = (id, value) => {
  $(id).textContent = value;
};
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
  const key = JSON.stringify([
    write?.backups || [],
    write?.busy,
    $("backup-emulator-closed").checked,
  ]);
  if (key !== backupKey) {
    backupKey = key;
    backupRows = write?.backups || [];
    renderBackups(Boolean(write?.busy));
  }
  $("reconcile-write").hidden = !write?.can_reconcile;
  const recovery = write?.status === "RECOVERY_REQUIRED";
  $("select-save").disabled = recovery;
  if ("observation" in state) {
    observation = state.observation;
    revision = state.receipt_id;
    text(
      "save-identity",
      observation
        ? `${observation.trainer.name} · ${{ SN: "Sol", MN: "Luna", US: "Ultrasol", UM: "Ultraluna", OR: "Rubí Omega", AS: "Zafiro Alfa" }[observation.game] || observation.game} · Gen ${observation.generation} · TID ${observation.trainer.tid}`
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
  text(
    "receipt",
    state.cloud_status === "OFFLINE"
      ? "Sin conexión"
      : state.error || state.outbox?.paused
        ? "No se pudo sincronizar"
        : state.cloud_receipt?.status === "registered" &&
            state.cloud_receipt.is_current
          ? "Sincronizado"
          : state.cloud_sync && state.outbox?.pending
            ? "Sincronizando…"
            : "Sin sincronizar",
  );
  $("enable-sync").disabled = recovery || !observation || !state.principal;
  if (state.outbox?.pending)
    $("receipt").textContent +=
      ` · ${state.outbox.pending} pendiente(s)${state.outbox.paused ? " · Revisa la conexión y pulsa Reintentar" : ""}`;
  $("login").querySelector("button").disabled =
    state.auth_status === "CHECKING";
  const errors = {
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
  text("message", errors[state.error] || "");
}

function renderBackups(busy) {
  const list = $("backup-list");
  list.replaceChildren();
  if (!backupRows.length) {
    list.textContent =
      "No hay copias cargadas para esta partida. Pulsa Ver / actualizar copias.";
    return;
  }
  for (const backup of backupRows) {
    const row = document.createElement("p"),
      label = document.createElement("span"),
      copy = document.createElement("button");
    label.textContent = `${backup.game} · ${backup.created_at ? new Date(backup.created_at).toLocaleString("es-ES") : "Fecha no disponible"} · ${backup.role === "before_restore" ? "Antes de restaurar" : "Original"} · ${backup.verified ? "Verificada" : "Inválida o ilegible"} · ${["RECOVERY_REQUIRED", "PREPARED"].includes(backup.status) ? "Recuperación pendiente" : "Conservada"} `;
    copy.textContent = "Guardar copia…";
    copy.disabled = !backup.verified || busy;
    copy.onclick = () =>
      action(() =>
        window.launcher.saveBackup(backup.operation_id, backup.role),
      );
    row.append(label, copy);
    if (backup.can_restore) {
      const restore = document.createElement("button");
      restore.textContent = "Restaurar copia…";
      restore.disabled = busy || !$("backup-emulator-closed").checked;
      restore.onclick = () =>
        action(() =>
          window.launcher.restoreBackup(
            backup.operation_id,
            $("backup-emulator-closed").checked,
          ),
        );
      row.append(restore);
    }
    list.append(row);
  }
}
async function action(fn) {
  try {
    const result = await fn();
    if (result?.status === "BUSY")
      text("message", "Hay una operación pendiente.");
  } catch {
    text("message", "No se pudo contactar con el núcleo local del Launcher.");
  }
}
function tab(cloud) {
  $("save-view").hidden = cloud;
  $("cloud-view").hidden = !cloud;
  $("save-tab").setAttribute("aria-pressed", String(!cloud));
  $("cloud-tab").setAttribute("aria-pressed", String(cloud));
}
$("save-tab").onclick = () => tab(false);
$("cloud-tab").onclick = () => tab(true);
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
$("export-save").onclick = () =>
  action(() => window.launcher.exportSave($("backup-emulator-closed").checked));
$("refresh-backups").onclick = () => action(() => window.launcher.backups());
$("backup-emulator-closed").onchange = () => {
  backupKey = "";
  $("export-save").disabled =
    !exportAvailable || !$("backup-emulator-closed").checked;
  renderBackups(backupBusy);
};
$("retry").onclick = () => action(() => window.launcher.retry());
$("logout").onclick = () => action(() => window.launcher.logout());
$("enable-sync").onclick = () => action(() => window.launcher.sync());
$("emulator-closed").onchange = () => {
  $("confirm-write").disabled = !pendingWrite || !$("emulator-closed").checked;
};
$("confirm-write").onclick = () =>
  action(() =>
    window.launcher.confirmWrite(pendingWrite, $("emulator-closed").checked),
  );
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
// Robbery actions: only this trainer's own leg; no peer data, no second logic.
const transferProgress = {
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
function transferActions(t) {
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
      : enabled
        ? "Sigue los pasos de cada robo. Solo puedes confirmar lo que te corresponde."
        : "Puedes consultar tus robos, pero este Launcher aún no aplica cambios: falta la certificación con Lime3DS.",
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
          ? observation?.boxes?.[where.box - 1]?.slots?.[where.slot - 1]
          : null;
      if (where)
        line(
          t.side === "source"
            ? `Pokémon: ${pokemon ? pokemon.nickname || `#${pokemon.species_id}` : "el indicado por PokeApp"} · Caja ${where.box}, posición ${where.slot}.`
            : `Llegará a tu partida en la Caja ${where.box}, posición ${where.slot}.`,
        );
      line(`Partida: ${state.selected_save || "sin seleccionar"}`, "muted");
      line(
        transferProgress[t.status] || "Estado no disponible.",
        "transfer-progress",
      );
      if (t.apply_started && t.status !== "COMMITTED")
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
      if (enabled && (actions.prepare || actions.apply))
        line(
          "Cierra el juego y el emulador y marca la casilla antes de continuar.",
        );
      const labels = {
        prepare: "Preparar copia",
        apply: t.apply_started ? "Reanudar mi parte" : "Aplicar mi parte",
        cancel: "Cancelar robo",
        refresh: "Comprobar estado",
      };
      for (const kind of ["prepare", "apply", "cancel", "refresh"]) {
        if (!actions[kind]) continue;
        const button = document.createElement("button");
        button.textContent = labels[kind];
        button.dataset.kind = kind;
        button.disabled =
          !enabled ||
          write.busy ||
          (["prepare", "apply"].includes(kind) && !closed);
        button.onclick = () =>
          action(() =>
            window.launcher.transfer(kind, t.authorization_id, closed),
          );
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
let lastState = null;
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
  const key = JSON.stringify(found);
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  list.replaceChildren(
    ...found.map((save) => {
      const button = document.createElement("button");
      button.textContent = `Usar Pokémon ${gameNames[save.game] || "partida"} · ${save.emulator}`;
      button.onclick = () =>
        action(() => window.launcher.selectDiscovered(save.path));
      return button;
    }),
  );
}
$("discover-saves").onclick = () =>
  action(async () => {
    const result = await window.launcher.discoverSaves();
    if (result?.count === 0)
      text(
        "message",
        "No se han encontrado partidas compatibles en Lime3DS, Azahar o Citra.",
      );
    return result;
  });

let deferredReason = null;
async function renderUpdate() {
  const u = await window.launcher.updateState().catch(() => null);
  if (!u) return;
  text(
    "launcher-version",
    `v${u.current}${u.channel === "private" ? " · canal privado" : ""}`,
  );
  const messages = {
    AVAILABLE: `Nueva versión ${u.version} disponible (tienes ${u.current}). ${u.notes || ""}`,
    DOWNLOADING: `Descargando y verificando la versión ${u.version}…`,
    DOWNLOADED: deferredReason
      ? "Actualización verificada. Se podrá instalar cuando termine la operación en curso; no se interrumpe ningún cambio."
      : `Versión ${u.version || u.recovered?.version} descargada y verificada.`,
    INSTALLING: "Instalando la actualización…",
  };
  $("update-banner").hidden = !messages[u.status];
  text("update-text", messages[u.status] || "");
  $("update-download").hidden = u.status !== "AVAILABLE";
  $("update-install").hidden = u.status !== "DOWNLOADED";
}
$("update-download").onclick = () =>
  action(() => window.launcher.downloadUpdate());
$("update-install").onclick = () =>
  action(async () => {
    const result = await window.launcher.installUpdate();
    deferredReason = result?.deferred || null;
    return result;
  });

async function poll() {
  if (polling) return;
  polling = true;
  try {
    const state = await window.launcher.state(revision);
    render(state);
    lastState = state;
    renderQuick(state);
    renderTransfers(state);
    renderEmulator(state);
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
