import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient, ApiError, errorText } from "./client";

const session = {
  user_id: "test-user",
  access_token: "old",
  refresh_token: "refresh",
};
const response = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
afterEach(() => vi.unstubAllGlobals());
describe("API transport", () => {
  it("ends a stalled read with a visible timeout and does not repeat it", async () => {
    const controller = new AbortController();
    vi.spyOn(AbortSignal, "timeout").mockReturnValue(controller.signal);
    const fetcher = vi.fn(
      (_url, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal!.addEventListener("abort", () =>
            reject(new Error("aborted")),
          );
        }),
    );
    vi.stubGlobal("fetch", fetcher);
    const client = new ApiClient("https://api.example");
    const pending = client.request("/v1/read/trainers");
    controller.abort();
    await expect(pending).rejects.toMatchObject({
      code: "READ_TIMEOUT",
      status: 0,
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(errorText(new ApiError(0, "READ_TIMEOUT"))).toContain(
      "tardado demasiado",
    );
  });
  it("keeps tokens in Authorization and never sends browser cookies", async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ ok: true }));
    vi.stubGlobal("fetch", fetcher);
    const client = new ApiClient("https://api.example/");
    client.setSession(session);
    await client.request("/v1/me");
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.example/v1/me",
      expect.objectContaining({
        credentials: "omit",
        cache: "no-store",
        headers: { Authorization: "Bearer old" },
      }),
    );
  });
  it("a Launcher session renews through the Launcher, never /refresh", async () => {
    const fetcher = vi.fn(async (path: string, init: RequestInit) => {
      const auth = (init.headers as Record<string, string>).Authorization;
      return auth === "Bearer fresh"
        ? response({ ok: true })
        : response({ detail: { code: "INVALID_SESSION" } }, 401);
    });
    vi.stubGlobal("fetch", fetcher);
    const client = new ApiClient("https://api.example");
    client.setSession({
      user_id: "",
      access_token: "stale",
      refresh_token: "",
    });
    client.renewSession = vi.fn().mockResolvedValue({
      user_id: "",
      access_token: "fresh",
      refresh_token: "",
    });
    await expect(client.request("/v1/me")).resolves.toEqual({ ok: true });
    expect(client.renewSession).toHaveBeenCalledTimes(1);
    expect(
      fetcher.mock.calls.some(([path]) => String(path).endsWith("/refresh")),
    ).toBe(false);
  });
  it("without a Launcher answer the Launcher session ends", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(response({ detail: {} }, 401)),
    );
    const client = new ApiClient("https://api.example");
    const expired = vi.fn();
    client.onExpired = expired;
    client.setSession({
      user_id: "",
      access_token: "stale",
      refresh_token: "",
    });
    client.renewSession = vi.fn().mockResolvedValue(null);
    await expect(client.request("/v1/me")).rejects.toMatchObject({
      status: 401,
    });
    expect(expired).toHaveBeenCalled();
  });
  it("coalesces simultaneous 401 refreshes and retries with the new JWT", async () => {
    let refreshes = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: string, init: RequestInit) => {
        if (path.endsWith("/refresh")) {
          refreshes++;
          await new Promise((resolve) => setTimeout(resolve, 5));
          return response({ session: { ...session, access_token: "new" } });
        }
        return (init.headers as Record<string, string>).Authorization ===
          "Bearer old"
          ? response({ detail: { code: "EXPIRED" } }, 401)
          : response({ ok: true });
      }),
    );
    const client = new ApiClient("https://api.example");
    client.setSession(session);
    await expect(
      Promise.all([client.request("/a"), client.request("/b")]),
    ).resolves.toEqual([{ ok: true }, { ok: true }]);
    expect(refreshes).toBe(1);
  });
  it("does not resurrect an old session when logout interrupts refresh", async () => {
    let release!: (value: Response) => void;
    let started!: () => void;
    const waiting = new Promise<void>((r) => {
      started = r;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: string) =>
        path.endsWith("/refresh")
          ? (started(),
            new Promise<Response>((r) => {
              release = r;
            }))
          : response({}, 401),
      ),
    );
    const client = new ApiClient("https://api.example");
    client.setSession(session);
    const expired = vi.fn();
    client.onExpired = expired;
    const request = client.request("/private");
    const rejected = expect(request).rejects.toMatchObject({
      code: "SESSION_CHANGED",
    });
    await waiting;
    client.logout();
    release(response({ session: { ...session, access_token: "new" } }));
    await rejected;
    expect(expired).toHaveBeenCalledTimes(1);
  });
  it.each([403, 409, 422, 503])(
    "surfaces %i without automatic mutation replay",
    async (status) => {
      const fetcher = vi
        .fn()
        .mockResolvedValue(response({ detail: { code: "REJECTED" } }, status));
      vi.stubGlobal("fetch", fetcher);
      const client = new ApiClient("https://api.example");
      client.setSession(session);
      await expect(
        client.command("/command", { expected_revision: 7 }, "key"),
      ).rejects.toMatchObject({ status, code: "REJECTED" });
      expect(fetcher).toHaveBeenCalledTimes(1);
    },
  );
  it("reuses an uncertain command key across navigation and coalesces concurrent submits", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Disconnected"))
      .mockResolvedValue(response({ ok: true }));
    vi.stubGlobal("fetch", fetcher);
    const client = new ApiClient("https://api.example");
    client.setSession(session);
    await expect(
      client.command("/purchase", { item_id: "item" }, "original"),
    ).rejects.toMatchObject({ status: 0 });
    await Promise.all([
      client.command("/purchase", { item_id: "item" }, "new-component-key"),
      client.command("/purchase", { item_id: "item" }, "double-click-key"),
    ]);
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls[1][1].headers["Idempotency-Key"]).toBe(
      "original",
    );
    expect(fetcher.mock.calls[1][1].body).toBe(fetcher.mock.calls[0][1].body);
  });
  it("starts a new intent after a definite CAS conflict", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        response({ detail: { code: "STALE_INPUTS" } }, 409),
      )
      .mockResolvedValue(response({ ok: true }));
    vi.stubGlobal("fetch", fetcher);
    const client = new ApiClient("https://api.example");
    client.setSession(session);
    await expect(
      client.command("/close", { expected_revision: 2 }, "old"),
    ).rejects.toMatchObject({ status: 409 });
    await client.command("/close", { expected_revision: 3 }, "reviewed");
    expect(fetcher.mock.calls[1][1].headers["Idempotency-Key"]).toBe(
      "reviewed",
    );
    expect(JSON.parse(fetcher.mock.calls[1][1].body).expected_revision).toBe(3);
  });
  it("sanitizes arbitrary backend errors and exposes stable Spanish error states", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(response({ detail: "DATABASE PASSWORD" }, 500)),
    );
    const client = new ApiClient("https://api.example");
    await expect(client.request("/x")).rejects.toMatchObject({
      code: "HTTP_500",
    });
    for (const status of [401, 403, 409, 422, 503]) {
      const error = new ApiError(status, "INTERNAL_RPC_CODE");
      expect(errorText(error)).not.toContain("INTERNAL_RPC_CODE");
      expect(errorText(error).length).toBeGreaterThan(15);
      expect(error.code).toBe("INTERNAL_RPC_CODE");
    }
  });
  it("explains Admin configuration, lifecycle and dependency failures without technical codes", () => {
    for (const [code, detail] of [
      ["CONFIG_ALREADY_USED", "jornadas futuras"],
      ["CONFIG_WINDOW_CLOSED", "jornada futura"],
      ["INVALID_REWARDS", "enteras no negativas"],
      ["SEASON_NOT_DRAFT", "borrador"],
      ["SEASON_NOT_FINISHED", "campeón"],
      ["ONGOING_COMPETITION_DEPENDENCY", "Copa"],
      ["PARTICIPANT_HAS_CURRENT_TEAM_LOCK", "fijó su equipo"],
      ["RESULTS_INCOMPLETE", "combates pendientes"],
      ["STALE_REVISION", "Actualiza"],
      ["PENDING_RETRY_REQUIRED", "misma solicitud"],
    ]) {
      expect(errorText(new ApiError(409, code))).toContain(detail);
      expect(errorText(new ApiError(409, code))).not.toContain(code);
    }
  });
});
