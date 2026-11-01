import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { TrainerProfilePage } from "./trainer-profile";

const mocks = vi.hoisted(() => ({ member: true, noSave: false }));
const observed = (game: string) => ({
  state: "observed",
  game,
  observed_at: "2026-10-28T20:00:00Z",
  badges_count: 3,
  native_model: "gym_badges",
  primary_region: "kalos",
  regions: [{ region: "kalos", earned_badges: [1, 2, 3] }],
});
vi.mock("../state", () => ({
  queries: { invalidateQueries: vi.fn() },
  useApp: () => ({
    me: { trainer_id: "me", is_admin: false },
    season: "season",
    accountsEnabled: true,
    adminOperationPending: false,
  }),
  useOverview: () => ({
    isPending: false,
    data: {
      players: mocks.member
        ? [
            {
              id: "p1",
              trainer_id: "me",
              display_name: "Yo",
              status: "active",
              progress: observed("SN"),
            },
            {
              id: "p2",
              trainer_id: "rival",
              display_name: "Rival",
              status: "active",
              progress: observed("Y"),
            },
          ]
        : [],
    },
  }),
  useMyPC: () => ({
    data: { status: "ready", save: { id: "me", game: "Y" }, pokemon: [] },
    personal: true,
    seasonGame: "SN",
    isPending: false,
    error: null,
  }),
  useRead: (path: string) => ({
    isPending: false,
    error: null,
    data: path.startsWith("/v1/accounts/")
      ? {
          trainer_id: path.split("/").pop(),
          display_name: "Perfil",
          photo_url: null,
          revision: 1,
        }
      : path === "/v1/read/active-saves"
        ? {
            items: [
              {
                trainer_id: "me",
                game: "Y",
                uploaded_at: "2026-10-28T20:00:00Z",
                progress: observed("Y"),
              },
            ],
          }
        : path.endsWith("/league")
          ? { rows: [], days: [] }
          : path.includes("/collection")
            ? mocks.noSave
              ? {
                  status: "no_current_save",
                  reason: "no_synced_save",
                  pokemon: [],
                }
              : { status: "ready", source: "personal", game: "Y", pokemon: [] }
            : undefined,
  }),
}));
vi.mock("./inventory", () => ({ Inventory: () => <p>Inventario</p> }));
vi.mock("./preferences", () => ({
  PreferencesCard: () => (
    <section aria-label="Ajustes de la app">Ajustes de la app</section>
  ),
}));
vi.mock("./account-editor", () => ({ AccountEditor: () => null }));

function profile(id: string) {
  render(
    <MemoryRouter initialEntries={[`/entrenadores/${id}`]}>
      <Routes>
        <Route
          path="/entrenadores/:trainerId"
          element={<TrainerProfilePage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}
beforeEach(() => {
  mocks.member = true;
  mocks.noSave = false;
});
afterEach(cleanup);

it("app settings close the own profile, next to «Editar mi perfil»", () => {
  profile("me");
  const settings = screen.getByRole("region", { name: "Ajustes de la app" });
  const edit = screen.getByRole("button", { name: "Editar mi perfil" });
  // Nothing of the profile comes after the personal options.
  expect(
    edit.compareDocumentPosition(settings) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  const personal = screen.getByRole("region", { name: "Opciones personales" });
  expect(personal).toContainElement(settings);
  expect(personal).toContainElement(edit);
  expect(personal.nextElementSibling).toBeNull();
});

it("another trainer's profile never shows the app settings", () => {
  profile("rival");
  expect(
    screen.queryByRole("region", { name: "Ajustes de la app" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /^Equipo$/ })).toBeVisible();
  expect(screen.getByText(/Partida personal sincronizada/)).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Editar mi perfil" }),
  ).not.toBeInTheDocument();
});

it("explains a genuine missing observation without blaming the absent Team Lock", () => {
  mocks.noSave = true;
  profile("rival");
  expect(
    screen.getByText(/aún no tiene una partida sincronizada/),
  ).toBeVisible();
});

it("the own profile shows the active save and names the season's other game", () => {
  profile("me");
  expect(screen.getAllByText(/Pokémon Y/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/compite con Pokémon Sol/).length).toBeGreaterThan(
    0,
  );
});

it("without a season the own profile still ends with the settings", () => {
  mocks.member = false;
  profile("me");
  expect(screen.getByRole("heading", { name: "Equipo" })).toBeVisible();
  expect(
    screen.getByRole("region", { name: "Opciones personales" }),
  ).toContainElement(screen.getByRole("region", { name: "Ajustes de la app" }));
});
