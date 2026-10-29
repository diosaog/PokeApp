// In-app confirmations (Phase 28). The tools page shows a dialog with the
// summary main computed from the core's state; the action then has to present
// the ticket main issued for it. A ticket is single use, short lived and bound
// to the kind of action, its target and a fingerprint of the state it was
// issued for, so a stale, reused or swapped confirmation is refused.
const crypto = require("node:crypto");

const STALE =
  "La confirmación ha caducado o ya no corresponde a esta operación. Vuelve a abrirla.";

function createConfirmations({ ttlMs = 120000, now = Date.now } = {}) {
  const tickets = new Map();
  const sweep = () => {
    for (const [id, ticket] of tickets)
      if (ticket.expires <= now()) tickets.delete(id);
  };
  return {
    issue(kind, target, fingerprint) {
      if (typeof kind !== "string" || typeof target !== "string")
        throw new Error("Confirmación no válida");
      sweep();
      // One open confirmation per action: a new dialog supersedes the old one.
      for (const [id, ticket] of tickets)
        if (ticket.kind === kind && ticket.target === target)
          tickets.delete(id);
      const id = crypto.randomBytes(18).toString("base64url");
      tickets.set(id, {
        kind,
        target,
        fingerprint: JSON.stringify(fingerprint),
        expires: now() + ttlMs,
      });
      return id;
    },
    redeem(id, kind, target, fingerprint) {
      const ticket = typeof id === "string" ? tickets.get(id) : undefined;
      // Spent on first use, whether or not it matches.
      if (ticket) tickets.delete(id);
      if (
        !ticket ||
        ticket.expires <= now() ||
        ticket.kind !== kind ||
        ticket.target !== target ||
        ticket.fingerprint !== JSON.stringify(fingerprint)
      )
        throw new Error(STALE);
    },
    get size() {
      sweep();
      return tickets.size;
    },
  };
}

// A robbery whose physical delivery is not verified yet: restoring an older
// file now could duplicate or lose the Pokémon.
const robberyOpen = (transfers) =>
  (transfers || []).some(
    (t) =>
      t.mandatory ||
      (t.obligation && !t.obligation.endsWith("_VERIFIED")) ||
      (t.apply_started && !["COMMITTED", "CANCELLED"].includes(t.status)),
  );
const restorable = (state, operationId) =>
  state.write?.backups?.find(
    (b) =>
      b.operation_id === operationId &&
      b.role === "original" &&
      b.can_restore &&
      b.verified,
  );
const transferFor = (state, authorizationId) =>
  (state.cloud?.data?.transfers || []).find(
    (t) => t.authorization_id === authorizationId,
  );
function fingerprint(kind, target, state) {
  if (kind === "write")
    return [state.selected_save, target, state.write?.description];
  if (kind === "quick-item")
    return [state.selected_save, target, state.receipt_id ?? null];
  if (kind === "delivery")
    return [state.selected_save, target, state.receipt_id ?? null];
  if (kind === "export")
    return [state.selected_save, JSON.stringify(state.write?.export_intent)];
  if (kind === "restore") {
    const backup = restorable(state, target);
    return [state.selected_save, target, backup?.game, backup?.created_at];
  }
  const t = transferFor(state, target);
  return [
    state.selected_save,
    kind,
    target,
    t?.status,
    t?.obligation ?? null,
    Boolean(t?.apply_started),
    JSON.stringify(t?.location ?? null),
  ];
}
const GAMES = {
  X: "X",
  Y: "Y",
  OR: "Rubí Omega",
  AS: "Zafiro Alfa",
  SN: "Sol",
  MN: "Luna",
  US: "Ultrasol",
  UM: "Ultraluna",
};
const CLOSED =
  "\n\nEl Launcher comprueba antes que el emulador está cerrado y que el archivo está libre; si no, no cambia nada y te dice por qué.";
const ITEMS = { rare_candy: "Caramelo Raro", heart_scale: "Escama Corazón" };
// The dialog text for one action, or an error when it is not available now.
function describe(kind, target, state) {
  const save = state.selected_save || "";
  if (kind === "quick-item") {
    const [item, amount] = target.split(":");
    const quantity = Number(amount);
    const info = state.quick_items?.items?.[item];
    if (!state.selected_save) throw new Error("Selecciona tu partida primero.");
    if (!ITEMS[item] || !Number.isInteger(quantity) || quantity < 1)
      throw new Error("Revisa el objeto y la cantidad.");
    if (state.write?.busy || state.write?.status === "RECOVERY_REQUIRED")
      throw new Error(
        "Hay otra operación en tu partida. Espera a que termine o revísala en «Cambios en tu partida».",
      );
    const game = state.observation?.game || state.quick_items?.game;
    const trainer = state.observation?.trainer?.name;
    return {
      title: "Añadir a la bolsa",
      message: `${quantity} × ${ITEMS[item]}${game ? ` · Pokémon ${GAMES[game] || game}` : ""}${trainer ? ` · ${trainer}` : ""}`,
      detail: `${info ? `Ahora tienes ${info.count}; tendrás ${info.count + quantity}. ` : ""}Antes de cambiar nada se guarda y verifica una copia completa de tu partida; después se vuelve a leer para comprobar el resultado.${CLOSED}`,
      go: "Añadir a la bolsa",
    };
  }
  if (kind === "delivery") {
    // 072: one paid Shop object into the bag of the league save.
    const [purchaseId, item] = target.split(":");
    const entry = (state.deliveries?.items || []).find(
      (i) => i.purchase_id === purchaseId,
    );
    const option = entry?.options.find((o) => o.code === item);
    if (!state.selected_save) throw new Error("Selecciona tu partida primero.");
    if (!entry || !option || entry.state !== "READY")
      throw new Error("Esta compra ya no se puede entregar desde aquí.");
    if (option.compatible === false)
      throw new Error("Ese objeto no existe en el juego de esta partida.");
    if (state.write?.busy || state.write?.status === "RECOVERY_REQUIRED")
      throw new Error(
        "Hay otra operación en tu partida. Espera a que termine o revísala en «Cambios en tu partida».",
      );
    const game = state.observation?.game || state.deliveries?.save_game;
    const trainer = state.observation?.trainer?.name;
    return {
      title: "Añadir a la bolsa",
      message: `1 × ${option.name}${game ? ` · Pokémon ${GAMES[game] || game}` : ""}${trainer ? ` · ${trainer}` : ""}`,
      detail: `Compra de la Tienda: ${entry.name}. Se gasta solo cuando el objeto está en tu bolsa y comprobado. Antes de cambiar nada se guarda y verifica una copia completa de tu partida; después se vuelve a leer para comprobar el resultado.${CLOSED}`,
      go: "Añadir a la bolsa",
    };
  }
  if (kind === "write") {
    const write = state.write || {};
    if (
      !write.can_confirm ||
      write.operation_id !== target ||
      !write.description
    )
      throw new Error("La acción ya no está pendiente de confirmación.");
    return {
      title: "Confirmar cambio en tu partida",
      message: `${write.game ? `${GAMES[write.game] || write.game} · ` : ""}${write.description}`,
      detail: `${save}\n\nSe conservará una copia del archivo original. No se consume ningún artículo.${CLOSED}`,
      go: "Confirmar cambio",
    };
  }
  if (kind === "export") {
    if (!state.write?.can_export || !state.write?.export_intent)
      throw new Error("No hay una operación de exportación autorizada.");
    return {
      title: "Exportar la partida actual",
      message:
        "Se creará un archivo nuevo y se conservará la partida original.",
      detail: `${save}\n\nElegirás la carpeta a continuación. Exportar no cambia el archivo original ni consume recursos de la Liga.`,
      go: "Elegir carpeta",
    };
  }
  if (kind === "restore") {
    const backup = restorable(state, target);
    if (!backup || state.write.busy)
      throw new Error("Restauración no disponible.");
    return {
      title: "Restaurar copia",
      facts: [
        ["Juego", GAMES[backup.game] || backup.game],
        ["Copia", "Original (antes del cambio)"],
        [
          "Fecha",
          backup.created_at
            ? new Date(backup.created_at).toLocaleString("es-ES")
            : "No disponible",
        ],
        ["Partida", save],
      ],
    };
  }
  const t = transferFor(state, target);
  if (!t) throw new Error("La operación ya no está pendiente.");
  if (kind === "transfer:cancel") {
    if (t.side !== "destination" || t.apply_started)
      throw new Error(
        "Solo quien solicitó el robo puede cancelarlo, y solo antes de aplicar.",
      );
    return {
      title: "Cancelar robo",
      message: "¿Cancelar este robo antes de aplicar ningún cambio?",
      detail:
        "No se modifica ninguna partida y el objeto no se consume. Las copias se conservan.",
      go: "Cancelar robo",
      danger: true,
    };
  }
  if (kind === "transfer:fulfil") {
    if (!t.obligation) throw new Error("PokeApp aún no ha decidido.");
    const victim = t.side === "source";
    return {
      title: victim ? "Sincronización obligatoria" : "Recibir Pokémon",
      message: victim
        ? "Retirar de tu partida el Pokémon robado"
        : "Añadir a tu partida el Pokémon robado",
      detail: `${save}\n\nEl robo ya está decidido por PokeApp. ${victim ? "Se retirará el Pokémon de tu partida actual" : "Se añadirá el Pokémon a tu partida actual"} con copia verificada, confirmación y verificación independiente. Si tu partida cambió desde la decisión, PokeApp recalculará tu parte sin modificar nada todavía.${CLOSED}`,
      go: victim ? "Retirar ahora" : "Recibir ahora",
    };
  }
  if (kind !== "transfer:prepare" && kind !== "transfer:apply")
    throw new Error("Confirmación no válida");
  const where = t.location
    ? `Caja ${t.location.box}, posición ${t.location.slot}`
    : "la posición indicada por PokeApp";
  const prepare = kind === "transfer:prepare";
  const effect = prepare
    ? "Se creará y comprobará una copia completa de tu partida. Todavía no se modifica nada."
    : t.side === "source"
      ? `Se retirará de tu partida el Pokémon de la ${where}.`
      : `Se añadirá a tu partida el Pokémon robado en la ${where}.`;
  return {
    title: prepare ? "Preparar copia para el robo" : "Aplicar tu parte",
    message: prepare
      ? "Preparar copia verificada"
      : "Aplicar tu parte del robo",
    detail: `${save}\n\n${effect} El robo solo es definitivo cuando PokeApp verifica las dos partidas.${CLOSED}`,
    go: prepare ? "Preparar copia" : "Aplicar mi parte",
  };
}

module.exports = {
  createConfirmations,
  describe,
  fingerprint,
  restorable,
  robberyOpen,
  STALE,
};
