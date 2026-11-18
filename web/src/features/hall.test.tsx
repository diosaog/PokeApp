import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { HallPage } from "./core";
vi.mock("../state", () => ({
  useRead: (path: string) => ({
    isPending: false,
    error: null,
    data: path.startsWith("/v1/read/hall")
      ? {
          next_offset: null,
          items: [
            {
              id: "league-hall",
              season_id: "league-season",
              competition_type: "league",
              champion_trainer_id: "league-winner",
              finalist_trainer_id: null,
              finalized_at: "2026-10-03T12:00:00Z",
              cup_id: null,
              cup_sides: [],
            },
            {
              id: "hall",
              season_id: "season",
              competition_type: "cup",
              champion_trainer_id: null,
              finalist_trainer_id: null,
              finalized_at: "2026-09-28T12:00:00Z",
              cup_id: "exact-cup",
              champion_side_id: "winner",
              finalist_side_id: "runner",
              cup_sides: [
                {
                  id: "winner",
                  name: "Dúo Aurora",
                  members: [
                    { trainer_id: "t1", display_name: "Antonio" },
                    { trainer_id: "t2", display_name: "Lucía" },
                  ],
                },
                {
                  id: "runner",
                  name: "Dúo rival",
                  members: [
                    { trainer_id: "t3", display_name: "Marta" },
                    { trainer_id: "t4", display_name: "Iván" },
                  ],
                },
              ],
            },
          ],
        }
      : path.startsWith("/v1/read/seasons")
        ? {
            items: [{ id: "season", name: "Copa histórica" }],
            next_offset: null,
          }
        : [{ id: "league-winner", display_name: "Campeona de Liga" }],
  }),
  useApp: () => ({}),
  useOverview: () => ({}),
  usePC: () => ({}),
}));
afterEach(cleanup);
it("renders both certified doubles members and links the exact Cup and season", () => {
  render(
    <MemoryRouter>
      <HallPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("Antonio & Lucía")).toBeInTheDocument();
  expect(screen.getByText("Finalista: Marta & Iván")).toBeInTheDocument();
  expect(screen.getByText("Campeona de Liga")).toBeInTheDocument();
  expect(screen.getByText("Copa histórica")).toBeInTheDocument();
  expect(
    screen.queryByText("Finalista: Entrenador histórico"),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Ver esta Copa" })).toHaveAttribute(
    "href",
    "/copa/exact-cup?season=season",
  );
});

it("2026-11-18: Leyendas shows each past champion's portrait and moving team, nothing else", () => {
  render(
    <MemoryRouter>
      <HallPage />
    </MemoryRouter>,
  );
  // One showcase per trainer, ranked by titles, with portrait and trophies.
  const showcases = screen.getAllByRole("listitem", { name: /títulos$/ });
  expect(showcases.map((s) => s.getAttribute("aria-label"))).toEqual([
    "Samu, 3 títulos",
    "Miguel, 2 títulos",
  ]);
  for (const showcase of showcases)
    expect(within(showcase).getAllByAltText(/Retrato de/)).toHaveLength(1);
  const cards = screen.getAllByRole("article");
  expect(cards.map((c) => c.getAttribute("aria-label"))).toEqual([
    "Samu, campeón de Pokémon Añil",
    "Samu, campeón de Pokémon Rojo Fuego",
    "Samu, campeón de la Copa Rojo Fuego",
    "Miguel, campeón de Pokémon Rubí Omega",
    "Miguel, campeón de Pokémon Platino",
  ]);
  for (const card of cards)
    expect(within(card).getAllByRole("img")).toHaveLength(6); // the team only
  // Every Pokémon resolves to real art; alternate forms keep their own.
  expect(
    screen.queryAllByLabelText(/No se pudo cargar la imagen/),
  ).toHaveLength(0);
  const platino = cards[4];
  expect(within(platino).getByTitle("Deoxys (forma Ataque)")).toBeVisible();
  expect(within(platino).getByAltText("Deoxys")).toHaveAttribute(
    "src",
    "/visuals/v1/gen7/386-form-1.png",
  );
  expect(within(cards[0]).getByAltText("Alakazam")).toHaveAttribute(
    "src",
    "/visuals/v1/pokemon/65-form-1.png",
  );
  // Sprites only: no moves, items or abilities.
  expect(screen.queryByText(/Close Combat|Focus Sash|Cameruptite/)).toBeNull();
});
