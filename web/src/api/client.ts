import type { Model, Session } from "./types";

const rankingCodes = new Set([
  "RANKING_TIE_UNRESOLVED",
  "RANKING_REVIEW_STALE",
  "INVALID_TIE_RESOLUTION",
]);

function rankingReview(value: unknown): Model<"RankingReview"> | undefined {
  if (!value || typeof value !== "object") return;
  const { input_hash, groups } = value as Record<string, unknown>;
  if (
    typeof input_hash !== "string" ||
    !/^[a-f0-9]{64}$/.test(input_hash) ||
    !Array.isArray(groups) ||
    groups.length > 250
  )
    return;
  const allowed = new Set([
    "points",
    "coins",
    "podium",
    "movement",
    "last_b_reward",
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
      consequences: [...consequences],
    });
  }
  return { input_hash, groups: clean };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public ranking?: Model<"RankingReview">,
  ) {
    super(code);
  }
}
export function errorText(error: unknown) {
  if (!(error instanceof ApiError))
    return "No se pudo conectar. Comprueba la conexión y vuelve a intentarlo.";
  const adminErrors: Record<string, string> = {
    INSUFFICIENT_FUNDS:
      "No tienes suficientes monedas para esta compra. Revisa tu saldo.",
    ADMIN_REQUIRED: "Esta acción está disponible solo para administradores.",
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
      "Esta temporada no puede descartarse. Solo se permite un borrador sin actividad que necesite conservarse.",
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
    PENDING_RETRY_REQUIRED:
      "Primero confirma el resultado de la solicitud pendiente con «Reintentar la misma solicitud».",
  };
  if (adminErrors[error.code]) return adminErrors[error.code];
  if (error.code === "POKEMON_REVIVE_PENDING")
    return "Ya has usado un revivir para esta muerte. El save todavía no muestra a este Pokémon vivo.";
  if (error.code === "RANKING_TIE_UNRESOLVED")
    return "Hay un empate que afecta al reparto de posiciones o recompensas. Registra la decisión externa antes de continuar.";
  if (error.code === "RANKING_REVIEW_STALE")
    return "Los datos del empate han cambiado. Revisa los grupos actuales y registra de nuevo la decisión.";
  if (error.code === "INVALID_TIE_RESOLUTION")
    return "Revisa el orden y el motivo de cada empate pendiente.";
  if (error.code === "INITIAL_ASSIGNMENT_REVIEW_STALE")
    return "El progreso o las muertes han cambiado. Revisa el reparto actualizado y registra de nuevo cualquier decisión pendiente.";
  if (error.code === "INITIAL_BOUNDARY_TIE_UNRESOLVED")
    return "Hay un empate en el corte A/B. Registra la decisión deportiva externa y su motivo.";
  if (error.code === "INITIAL_ASSIGNMENT_NOT_READY")
    return "El reparto necesita progreso observado suficiente, muertes observadas y una temporada preparada.";
  if (error.code === "INITIAL_ASSIGNMENT_REQUIRED")
    return "Confirma el reparto inicial observado antes de abrir la jornada.";
  if (error.code === "INITIAL_ASSIGNMENT_LOCKED")
    return "El reparto inicial ya no puede modificarse en este estado.";
  if (error.code === "CHAMPIONSHIP_REVIEW_STALE")
    return "Los datos del campeonato han cambiado. Revisa los puntos y el desempate antes de continuar.";
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

export class ApiClient {
  private session: Session | null = null;
  private refreshing: Promise<void> | null = null;
  private generation = 0;
  private commands = new Map<
    string,
    { key: string; promise?: Promise<unknown> }
  >();
  onExpired = () => {};
  constructor(readonly base = import.meta.env.VITE_API_BASE_URL || "") {}
  setSession(session: Session | null) {
    this.generation++;
    this.session = session;
    this.commands.clear();
  }
  logout() {
    this.setSession(null);
    this.onExpired();
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
    try {
      response = await fetch(this.base.replace(/\/$/, "") + path, {
        ...init,
        credentials: "omit",
        cache: "no-store",
        headers: {
          ...init.headers,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch {
      throw new ApiError(0, "NETWORK_ERROR");
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const code =
        typeof data?.detail?.code === "string"
          ? data.detail.code
          : `HTTP_${response.status}`;
      throw new ApiError(
        response.status,
        code,
        response.status === 409 && rankingCodes.has(code)
          ? rankingReview(data?.detail?.ranking)
          : undefined,
      );
    }
    return data as T;
  }
  private refresh() {
    if (!this.refreshing) {
      const generation = this.generation;
      const token = this.session?.refresh_token;
      this.refreshing = (async () => {
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
      })()
        .catch((error) => {
          if (generation === this.generation) this.logout();
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
