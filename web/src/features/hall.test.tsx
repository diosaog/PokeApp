import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
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
                    { display_name: "Antonio" },
                    { display_name: "Lucía" },
                  ],
                },
                {
                  id: "runner",
                  name: "Dúo rival",
                  members: [
                    { display_name: "Marta" },
                    { display_name: "Iván" },
                  ],
                },
              ],
            },
          ],
        }
      : [{ id: "league-winner", display_name: "Campeona de Liga" }],
  }),
  useApp: () => ({}),
  useOverview: () => ({}),
  usePC: () => ({}),
}));
it("renders both certified doubles members and links the exact Cup and season", () => {
  render(
    <MemoryRouter>
      <HallPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("Antonio & Lucía")).toBeInTheDocument();
  expect(screen.getByText("Finalista: Marta & Iván")).toBeInTheDocument();
  expect(screen.getByText("Campeona de Liga")).toBeInTheDocument();
  expect(
    screen.queryByText("Finalista: Entrenador histórico"),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Ver esta Copa" })).toHaveAttribute(
    "href",
    "/copa/exact-cup?season=season",
  );
});
