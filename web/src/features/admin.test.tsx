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
  rules: {} as Model<"LiveRulesRead">,
  setup: {} as Model<"SeasonSetup">,
  overview: {} as Model<"OverviewRead">,
  day: {} as Model<"DayState">,
  execute: vi.fn(),
  retry: vi.fn(),
  holdNavigation: vi.fn(),
  releaseNavigation: vi.fn(),
  uncertain: false,
  rulesError: null as Error | null,
}));
vi.mock("../state", () => ({
  useApp: () => ({
    season: "season",
    holdAdminNavigation: mocks.holdNavigation,
    adminOperationPending: mocks.uncertain,
  }),
  useRead: (path: string) => ({
    data: path.endsWith("/rules")
      ? mocks.rules
      : path.endsWith("/setup")
        ? mocks.setup
        : path.endsWith("/trainers")
          ? [{ id: "new-trainer", display_name: "Elena" }]
          : mocks.day,
    isPending: false,
    error: path.endsWith("/rules") ? mocks.rulesError : null,
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
beforeEach(() => {
  vi.clearAllMocks();
  mocks.uncertain = false;
  mocks.rulesError = null;
  mocks.rules = {
    season_id: "season",
    revision: 0,
    config_revision: 3,
    badge_reward_coins: 0,
    game_completion_reward_coins: 20,
    effective_at: null,
    editable: true,
  };
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

it("retains the pending rules retry and unsaved input after a failed follow-up read", () => {
  const view = render(page());
  tab("Configuración");
  fireEvent.change(screen.getByLabelText("Monedas por medalla"), {
    target: { value: "9" },
  });
  mocks.uncertain = true;
  mocks.rulesError = new Error("read unavailable");
  view.rerender(page());
  expect(screen.getByLabelText("Monedas por medalla")).toHaveValue(9);
  expect(screen.getByLabelText("Monedas por medalla")).toBeDisabled();
  const card = screen
    .getByRole("heading", { name: "Reglas de recompensas" })
    .closest("section")!;
  fireEvent.click(
    within(card).getByRole("button", { name: "Reintentar la misma solicitud" }),
  );
  expect(mocks.retry).toHaveBeenCalledOnce();
});

it("edits current rewards including zero with no version or future-day requirement", () => {
  render(page());
  tab("Configuración");
  expect(screen.getByLabelText("Monedas por medalla")).toHaveValue(0);
  expect(screen.getByLabelText("Monedas por vencer al Campeón")).toHaveValue(
    20,
  );
  expect(screen.queryByLabelText("Nombre de versión")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Primera jornada")).not.toBeInTheDocument();
  fireEvent.submit(
    screen.getByLabelText("Monedas por medalla").closest("form")!,
  );
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/season/rules",
    {
      expected_revision: 0,
      expected_config_revision: 3,
      badge_reward_coins: 0,
      game_completion_reward_coins: 20,
    },
    "PUT",
  );
  expect(screen.queryByLabelText("Total de jornadas")).not.toBeInTheDocument();
});

it("preserves unsaved rewards on concurrent change and requires deliberate renewed review", () => {
  const view = render(page());
  tab("Configuración");
  fireEvent.change(screen.getByLabelText("Monedas por medalla"), {
    target: { value: "9" },
  });
  mocks.rules = {
    ...mocks.rules,
    revision: 1,
    config_revision: 4,
    badge_reward_coins: 7,
  };
  view.rerender(page());
  expect(screen.getByLabelText("Monedas por medalla")).toHaveValue(9);
  expect(
    screen.getByRole("button", { name: "Guardar cambios" }),
  ).toBeDisabled();
  fireEvent.submit(
    screen.getByLabelText("Monedas por medalla").closest("form")!,
  );
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "He revisado los cambios" }),
  );
  expect(screen.getByLabelText("Monedas por medalla")).toHaveValue(9);
  fireEvent.submit(
    screen.getByLabelText("Monedas por medalla").closest("form")!,
  );
  expect(mocks.execute).toHaveBeenCalledWith(
    expect.any(String),
    expect.objectContaining({
      expected_revision: 1,
      expected_config_revision: 4,
      badge_reward_coins: 9,
    }),
    "PUT",
  );
});

it.each(["", "-1", "0.5", "2147483648"])(
  "rejects invalid reward %s on direct submission",
  (value) => {
    render(page());
    tab("Configuración");
    fireEvent.change(screen.getByLabelText("Monedas por medalla"), {
      target: { value },
    });
    fireEvent.submit(
      screen.getByLabelText("Monedas por medalla").closest("form")!,
    );
    expect(mocks.execute).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("monedas enteras");
  },
);

it("holds navigation and editing while a rule request has an uncertain outcome", () => {
  const view = render(page());
  tab("Configuración");
  mocks.uncertain = true;
  view.rerender(page());
  expect(screen.getByLabelText("Monedas por medalla")).toBeDisabled();
  expect(screen.getByRole("tab", { name: "Entrenadores" })).toBeDisabled();
  fireEvent.click(
    screen.getAllByRole("button", { name: "Reintentar la misma solicitud" })[0],
  );
  expect(mocks.retry).toHaveBeenCalledOnce();
  expect(mocks.execute).not.toHaveBeenCalled();
});

it("configures draft structure with generated internal metadata and preserves reward defaults", () => {
  mocks.setup.season.status = "draft";
  mocks.setup.config_versions[0].used = false;
  render(page());
  tab("Configuración");
  fireEvent.submit(screen.getByLabelText("Total de jornadas").closest("form")!);
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/season/config-versions/config/replace-unused",
    expect.objectContaining({
      name: "Reglas de la Liga",
      effective_from_matchday: 1,
      reason: expect.any(String),
      rules: expect.objectContaining({
        badge_reward_coins: 0,
        game_completion_reward_coins: 20,
      }),
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
      timing_status: "unknown",
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
  expect(screen.getByText(/horario sin evidencia/)).toBeInTheDocument();
  expect(screen.queryByText("Tarde", { exact: true })).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Preparar primera jornada" }),
  ).not.toBeInTheDocument();
});
