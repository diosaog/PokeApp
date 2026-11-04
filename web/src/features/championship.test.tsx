import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Model } from "../api/types";
import { ChampionshipReview } from "./championship";
import { LeagueOperations } from "./league-operations";
import { ApiError } from "../api/client";

const mocks = vi.hoisted(() => ({
  data: null as Model<"ChampionshipRead"> | null,
  refetch: vi.fn(),
  execute: vi.fn(),
  retry: vi.fn(),
  pending: false,
  uncertain: false,
  error: null as unknown,
  hold: vi.fn(() => () => {}),
  isAdmin: true,
}));
vi.mock("../state", () => ({
  useApp: () => ({
    season: "season",
    me: { trainer_id: "t2", is_admin: mocks.isAdmin },
    holdAdminNavigation: mocks.hold,
  }),
  // 079: the opening control reads its own readiness (not under test here).
  useRead: (path: string) => ({
    data: path.includes("/league/readiness") ? undefined : mocks.data,
    isPending: false,
    isFetching: false,
    error: null,
    refetch: mocks.refetch,
  }),
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  Modal: ({
    title,
    children,
    onClose,
  }: {
    title: string;
    children: React.ReactNode;
    onClose: () => void;
  }) => (
    <div role="dialog" aria-label={title}>
      <button type="button" aria-label="Cerrar" onClick={onClose}>
        Cerrar
      </button>
      {children}
    </div>
  ),
  useCommand: () => ({
    pending: mocks.pending,
    uncertain: mocks.uncertain,
    error: mocks.error,
    success: false,
    execute: mocks.execute,
    retry: mocks.retry,
  }),
}));
afterEach(cleanup);
beforeEach(() => {
  mocks.execute.mockReset();
  mocks.execute.mockResolvedValue(true);
  mocks.retry.mockReset();
  mocks.hold.mockClear();
  mocks.pending = false;
  mocks.uncertain = false;
  mocks.error = null;
  mocks.isAdmin = true;
  mocks.data = {
    season_id: "season",
    state: "ready",
    setup_revision: 7,
    input_hash: "a".repeat(64),
    players: [
      {
        season_player_id: "p1",
        trainer_id: "t1",
        display_name: "Primera fila",
        total_points: "-0.000000000000000001",
        adjusted_deaths: 3,
      },
      {
        season_player_id: "p2",
        trainer_id: "t2",
        display_name: "Ganadora oficial",
        total_points: "0.000000000000000001",
        adjusted_deaths: null,
      },
    ],
    tied_player_ids: [],
    champion_trainer_id: "t2",
    resolution_type: "unique_points",
    finalist_status: "OWNER_DECISION_REQUIRED",
    blocking_reason: null,
  };
});
it("renders exact official totals and the server's champion without ranking or rounding", () => {
  render(<ChampionshipReview seasonName="Liga" />);
  expect(
    screen.getByRole("heading", { name: "Campeón de Liga: Ganadora oficial" }),
  ).toBeInTheDocument();
  // Exact digits with the app's decimal separator: never rounded to 0.
  expect(screen.getByText("-0,000000000000000001")).toBeInTheDocument();
  expect(screen.getByText("0,000000000000000001")).toBeInTheDocument();
  expect(screen.getByText("Sin evidencia oficial")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Finalizar Liga" })).toBeEnabled();
});
it("offers no fabricated champion or finalization for unresolved title", () => {
  Object.assign(mocks.data!, {
    state: "owner_decision_required",
    champion_trainer_id: null,
    resolution_type: null,
  });
  render(<ChampionshipReview seasonName="Liga" />);
  expect(
    screen.getByText(
      /El campeonato sigue pendiente de una revisión excepcional/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Finalizar Liga" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: /Campeón de Liga:/ }),
  ).not.toBeInTheDocument();
  expect(mocks.execute).not.toHaveBeenCalled();
});
it.each([
  ["championship_deaths_unavailable", /Faltan muertes oficiales fiables/],
  [
    "league_net_championship_tie_rule_required",
    /La regla para decidir el campeón aún no está definida/,
  ],
])(
  "explains %s without inventing an Admin resolution or ranking",
  (reason, message) => {
    Object.assign(mocks.data!, {
      state: "owner_decision_required",
      champion_trainer_id: null,
      resolution_type: null,
      blocking_reason: reason,
    });
    render(<ChampionshipReview seasonName="Liga" />);
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.queryByText(reason)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Finalizar Liga" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("combobox", { name: "Ganador del Mejor de 3" }),
    ).not.toBeInTheDocument();
    expect(mocks.execute).not.toHaveBeenCalled();
  },
);
it("requires an explicit BO3 winner and reason; never preselects technical order", () => {
  Object.assign(mocks.data!, {
    state: "bo3_required",
    champion_trainer_id: null,
    resolution_type: null,
    tied_player_ids: ["p1", "p2"],
  });
  render(<ChampionshipReview seasonName="Liga" />);
  expect(
    screen.getByRole("combobox", { name: "Ganador del Mejor de 3" }),
  ).toHaveValue("");
  expect(
    screen.getByLabelText("Resultado y motivo del desempate"),
  ).toBeRequired();
  expect(
    screen.queryByRole("button", { name: "Finalizar Liga" }),
  ).not.toBeInTheDocument();
});

it("records a residual decision only from the server candidate list and explicit reason", () => {
  Object.assign(mocks.data!, {
    state: "residual_required",
    champion_trainer_id: null,
    resolution_type: null,
    tied_player_ids: ["p1", "p2"],
  });
  render(<ChampionshipReview seasonName="Liga" />);
  const select = screen.getByLabelText("Ganador del desempate externo");
  expect(select).toHaveValue("");
  fireEvent.change(select, { target: { value: "p2" } });
  fireEvent.change(screen.getByLabelText("Resultado y motivo del desempate"), {
    target: { value: "Decisión externa acordada" },
  });
  fireEvent.submit(select.closest("form")!);
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/season/championship/residual",
    {
      expected_revision: 7,
      input_hash: "a".repeat(64),
      winner_season_player_id: "p2",
      reason: "Decisión externa acordada",
    },
  );
});
it("participants can review a residual tie but cannot record the exception", () => {
  Object.assign(mocks.data!, {
    state: "residual_required",
    champion_trainer_id: null,
    resolution_type: null,
    tied_player_ids: ["p1", "p2"],
  });
  render(<ChampionshipReview participant seasonName="Liga" />);
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  expect(screen.getByText(/Administración debe registrar/)).toBeVisible();
});

function titleTie(
  state: "tiebreak_required" | "battle_required" = "tiebreak_required",
) {
  Object.assign(mocks.data!, {
    state,
    champion_trainer_id: null,
    resolution_type: null,
    tiebreak_method: state === "battle_required" ? "total_actual_deaths" : null,
    tied_player_ids: ["p1", "p2"],
  });
  mocks.data!.players = mocks.data!.players.map((player, index) => ({
    ...player,
    total_points: "10.5",
    actual_deaths: index === 0 ? 3 : 5,
    adjusted_deaths: index === 0 ? 999 : 0,
  }));
}

const titleDialog = () =>
  screen.getByRole("dialog", { name: "Desempate del título de Liga" });

it("opens only the unresolved NET title popup with exactly two choices and historical deaths preferred", () => {
  titleTie();
  render(<ChampionshipReview seasonName="Liga" />);
  const popup = within(titleDialog());
  expect(popup.getAllByRole("radio")).toHaveLength(2);
  expect(
    popup.getByRole("radio", { name: "Muertes totales del Locke" }),
  ).toBeChecked();
  expect(
    popup.getByRole("radio", { name: "Combate de desempate 1v1" }),
  ).not.toBeChecked();
  expect(
    screen.getByRole("columnheader", { name: "Muertes totales del Locke" }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("cell", { name: "999" })).not.toBeInTheDocument();
  expect(popup.getByText("Primera fila: 3 muertos")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Finalizar Liga" }),
  ).not.toBeInTheDocument();
  expect(mocks.execute).not.toHaveBeenCalled();
});

it("requires explicit admin confirmation and submits only the historical-deaths choice and bound review", () => {
  titleTie();
  render(<ChampionshipReview seasonName="Liga" />);
  const popup = within(titleDialog());
  const reason = popup.getByLabelText("Motivo de la confirmación del título");
  fireEvent.change(reason, {
    target: { value: " Comparar el historial oficial congelado " },
  });
  fireEvent.submit(reason.closest("form")!);
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.click(
    popup.getByRole("checkbox", {
      name: "Confirmo el método y la evidencia del desempate",
    }),
  );
  fireEvent.submit(reason.closest("form")!);
  expect(mocks.execute).toHaveBeenCalledExactlyOnceWith(
    "/v1/admin/seasons/season/championship/tiebreak",
    {
      expected_revision: 7,
      input_hash: "a".repeat(64),
      method: "total_actual_deaths",
      confirmation: true,
      reason: "Comparar el historial oficial congelado",
    },
  );
});

it("equal historical deaths request an explicitly recorded 1v1 without naming a champion", () => {
  titleTie("battle_required");
  mocks.data!.players.forEach((player) => {
    player.actual_deaths = 3;
  });
  render(<ChampionshipReview seasonName="Liga" />);
  const popup = within(titleDialog());
  expect(
    popup.getByRole("radio", { name: "Muertes totales del Locke" }),
  ).toBeDisabled();
  expect(
    popup.getByRole("radio", { name: "Combate de desempate 1v1" }),
  ).toBeChecked();
  expect(
    popup.getByText(/La comparación de muertes ya está registrada/),
  ).toBeVisible();
  expect(popup.getByLabelText("Ganador del título por 1v1")).toHaveValue("");
  expect(popup.getByLabelText("Ganador del combate 1")).toHaveValue("");
  expect(popup.getByLabelText("Fecha del combate 1")).toBeRequired();
  expect(popup.getByLabelText("Evidencia del combate 1")).toBeRequired();
  expect(
    screen.queryByRole("heading", { name: /Campeón de Liga:/ }),
  ).not.toBeInTheDocument();
  expect(mocks.execute).not.toHaveBeenCalled();
});

it("records the two-person battle, winner, timestamp and evidence without score or reward edits", () => {
  titleTie();
  render(<ChampionshipReview seasonName="Liga" />);
  const popup = within(titleDialog());
  fireEvent.click(
    popup.getByRole("radio", { name: "Combate de desempate 1v1" }),
  );
  fireEvent.change(popup.getByLabelText("Ganador del título por 1v1"), {
    target: { value: "p2" },
  });
  fireEvent.change(popup.getByLabelText("Ganador del combate 1"), {
    target: { value: "p2" },
  });
  fireEvent.change(popup.getByLabelText("Fecha del combate 1"), {
    target: { value: "2026-01-01T12:00" },
  });
  fireEvent.change(popup.getByLabelText("Evidencia del combate 1"), {
    target: { value: " Vídeo del 1v1 definitivo " },
  });
  const reason = popup.getByLabelText("Motivo de la confirmación del título");
  fireEvent.change(reason, {
    target: { value: "Resultado confirmado por Administración" },
  });
  fireEvent.click(
    popup.getByRole("checkbox", {
      name: "Confirmo el método y la evidencia del desempate",
    }),
  );
  fireEvent.submit(reason.closest("form")!);
  expect(mocks.execute).toHaveBeenCalledExactlyOnceWith(
    "/v1/admin/seasons/season/championship/tiebreak",
    {
      expected_revision: 7,
      input_hash: "a".repeat(64),
      method: "championship_1v1",
      confirmation: true,
      reason: "Resultado confirmado por Administración",
      winner_season_player_id: "p2",
      battles: [
        {
          player_a_id: "p1",
          player_b_id: "p2",
          winner_id: "p2",
          played_at: new Date("2026-01-01T12:00").toISOString(),
          evidence: "Vídeo del 1v1 definitivo",
        },
      ],
    },
  );
});

it("multiway title ties record only manually entered played battles without generating a tournament", () => {
  titleTie();
  mocks.data!.players.push({
    season_player_id: "p3",
    trainer_id: "t3",
    display_name: "Tercer candidato",
    total_points: "10.5",
    actual_deaths: 4,
    adjusted_deaths: 8,
  });
  mocks.data!.tied_player_ids.push("p3");
  render(<ChampionshipReview seasonName="Liga" />);
  const popup = within(titleDialog());
  fireEvent.click(
    popup.getByRole("radio", { name: "Combate de desempate 1v1" }),
  );
  expect(popup.getAllByRole("group", { name: /Combate 1v1/ })).toHaveLength(1);
  expect(popup.getByLabelText("Participante A del combate 1")).toHaveValue("");
  expect(popup.getByLabelText("Participante B del combate 1")).toHaveValue("");
  fireEvent.change(popup.getByLabelText("Participante A del combate 1"), {
    target: { value: "p1" },
  });
  fireEvent.change(popup.getByLabelText("Participante B del combate 1"), {
    target: { value: "p2" },
  });
  fireEvent.change(popup.getByLabelText("Ganador del combate 1"), {
    target: { value: "p1" },
  });
  fireEvent.change(popup.getByLabelText("Fecha del combate 1"), {
    target: { value: "2026-01-01T12:00" },
  });
  fireEvent.change(popup.getByLabelText("Evidencia del combate 1"), {
    target: { value: "Acta del primer combate jugado" },
  });
  fireEvent.click(
    popup.getByRole("button", { name: "Añadir combate ya jugado" }),
  );
  fireEvent.change(popup.getByLabelText("Participante A del combate 2"), {
    target: { value: "p2" },
  });
  fireEvent.change(popup.getByLabelText("Participante B del combate 2"), {
    target: { value: "p3" },
  });
  fireEvent.change(popup.getByLabelText("Ganador del combate 2"), {
    target: { value: "p2" },
  });
  fireEvent.change(popup.getByLabelText("Fecha del combate 2"), {
    target: { value: "2026-01-01T11:00" },
  });
  fireEvent.change(popup.getByLabelText("Evidencia del combate 2"), {
    target: { value: "Acta del otro combate jugado" },
  });
  fireEvent.change(popup.getByLabelText("Ganador del título por 1v1"), {
    target: { value: "p1" },
  });
  const reason = popup.getByLabelText("Motivo de la confirmación del título");
  fireEvent.change(reason, {
    target: { value: "Resultado documentado entre los tres candidatos" },
  });
  fireEvent.click(
    popup.getByRole("checkbox", {
      name: "Confirmo el método y la evidencia del desempate",
    }),
  );
  fireEvent.submit(reason.closest("form")!);
  const body = mocks.execute.mock.calls[0][1];
  expect(body.winner_season_player_id).toBe("p1");
  expect(
    body.battles.map(
      (battle: {
        player_a_id: string;
        player_b_id: string;
        winner_id: string;
      }) => [battle.player_a_id, battle.player_b_id, battle.winner_id],
    ),
  ).toEqual([
    ["p1", "p2", "p1"],
    ["p2", "p3", "p2"],
  ]);
  expect(body).not.toHaveProperty("ranking");
  expect(body).not.toHaveProperty("points_awarded");
});

it.each(["tiebreak_required", "battle_required"] as const)(
  "ordinary trainers can only read %s and never edit its title decision",
  (state) => {
    titleTie(state);
    render(<ChampionshipReview participant seasonName="Liga" />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Resolver desempate del título" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Administración debe registrar/)).toBeVisible();
    expect(mocks.execute).not.toHaveBeenCalled();
  },
);

it.each(["total_actual_deaths", "championship_1v1"] as const)(
  "displays the server champion and confirmed %s method, without another popup",
  (method) => {
    mocks.data!.resolution_type = method;
    mocks.data!.tiebreak_method = method;
    mocks.data!.players.forEach((player) => {
      player.actual_deaths = 3;
    });
    render(<ChampionshipReview seasonName="Liga" />);
    expect(
      screen.getByRole("heading", {
        name: "Campeón de Liga: Ganadora oficial",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        method === "total_actual_deaths"
          ? /Desempate del título confirmado por Muertes totales del Locke/
          : /Desempate del título confirmado por Combate de desempate 1v1/,
      ),
    ).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mocks.execute).not.toHaveBeenCalled();
  },
);

it("uncertain confirmation keeps the popup and exact retry, disabling new decisions", () => {
  titleTie();
  mocks.uncertain = true;
  render(<ChampionshipReview seasonName="Liga" />);
  const popup = within(titleDialog());
  expect(
    popup.getByRole("radio", { name: "Muertes totales del Locke" }),
  ).toBeDisabled();
  expect(
    popup.getByRole("button", { name: "Confirmar desempate del título" }),
  ).toBeDisabled();
  fireEvent.click(popup.getByRole("button", { name: "Cerrar" }));
  expect(titleDialog()).toBeInTheDocument();
  fireEvent.click(
    popup.getByRole("button", { name: "Reintentar la misma solicitud" }),
  );
  expect(mocks.retry).toHaveBeenCalledOnce();
  expect(mocks.execute).not.toHaveBeenCalled();
  expect(mocks.hold).toHaveBeenCalled();
});

it("a stale title review resets the decision and requires fresh explicit confirmation", () => {
  titleTie();
  const view = render(<ChampionshipReview seasonName="Liga" />);
  fireEvent.click(
    screen.getByRole("radio", { name: "Combate de desempate 1v1" }),
  );
  fireEvent.change(
    screen.getByLabelText("Motivo de la confirmación del título"),
    { target: { value: "Prueba anterior" } },
  );
  mocks.error = new ApiError(409, "CHAMPIONSHIP_REVIEW_STALE");
  mocks.data = {
    ...mocks.data!,
    input_hash: "b".repeat(64),
    setup_revision: 8,
  };
  view.rerender(<ChampionshipReview seasonName="Liga" />);
  expect(
    screen.getByRole("radio", { name: "Muertes totales del Locke" }),
  ).toBeChecked();
  expect(
    screen.getByLabelText("Motivo de la confirmación del título"),
  ).toHaveValue("");
  expect(
    screen.getByRole("checkbox", {
      name: "Confirmo el método y la evidencia del desempate",
    }),
  ).not.toBeChecked();
  expect(
    screen.getByText(/Los datos del campeonato han cambiado/),
  ).toBeVisible();
  expect(mocks.execute).not.toHaveBeenCalled();
});

const closedLeague = () =>
  ({
    season: {
      id: "season",
      name: "Liga",
      status: "active",
      current_matchday_id: "day",
    },
    days: [{ id: "day", number: 4, status: "closed" }],
    rows: [
      {
        season_player_id: "p1",
        trainer_id: "t1",
        status: "active",
        display_name: "Primera fila",
      },
    ],
  }) as Model<"LeagueGeneralRead">;

it("the League view shows the final tie popup to an administrator even outside the participant roster", () => {
  titleTie();
  render(<LeagueOperations data={closedLeague()} />);
  expect(titleDialog()).toBeVisible();
  expect(
    screen.getByRole("radio", { name: "Muertes totales del Locke" }),
  ).toBeChecked();
});

it("the League view leaves an ordinary participant's final championship read-only", () => {
  titleTie();
  mocks.isAdmin = false;
  const data = closedLeague();
  data.rows[0].trainer_id = "t2";
  render(<LeagueOperations data={data} />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  expect(screen.getByText(/Administración debe registrar/)).toBeVisible();
});

it("a completed intermediate matchday never triggers the final-title popup", () => {
  titleTie();
  mocks.data!.state = "incomplete";
  render(<LeagueOperations data={closedLeague()} />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  expect(
    screen.getByText(/Completa y cierra todas las jornadas/),
  ).toBeVisible();
});

it("keeps the original uncertain retry accessible when a background read already observes the resolved title", () => {
  titleTie();
  mocks.uncertain = true;
  const view = render(<ChampionshipReview seasonName="Liga" />);
  expect(titleDialog()).toBeVisible();
  mocks.data = {
    ...mocks.data!,
    state: "ready",
    champion_trainer_id: "t2",
    resolution_type: "championship_1v1",
    tiebreak_method: "championship_1v1",
  };
  view.rerender(<ChampionshipReview seasonName="Liga" />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Finalizar Liga" })).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
  );
  expect(mocks.retry).toHaveBeenCalledOnce();
  expect(mocks.execute).not.toHaveBeenCalled();
});
