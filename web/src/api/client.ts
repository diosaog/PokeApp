import type { Model, Session } from "./types";

const rankingCodes = new Set([
  "RANKING_TIE_UNRESOLVED",
  "RANKING_REVIEW_STALE",
  "INVALID_TIE_RESOLUTION",
]);

function rankingReview(value: unknown): Model<"RankingReview"> | undefined {
  if (!value || typeof value !== "object") return;
  const { input_hash, groups, ranking_rule } = value as Record<string, unknown>;
  if (
    typeof input_hash !== "string" ||
    !/^[a-f0-9]{64}$/.test(input_hash) ||
    !Array.isArray(groups) ||
    groups.length > 250 ||
    (ranking_rule != null &&
      ![
        "wins_adjusted_deaths_v1",
        "wins_segment_deaths_v2",
        "legacy_pre_10_5d",
      ].includes(String(ranking_rule)))
  )
    return;
  const allowed = new Set([
    "points",
    "coins",
    "podium",
    "movement",
    "last_b_reward",
    "single_league_prize",
    "matchday_prize",
  ]);
  const clean: Model<"TieGroup">[] = [];
  for (const group of groups) {
    if (!group || typeof group !== "object") return;
    const {
      division,
      player_ids,
      position,
      position_end,
      wins,
      adjusted_deaths,
      segment_deaths,
      consequences,
    } = group;
    if (
      !["A", "B"].includes(division) ||
      !Array.isArray(player_ids) ||
      player_ids.length < 2 ||
      player_ids.length > 500 ||
      player_ids.some((id: unknown) => typeof id !== "string" || !id) ||
      new Set(player_ids).size !== player_ids.length ||
      ![position, position_end, wins, adjusted_deaths].every(
        Number.isSafeInteger,
      ) ||
      position < 1 ||
      position_end < position ||
      wins < 0 ||
      adjusted_deaths < 0 ||
      (segment_deaths != null &&
        (!Number.isSafeInteger(segment_deaths) || segment_deaths < 0)) ||
      (ranking_rule === "wins_segment_deaths_v2" && segment_deaths == null) ||
      !Array.isArray(consequences) ||
      consequences.some((effect: unknown) => !allowed.has(String(effect)))
    )
      return;
    clean.push({
      division,
      player_ids: [...player_ids],
      position,
      position_end,
      wins,
      adjusted_deaths,
      ...(segment_deaths !== undefined ? { segment_deaths } : {}),
      consequences: [...consequences],
    });
  }
  return {
    input_hash,
    groups: clean,
    ...(ranking_rule !== undefined
      ? { ranking_rule: ranking_rule as Model<"RankingReview">["ranking_rule"] }
      : {}),
  };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public ranking?: Model<"RankingReview">,
    // A refusal's own server reason (Team Lock: `team_requires_six`…).
    public reason?: string,
  ) {
    super(code);
  }
}
// Team Lock refusals the trainer can act on (079: «Fijar Equipo»).
const teamLockReasons: Record<string, string> = {
  season_not_active:
    "La Liga no está en curso: no hay ninguna jornada en la que fijar un equipo.",
  matchday_not_found:
    "Esa jornada ya no existe. Actualiza la Liga y vuelve a intentarlo.",
  matchday_not_lockable:
    "La jornada actual ya está cerrada. Podrás fijar tu equipo cuando se prepare la siguiente.",
  participant_inactive: "Tu participación en esta Liga no está activa.",
  participation_not_found: "No participas en esta Liga.",
  trainer_disabled: "Tu cuenta está desactivada.",
  save_not_found:
    "Tu partida oficial ya no está disponible. Sincronízala de nuevo desde PokeApp Launcher.",
  save_not_ready:
    "Tu partida oficial aún se está procesando. Vuelve a intentarlo en unos segundos.",
  parsed_save_not_ready:
    "Tu partida oficial aún se está procesando. Vuelve a intentarlo en unos segundos.",
  parsed_save_changed:
    "Tu partida acaba de cambiar. Revisa el equipo actualizado y vuelve a fijarlo.",
  team_requires_six:
    "Necesitas exactamente seis Pokémon en el equipo de tu partida oficial.",
  invalid_parsed_team:
    "El equipo de tu partida oficial no se puede leer. Vuelve a sincronizar desde PokeApp Launcher.",
};
// A 409 that means "what you were looking at is out of date" (refresh and
// review), as opposed to a refusal with its own reason (funds, availability…).
export function isStaleConflict(error: unknown) {
  return (
    error instanceof ApiError &&
    error.status === 409 &&
    /STALE|REVISION_CONFLICT|_CHANGED$|_MISMATCH$/.test(error.code)
  );
}
export function errorText(error: unknown) {
  if (error instanceof ApiError && error.code === "READ_TIMEOUT")
    return "La consulta ha tardado demasiado. Puedes volver a consultar los datos.";
  if (error instanceof ApiError && error.code === "SESSION_RENEWAL_PENDING")
    return "Renovando tu sesión con PokeApp Launcher… vuelve a intentarlo en unos segundos.";
  if (!(error instanceof ApiError))
    return "No se pudo conectar. Comprueba la conexión y vuelve a intentarlo.";
  if (
    error.code.startsWith("TEAM_LOCK_") &&
    error.reason &&
    teamLockReasons[error.reason]
  )
    return teamLockReasons[error.reason];
  const adminErrors: Record<string, string> = {
    death_history_baseline_required:
      "Falta que algún participante confirme su historial de muertes. Cada entrenador lo confirma en su perfil; en Liga › General verás quién.",
    death_history_admin_required:
      "Tu historial necesita una revisión de Administración: es un caso excepcional que no se confirma desde el perfil.",
    death_history_already_confirmed:
      "Tu historial de muertes ya está confirmado.",
    death_history_changed:
      "Tus muertes observadas acaban de cambiar. Revisa los valores actualizados y vuelve a confirmar.",
    opponent_missing: "Hacen falta al menos dos participantes.",
    death_history_source_unavailable:
      "Falta una partida completa y válida del participante. Sincronízala y vuelve a revisar el historial; la ausencia de datos no cuenta como cero muertes.",
    death_history_source_changed:
      "La partida sincronizada cambió. Revisa la evidencia actual antes de confirmar el historial.",
    death_history_observation_gap:
      "Hay un intervalo del historial sin evidencia suficiente. Administración debe reconciliar las muertes antes de continuar.",
    death_history_dead_box_changed:
      "La caja de muertos cambió. Revisa el historial con la caja actual antes de abrir la jornada.",
    death_history_wipe_reconciliation_required:
      "Un contador de revividos tras wipe cambió. Su entrenador lo confirma desde su perfil; en Liga › General verás quién.",
    death_history_wipe_state_unavailable:
      "No se puede verificar el contador de revividos tras wipe. Administración debe reparar su registro antes de confirmar el historial; no se supondrá un cero.",
    death_history_unmapped_revival:
      "Existe un revivir histórico sin identidad de Pokémon suficiente. Administración debe reconciliarlo con evidencia antes de continuar.",
    death_history_revision_conflict:
      "El historial cambió. Actualiza y revisa sus recuentos antes de volver a confirmar.",
    death_history_inconsistent:
      "Los recuentos no coinciden con la evidencia. Revisa el total histórico, las muertes del tramo y el contador de wipe actual.",
    death_history_segment_frozen:
      "Las muertes de este tramo ya quedaron fijadas al abrir la jornada. Una partida posterior no puede reescribirlas.",
    death_history_start_unproven:
      "No hay evidencia fiable de la primera apertura de esta jornada histórica. Se necesita una resolución auditada; no se inventará un recuento de cero.",
    death_history_evidence_required:
      "Introduce recuentos explícitos, un motivo y evidencia del historial y del tramo de progresión.",
    death_history_closed:
      "Esta temporada ya está cerrada y conserva su historial oficial.",
    legacy_scoring_migration_required:
      "Esta temporada conserva un contrato de puntuación anterior. Adoptar las reglas nuevas requiere una corrección explícita y auditada; no se sobrescribirá su historial.",
    OWNER_DECISION_REQUIRED:
      "Hay un empate exacto en los puntos finales. Falta definir la regla oficial para decidir el campeón; no se aplicará un desempate inventado.",
    ACCOUNTS_UNAVAILABLE:
      "La gestión de cuentas no está disponible en este momento.",
    ACCOUNT_CONFLICT:
      "Ese nombre o solicitud no está disponible. Revisa los datos.",
    ACCOUNT_STALE:
      "El perfil cambió. Revisa los valores actuales antes de guardar.",
    INVALID_ACCOUNT_NAME:
      "Usa hasta 48 letras, números, espacios, guiones o guiones bajos.",
    INVALID_PIN_CONFIRMATION:
      "Introduce y repite un PIN nuevo de cuatro cifras.",
    INVALID_CURRENT_PIN: "El PIN actual no es correcto.",
    ACCOUNT_RENEWAL_REQUIRED:
      "Necesitas una autorización de renovación tras verificar tu identidad. Solicítala al responsable de PokeApp.",
    INVALID_PHOTO: "Usa una imagen JPEG, PNG o WebP válida de hasta 5 MB.",
    REGISTRATION_REJECTED:
      "No se pudo validar el acceso. Revisa los datos de registro.",
    ACCOUNT_RETRY_REQUIRED:
      "El registro no está confirmado. Reintenta la misma solicitud.",
    ACCOUNT_RECONCILIATION_REQUIRED:
      "La cuenta necesita una comprobación antes de continuar. Contacta con el administrador.",
    PIN_RECONCILIATION_REQUIRED:
      "El cambio de PIN sigue pendiente de comprobación. No inicies otro cambio.",
    ACCOUNT_FORBIDDEN: "Esta cuenta no permite la operación solicitada.",
    INSUFFICIENT_FUNDS:
      "No tienes suficientes monedas para esta compra. Revisa tu saldo.",
    // Purchases: the server's real reason, never a generic "data changed".
    ITEM_UNAVAILABLE: "Este objeto no está disponible ahora mismo.",
    ITEM_NOT_FOUND: "Este objeto ya no está en la Tienda.",
    STORE_BANNED: "Tienes la Tienda bloqueada por una sanción en esta jornada.",
    PARTICIPANT_INACTIVE: "Tu participación en esta temporada no está activa.",
    TRAINER_DISABLED: "Tu cuenta está desactivada.",
    BASE_PRICE_CONFIRMATION_REQUIRED:
      "La promoción de este objeto ha terminado: confirma el precio base para comprarlo.",
    PROMOTION_AVAILABLE:
      "Este objeto tiene ahora una promoción: revisa el precio actualizado y confirma.",
    PROMOTION_PENDING:
      "Este objeto tendrá una promoción en breve. Podrás comprarlo cuando empiece.",
    PROMOTION_NOT_FOUND:
      "Esta promoción ya no está activa. Revisa el precio actual.",
    PROMOTION_NOT_CURRENT:
      "Esta promoción ya no está activa. Revisa el precio actual.",
    PROMOTION_EXPIRED: "Esta promoción ha terminado. Revisa el precio actual.",
    PROMOTION_CHANGED:
      "La promoción ha cambiado. Revisa el precio actualizado y confirma de nuevo.",
    PROMOTION_EXHAUSTED: "Esta promoción se ha agotado.",
    PROMOTION_ALREADY_CLAIMED: "Ya has usado esta promoción.",
    PROMOTION_PRICE_INVALID:
      "Esta promoción no tiene un precio válido. Avisa a un administrador.",
    INVALID_PURCHASE_REQUEST:
      "La solicitud de compra no es válida. Vuelve a intentarlo.",
    PURCHASE_UNAVAILABLE: "La Tienda no ha respondido.",
    CURRENT_MATCHDAY_REQUIRED: "Esta acción necesita una jornada preparada.",
    CURRENT_MATCHDAY_INVALID:
      "La jornada actual no está disponible. Avisa a un administrador.",
    ADMIN_REQUIRED: "Esta acción está disponible solo para administradores.",
    ROBBERY_RECONCILIATION_REQUIRED:
      "Este robo ya tiene decisión competitiva o cambios en las partidas: no se anula cambiando un estado. Requiere conciliación.",
    ROBBERY_ALREADY_CANCELLED:
      "Este robo ya está anulado. Actualiza la lista; sus monedas solo se devuelven una vez.",
    ROBBERY_NOT_FOUND:
      "Ese robo ya no existe en esta temporada. Actualiza la lista.",
    SEASON_NOT_DRAFT:
      "Esta acción solo está disponible mientras la temporada es un borrador.",
    SEASON_NOT_ACTIVE: "La Liga debe estar en curso para realizar esta acción.",
    SEASON_NOT_FINISHED:
      "Primero confirma el campeón y finaliza la Liga antes de archivarla.",
    ACTIVE_SEASON_EXISTS:
      "Ya hay una Liga en curso. Termínala antes de activar otra temporada.",
    SETUP_INCOMPLETE:
      "Completa los pasos pendientes de preparación antes de activar la Liga.",
    TRAINER_UNAVAILABLE:
      "Ese entrenador ya no está disponible. Actualiza la lista antes de añadirlo.",
    PARTICIPANT_EXISTS: "Ese entrenador ya forma parte de esta temporada.",
    PARTICIPANT_REFERENCED:
      "Este entrenador ya tiene actividad vinculada y no se puede quitar del borrador.",
    PARTICIPANT_ALREADY_INACTIVE:
      "Ese entrenador ya dejó de participar en la Liga. Actualiza su estado.",
    INVALID_ROSTER:
      "Revisa la plantilla: la configuración necesita participantes activos y sus estadísticas disponibles.",
    INVALID_CONFIG:
      "Revisa las jornadas, las divisiones y los ascensos de la configuración.",
    INVALID_REWARDS:
      "Revisa los puntos y las monedas: usa cantidades enteras no negativas y cubre todas las posiciones.",
    SINGLE_LEAGUE_COMMON_COINS_REQUIRED:
      "Una Liga de una sola jornada necesita la misma cantidad de monedas para todos los participantes. Revisa las monedas de jornada en el formato.",
    EFFECTIVE_ROUND_EXISTS:
      "Ya existe una configuración que empieza en esa jornada. Elige otra jornada o modifica la versión sin usar.",
    CONFIG_WINDOW_CLOSED:
      "Esa configuración ya no puede cambiarse en este momento. Elige una jornada futura disponible.",
    CONFIG_ALREADY_USED:
      "Esa configuración ya se ha utilizado. Conservamos el historial; crea una versión para jornadas futuras.",
    CONFIG_NOT_EFFECTIVE:
      "La configuración elegida todavía no corresponde a esta jornada.",
    INITIAL_SETUP_LOCKED:
      "La preparación inicial ya está fijada y no permite cambiar la plantilla o sus divisiones.",
    COMPETITION_STRUCTURE_LOCKED:
      "La estructura de competición ya está fijada porque la temporada ha empezado. Puedes ajustar jornadas, puntos y monedas, pero no pasar de una Liga a Liga A y Liga B ni al revés.",
    COMPETITION_STRUCTURE_MISMATCH:
      "Todas las versiones de la configuración de una temporada usan la misma estructura de competición. Cambia primero la configuración inicial.",
    DIVISION_CAPACITY_MISMATCH:
      "El reparto no coincide con las plazas configuradas de las divisiones A y B.",
    MATCHDAY_ALREADY_PREPARED:
      "La primera jornada ya está preparada. Selecciónala para continuar.",
    MATCHDAY_NOT_SCHEDULED:
      "Esta acción requiere una jornada preparada que aún no esté abierta.",
    MATCHDAY_NOT_OPEN:
      "Abre la jornada antes de registrar o cerrar sus resultados.",
    CORRECTION_WINDOW_CLOSED:
      "La jornada ya tiene consecuencias posteriores que impiden esta corrección. Su historial se conserva.",
    ONGOING_COMPETITION_DEPENDENCY:
      "Hay una Copa en curso o en preparación vinculada a este entrenador. Resuelve esa participación antes de cambiar su estado en Liga.",
    DISCARD_NOT_ALLOWED:
      "No se puede cancelar ahora: la temporada no está en marcha o tiene robos o revividos sin cerrar. Revisa la vista previa de la cancelación.",
    ACCOUNT_NOT_FOUND: "Esa cuenta ya no existe. Actualiza la lista.",
    ACCOUNT_CONFIRMATION_REQUIRED:
      "Escribe exactamente el nombre actual de la cuenta para confirmar.",
    ACCOUNT_ACTIVE_PARTICIPANT:
      "Esta cuenta participa en una Liga en curso. Retírala primero de esa temporada (Administración › Entrenadores) y vuelve a intentarlo.",
    SEASON_PARTICIPANT_REQUIRED:
      "Ese entrenador no participa en la temporada seleccionada.",
    PARTICIPANT_HAS_CURRENT_TEAM_LOCK:
      "Este entrenador ya fijó su equipo para la jornada. Su participación no puede cambiarse ahora.",
    ROUND_OPEN:
      "La jornada ya está abierta. No se puede cambiar ahora la participación de sus entrenadores.",
    DEPENDENT_DATA_EXISTS:
      "Hay actividad posterior vinculada que impide este cambio. El historial se conserva.",
    RESULTS_INCOMPLETE:
      "Faltan resultados de la jornada. Revisa los combates pendientes antes de cerrarla.",
    INVALID_RESULTS:
      "Revisa los ganadores: cada resultado debe corresponder a uno de los entrenadores del combate.",
    HISTORICAL_SOURCE_INVALID:
      "La información oficial del historial no permite confirmar esta operación. Se necesita revisar su origen sin sobrescribirla.",
    HISTORICAL_ARTIFACT_IMMUTABLE:
      "Este registro histórico ya está congelado y no puede modificarse.",
    CONFIG_MISMATCH:
      "La jornada y la configuración consultadas ya no coinciden. Actualiza antes de continuar.",
    IDEMPOTENCY_CONFLICT:
      "Esta solicitud ya se registró con otros datos. Actualiza y revisa el resultado antes de realizar otra acción.",
    SHOWDOWN_SAVE_NOT_READY:
      "Tu partida aún no está lista en PokeApp. Sincronízala desde el Launcher y vuelve a intentarlo.",
    SHOWDOWN_TEAM_EMPTY:
      "Tu partida sincronizada no tiene Pokémon en el equipo para exportar.",
    PENDING_RETRY_REQUIRED:
      "Primero confirma el resultado de la solicitud pendiente con «Reintentar la misma solicitud».",
  };
  if (adminErrors[error.code] || adminErrors[error.code.toLowerCase()])
    return adminErrors[error.code] ?? adminErrors[error.code.toLowerCase()];
  if (error.code === "POKEMON_REVIVE_PENDING")
    return "Ya has usado un revivir para esta muerte. El save todavía no muestra a este Pokémon vivo.";
  if (error.code === "RANKING_TIE_UNRESOLVED")
    return "Hay un empate que afecta a posiciones o recompensas. Registra el desempate aplicable y, en la Liga actual, los resultados reales de los combates extra 1v1 antes de continuar.";
  if (error.code === "RANKING_REVIEW_STALE")
    return "Los datos del empate han cambiado. Revisa los grupos actuales y registra de nuevo la decisión.";
  if (error.code === "INVALID_TIE_RESOLUTION")
    return "Revisa el orden y el motivo de cada empate pendiente, y los resultados 1v1 con fecha y evidencia cuando sean necesarios.";
  if (error.code === "INITIAL_ASSIGNMENT_REVIEW_STALE")
    return "El progreso o las muertes han cambiado. Revisa el reparto actualizado y registra de nuevo cualquier decisión pendiente.";
  if (error.code === "INITIAL_BOUNDARY_TIE_UNRESOLVED")
    return "Hay un empate en el corte A/B. Registra la decisión deportiva externa y su motivo.";
  if (error.code === "INITIAL_ASSIGNMENT_NOT_READY")
    return "Algún participante aún no tiene una partida oficial con las dos primeras medallas observadas. En Liga › General verás quién.";
  if (error.code === "INITIAL_ASSIGNMENT_REQUIRED")
    return "Esta temporada se juega en Liga A y Liga B: Administración confirma su reparto inicial antes de la J1.";
  if (error.code === "INITIAL_ASSIGNMENT_LOCKED")
    return "El reparto inicial ya no puede modificarse en este estado.";
  if (error.code === "CHAMPIONSHIP_REVIEW_STALE")
    return "Los datos del campeonato han cambiado. Revisa los puntos y el desempate antes de continuar.";
  if (error.code === "CHAMPIONSHIP_TIEBREAK_NOT_REQUIRED")
    return "El campeonato ya no tiene este empate pendiente. Actualiza la revisión antes de confirmar.";
  if (error.code === "CHAMPIONSHIP_BATTLE_REQUIRED")
    return "Las muertes totales también están empatadas. Registra los combates 1v1 que resuelven el título.";
  if (error.code === "CHAMPIONSHIP_DEATHS_UNAVAILABLE")
    return "Falta historial oficial de muertes para esta comparación. No cuenta como cero: revisa la evidencia o registra el desempate 1v1.";
  if (error.code === "CHAMPIONSHIP_RESOLUTION_CONFLICT")
    return "Ya existe una confirmación de este desempate. Actualiza la revisión para consultar su resultado.";
  if (error.code === "CHAMPIONSHIP_BATTLE_INVALID")
    return "Revisa los participantes, el ganador, la fecha y la evidencia de cada combate 1v1 registrado.";
  if (error.code === "CHAMPIONSHIP_BATTLE_AMBIGUOUS")
    return "Los combates registrados no acreditan un ganador único entre todos los candidatos. El título sigue pendiente; no se asignará un campeón arbitrario.";
  if (error.code === "STALE_REVISION")
    return "La temporada ha cambiado. Actualiza los datos y revisa la operación antes de continuar.";
  if (error.code === "WIPE_REVISION_CONFLICT")
    return "El recuento de revividos ha cambiado. Revisa la cantidad actual antes de volver a guardar.";
  if (error.code === "WIPE_REVIVALS_NOT_EDITABLE")
    return "El recuento ya no puede cambiar en el estado actual de la Liga. Actualiza para consultar sus datos.";
  if (error.code === "WIPE_STATE_UNAVAILABLE")
    return "No se pudo consultar o confirmar el recuento de revividos. Inténtalo de nuevo cuando el servicio esté disponible.";
  if (error.code === "CHAMPIONSHIP_BO3_REQUIRED")
    return "Los dos líderes deben jugar un Mejor de 3. Registra su ganador antes de finalizar.";
  if (error.code === "CHAMPIONSHIP_UNRESOLVED")
    return "El campeonato sigue pendiente. Consulta el motivo en la revisión del título antes de finalizar la Liga.";
  if (error.code === "CHAMPIONSHIP_BO3_NOT_REQUIRED")
    return "El estado actual del campeonato no permite registrar este desempate. Revisa los datos actualizados.";
  if (error.code === "INVALID_CHAMPIONSHIP_WINNER")
    return "El ganador debe ser uno de los candidatos indicados para el desempate.";
  if (error.code === "CHAMPIONSHIP_RESOLUTION_NOT_REQUIRED")
    return "El campeonato cambió. Revisa el desempate actual antes de registrar una decisión.";
  if (error.code === "LEGACY_TITLE_UNCERTIFIED")
    return "Esta temporada anterior no tiene una certificación de título compatible. Su historia se conserva y requiere revisión.";
  const labels: Record<number, string> = {
    401: "La sesión ha caducado. Vuelve a entrar.",
    403: "No tienes permiso para esta acción.",
    404: "No se encuentra este recurso.",
    409: "El estado ha cambiado o la acción no está disponible. Actualiza y revisa antes de continuar.",
    422: "Revisa los datos del formulario.",
    429: "Demasiados intentos. Espera antes de volver a entrar.",
  };
  return labels[error.status] ?? "Servicio temporalmente no disponible.";
}

// A browser keeps its own sign-in across reloads and restarts (refresh token
// only, never the PIN); inside the Launcher the Launcher keeps it instead.
type StoredSession = { refresh_token: string; user_id: string };
export type SessionStore = {
  read(): StoredSession | null;
  write(value: StoredSession | null): void;
};
const STORE_KEY = "pokeapp.session.v1";
export const browserSessionStore: SessionStore = {
  read() {
    try {
      const value = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
      return value &&
        typeof value.refresh_token === "string" &&
        value.refresh_token.length >= 8 &&
        value.refresh_token.length <= 16384 &&
        typeof value.user_id === "string"
        ? { refresh_token: value.refresh_token, user_id: value.user_id }
        : null;
    } catch {
      return null;
    }
  },
  write(value) {
    try {
      if (value) localStorage.setItem(STORE_KEY, JSON.stringify(value));
      else localStorage.removeItem(STORE_KEY);
    } catch {
      // Storage unavailable (private mode): the session stays in memory.
    }
  },
};

export class ApiClient {
  private session: Session | null = null;
  private refreshing: Promise<void> | null = null;
  private generation = 0;
  private commands = new Map<
    string,
    { key: string; promise?: Promise<unknown> }
  >();
  onExpired = () => {};
  // Inside PokeApp Launcher the session belongs to the Launcher: this web holds
  // an access token only and asks the Launcher for a fresh one instead.
  renewSession: (() => Promise<Session | "signed_out" | null>) | null = null;
  persist: SessionStore | null = null;
  constructor(readonly base = import.meta.env.VITE_API_BASE_URL || "") {}
  setSession(session: Session | null) {
    this.generation++;
    this.session = session;
    this.commands.clear();
    this.remember(session);
  }
  private remember(session: Session | null) {
    this.persist?.write(
      session?.refresh_token
        ? { refresh_token: session.refresh_token, user_id: session.user_id }
        : null,
    );
  }
  logout() {
    this.setSession(null);
    this.onExpired();
  }
  // A remembered browser sign-in, renewed once; false when there is none.
  async restore() {
    const stored = this.persist?.read();
    if (!stored || this.session) return false;
    this.session = {
      user_id: stored.user_id,
      access_token: "",
      refresh_token: stored.refresh_token,
    };
    await this.refresh();
    return true;
  }
  // The same signed-in trainer, with a newer access token from the Launcher.
  renewAccess(session: Session) {
    if (this.session && !this.session.refresh_token) this.session = session;
  }
  get signedIn() {
    return this.session !== null;
  }
  // A token handed over by the Launcher (renewed only through it).
  get launcherSession() {
    return this.session !== null && !this.session.refresh_token;
  }
  get configured() {
    return Boolean(this.base);
  }
  private async send<T>(
    path: string,
    init: RequestInit,
    token?: string,
  ): Promise<T> {
    if (!this.base) throw new ApiError(503, "API_NOT_CONFIGURED");
    let response: Response;
    // Bound stalled reads without changing command retries or outcome handling.
    const readDeadline =
      !init.method || init.method === "GET"
        ? AbortSignal.timeout(20000)
        : undefined;
    const signal = readDeadline
      ? init.signal
        ? AbortSignal.any([init.signal, readDeadline])
        : readDeadline
      : init.signal;
    try {
      response = await fetch(this.base.replace(/\/$/, "") + path, {
        ...init,
        signal,
        credentials: "omit",
        cache: "no-store",
        headers: {
          ...init.headers,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch {
      if (readDeadline?.aborted) throw new ApiError(0, "READ_TIMEOUT");
      throw new ApiError(0, "NETWORK_ERROR");
    }
    const data = await response.json().catch(() => {
      if (readDeadline?.aborted) throw new ApiError(0, "READ_TIMEOUT");
      return null;
    });
    if (!response.ok) {
      const code =
        typeof data?.detail?.code === "string"
          ? data.detail.code
          : `HTTP_${response.status}`;
      const reason = data?.detail?.reason;
      throw new ApiError(
        response.status,
        code,
        response.status === 409 && rankingCodes.has(code)
          ? rankingReview(data?.detail?.ranking)
          : undefined,
        typeof reason === "string" && /^[a-z_]{3,64}$/.test(reason)
          ? reason
          : undefined,
      );
    }
    return data as T;
  }
  private refresh() {
    if (!this.refreshing) {
      const generation = this.generation;
      // Another tab may already have rotated the remembered token.
      const stored = this.persist?.read();
      const token =
        stored && stored.user_id === this.session?.user_id
          ? stored.refresh_token
          : this.session?.refresh_token;
      this.refreshing = (async () => {
        if (!token && this.renewSession) {
          const renewed = await this.renewSession();
          if (generation !== this.generation)
            throw new ApiError(401, "SESSION_CHANGED");
          if (renewed === "signed_out")
            throw new ApiError(401, "INVALID_SESSION");
          if (renewed) {
            this.session = renewed;
            return;
          }
          // No answer yet: the session is kept and the next request asks
          // the Launcher again. A slow answer is never a sign-out.
          throw new ApiError(0, "SESSION_RENEWAL_PENDING");
        }
        if (!token) throw new ApiError(401, "INVALID_SESSION");
        const data = await this.send<Model<"RefreshResponse">>(
          "/v1/auth/refresh",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: token }),
          },
        );
        if (generation !== this.generation)
          throw new ApiError(401, "SESSION_CHANGED");
        this.session = data.session;
        this.remember(data.session);
      })()
        .catch((error) => {
          // Only a rejected session signs out; a network failure or a busy
          // server keeps it for the next attempt.
          if (
            generation === this.generation &&
            error instanceof ApiError &&
            error.status === 401
          )
            this.logout();
          throw error;
        })
        .finally(() => {
          this.refreshing = null;
        });
    }
    return this.refreshing;
  }
  async request<T>(
    path: string,
    init: RequestInit = {},
    authenticated = true,
  ): Promise<T> {
    const generation = this.generation;
    const token = this.session?.access_token;
    try {
      return await this.send<T>(path, init, authenticated ? token : undefined);
    } catch (error) {
      if (
        !authenticated ||
        !(error instanceof ApiError) ||
        error.status !== 401
      )
        throw error;
      if (generation !== this.generation)
        throw new ApiError(401, "SESSION_CHANGED");
      if (token === this.session?.access_token) await this.refresh();
      try {
        return await this.send<T>(path, init, this.session?.access_token);
      } catch (retryError) {
        if (retryError instanceof ApiError && retryError.status === 401)
          this.logout();
        throw retryError;
      }
    }
  }
  async login(trainer_identifier: string, pin: string) {
    const data = await this.request<Model<"AuthSessionResponse">>(
      "/v1/auth/pin-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trainer_identifier, pin }),
      },
      false,
    );
    this.setSession(data.session);
    try {
      return await this.request<Model<"MeResponse">>("/v1/me");
    } catch (error) {
      this.logout();
      throw error;
    }
  }
  command<T>(path: string, body: unknown, key: string, method = "POST") {
    const encoded = JSON.stringify(body);
    const signature = `${method}:${path}:${encoded}`;
    const generation = this.generation;
    const entry = this.commands.get(signature) ?? { key };
    if (entry.promise) return entry.promise as Promise<T>;
    this.commands.set(signature, entry);
    const promise = this.request<T>(path, {
      method,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": entry.key,
      },
      body: encoded,
    })
      .then((result) => {
        if (generation === this.generation) this.commands.delete(signature);
        return result;
      })
      .catch((error) => {
        if (
          generation === this.generation &&
          error instanceof ApiError &&
          error.status > 0 &&
          error.status < 500
        )
          this.commands.delete(signature);
        throw error;
      })
      .finally(() => {
        entry.promise = undefined;
      });
    entry.promise = promise;
    return promise;
  }
}
export const api = new ApiClient();
