import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Model } from "../api/types";
import { OwnDeathHistory, trainerReasonText } from "./league-start";

type Own = Model<"OwnDeathHistoryRead">;
const mocks = vi.hoisted(() => ({
  data: null as Own | null,
  reads: [] as string[],
}));
vi.mock("../state", () => ({
  queries: { invalidateQueries: vi.fn() },
  useApp: () => ({ season: "season", me: { trainer_id: "t1" } }),
  useRead: (path: string) => {
    mocks.reads.push(path);
    return { data: mocks.data, isPending: false, error: null };
  },
}));
const own = (changes: Partial<Own> = {}): Own => ({
  season_id: "season",
  season_player_id: "p1",
  trainer_id: "t1",
  revision: 1,
  known: true,
  blocking_reason: null,
  actual_deaths: 0,
  wipe_deaths: 0,
  segment_deaths: 0,
  dead_box_number: 7,
  source_sha256: "a".repeat(64),
  confirmed_at: null,
  current_matchday_id: null,
  can_confirm: false,
  confirm_blocker: "death_history_confirmed",
  proposed: null,
  replayed: false,
  ...changes,
});
beforeEach(() => {
  mocks.data = own();
  mocks.reads = [];
});
afterEach(cleanup);
it.each([0, 3])(
  "observed history with %s deaths never asks for confirmation",
  (count) => {
    mocks.data = own({ actual_deaths: count, segment_deaths: count });
    render(<OwnDeathHistory />);
    expect(mocks.reads).toContain("/v1/seasons/season/death-history");
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  },
);
it("a legacy unconfirmed answer cannot expose a confirmation action", () => {
  mocks.data = own({
    known: false,
    blocking_reason: "death_history_baseline_required",
    actual_deaths: null,
    wipe_deaths: null,
    segment_deaths: null,
    can_confirm: true,
    confirm_blocker: null,
    proposed: { actual_deaths: 0, wipe_deaths: 0, segment_deaths: 0 },
  });
  render(<OwnDeathHistory />);
  expect(screen.getByText(/Los puntos se calculan/)).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
it("missing or inconsistent evidence remains explicit without a player confirmation", () => {
  mocks.data = own({
    known: false,
    confirm_blocker: "save_missing",
    source_sha256: null,
  });
  const view = render(<OwnDeathHistory />);
  expect(screen.getByText(/Sincroniza tu partida oficial/)).toBeVisible();
  mocks.data = own({
    known: false,
    confirm_blocker: "death_history_admin_required",
  });
  view.rerender(<OwnDeathHistory />);
  expect(
    screen.getByText(
      /La evidencia de tu historial es inconsistente o incompleta/,
    ),
  ).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
it("League readiness never offers an inline confirmation action", () => {
  mocks.data = own({
    known: false,
    confirm_blocker: null,
    can_confirm: true,
    proposed: { actual_deaths: 3, wipe_deaths: 0, segment_deaths: 3 },
  });
  render(<OwnDeathHistory inline />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
it("readiness reasons describe missing evidence without asking the player to confirm", () => {
  for (const code of [
    "death_history_baseline_required",
    "death_history_wipe_reconciliation_required",
  ] as const)
    for (const viewer of [true, false])
      expect(trainerReasonText(code, viewer)).not.toMatch(/confirm/i);
  expect(trainerReasonText("save_missing", true)).toMatch(
    /^registra tu partida oficial/,
  );
});
