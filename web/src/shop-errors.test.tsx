import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ApiError, errorText, isStaleConflict } from "./api/client";
import { CommandState } from "./ui";

afterEach(cleanup);

const command = (error: unknown) =>
  ({
    pending: false,
    uncertain: false,
    success: false,
    error,
    refresh: vi.fn(),
    execute: vi.fn(),
    retry: vi.fn(),
  }) as never;

it("the owner's preseason refusal says its reason, never «Los datos cambiaron»", () => {
  render(
    <CommandState
      command={command(new ApiError(409, "CURRENT_MATCHDAY_REQUIRED"))}
    />,
  );
  expect(
    screen.getByText("Esta acción necesita una jornada preparada."),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Los datos cambiaron/)).not.toBeInTheDocument();
  expect(screen.queryByText(/El estado ha cambiado/)).not.toBeInTheDocument();
});

it("a real stale conflict still asks to review the refreshed data", () => {
  render(
    <CommandState command={command(new ApiError(409, "STALE_REVISION"))} />,
  );
  expect(
    screen.getByText(/Los datos cambiaron mientras editabas/),
  ).toBeInTheDocument();
});

it.each([
  ["INSUFFICIENT_FUNDS", 409, /suficientes monedas/],
  ["ITEM_UNAVAILABLE", 409, /no está disponible/],
  ["STORE_BANNED", 403, /Tienda bloqueada por una sanción/],
  ["PROMOTION_AVAILABLE", 409, /precio actualizado/],
  ["PROMOTION_CHANGED", 409, /precio actualizado/],
  ["BASE_PRICE_CONFIRMATION_REQUIRED", 409, /confirma el precio base/],
  ["IDEMPOTENCY_CONFLICT", 409, /ya se registró/],
  ["PARTICIPANT_INACTIVE", 403, /no está activa/],
])("purchase refusal %s explains itself", (code, status, text) => {
  expect(errorText(new ApiError(status, code))).toMatch(text);
});

it("only out-of-date data counts as a stale conflict", () => {
  for (const code of [
    "STALE_REVISION",
    "WIPE_REVISION_CONFLICT",
    "PROMOTION_CHANGED",
    "CONFIG_MISMATCH",
    "INITIAL_ASSIGNMENT_REVIEW_STALE",
  ])
    expect(isStaleConflict(new ApiError(409, code))).toBe(true);
  for (const code of [
    "INSUFFICIENT_FUNDS",
    "CURRENT_MATCHDAY_REQUIRED",
    "ITEM_UNAVAILABLE",
    "IDEMPOTENCY_CONFLICT",
    "PROMOTION_EXHAUSTED",
  ])
    expect(isStaleConflict(new ApiError(409, code))).toBe(false);
  expect(isStaleConflict(new ApiError(503, "STALE_REVISION"))).toBe(false);
});
