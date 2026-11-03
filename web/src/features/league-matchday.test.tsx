import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { CloseMatchday, OpenMatchday } from "./league-matchday";
import { LeaguePage } from "./core";

type DayState = Model<"DayState">;
const mocks = vi.hoisted(() => ({
  me: { trainer_id: "t1", is_admin: false } as {
    trainer_id: string;
    is_admin: boolean;
  } | null,
  dayState: null as DayState | null,
  league: null as Model<"LeagueGeneralRead"> | null,
  overview: null as Record<string, unknown> | null,
  execute: vi.fn(),
  pending: false,
  uncertain: false,
  error: null as unknown,
  reads: [] as string[],
}));
vi.mock("../state", () => ({
  queries: { invalidateQueries: vi.fn() },
  useViewer: () => mocks.me?.trainer_id,
  useApp: () => ({
    me: mocks.me,
    season: "season",
    holdAdminNavigation: () => () => {},
  }),
  useOverview: () => ({
    data: mocks.overview,
    isPending: false,
    error: null,
  }),
  useRead: (path: string, enabled = true) => {
    if (enabled) mocks.reads.push(path);
    return {
      data: !enabled
        ? undefined
        : path.includes("/matchdays/")
          ? mocks.dayState
          : path.endsWith("/league")
            ? mocks.league
            : undefined,
      isPending: false,
      isFetching: false,
      error: null,
    };
  },
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  useCommand: () => ({
    pending: mocks.pending,
    uncertain: mocks.uncertain,
    error: mocks.error,
    success: false,
    execute: mocks.execute,
    retry: vi.fn(),
  }),
}));
vi.mock("./championship", () => ({ ChampionshipReview: () => null }));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});

const season = (status: "scheduled" | "open" | "closed" = "scheduled") => ({
  season: {
    id: "season",
    name: "ChampionsLocke",
    status: "active",
    current_matchday_id: "day",
  },
  days: [{ id: "day", number: 1, status }],
});
function league(
  status: "scheduled" | "open" | "closed" = "scheduled",
  playerStatus = "active",
): Model<"LeagueGeneralRead"> {
  return {
    ...season(status),
    rows: [
      {
        season_player_id: "p1",
        trainer_id: "t1",
        display_name: "Anto",
        status: playerStatus,
        total_points: "0",
        coin_balance: "8",
      },
      {
        season_player_id: "p2",
        trainer_id: "t2",
        display_name: "Aaron",
        status: "active",
        total_points: "-0.3",
        coin_balance: "4",
      },
    ],
  } as Model<"LeagueGeneralRead">;
}
const state = (changes: Partial<DayState> = {}): DayState => ({
  season_id: "season",
  matchday_id: "day",
  current_matchday_id: "day",
  state: "scheduled",
  revision: 3,
  results_revision: 7,
  snapshot_revision: 0,
  matches: [],
  ...changes,
});
const played = [
  { id: "m1", player_a_id: "p1", player_b_id: "p2", winner_id: "p2" },
  { id: "m2", player_a_id: "p2", player_b_id: "p3", winner_id: "p2" },
];
beforeEach(() => {
  vi.clearAllMocks();
  mocks.me = { trainer_id: "t1", is_admin: false };
  mocks.pending = false;
  mocks.uncertain = false;
  mocks.error = null;
  mocks.reads = [];
  mocks.execute.mockResolvedValue(true);
  mocks.dayState = state();
});
afterEach(cleanup);

const names: Record<string, string> = { p1: "Anto", p2: "Aaron", p3: "Iker" };
const name = (id: string) => names[id] ?? "Entrenador";

it("any active participant opens the scheduled matchday with its revision", async () => {
  const show = vi.fn();
  render(<OpenMatchday data={league()} onShowDay={show} />);
  fireEvent.click(screen.getByRole("button", { name: "Abrir jornada 1" }));
  const dialog = screen.getByRole("dialog", { name: "Abrir jornada 1" });
  expect(dialog).toHaveTextContent(/Se fijarán las muertes de la progresión/);
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Confirmar apertura" }),
  );
  await vi.waitFor(() => expect(show).toHaveBeenCalledWith("day"));
  // The participant route, never the administrator one.
  expect(mocks.execute).toHaveBeenCalledExactlyOnceWith(
    "/v1/seasons/season/matchdays/day/open",
    { expected_revision: 3 },
  );
});

it("an open matchday shows its state instead of a second opening", () => {
  mocks.dayState = state({ state: "open" });
  const show = vi.fn();
  render(<OpenMatchday data={league("open")} onShowDay={show} />);
  expect(
    screen.queryByRole("button", { name: /Abrir jornada/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("Jornada 1 en curso.")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Ir a J1" }));
  expect(show).toHaveBeenCalledWith("day");
  expect(mocks.execute).not.toHaveBeenCalled();
});

it("the button waits for the authoritative state before acting", () => {
  mocks.dayState = state({ state: "open" });
  render(<OpenMatchday data={league("scheduled")} onShowDay={vi.fn()} />);
  expect(
    screen.getByRole("button", { name: "Abrir jornada 1" }),
  ).toBeDisabled();
});

it("a stale revision blocks the confirmation", () => {
  const view = render(<OpenMatchday data={league()} onShowDay={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Abrir jornada 1" }));
  mocks.dayState = state({ revision: 4 });
  view.rerender(<OpenMatchday data={league()} onShowDay={vi.fn()} />);
  expect(screen.getByRole("alert")).toHaveTextContent("La jornada cambió");
  expect(
    screen.getByRole("button", { name: "Confirmar apertura" }),
  ).toBeDisabled();
  expect(mocks.execute).not.toHaveBeenCalled();
});

it.each([
  ["a trainer outside this League", { trainer_id: "other", is_admin: false }],
  ["an anonymous visitor", null],
])("%s gets no opening control or state read", (_, me) => {
  mocks.me = me;
  render(<OpenMatchday data={league()} onShowDay={vi.fn()} />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(mocks.reads).toEqual([]);
});

it("an inactive participant gets no opening control", () => {
  render(
    <OpenMatchday data={league("scheduled", "retired")} onShowDay={vi.fn()} />,
  );
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("closing waits for every scheduled battle to have a result", () => {
  mocks.dayState = state({
    state: "open",
    matches: [played[0], { ...played[1], winner_id: null }],
  });
  render(
    <CloseMatchday
      seasonId="season"
      dayId="day"
      number={1}
      single
      name={name}
    />,
  );
  expect(screen.getByText("Faltan 1 combate por registrar.")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Cerrar jornada 1" }),
  ).toBeDisabled();
});

it("closing confirms what will be frozen and sends the reviewed revision", async () => {
  mocks.dayState = state({ state: "open", matches: played });
  render(
    <CloseMatchday
      seasonId="season"
      dayId="day"
      number={1}
      single
      name={name}
    />,
  );
  expect(screen.getByText(/lista para cerrarse/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Cerrar jornada 1" }));
  const dialog = screen.getByRole("dialog", { name: "Cerrar jornada 1" });
  expect(dialog).toHaveTextContent(/congelará su clasificación oficial/);
  expect(dialog).toHaveTextContent("Anto vs Aaron · gana Aaron");
  expect(dialog).toHaveTextContent("Aaron vs Iker · gana Aaron");
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Confirmar cierre" }),
  );
  await vi.waitFor(() => expect(mocks.execute).toHaveBeenCalledOnce());
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/seasons/season/matchdays/day/close",
    { expected_results_revision: 7 },
  );
});

it("changed results after review block a blind close", () => {
  mocks.dayState = state({ state: "open", matches: played });
  const view = render(
    <CloseMatchday
      seasonId="season"
      dayId="day"
      number={1}
      single
      name={name}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Cerrar jornada 1" }));
  mocks.dayState = state({
    state: "open",
    matches: played,
    results_revision: 8,
  });
  view.rerender(
    <CloseMatchday
      seasonId="season"
      dayId="day"
      number={1}
      single
      name={name}
    />,
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Los resultados han cambiado",
  );
  expect(
    screen.getByRole("button", { name: "Confirmar cierre" }),
  ).toBeDisabled();
});

it("an unresolved tie asks for the 1v1 evidence inside the same confirmation", () => {
  mocks.dayState = state({ state: "open", matches: played });
  const view = render(
    <CloseMatchday
      seasonId="season"
      dayId="day"
      number={1}
      single
      name={name}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Cerrar jornada 1" }));
  mocks.error = Object.assign(new ApiError(409, "RANKING_TIE_UNRESOLVED"), {
    ranking: {
      ranking_rule: "wins_segment_deaths_v2",
      input_hash: "a".repeat(64),
      groups: [],
    },
  });
  view.rerender(
    <CloseMatchday
      seasonId="season"
      dayId="day"
      number={1}
      single
      name={name}
    />,
  );
  expect(
    screen.getByRole("region", { name: "Resolución de empates" }),
  ).toBeVisible();
});

it.each(["scheduled", "closed"] as const)(
  "a %s matchday has no closing control",
  (value) => {
    mocks.dayState = state({ state: value, matches: played });
    render(
      <CloseMatchday
        seasonId="season"
        dayId="day"
        number={1}
        single
        name={name}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  },
);

function overview(status: "scheduled" | "open" | "closed") {
  return {
    ...season(status),
    players: [
      { id: "p1", trainer_id: "t1", display_name: "Anto", status: "active" },
      { id: "p2", trainer_id: "t2", display_name: "Aaron", status: "active" },
    ],
    divisions: [{ id: "a", code: "A" }],
    memberships: [],
    matches: [],
    locks: [{ trainer_id: "t1", matchday_id: "day" }],
    snapshots: [],
    matchday_scores: [],
  };
}

it("Liga › General: the open action sits right below the standings, with no empty «Jornada» card or wipe control", () => {
  mocks.league = league();
  mocks.overview = overview("scheduled");
  render(
    <MemoryRouter>
      <LeaguePage />
    </MemoryRouter>,
  );
  const table = screen
    .getByRole("heading", { name: "Clasificación general" })
    .closest(".league-table-card")!;
  const open = screen.getByRole("button", { name: "Abrir jornada 1" });
  expect(table.nextElementSibling).toContainElement(open);
  expect(
    screen.queryByRole("heading", { name: /^Jornada/ }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Revividos tras wipe")).not.toBeInTheDocument();
});

it("Liga › J1: results are recorded on the page and closing is its last control", () => {
  mocks.league = league("open");
  mocks.overview = overview("open");
  mocks.dayState = state({ state: "open", matches: played });
  const { container } = render(
    <MemoryRouter>
      <LeaguePage />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "J1" }));
  expect(screen.getByText("2/2 resultados registrados")).toBeVisible();
  const close = screen.getByRole("button", { name: "Cerrar jornada 1" });
  const section = close.closest(".matchday-close")!;
  expect(section.nextElementSibling).toBeNull();
  expect(section.parentElement).toBe(
    container.firstElementChild?.parentElement,
  );
});

it("Liga › J1 not yet open points to General instead of offering actions", () => {
  mocks.league = league("scheduled");
  mocks.overview = overview("scheduled");
  render(
    <MemoryRouter>
      <LeaguePage />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "J1" }));
  expect(screen.getByText(/Se abre desde General/)).toBeVisible();
  expect(
    screen.queryByRole("button", { name: /Cerrar jornada/ }),
  ).not.toBeInTheDocument();
});
