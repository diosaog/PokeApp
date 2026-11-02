import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Model } from "../api/types";
import { TrainerLeagueStats } from "./trainer-league-stats";

vi.mock("../state", () => ({}));
afterEach(cleanup);

const row = (extra: Partial<Model<"LeagueStandingRead">> = {}) => ({
  season_player_id: "player",
  trainer_id: "trainer",
  display_name: "Entrenador",
  status: "active",
  total_points: "-0.7",
  coin_balance: "3",
  points_source_matchday_id: null,
  dead_count: 30,
  dead_count_source: "observed_current_save" as const,
  dead_count_observed_at: null,
  historical_deaths: null,
  historical_deaths_status: "unknown" as const,
  league_save_status: "linked" as const,
  ...extra,
});

const deaths = () =>
  screen.getByText("Muertes históricas").closest(".stat-pill");

it("shows known totals above box capacity and confirmed zero without consulting occupancy", () => {
  const view = render(
    <TrainerLeagueStats
      row={row({ historical_deaths: 37, historical_deaths_status: "known" })}
    />,
  );
  expect(deaths()).toHaveTextContent("37");
  view.rerender(
    <TrainerLeagueStats
      row={row({ historical_deaths: 0, historical_deaths_status: "known" })}
    />,
  );
  expect(deaths()).toHaveTextContent("0");
});

it("does not present partial historical evidence as a confirmed total", () => {
  render(
    <TrainerLeagueStats
      row={row({
        historical_deaths: 7,
        historical_deaths_status: "incomplete",
        historical_deaths_source: "death_history_observation_gap",
      })}
    />,
  );
  expect(deaths()).toHaveTextContent("—");
  expect(
    screen.getByText(/7 muertes registradas; total sin confirmar/),
  ).toHaveTextContent(
    "Hay un intervalo del historial sin evidencia suficiente.",
  );
});

it("leaves an unavailable League response unknown and never manufactures zero", () => {
  render(<TrainerLeagueStats />);
  for (const pill of document.querySelectorAll(".stat-pill"))
    expect(pill.querySelector("strong")).toHaveTextContent("—");
  expect(screen.queryByText(/Falta confirmar/)).toBeNull();
});

it("does not mistake unavailable linkage evidence for an unlinked save", () => {
  render(
    <TrainerLeagueStats row={row({ league_save_status: "unavailable" })} />,
  );
  expect(
    screen.getByText(/No se ha podido comprobar la vinculación/),
  ).toBeVisible();
  expect(screen.queryByText(/Sin partida vinculada/)).toBeNull();
  expect(deaths()).toHaveTextContent("—");
});
