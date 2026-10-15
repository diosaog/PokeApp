import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ScoutingPage } from "./scouting";

const mocks = vi.hoisted(() => ({
  season: "season",
  missing: false,
  day: true,
  empty: false,
  error: null as Error | null,
  reads: vi.fn(),
  pc: vi.fn(),
}));
vi.mock("../state", () => ({
  useApp: () => ({ season: mocks.season }),
  usePC: mocks.pc,
  useRead: (path: string) => {
    mocks.reads(path);
    const id =
      new URL(path, "https://example.invalid").searchParams.get("trainer_id") ||
      "owner";
    return {
      isPending: false,
      error: mocks.error,
      data: {
        trainers: mocks.empty
          ? []
          : [
              { trainer_id: "owner", display_name: "Antonio" },
              { trainer_id: "rival", display_name: "Lucía" },
            ],
        trainer_id: id,
        day: mocks.day ? { number: 1 } : null,
        team: mocks.missing
          ? null
          : Array.from({ length: 6 }, () => ({
              species: "Pikachu",
              nickname: "Fijado",
              types: [],
              item: "Baya",
              moves: [{ name: "Impactrueno" }],
              ability: "PRIVATE_SECRET",
            })),
      },
    };
  },
}));
vi.mock("./trainer-profile", () => ({
  Profile: ({ trainer }: { trainer: string }) => <div>Ficha: {trainer}</div>,
}));
vi.mock("./core", () => ({
  WithSeason: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Pokemon: ({ pokemon }: { pokemon: { nickname: string } }) => (
    <span>{pokemon.nickname}</span>
  ),
}));
const show = (state?: object) =>
  render(
    <MemoryRouter
      initialEntries={[{ pathname: "/entrenadores/scouting", state }]}
    >
      <ScoutingPage />
    </MemoryRouter>,
  );
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  mocks.season = "season";
  mocks.missing = false;
  mocks.day = true;
  mocks.empty = false;
  mocks.error = null;
});

it("selects the full trainer profile without a private-mode switch", () => {
  show();
  expect(screen.getAllByRole("combobox")).toHaveLength(1);
  fireEvent.change(screen.getByLabelText("Entrenador a consultar"), {
    target: { value: "rival" },
  });
  expect(screen.getByText("Ficha: rival")).toBeVisible();
  expect(mocks.pc).not.toHaveBeenCalled();
});
it("shows the profile even without a lock or current matchday", () => {
  mocks.missing = true;
  mocks.day = false;
  show();
  expect(screen.getByText("Ficha: owner")).toBeVisible();
});
it("initial trainer links are scoped to their season and selection resets on season change", () => {
  const view = show({ season: "season", trainer: "rival" });
  expect(mocks.reads).toHaveBeenLastCalledWith(
    "/v1/read/seasons/season/scouting?trainer_id=rival",
  );
  mocks.season = "another";
  view.rerender(
    <MemoryRouter>
      <ScoutingPage />
    </MemoryRouter>,
  );
  expect(mocks.reads).toHaveBeenLastCalledWith(
    "/v1/read/seasons/another/scouting?",
  );
});
it("failed or empty reads cannot render the previous trainer team", () => {
  mocks.empty = true;
  const view = show();
  expect(screen.getByText(/No hay entrenadores publicados/)).toBeVisible();
  mocks.empty = false;
  mocks.error = new Error("read unavailable");
  view.rerender(
    <MemoryRouter>
      <ScoutingPage />
    </MemoryRouter>,
  );
  expect(screen.queryByText("Fijado")).not.toBeInTheDocument();
  expect(mocks.pc).not.toHaveBeenCalled();
});
