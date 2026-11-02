import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LeaguePage } from "./core";

const mocks = vi.hoisted(() => ({
  overview: {} as Record<string, unknown>,
  league: {} as Record<string, unknown>,
}));
vi.mock("../state", () => ({
  useApp: () => ({ season: "season", me: null }),
  useOverview: () => ({ data: mocks.overview, isPending: false, error: null }),
  useRead: () => ({ data: mocks.league, isPending: false, error: null }),
}));
vi.mock("./league-operations", () => ({ LeagueOperations: () => null }));
vi.mock("./wipe-revivals", () => ({ WipeRevivals: () => null }));
afterEach(cleanup);
const row = (changes: Record<string, unknown> = {}) => ({
  season_player_id: "p",
  division: "A",
  position: 1,
  division_position: 1,
  points_awarded: 3,
  score: "2.9",
  wins: 3,
  losses: 1,
  actual_segment_deaths: 1,
  point_penalties: "0.1",
  net_points: "2.9",
  tie_status: "unique",
  placement_rewards: ["blindar_pokemon"],
  ...changes,
});
function fixture() {
  const season = {
    id: "season",
    name: "Liga",
    status: "active",
    current_matchday_id: "j2",
  };
  const days = [
    { id: "j1", number: 1, status: "closed" },
    { id: "j2", number: 2, status: "open" },
  ];
  mocks.league = { season, days, rows: [] };
  mocks.overview = {
    season,
    days,
    players: [
      { id: "p", display_name: "Anto", trainer_id: "t", status: "active" },
    ],
    divisions: [
      { id: "a", code: "A" },
      { id: "b", code: "B" },
    ],
    memberships: [],
    matches: [],
    locks: [],
    points: [],
    balance: null,
    snapshots: [
      {
        matchday_id: "j1",
        revision: 1,
        closed_at: "2026-11-01T12:00:00Z",
        standings: [row()],
      },
    ],
    matchday_scores: [
      {
        matchday_id: "j1",
        provisional: true,
        standings: [row({ actual_segment_deaths: 999 })],
      },
      {
        matchday_id: "j2",
        provisional: true,
        standings: [
          row({
            actual_segment_deaths: 6,
            point_penalties: "0.6",
            net_points: "2.4",
            placement_rewards: [],
          }),
        ],
      },
    ],
  };
}
it("keeps J1 frozen when later observations differ, and shows the independent J2 progression segment", () => {
  fixture();
  const view = render(
    <MemoryRouter>
      <LeaguePage />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "J1" }));
  expect(screen.getByText("Resultado oficial congelado")).toBeInTheDocument();
  let cells = within(screen.getByRole("row", { name: /Anto/ })).getAllByRole(
    "cell",
  );
  expect(cells[4]).toHaveTextContent("1");
  expect(screen.queryByText("999")).not.toBeInTheDocument();
  mocks.overview = {
    ...mocks.overview,
    matchday_scores: [
      { matchday_id: "j1", standings: [row({ actual_segment_deaths: 0 })] },
      {
        matchday_id: "j2",
        standings: [
          row({
            actual_segment_deaths: 6,
            point_penalties: "0.6",
            net_points: "2.4",
            placement_rewards: [],
          }),
        ],
      },
    ],
  };
  view.rerender(
    <MemoryRouter>
      <LeaguePage />
    </MemoryRouter>,
  );
  expect(
    within(screen.getByRole("row", { name: /Anto/ })).getAllByRole("cell")[4],
  ).toHaveTextContent("1");
  fireEvent.click(screen.getByRole("button", { name: "J2" }));
  expect(
    screen.getByText("Provisional · jornada en curso"),
  ).toBeInTheDocument();
  cells = within(screen.getByRole("row", { name: /Anto/ })).getAllByRole(
    "cell",
  );
  expect(cells[4]).toHaveTextContent("6");
  expect(cells[5]).toHaveTextContent("−0,6");
  expect(cells[6]).toHaveTextContent("2,4");
  expect(screen.queryByText("Blindar Pokémon extra")).not.toBeInTheDocument();
});
it("does not turn an unknown open segment or net calculation into zero", () => {
  fixture();
  mocks.overview = {
    ...mocks.overview,
    matchday_scores: [
      {
        matchday_id: "j2",
        provisional: true,
        standings: [
          row({
            actual_segment_deaths: null,
            point_penalties: null,
            net_points: null,
            position: null,
            division_position: null,
            tie_status: null,
            placement_rewards: [],
          }),
        ],
      },
    ],
  };
  render(
    <MemoryRouter>
      <LeaguePage />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "J2" }));
  const cells = within(screen.getByRole("row", { name: /Anto/ })).getAllByRole(
    "cell",
  );
  expect(cells[0]).toHaveTextContent("Pendiente");
  for (const index of [4, 5, 6])
    expect(cells[index]).toHaveTextContent("Desconocido");
});
