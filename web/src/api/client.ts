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
  if (error.code === "RANKING_TIE_UNRESOLVED")
    return "Hay un empate que afecta al reparto de posiciones o recompensas. Registra la decisión externa antes de continuar.";
  if (error.code === "RANKING_REVIEW_STALE")
    return "Los datos del empate han cambiado. Revisa los grupos actuales y registra de nuevo la decisión.";
  if (error.code === "INVALID_TIE_RESOLUTION")
    return "Revisa el orden y el motivo de cada empate pendiente.";
  const labels: Record<number, string> = {
    401: "La sesión ha caducado. Vuelve a entrar.",
    403: "No tienes permiso para esta acción.",
    404: "No se encuentra este recurso.",
    409: "El estado ha cambiado o la acción no está disponible. Actualiza y revisa antes de continuar.",
    422: "Revisa los datos del formulario.",
    429: "Demasiados intentos. Espera antes de volver a entrar.",
  };
  return `${labels[error.status] ?? "Servicio temporalmente no disponible."} (${error.code})`;
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
