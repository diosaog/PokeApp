import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { DayStandingCells, LeagueGeneral, points } from "./core";
vi.mock("../state", () => ({}));
afterEach(cleanup);

const row = (extra: Record<string, unknown> = {}) => ({
  season_player_id: "p",
  trainer_id: "t",
  display_name: "Anto",
  status: "active",
  total_points: "-0.4",
  official_points: "0",
  points_source_matchday_id: null,
  coin_balance: "32",
  dead_count: 2,
  dead_count_source: "observed_current_save" as const,
  dead_count_observed_at: "2026-10-29T10:35:23Z",
  dead_box_number: 7,
  normal_wins: 0,
  total_penalties: "0.4",
  historical_deaths: 2,
  historical_deaths_status: "known",
  points_provisional: false,
  ...extra,
});

function league(rows: ReturnType<typeof row>[]) {
  return {
    season: { id: "s", name: "Prueba2", status: "active" },
    days: [],
    rows,
  } as never;
}

it("shows one total with the deaths already subtracted, and no dates", () => {
  render(
    <MemoryRouter>
      <LeagueGeneral
        data={league([
          row(),
          row({
            season_player_id: "q",
            trainer_id: "u",
            display_name: "Samu",
            total_points: "0",
            official_points: "0",
            dead_count: null,
            dead_count_source: "unknown",
            dead_count_observed_at: null,
            historical_deaths: null,
            historical_deaths_status: "unknown",
            total_penalties: "0",
          }),
        ])}
      />
    </MemoryRouter>,
  );
  const anto = screen.getByRole("row", { name: /Anto/ });
  expect(
    within(anto)
      .getAllByRole("cell")
      .map((c) => c.textContent),
  ).toEqual(["Anto", "-0,4", "2", "32"]);
  expect(screen.queryByRole("columnheader", { name: "Victorias" })).toBeNull();
  expect(
    screen.queryByRole("columnheader", { name: "Penalizaciones" }),
  ).toBeNull();
  // Unknown stays unknown, never a false zero.
  const samu = screen.getByRole("row", { name: /Samu/ });
  expect(within(samu).getAllByRole("cell")[2]).toHaveTextContent("Desconocido");
  for (const gone of [
    /Provisional/,
    /se aplica al cerrar/,
    /Pretemporada/,
    /Sin jornadas oficiales/,
    /29 oct/,
    /Caja 8/,
  ])
    expect(screen.queryByText(gone)).not.toBeInTheDocument();
});

it("formats totals in Spanish, negative ones included", () => {
  expect(points("-2.3")).toBe("-2,3");
  expect(points("0.7")).toBe("0,7");
  expect(points("12")).toBe("12");
  expect(points("10.25")).toBe("10,25");
  expect(points("9007199254740993.1")).toBe("9.007.199.254.740.993,1");
});

it("keeps general net ordering and historical deaths without showing wins or penalties", () => {
  render(
    <MemoryRouter>
      <LeagueGeneral
        data={league([
          row({
            display_name: "B",
            normal_wins: 11,
            total_penalties: "0.5",
            total_points: "10.5",
            historical_deaths: 5,
          }),
          row({
            season_player_id: "a",
            display_name: "A",
            normal_wins: 12,
            total_penalties: "2",
            total_points: "10",
            dead_count: 30,
            historical_deaths: null,
            historical_deaths_status: "unknown",
          }),
        ])}
      />
    </MemoryRouter>,
  );
  expect(screen.getAllByRole("row")[1]).toHaveTextContent("B");
  expect(
    within(screen.getByRole("row", { name: /A/ })).getAllByRole("cell")[2],
  ).toHaveTextContent("Desconocido");
});

it("displays actual segment deaths, exact deductions and separate 1v1/rewards in a frozen row", () => {
  render(
    <table>
      <tbody>
        <tr>
          <DayStandingCells
            row={{
              season_player_id: "p",
              division: "A",
              position: 1,
              division_position: 1,
              points_awarded: 3,
              score: "2",
              wins: 3,
              losses: 1,
              actual_segment_deaths: 5,
              point_penalties: "1.0",
              net_points: "2.0",
              tie_status: "externally_resolved",
              placement_rewards: ["blindar_pokemon"],
            }}
          />
        </tr>
      </tbody>
    </table>,
  );
  expect(screen.getAllByRole("cell").map((cell) => cell.textContent)).toEqual([
    "3",
    "1",
    "5",
    "−1",
    "2",
    "1v1 registrado",
    "Blindar Pokémon extra",
  ]);
});

it("keeps unknown live net points pending even when an earlier official total exists", () => {
  render(
    <MemoryRouter>
      <LeagueGeneral
        data={league([
          row({
            total_points: null,
            official_points: "3",
            total_penalties: null,
            historical_deaths: null,
            historical_deaths_status: "unknown",
            points_provisional: true,
          }),
        ])}
      />
    </MemoryRouter>,
  );
  const cells = within(screen.getByRole("row", { name: /Anto/ })).getAllByRole(
    "cell",
  );
  expect(cells[1]).toHaveTextContent("Pendiente de confirmar");
  expect(cells[2]).toHaveTextContent("Desconocido");
  expect(screen.getByText(/Provisional:/)).toBeInTheDocument();
});
