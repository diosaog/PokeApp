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
it("keeps unknown visible deaths separate from the known wipe count", () => {
  render(<WipeRevivals data={league()} />);
  expect(screen.getByLabelText("Cantidad de revividos tras wipe")).toHaveValue(
    1,
  );
  expect(
    screen.getByText(/Pendiente de observar las muertes del save/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/penalización adicional de 0,4 puntos/),
  ).toBeInTheDocument();
  expect(screen.queryByText(/2 muertes|0 muertes/)).not.toBeInTheDocument();
  expect(mocks.read).toHaveBeenCalledWith("/v1/seasons/season/wipe-revivals");
});
it("observed zero does not show the unknown-evidence warning", () => {
  const data = league();
  Object.assign(data.rows[0], {
    dead_count: 0,
    dead_count_source: "observed_current_save",
    dead_count_observed_at: "2026-10-04T12:00:00Z",
  });
  render(<WipeRevivals data={data} />);
  expect(screen.queryByText(/Pendiente de observar/)).not.toBeInTheDocument();
});
it("has no own-counter read or editor for an unrelated trainer", () => {
  mocks.trainer = "outsider";
  render(<WipeRevivals data={league()} />);
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  expect(mocks.read).not.toHaveBeenCalled();
});
it("submits the absolute owned count and current revision with narrow invalidation", () => {
  render(<WipeRevivals data={league()} />);
  const input = screen.getByLabelText("Cantidad de revividos tras wipe");
  fireEvent.change(input, { target: { value: "3" } });
  fireEvent.submit(input.closest("form")!);
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
it("rejects negative, fractional and overflowing counts without clamping", () => {
  render(<WipeRevivals data={league()} />);
  const input = screen.getByLabelText("Cantidad de revividos tras wipe");
  for (const value of ["-1", "1.5", "2147483648", "1e3", ""]) {
    fireEvent.change(input, { target: { value } });
    fireEvent.submit(input.closest("form")!);
  }
  expect(mocks.execute).not.toHaveBeenCalled();
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
  expect(screen.getByText(/Cantidad registrada/)).toHaveTextContent("1");
  expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  expect(mocks.execute).not.toHaveBeenCalled();
});
it("an uncertain outcome locks the form and offers only an explicit same-request retry", () => {
  mocks.uncertain = true;
  mocks.error = new ApiError(503, "WIPE_STATE_UNAVAILABLE");
  render(<WipeRevivals data={league()} />);
  expect(
    screen.getByLabelText("Cantidad de revividos tras wipe"),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Actualizar revividos" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
  ).toBeEnabled();
  expect(mocks.execute).not.toHaveBeenCalled();
});
it("a stale write refreshes the owned state and asks for review without retrying", () => {
  mocks.error = new ApiError(409, "WIPE_REVISION_CONFLICT");
  render(<WipeRevivals data={league()} />);
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Revisa la cantidad actual",
  );
  // useCommand owns the single refresh; this form must not duplicate it.
  expect(mocks.refetch).not.toHaveBeenCalled();
  expect(mocks.execute).not.toHaveBeenCalled();
});
