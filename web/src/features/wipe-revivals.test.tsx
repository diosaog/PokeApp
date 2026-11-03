import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { WipeRevivals } from "./wipe-revivals";

const mocks = vi.hoisted(() => ({
  trainer: "owner",
  data: null as Model<"WipeRevivalsRead"> | null,
  refetch: vi.fn(),
  execute: vi.fn(),
  read: vi.fn(),
  invalidate: vi.fn(),
  pending: false,
  uncertain: false,
  error: null as ApiError | null,
}));
vi.mock("../state", () => ({
  useApp: () => ({ me: { trainer_id: mocks.trainer } }),
  useRead: (path: string) => {
    mocks.read(path);
    return {
      data: mocks.data,
      isPending: false,
      isFetching: false,
      error: null,
      refetch: mocks.refetch,
    };
  },
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  useCommand: (paths: string[]) => {
    mocks.invalidate(paths);
    return {
      pending: mocks.pending,
      uncertain: mocks.uncertain,
      error: mocks.error,
      success: false,
      execute: mocks.execute,
    };
  },
}));
const league = (): Model<"LeagueGeneralRead"> => ({
  season: {
    id: "season",
    name: "Liga",
    status: "active",
    current_matchday_id: "day",
  },
  days: [],
  rows: [
    {
      season_player_id: "own-participant",
      trainer_id: "owner",
      display_name: "Entrenador",
      status: "active",
      total_points: "-1.4",
      points_source_matchday_id: "closed-day",
      coin_balance: "2",
      dead_count: null,
      dead_count_source: "unknown",
      dead_count_observed_at: null,
      league_save_status: "unavailable",
    },
  ],
});
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  mocks.trainer = "owner";
  mocks.pending = false;
  mocks.uncertain = false;
  mocks.error = null;
  mocks.data = {
    season_id: "season",
    revived_after_wipe: 1,
    revision: 4,
    editable: true,
    blocking_reason: null,
    replayed: false,
  };
});
const count = () => screen.getByLabelText("Cantidad");
const minus = () => screen.getByRole("button", { name: "Restar un revivido" });
const plus = () => screen.getByRole("button", { name: "Sumar un revivido" });
const update = () => screen.getByRole("button", { name: "Actualizar" });

it("is a compact − value + Actualizar control with no explanatory paragraphs", () => {
  render(<WipeRevivals data={league()} />);
  expect(
    screen.getByRole("heading", { name: "Revividos tras wipe" }),
  ).toBeVisible();
  expect(count()).toHaveTextContent("1");
  // Nothing to send until the pending value differs from the server's.
  expect(update()).toBeDisabled();
  for (const gone of [
    /Pendiente de observar/,
    /penalización adicional/,
    /próximo cálculo/,
    /Caja 8/,
  ])
    expect(screen.queryByText(gone)).not.toBeInTheDocument();
  expect(mocks.read).toHaveBeenCalledWith("/v1/seasons/season/wipe-revivals");
});
it("has no own-counter read or editor for an unrelated trainer", () => {
  mocks.trainer = "outsider";
  render(<WipeRevivals data={league()} />);
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  expect(mocks.read).not.toHaveBeenCalled();
});
it("+ and − change only a pending value; nothing is sent before Actualizar", () => {
  render(<WipeRevivals data={league()} />);
  fireEvent.click(plus());
  fireEvent.click(plus());
  expect(count()).toHaveTextContent("3");
  fireEvent.click(minus());
  expect(count()).toHaveTextContent("2");
  expect(screen.getByText("Sin guardar · antes: 1")).toBeVisible();
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.click(minus());
  expect(count()).toHaveTextContent("1");
  expect(update()).toBeDisabled();
});
it("never goes below zero", () => {
  mocks.data!.revived_after_wipe = 0;
  render(<WipeRevivals data={league()} />);
  expect(minus()).toBeDisabled();
  fireEvent.click(minus());
  expect(count()).toHaveTextContent("0");
  expect(update()).toBeDisabled();
});
it("stops at the server's upper bound", () => {
  mocks.data!.revived_after_wipe = 2147483647;
  render(<WipeRevivals data={league()} />);
  expect(plus()).toBeDisabled();
});
it("submits the absolute owned count and current revision with narrow invalidation", () => {
  render(<WipeRevivals data={league()} />);
  fireEvent.click(plus());
  fireEvent.click(plus());
  fireEvent.click(update());
  expect(mocks.execute).toHaveBeenCalledOnce();
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/seasons/season/wipe-revivals",
    { revived_after_wipe: 3, expected_revision: 4 },
    "PUT",
  );
  expect(mocks.invalidate).toHaveBeenCalledWith([
    "/v1/seasons/season/wipe-revivals",
    "/v1/read/seasons/season/league",
    "/v1/seasons/season/initial-assignment",
    "/v1/admin/seasons/season/matchdays/day",
  ]);
});
it("shows the refreshed authoritative value after a confirmed change", () => {
  const { rerender } = render(<WipeRevivals data={league()} />);
  fireEvent.click(plus());
  Object.assign(mocks.data!, { revived_after_wipe: 2, revision: 5 });
  rerender(<WipeRevivals data={league()} />);
  expect(count()).toHaveTextContent("2");
  expect(update()).toBeDisabled();
  // Another device changed it meanwhile: the server's number wins.
  fireEvent.click(plus());
  Object.assign(mocks.data!, { revived_after_wipe: 0, revision: 6 });
  rerender(<WipeRevivals data={league()} />);
  expect(count()).toHaveTextContent("0");
});
it("a closed league keeps its count visible without an ordinary editor", () => {
  Object.assign(mocks.data!, {
    editable: false,
    blocking_reason: "league_closed",
  });
  render(<WipeRevivals data={league()} />);
  expect(
    screen.getByText(/La última jornada ya está cerrada/),
  ).toBeInTheDocument();
  expect(screen.getByText(/Cantidad:/)).toHaveTextContent("Cantidad: 1");
  expect(
    screen.queryByRole("button", { name: "Sumar un revivido" }),
  ).not.toBeInTheDocument();
  expect(mocks.execute).not.toHaveBeenCalled();
});
it("an uncertain outcome locks the control and offers only an explicit same-request retry", () => {
  mocks.uncertain = true;
  mocks.error = new ApiError(503, "WIPE_STATE_UNAVAILABLE");
  render(<WipeRevivals data={league()} />);
  expect(plus()).toBeDisabled();
  expect(minus()).toBeDisabled();
  expect(update()).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
  ).toBeEnabled();
  expect(mocks.execute).not.toHaveBeenCalled();
});
it("a stale write shows the reason and resets to the authoritative value", () => {
  const { rerender } = render(<WipeRevivals data={league()} />);
  fireEvent.click(plus());
  expect(count()).toHaveTextContent("2");
  mocks.error = new ApiError(409, "WIPE_REVISION_CONFLICT");
  rerender(<WipeRevivals data={league()} />);
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Revisa la cantidad actual",
  );
  expect(count()).toHaveTextContent("1");
  // useCommand owns the single refresh; this control must not duplicate it.
  expect(mocks.refetch).not.toHaveBeenCalled();
  expect(mocks.execute).not.toHaveBeenCalled();
});
