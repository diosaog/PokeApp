import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { LeagueGeneral, points } from "./core";
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
  ).toEqual(["Anto", "-0,4", "32", "2"]);
  // Unknown stays unknown, never a false zero.
  const samu = screen.getByRole("row", { name: /Samu/ });
  expect(within(samu).getAllByRole("cell")[3]).toHaveTextContent("Desconocido");
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
});
