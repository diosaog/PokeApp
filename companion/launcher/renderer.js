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
async function poll() {
  if (polling) return;
  polling = true;
  try {
    render(await window.launcher.state(revision));
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
