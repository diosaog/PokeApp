import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Model } from "../api/types";
import { AdminPage } from "./admin";

const mocks = vi.hoisted(() => ({
  setup: {} as Model<"SeasonSetup">,
  overview: {} as Model<"OverviewRead">,
  day: {} as Model<"DayState">,
  execute: vi.fn(),
  retry: vi.fn(),
  holdNavigation: vi.fn(),
  releaseNavigation: vi.fn(),
  uncertain: false,
}));
vi.mock("../state", () => ({
  useApp: () => ({
    season: "season",
    holdAdminNavigation: mocks.holdNavigation,
    adminOperationPending: mocks.uncertain,
  }),
  useRead: (path: string) => ({
    data: path.endsWith("/setup")
      ? mocks.setup
      : path.endsWith("/trainers")
        ? [{ id: "new-trainer", display_name: "Elena" }]
        : mocks.day,
    isPending: false,
    error: null,
  }),
  useOverview: () => ({ data: mocks.overview }),
}));
vi.mock("./initial-assignment", () => ({ InitialAssignment: () => null }));
vi.mock("./championship", () => ({ ChampionshipReview: () => null }));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  Modal: ({
    children,
    title,
  }: {
    children: React.ReactNode;
    title: string;
  }) => (
    <div role="dialog" aria-label={title}>
      {children}
    </div>
  ),
  useCommand: () => ({
    pending: false,
    uncertain: mocks.uncertain,
    error: null,
    success: false,
    execute: mocks.execute,
    retry: mocks.retry,
  }),
}));

function page() {
  return (
    <MemoryRouter>
      <AdminPage />
    </MemoryRouter>
  );
}
function tab(name: string) {
  fireEvent.click(screen.getByRole("tab", { name }));
}
function submitConfiguration() {
  fireEvent.submit(screen.getByLabelText("Nombre de versión").closest("form")!);
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.uncertain = false;
  mocks.execute.mockResolvedValue(true);
  mocks.holdNavigation.mockReturnValue(mocks.releaseNavigation);
  mocks.setup = {
    initial_assignment_rule: "observed_deaths_v1",
    season: {
      id: "season",
      name: "Liga Horizonte",
      status: "active",
      started_at: null,
    },
    setup_revision: 7,
    roster_revision: 4,
    config_revision: 3,
    current_matchday_id: "day",
    participants: [
      {
        id: "player",
        trainer_id: "trainer",
        display_name: "Antonio",
        status: "active",
        seed_order: 1,
        stats_ready: true,
      },
    ],
    config_versions: [
      {
        id: "config",
        name: "Reglas actuales",
        version_number: 1,
        effective_from_matchday: 1,
        total_matchdays: 4,
        division_sizes: { A: 2, B: 2 },
        movement_count: 1,
        scoring: { "1": 4, "2": 2 },
        coin_rewards: { "1": 4, "2": 2 },
        rules: {
          team_lock_required: true,
          last_b_gets_steal: false,
          badge_reward_coins: 0,
          game_completion_reward_coins: 20,
        },
        roster_revision: 4,
        used: true,
        is_current: true,
      },
    ],
    divisions: [],
    memberships: [],
    first_matchday: null,
    readiness: {
      can_activate: false,
      blocking_reasons: ["is_draft"],
      checks: {
        has_roster: true,
        has_valid_config: true,
        no_other_active_season: true,
        is_draft: false,
        initial_assignment_pending: true,
      },
    },
  };
  mocks.overview = {
    season: {
      id: "season",
      name: "Liga Horizonte",
      status: "active",
      current_matchday_id: "day",
    },
    players: [],
    days: [{ id: "day", number: 2, status: "scheduled" }],
    matches: [],
    divisions: [],
    memberships: [],
    snapshots: [],
    locks: [],
    points: [],
    balance: "0",
  };
  mocks.day = {
    season_id: "season",
    matchday_id: "day",
    current_matchday_id: "day",
    state: "scheduled",
    revision: 2,
    results_revision: 1,
    snapshot_revision: 0,
    matches: [],
  };
});
afterEach(cleanup);

it("inherits current server rewards including zero and submits the captured configuration revisions", () => {
  render(page());
  tab("Configuración");
  expect(screen.getByLabelText("Monedas por medalla observada")).toHaveValue(0);
  expect(
    screen.getByLabelText("Monedas por vencer al Campeón del juego"),
  ).toHaveValue(20);
  expect(
    screen.getByText(/La nueva versión parte de Reglas actuales/),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Guardar nombre" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Nombre de versión"), {
    target: { value: "Reglas siguientes" },
  });
  submitConfiguration();
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/season/config-versions",
    expect.objectContaining({
      expected_config_revision: 3,
      expected_roster_revision: 4,
      rules: {
        team_lock_required: true,
        last_b_gets_steal: false,
        badge_reward_coins: 0,
        game_completion_reward_coins: 20,
      },
    }),
  );
});

it("requires explicit renewed review when server configuration changes instead of submitting old fields with a new revision", () => {
  const view = render(page());
  tab("Configuración");
  fireEvent.change(screen.getByLabelText("Monedas por medalla observada"), {
    target: { value: "9" },
  });
  mocks.setup = {
    ...mocks.setup,
    config_revision: 4,
    config_versions: mocks.setup.config_versions.map((config) => ({
      ...config,
      rules: { ...config.rules, badge_reward_coins: 7 },
    })),
  };
  view.rerender(page());
  expect(screen.getByLabelText("Monedas por medalla observada")).toHaveValue(9);
  expect(screen.getByRole("button", { name: "Crear versión" })).toBeDisabled();
  submitConfiguration();
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar configuración actualizada" }),
  );
  expect(screen.getByLabelText("Monedas por medalla observada")).toHaveValue(7);
  fireEvent.change(screen.getByLabelText("Nombre de versión"), {
    target: { value: "Revisada" },
  });
  submitConfiguration();
  expect(mocks.execute).toHaveBeenCalledWith(
    expect.any(String),
    expect.objectContaining({ expected_config_revision: 4 }),
  );
});

it.each(["", "-1", "0.5", "2147483648"])(
  "rejects invalid reward value %s even on a direct form submission",
  (value) => {
    render(page());
    tab("Configuración");
    fireEvent.change(screen.getByLabelText("Nombre de versión"), {
      target: { value: "Intento" },
    });
    fireEvent.change(screen.getByLabelText("Monedas por medalla observada"), {
      target: { value },
    });
    submitConfiguration();
    expect(mocks.execute).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "cantidades enteras válidas",
    );
  },
);

it("keeps the configuration and selector disabled while the original request can be retried", () => {
  const view = render(page());
  tab("Configuración");
  mocks.uncertain = true;
  view.rerender(page());
  expect(screen.getByLabelText("Versión a configurar")).toBeDisabled();
  expect(screen.getByLabelText("Monedas por medalla observada")).toBeDisabled();
  expect(screen.getByRole("tab", { name: "Entrenadores" })).toBeDisabled();
  expect(mocks.holdNavigation).toHaveBeenCalledTimes(2);
  fireEvent.click(
    screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
  );
  expect(mocks.retry).toHaveBeenCalledTimes(1);
  expect(mocks.execute).not.toHaveBeenCalled();
  mocks.uncertain = false;
  view.rerender(page());
  expect(mocks.releaseNavigation).toHaveBeenCalledTimes(2);
  expect(screen.getByRole("tab", { name: "Entrenadores" })).toBeEnabled();
});

it("makes initial and legacy defaults explicit instead of implying saved reward values", () => {
  mocks.setup.config_versions = [];
  render(page());
  tab("Configuración");
  expect(
    screen.getByText("No hay una configuración vigente."),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/La primera configuración usa los valores iniciales de 4/),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Monedas por medalla observada")).toHaveValue(4);
  expect(
    screen.getByLabelText("Monedas por vencer al Campeón del juego"),
  ).toHaveValue(12);
});

it("offers only unused named replacements and preserves the reason in the existing contract", () => {
  mocks.setup.config_versions.push({
    ...mocks.setup.config_versions[0],
    id: "next",
    name: "Próxima jornada",
    used: false,
    is_current: false,
    rules: {
      team_lock_required: false,
      last_b_gets_steal: false,
      badge_reward_coins: 7,
      game_completion_reward_coins: 0,
    },
  });
  render(page());
  tab("Configuración");
  expect(
    screen.queryByRole("option", { name: /Reemplazar Reglas actuales/ }),
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Versión a configurar"), {
    target: { value: "next" },
  });
  expect(
    screen.getByLabelText("Monedas por vencer al Campeón del juego"),
  ).toHaveValue(0);
  fireEvent.change(screen.getByLabelText("Motivo de reemplazo"), {
    target: { value: "Premios acordados" },
  });
  submitConfiguration();
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/season/config-versions/next/replace-unused",
    expect.objectContaining({
      reason: "Premios acordados",
      expected_config_revision: 3,
    }),
  );
});

it("renders human readiness and status names without leaking unknown internal reason codes", () => {
  mocks.setup.readiness.blocking_reasons = [
    "has_valid_config",
    "no_other_active_season",
    "private_unknown_internal",
  ];
  render(page());
  expect(screen.getByText("En curso")).toBeInTheDocument();
  expect(
    screen.getByText(/Guarda una configuración válida/),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/private_unknown_internal/),
  ).not.toBeInTheDocument();
  tab("Entrenadores");
  expect(screen.getByText("Activo")).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Elena" })).toBeInTheDocument();
});

it("disables participation changes after the current day opens and explains the League-only disqualification", () => {
  const view = render(page());
  tab("Entrenadores");
  fireEvent.click(screen.getByRole("button", { name: "Gestionar estado" }));
  expect(
    screen.getByRole("option", { name: "Descalificación de la Liga" }),
  ).toBeInTheDocument();
  expect(
    within(screen.getByRole("dialog")).getByText(
      /no implica una descalificación automática de la Copa/,
    ),
  ).toBeInTheDocument();
  mocks.overview = {
    ...mocks.overview,
    days: [{ id: "day", number: 2, status: "open" }],
  };
  view.rerender(page());
  expect(
    screen.getByRole("button", { name: "Confirmar cambio de estado" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Gestionar estado" }),
  ).toBeDisabled();
});

it("disables invalid historical operations and shows Team Lock presence without inferring timing", () => {
  mocks.setup.season.status = "archived";
  mocks.overview.locks = [
    {
      trainer_id: "trainer",
      matchday_id: "day",
      locked_at: "2026-10-07T12:00:00Z",
      is_late: true,
      public_team_snapshot: [],
    },
  ];
  render(page());
  tab("Zona de riesgo");
  expect(
    screen.getByRole("button", { name: "Archivar temporada" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Descartar temporada" }),
  ).toBeDisabled();
  tab("Competición");
  expect(screen.getByRole("button", { name: "Abrir jornada" })).toBeDisabled();
  expect(screen.getByText("Fijado")).toBeInTheDocument();
  expect(screen.queryByText("Tarde", { exact: true })).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Preparar primera jornada" }),
  ).not.toBeInTheDocument();
});
