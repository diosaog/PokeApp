/* All navigation uses this in-memory local DTO. No browser network access. */
const $ = (id) => document.getElementById(id);
let observation = null,
  revision = null,
  boxIndex = 0,
  polling = false;
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
  if ("observation" in state) {
    observation = state.observation;
    revision = state.receipt_id;
    text(
      "save-identity",
      observation
        ? `${observation.trainer.name} · ${observation.game} · Gen ${observation.generation} · TID ${observation.trainer.tid}`
        : "",
    );
    slots("party", observation?.party || Array(6).fill(null), "Equipo");
    renderBox();
  }
  const local =
    state.local_status === "READY"
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
    state.cloud_status === "ONLINE"
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
    state.cloud_receipt
      ? `Recibida el ${new Date(state.cloud_receipt.received_at).toLocaleString()} · Privada, sin autoridad competitiva`
      : state.cloud_sync
        ? "Sincronización activada. Pendiente de recibo de la nube."
        : "Todavía no hay un recibo de la nube.",
  );
  $("enable-sync").disabled = !observation || !state.principal;
  if (state.outbox?.pending)
    $("receipt").textContent +=
      ` · ${state.outbox.pending} pendiente(s)${state.outbox.paused ? " · Revisa la conexión y pulsa Reintentar" : ""}`;
  $("login").querySelector("button").disabled =
    state.auth_status === "CHECKING";
  const errors = {
    LOGIN_REQUIRED: "Vuelve a iniciar sesión para sincronizar.",
    SESSION_REJECTED: "Sesión no válida. Vuelve a conectar.",
    OBSERVATION_REJECTED:
      "La nube no ha aceptado esta observación. Tu save local sigue disponible.",
    BACKEND_UNAVAILABLE:
      "Sin conexión con PokeApp. Puedes seguir explorando tu save.",
    SYNC_UNAVAILABLE:
      "No se pudo sincronizar. Puedes seguir explorando y reintentar.",
  };
  text("message", errors[state.error] || "");
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
$("retry").onclick = () => action(() => window.launcher.retry());
$("logout").onclick = () => action(() => window.launcher.logout());
$("enable-sync").onclick = () => action(() => window.launcher.sync());
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
