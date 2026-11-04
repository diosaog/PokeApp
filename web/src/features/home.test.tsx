import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { HomePage } from "./home";

const mocks = vi.hoisted(() => ({
  league: {} as Record<string, unknown>,
  overview: {} as Record<string, unknown>,
  pc: null as Record<string, unknown> | null,
}));
vi.mock("../state", () => ({
  useApp: () => ({
    season: "season",
    me: { trainer_id: "t", display_name: "Anto" },
  }),
  useOverview: () => ({ data: mocks.overview, isPending: false, error: null }),
  usePC: () => ({ data: mocks.pc, isPending: false, error: null }),
  useRead: () => ({ data: mocks.league, isPending: false, error: null }),
}));
afterEach(cleanup);

function fixture(total: string | null, historySource: string | null = null) {
  mocks.pc = null;
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
        historical_deaths_source: historySource,
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

it("Home hides numerical form labels while preserving the Gourgeist form sprite", () => {
  fixture("0");
  mocks.pc = {
    status: "ready",
    save: { game: "Y" },
    pokemon: [
      {
        location: "Equipo · 1",
        pokemon: { species: "Gourgeist", nickname: "Jalowin", form: 2 },
      },
    ],
  };
  render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  expect(screen.getByAltText("Gourgeist")).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/711-form-2.png",
  );
  expect(screen.queryByText(/Forma \d/)).not.toBeInTheDocument();
});

it("links an unconfirmed points balance to the own history without inventing zero", () => {
  fixture(null, "death_history_baseline_required");
  const view = render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  expect(screen.getByText(/Tus puntos oficiales aparecen como/)).toBeVisible();
  expect(
    screen.getByRole("link", { name: /Ir a confirmar mi historial/ }),
  ).toHaveAttribute("href", "/entrenadores/t");
  fixture("0", "audited_event_history");
  view.rerender(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  expect(
    screen.queryByText(/Tus puntos oficiales aparecen como/),
  ).not.toBeInTheDocument();
});
