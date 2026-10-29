import { afterEach, expect, it, vi } from "vitest";
import { ApiError } from "./api/client";
import { queries, refreshSoon } from "./state";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it("one sync's several Launcher events become one refresh", () => {
  vi.useFakeTimers();
  const refresh = vi
    .spyOn(queries, "invalidateQueries")
    .mockResolvedValue(undefined);
  refreshSoon();
  refreshSoon();
  vi.advanceTimersByTime(300);
  refreshSoon();
  expect(refresh).not.toHaveBeenCalled();
  vi.advanceTimersByTime(400);
  expect(refresh).toHaveBeenCalledTimes(1);
});

it("a dropped read is retried with backoff; a refusal is not", () => {
  const { retry, retryDelay, refetchInterval } =
    queries.getDefaultOptions().queries!;
  const decide = retry as (count: number, error: unknown) => boolean;
  expect(decide(0, new ApiError(503, "X"))).toBe(true);
  expect(decide(2, new ApiError(0, "NETWORK"))).toBe(true);
  expect(decide(3, new ApiError(503, "X"))).toBe(false);
  expect(decide(0, new ApiError(409, "STALE"))).toBe(false);
  expect(decide(0, new ApiError(503, "SESSION_RENEWAL_PENDING"))).toBe(false);
  const delay = retryDelay as (attempt: number) => number;
  expect([0, 1, 2].map((n) => delay(n))).toEqual([1000, 2000, 4000]);
  expect(refetchInterval).toBe(60000);
});
