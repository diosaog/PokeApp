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
  dead_count: 3,
  dead_count_source: "observed_current_save" as const,
  dead_count_observed_at: null,
  historical_deaths: 7,
  historical_deaths_status: "known" as const,
  league_save_status: "linked" as const,
  ...extra,
});

const deaths = () => screen.getByText("Muertos").closest(".stat-pill");

it("shows the configured-box count and a genuinely empty box as zero", () => {
  const view = render(<TrainerLeagueStats row={row()} />);
  expect(deaths()).toHaveTextContent("3");
  view.rerender(<TrainerLeagueStats row={row({ dead_count: 0 })} />);
  expect(deaths()).toHaveTextContent("0");
});

it("keeps an unreadable count unknown rather than manufacturing zero", () => {
  render(
    <TrainerLeagueStats
      row={row({ dead_count: null, dead_count_source: "unknown" })}
    />,
  );
  expect(deaths()).toHaveTextContent("\u2014");
});

it("shows a server-counted personal fallback with no explanatory paragraphs", () => {
  const view = render(
    <TrainerLeagueStats
      row={row({
        league_save_status: "unlinked",
        historical_deaths: null,
        historical_deaths_status: "unknown",
      })}
    />,
  );
  expect(deaths()).toHaveTextContent("3");
  expect(screen.getByText("Puntos").closest(".stat-pill")).toHaveTextContent(
    "-0,7",
  );
  expect(screen.getByText("Monedas").closest(".stat-pill")).toHaveTextContent(
    "3",
  );
  expect(view.container.querySelector("p")).toBeNull();
  expect(
    screen.queryByText(/historial|vinculada|premios|pendientes/i),
  ).toBeNull();
});

it("leaves an unavailable response unknown with only the three requested labels", () => {
  render(<TrainerLeagueStats />);
  expect(screen.getAllByText("\u2014")).toHaveLength(3);
  expect(
    [...document.querySelectorAll(".stat-pill span")].map((p) => p.textContent),
  ).toEqual(["Puntos", "Monedas", "Muertos"]);
});
