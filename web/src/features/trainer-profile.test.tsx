import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { TrainerProfilePage } from "./trainer-profile";
import { TrainersPage } from "./trainers";

const mocks = vi.hoisted(() => ({
  member: true,
  noSave: false,
  accountsEnabled: true,
  historyKnown: true,
  linked: true,
}));
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
  useViewer: () => "me",
  useApp: () => ({
    me: { trainer_id: "me", is_admin: false },
    season: "season",
    accountsEnabled: mocks.accountsEnabled,
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
    data: {
      status: "ready",
      save: { id: "me", game: "Y" },
      pokemon: [],
      dead_box: 7,
    },
    personal: true,
    seasonGame: "SN",
    isPending: false,
    error: null,
  }),
  useRead: (path: string) => ({
    isPending: false,
    error: null,
    data: path.startsWith("/v1/accounts?")
      ? {
          items: [
            { trainer_id: "me", display_name: "Yo", photo_url: null },
            { trainer_id: "rival", display_name: "Rival", photo_url: null },
          ],
          has_more: false,
        }
      : path.startsWith("/v1/accounts/")
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
          : path.endsWith("/wipe-revivals")
            ? {
                season_id: "season",
                revived_after_wipe: 2,
                revision: 1,
                editable: true,
                blocking_reason: null,
                replayed: false,
              }
            : path.endsWith("/league")
              ? {
                  season: { id: "season", status: "active" },
                  rows: ["me", "rival"].map((trainer_id) => ({
                    trainer_id,
                    league_save_status: mocks.linked ? "linked" : "unlinked",
                    coin_balance: "4",
                    total_points: mocks.historyKnown ? "-0.6" : null,
                    dead_count: 3,
                    historical_deaths: mocks.historyKnown ? 6 : null,
                    historical_deaths_status: mocks.historyKnown
                      ? "known"
                      : "unknown",
                    historical_deaths_source: mocks.historyKnown
                      ? "audited_event_history"
                      : "death_history_baseline_required",
                  })),
                  days: [],
                }
              : path.includes("/collection")
                ? mocks.noSave
                  ? {
                      status: "no_current_save",
                      reason: "no_synced_save",
                      pokemon: [],
                    }
                  : {
                      status: "ready",
                      source: "personal",
                      game: "Y",
                      pokemon: [],
                    }
                : undefined,
  }),
}));
vi.mock("./inventory", () => ({ Inventory: () => <p>Inventario</p> }));

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
  mocks.accountsEnabled = true;
  mocks.historyKnown = true;
  mocks.linked = true;
});
afterEach(cleanup);

function expectNoInlineSettings() {
  // Name, photo, PIN and app preferences live in the «Mi perfil» dialog.
  expect(
    screen.queryByRole("region", { name: "Opciones personales" }),
  ).toBeNull();
  expect(screen.queryByRole("button", { name: "Editar mi perfil" })).toBeNull();
  expect(screen.queryByText("Ajustes de la app")).toBeNull();
  expect(screen.queryByLabelText("PIN actual")).toBeNull();
  expect(screen.queryByLabelText("Nombre de entrenador")).toBeNull();
}

it("the own profile keeps team, boxes and Dead Box 7 without inline settings", () => {
  profile("me");
  expectNoInlineSettings();
  expect(screen.getByRole("heading", { name: "Equipo" })).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Muertos · Caja 7" }),
  ).toBeVisible();
  expect(screen.getByText("Inventario")).toBeVisible();
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

it("without a season the own profile shows the save and no inline settings", () => {
  mocks.member = false;
  profile("me");
  expect(screen.getByRole("heading", { name: "Equipo" })).toBeVisible();
  expectNoInlineSettings();
});

function expectLeagueStats(container: HTMLElement, deathTotal: string) {
  const field = (name: string) =>
    within(container).getByText(name).closest(".stat-pill")!;
  expect(field("Muertos")).toHaveTextContent(deathTotal);
  expect(field("Monedas")).toHaveTextContent("4");
  expect(field("Puntos")).toHaveTextContent("-0,6");
  expect(
    within(container).queryByText(
      /Liga seleccionada|Falta confirmar|no acreditan/,
    ),
  ).toBeNull();
}

it.each([true, false])(
  "cards and profile agree on configured-box deaths and ledger balance (accounts=%s)",
  (accountsEnabled) => {
    mocks.accountsEnabled = accountsEnabled;
    render(
      <MemoryRouter>
        <TrainersPage />
      </MemoryRouter>,
    );
    const card = screen
      .getByRole("heading", { name: "Yo" })
      .closest("article")!;
    expectLeagueStats(card, "3");
    expect(
      within(card).queryByText(/Partida activa|progreso personal|no acreditan/),
    ).toBeNull();
    cleanup();
    profile("me");
    expectLeagueStats(document.querySelector(".profile-identity")!, "3");
  },
);

it("shows the observed box count even when the historical baseline is pending", () => {
  mocks.historyKnown = false;
  render(
    <MemoryRouter>
      <TrainersPage />
    </MemoryRouter>,
  );
  const card = screen.getByRole("heading", { name: "Yo" }).closest("article")!;
  expect(
    within(card).getByText("Muertos").closest(".stat-pill"),
  ).toHaveTextContent("3");
  expect(
    within(card).getByText("Puntos").closest(".stat-pill"),
  ).toHaveTextContent("\u2014");
  expect(
    within(card).queryByText(/Falta confirmar|pendientes|Liga seleccionada/),
  ).toBeNull();
  cleanup();
  profile("rival");
  const identity = document.querySelector<HTMLElement>(".profile-identity")!;
  expect(
    within(identity).getByText("Muertos").closest(".stat-pill"),
  ).toHaveTextContent("3");
  expect(
    within(identity).queryByText(
      /Falta confirmar|pendientes|Liga seleccionada/,
    ),
  ).toBeNull();
  expect(screen.queryByRole("button", { name: "Editar mi perfil" })).toBeNull();
  expect(screen.queryByText("Inventario")).toBeNull();
});

it("shows a validated personal fallback without linking disclaimers or a public mutation", () => {
  mocks.historyKnown = false;
  mocks.linked = false;
  render(
    <MemoryRouter>
      <TrainersPage />
    </MemoryRouter>,
  );
  const card = screen
    .getByRole("heading", { name: "Rival" })
    .closest("article")!;
  expect(
    within(card).getByText("Muertos").closest(".stat-pill"),
  ).toHaveTextContent("3");
  expect(
    within(card).queryByText(/Sin partida vinculada|premios ni muertes/),
  ).toBeNull();
  cleanup();
  profile("rival");
  const identity = document.querySelector<HTMLElement>(".profile-identity")!;
  expect(
    within(identity).getByText("Muertos").closest(".stat-pill"),
  ).toHaveTextContent("3");
  expect(
    within(identity).queryByText(/Sin partida vinculada|premios ni muertes/),
  ).toBeNull();
  expect(screen.queryByRole("button", { name: /vincular/i })).toBeNull();
});

it("the wipe counter sits right under the own licence card", () => {
  profile("me");
  const identity = document.querySelector(".profile-identity")!;
  const wipe = screen
    .getByRole("heading", { name: "Revividos tras wipe" })
    .closest(".wipe-revivals")!;
  expect(identity.nextElementSibling).toBe(wipe);
  expect(identity.parentElement).toHaveClass("profile-licence-column");
  expect(screen.getByLabelText("Cantidad")).toHaveTextContent("2");
  expect(
    screen.getByRole("button", { name: "Sumar un revivido" }),
  ).toBeEnabled();
});

it("another trainer's profile never offers the wipe editor", () => {
  profile("rival");
  expect(
    screen.queryByRole("button", { name: "Sumar un revivido" }),
  ).toBeNull();
  expect(screen.queryByRole("button", { name: "Actualizar" })).toBeNull();
});
