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
  preview: null as Record<string, unknown> | null,
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
          : path.endsWith("/cancellation-preview")
            ? mocks.preview
            : path.endsWith("/league")
              ? {
                  rows: [{ season_player_id: "player", dead_box_number: 8 }],
                }
              : path.startsWith("/v1/read/seasons?")
                ? { items: [], next_offset: null }
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
    can_discard: false,
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

function fourPlayerDraft() {
  mocks.setup.season.status = "draft";
  mocks.setup.config_versions[0].used = false;
  mocks.setup.participants = Array.from({ length: 4 }, (_, i) => ({
    ...mocks.setup.participants[0],
    id: `player-${i}`,
    trainer_id: `trainer-${i}`,
  }));
  mocks.setup.config_versions[0].scoring = { "1": 4, "2": 2, "3": 1, "4": 0 };
  mocks.setup.config_versions[0].coin_rewards = {
    "1": 4,
    "2": 2,
    "3": 1,
    "4": 0,
  };
}

it("configures draft structure with generated internal metadata and preserves reward defaults", () => {
  fourPlayerDraft();
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

it("configures one league without a B division, movement or last-of-B reward", () => {
  fourPlayerDraft();
  render(page());
  tab("Configuración");
  expect(screen.getByLabelText(/Liga A y Liga B/)).toBeChecked();
  fireEvent.click(screen.getByLabelText(/Una Liga/));
  expect(screen.queryByLabelText("Participantes en B")).not.toBeInTheDocument();
  expect(
    screen.queryByLabelText("Ascensos / descensos"),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Último de B recibe robo")).not.toBeInTheDocument();
  expect(screen.getByText(/Participantes en la Liga/)).toHaveTextContent("4");
  fireEvent.submit(screen.getByLabelText("Total de jornadas").closest("form")!);
  const body = mocks.execute.mock.calls[0][1];
  expect(body.division_sizes).toEqual({ A: 4 });
  expect(body.movement_count).toBe(0);
  expect(body.rules.last_b_gets_steal).toBe(false);
});

it("an older season without the observed assignment keeps Liga A and Liga B", () => {
  fourPlayerDraft();
  mocks.setup.initial_assignment_rule = null;
  render(page());
  tab("Configuración");
  expect(screen.queryByLabelText(/Una Liga/)).not.toBeInTheDocument();
  expect(screen.getByLabelText("Participantes en B")).toBeInTheDocument();
  fireEvent.submit(screen.getByLabelText("Total de jornadas").closest("form")!);
  expect(mocks.execute.mock.calls[0][1].division_sizes).toEqual({
    A: 2,
    B: 2,
  });
});

it("requires explicit common coins for a single-day round robin and shows its win/prize rules", () => {
  mocks.setup.season.status = "draft";
  mocks.setup.config_versions[0].used = false;
  render(page());
  tab("Configuración");
  fireEvent.click(screen.getByLabelText(/Una Liga/));
  fireEvent.change(screen.getByLabelText("Total de jornadas"), {
    target: { value: "1" },
  });
  const common = screen.getByLabelText(
    "Monedas de jornada para cada participante",
  );
  expect(common).toHaveValue(null);
  expect(
    screen.queryByLabelText("Puntos por posición"),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByLabelText("Monedas por posición"),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/2 puntos por victoria/)).toHaveTextContent(
    "Primero: Blindar Pokémon extra. Último: Robar Pokémon extra.",
  );
  fireEvent.submit(common.closest("form")!);
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.change(common, { target: { value: "23" } });
  fireEvent.submit(common.closest("form")!);
  expect(mocks.execute.mock.calls[0][1]).toEqual(
    expect.objectContaining({
      total_matchdays: 1,
      division_sizes: { A: 1 },
      scoring: { "1": 0 },
      coin_rewards: { "1": 23 },
    }),
  );
});

it("keeps an existing uniform configured coin amount when selecting a single-day league", () => {
  mocks.setup.season.status = "draft";
  mocks.setup.config_versions[0].used = false;
  mocks.setup.config_versions[0].total_matchdays = 1;
  mocks.setup.config_versions[0].coin_rewards = { "1": 19, "2": 19 };
  render(page());
  tab("Configuración");
  fireEvent.click(screen.getByLabelText(/Una Liga/));
  expect(
    screen.getByLabelText("Monedas de jornada para cada participante"),
  ).toHaveValue(19);
});

it("shows the fixed competition structure once the season has started", () => {
  mocks.setup.config_versions[0].division_sizes = { A: 4 };
  render(page());
  tab("Configuración");
  expect(screen.getByText("Una Liga")).toBeInTheDocument();
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  expect(
    screen.getByText(/no pueden cambiarse con la temporada en marcha/),
  ).toBeInTheDocument();
});

function fivePlayerDraft() {
  mocks.setup.season.status = "draft";
  mocks.setup.participants = Array.from({ length: 5 }, (_, i) => ({
    ...mocks.setup.participants[0],
    id: `player-${i}`,
    trainer_id: `trainer-${i}`,
  }));
  Object.assign(mocks.setup.config_versions[0], {
    used: false,
    total_matchdays: 1,
    division_sizes: { A: 5 },
    movement_count: 0,
    scoring: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 },
    coin_rewards: { "1": 9, "2": 9, "3": 9, "4": 9, "5": 9 },
  });
}

it("shows empty rewards as empty and rejects missing, extra or noninteger positions", () => {
  fivePlayerDraft();
  mocks.setup.config_versions = [];
  render(page());
  tab("Configuración");
  fireEvent.click(screen.getByLabelText(/Una Liga/));
  fireEvent.change(screen.getByLabelText("Total de jornadas"), {
    target: { value: "4" },
  });
  const points = screen.getByLabelText("Puntos por posición");
  const coins = screen.getByLabelText("Monedas por posición");
  expect(points).toHaveValue("");
  expect(points).not.toHaveAttribute("placeholder", "10,8,6,4");
  fireEvent.change(coins, { target: { value: "5,4,3,2,0" } });
  for (const value of [
    "",
    "10,8,6,4",
    "10,8,6,4,2,0",
    "10,8,6,4,",
    "10,8,6,4,-1",
    "10,8,6,4,1.5",
  ]) {
    fireEvent.change(points, { target: { value } });
    fireEvent.submit(points.closest("form")!);
    expect(mocks.execute).not.toHaveBeenCalled();
  }
  fireEvent.change(points, { target: { value: "10, 8, 6, 4, 0" } });
  fireEvent.submit(points.closest("form")!);
  expect(mocks.execute).toHaveBeenCalledOnce();
  expect(mocks.execute.mock.lastCall![0]).toBe(
    "/v1/admin/seasons/season/config-versions",
  );
});

it("requires five actual positional values for five players when changing 1 to 4 days", () => {
  fivePlayerDraft();
  render(page());
  tab("Configuración");
  fireEvent.change(screen.getByLabelText("Total de jornadas"), {
    target: { value: "4" },
  });
  const points = screen.getByLabelText("Puntos por posición");
  const coins = screen.getByLabelText("Monedas por posición");
  expect(points).toHaveValue("0,0,0,0,0");
  expect(coins).toHaveValue("9,9,9,9,9");
  fireEvent.change(points, { target: { value: "10,8,6,4" } });
  fireEvent.change(coins, { target: { value: "10,8,6,4" } });
  fireEvent.submit(points.closest("form")!);
  expect(mocks.execute).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toHaveTextContent("5 valores");
  fireEvent.change(points, { target: { value: "10,8,6,4,2" } });
  fireEvent.change(coins, { target: { value: "50,40,30,20,0" } });
  fireEvent.submit(points.closest("form")!);
  expect(mocks.execute.mock.calls[0][1]).toEqual(
    expect.objectContaining({
      total_matchdays: 4,
      division_sizes: { A: 5 },
      movement_count: 0,
      scoring: { "1": 10, "2": 8, "3": 6, "4": 4, "5": 2 },
      coin_rewards: { "1": 50, "2": 40, "3": 30, "4": 20, "5": 0 },
    }),
  );
});

it("preserves separate one-day and positional edits across 1/2/3/4 switches and reloads saved values", () => {
  fivePlayerDraft();
  const view = render(page());
  tab("Configuración");
  const total = () => screen.getByLabelText("Total de jornadas");
  fireEvent.change(
    screen.getByLabelText("Monedas de jornada para cada participante"),
    { target: { value: "17" } },
  );
  fireEvent.change(total(), { target: { value: "4" } });
  fireEvent.change(screen.getByLabelText("Puntos por posición"), {
    target: { value: "10,8,6,4,2" },
  });
  fireEvent.change(screen.getByLabelText("Monedas por posición"), {
    target: { value: "50,40,30,20,0" },
  });
  for (const days of [1, 2, 1, 3, 1, 4]) {
    fireEvent.change(total(), { target: { value: String(days) } });
    if (days === 1) {
      expect(
        screen.getByLabelText("Monedas de jornada para cada participante"),
      ).toHaveValue(17);
      fireEvent.submit(total().closest("form")!);
      expect(mocks.execute.mock.lastCall![1].coin_rewards).toEqual({
        "1": 17,
        "2": 17,
        "3": 17,
        "4": 17,
        "5": 17,
      });
    } else {
      expect(screen.getByLabelText("Puntos por posición")).toHaveValue(
        "10,8,6,4,2",
      );
      expect(screen.getByLabelText("Monedas por posición")).toHaveValue(
        "50,40,30,20,0",
      );
    }
  }
  fireEvent.submit(total().closest("form")!);
  const body = mocks.execute.mock.lastCall![1];
  mocks.setup = {
    ...mocks.setup,
    config_revision: 4,
    config_versions: [
      {
        ...mocks.setup.config_versions[0],
        ...body,
      },
    ],
  };
  view.rerender(page());
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar formato actual" }),
  );
  expect(total()).toHaveValue(4);
  expect(screen.getByLabelText("Puntos por posición")).toHaveValue(
    "10,8,6,4,2",
  );
  expect(screen.getByLabelText("Monedas por posición")).toHaveValue(
    "50,40,30,20,0",
  );
  fireEvent.submit(total().closest("form")!);
  expect(mocks.execute.mock.lastCall![1].expected_config_revision).toBe(4);
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
    within(screen.getByRole("dialog")).getByText(/no afecta a la Copa/),
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
  // An archived season is no longer running: nothing to cancel, and it says so.
  expect(
    screen.getByRole("button", { name: "Cancelar temporada" }),
  ).toBeDisabled();
  expect(
    screen.getByText(/no hay competición que cancelar/),
  ).toBeInTheDocument();
  tab("Competición");
  expect(screen.getByRole("button", { name: "Abrir jornada" })).toBeDisabled();
  expect(screen.getByText(/horario sin evidencia/)).toBeInTheDocument();
  expect(screen.queryByText("Tarde", { exact: true })).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Preparar primera jornada" }),
  ).not.toBeInTheDocument();
});

const preview = (patch = {}) => ({
  season_id: "season",
  name: "Liga Horizonte",
  status: "active",
  allowed: true,
  mode: "preserving",
  open_robberies: 0,
  open_item_uses: 0,
  participants: 2,
  matchdays: 3,
  closed_matchdays: 2,
  open_matchdays: 1,
  results: 4,
  team_locks: 4,
  purchases: 1,
  pending_purchases: 0,
  coin_transactions: 9,
  coins_awarded: "44",
  progress_rewards: 3,
  saves: 2,
  cups: 0,
  penalties: 0,
  trials: 0,
  ...patch,
});
it("an active season with matchdays can be cancelled after seeing what is kept", () => {
  mocks.preview = preview();
  render(page());
  tab("Zona de riesgo");
  const cancel = screen.getByRole("button", { name: "Cancelar temporada" });
  expect(cancel).toBeEnabled();
  fireEvent.click(cancel);
  const dialog = screen.getByRole("dialog", { name: "Cancelar temporada" });
  expect(dialog).toHaveTextContent(/2 jornadas cerradas/);
  expect(dialog).toHaveTextContent(
    /9 movimientos de monedas \(44 monedas concedidas\)/,
  );
  expect(dialog).toHaveTextContent(/se conserva para la trazabilidad/);
  expect(
    screen.getByLabelText("Motivo (queda en la auditoría)"),
  ).toBeRequired();
  expect(
    screen.getByLabelText("Escribe Liga Horizonte para confirmar"),
  ).toBeRequired();
  expect(
    within(dialog).getByRole("button", { name: /Confirmar operación/ }),
  ).toBeEnabled();
  expect(mocks.execute).not.toHaveBeenCalled();
});
it("an unfinished robbery blocks cancellation and says how to resolve it", () => {
  mocks.preview = preview({ allowed: false, open_robberies: 1 });
  render(page());
  tab("Zona de riesgo");
  fireEvent.click(screen.getByRole("button", { name: "Cancelar temporada" }));
  const dialog = screen.getByRole("dialog", { name: "Cancelar temporada" });
  expect(dialog).toHaveTextContent(/1 robo sin cerrar/);
  expect(dialog).toHaveTextContent(/Economía e incidencias/);
  expect(
    within(dialog).getByRole("button", { name: /Confirmar operación/ }),
  ).toBeDisabled();
});

it("sets one participant's dead box with an audited PUT", () => {
  render(page());
  tab("Entrenadores");
  const card = screen
    .getByRole("heading", { name: "Caja de muertos" })
    .closest("section")!;
  const input = within(card).getByLabelText("Antonio");
  expect(input).toHaveValue(8);
  fireEvent.change(input, { target: { value: "7" } });
  fireEvent.click(within(card).getByRole("button", { name: "Guardar" }));
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/season/participants/player/dead-box",
    { dead_box_number: 7 },
    "PUT",
  );
  fireEvent.change(input, { target: { value: "33" } });
  fireEvent.submit(input.closest("form")!);
  expect(mocks.execute).toHaveBeenCalledTimes(1);
});
