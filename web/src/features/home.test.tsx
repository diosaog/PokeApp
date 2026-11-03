import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { HomePage } from "./home";

const mocks = vi.hoisted(() => ({
  league: {} as Record<string, unknown>,
  overview: {} as Record<string, unknown>,
}));
vi.mock("../state", () => ({
  useApp: () => ({
    season: "season",
    me: { trainer_id: "t", display_name: "Anto" },
  }),
  useOverview: () => ({ data: mocks.overview, isPending: false, error: null }),
  usePC: () => ({ data: null, isPending: false, error: null }),
  useRead: () => ({ data: mocks.league, isPending: false, error: null }),
}));
afterEach(cleanup);

function fixture(total: string | null) {
  const season = {
    id: "season",
    name: "ChampionsLocke",
    status: "active",
    current_matchday_id: null,
  };
  mocks.overview = {
    season,
    days: [],
    players: [
      {
        id: "p",
        trainer_id: "t",
        display_name: "Anto",
        status: "active",
        progress: { state: "unknown" },
      },
    ],
    matches: [],
    locks: [],
  };
  mocks.league = {
    season,
    days: [],
    rows: [
      {
        season_player_id: "p",
        trainer_id: "t",
        display_name: "Anto",
        status: "active",
        total_points: total,
        coin_balance: 8,
        dead_count: 0,
      },
    ],
  };
}

it("shows exact zero points as 0 instead of the decimal artefact", () => {
  fixture("0.000000000000000000000");
  render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  const value = screen
    .getByText("Puntos", { selector: ".stat-pill span" })
    .parentElement!.querySelector("strong")!;
  expect(value.textContent).toBe("0");
  expect(document.body.textContent).not.toContain("0.000");
  // Status lines that explain the current state stay.
  expect(
    screen.getByText(
      "No tienes un enfrentamiento pendiente en la jornada actual.",
    ),
  ).toBeVisible();
});

it("shows a negative tenth and keeps unknown points distinct", () => {
  fixture("-0.40");
  const { unmount } = render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  expect(
    screen
      .getByText("Puntos", { selector: ".stat-pill span" })
      .parentElement!.querySelector("strong")!.textContent,
  ).toBe("-0,4");
  unmount();
  fixture(null);
  render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  expect(
    screen
      .getByText("Puntos", { selector: ".stat-pill span" })
      .parentElement!.querySelector("strong")!.textContent,
  ).toBe("—");
});
