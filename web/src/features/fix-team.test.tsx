import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Model } from "../api/types";
import { FixTeamButton } from "./fix-team";

type Readiness = Model<"LeagueReadinessRead">;
const slot = (n: number, species = "Pokémon #25") => ({
  location: `Equipo · ${n}`,
  pokemon_entity_id: null,
  pokemon: {
    species,
    nickname: `Slot ${n}`,
    level: 20 + n,
    types: [],
    moves: [],
    item: "",
    is_shiny: false,
    status_flags: [],
    ability: "",
    nature: "",
  },
});
const mocks = vi.hoisted(() => ({
  readiness: null as Readiness | null,
  pc: null as Model<"PCRead"> | null,
  overview: null as Record<string, unknown> | null,
  execute: vi.fn(),
  prepare: vi.fn(),
  notify: vi.fn(),
  success: false,
}));
vi.mock("../state", () => ({
  queries: { invalidateQueries: vi.fn() },
  useApp: () => ({ season: "season", me: { trainer_id: "t1" } }),
  useOverview: () => ({ data: mocks.overview }),
  usePC: () => ({ data: mocks.pc, isPending: false, error: null }),
  useRead: (path: string) => ({
    data: path.endsWith("/league/readiness") ? mocks.readiness : undefined,
    isPending: false,
    error: null,
    refetch: vi.fn(),
  }),
}));
vi.mock("./league-start", async (original) => ({
  ...(await original<typeof import("./league-start")>()),
  prepareFirstMatchday: mocks.prepare,
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  notify: mocks.notify,
  useCommand: () => ({
    pending: false,
    uncertain: false,
    error: null,
    success: mocks.success,
    execute: mocks.execute,
    retry: vi.fn(),
  }),
}));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});
const readiness = (changes: Partial<Readiness> = {}): Readiness => ({
  season_id: "season",
  state: "unprepared",
  structure: "all_vs_all",
  matchday: null,
  next_number: 1,
  can_prepare: true,
  can_open: false,
  can_operate: true,
  reasons: [],
  participants: [],
  ...changes,
});
const pc = (party: ReturnType<typeof slot>[]): Model<"PCRead"> => ({
  save: {
    id: "league-save",
    parser_status: "parsed",
    parser_version: "v3",
    uploaded_at: "2026-11-04T10:00:00Z",
    game: "Y",
  },
  status: "ready",
  pokemon: [...party, { ...slot(1), location: "Caja 1 · 1" }],
  dead_box: 7,
});
beforeEach(() => {
  vi.clearAllMocks();
  mocks.success = false;
  mocks.readiness = readiness();
  // Out of order on purpose: the dialog lists them in slot order.
  mocks.pc = pc([6, 2, 3, 1, 5, 4].map((n) => slot(n)));
  mocks.overview = {
    season: { current_matchday_id: null },
    days: [],
    locks: [],
  };
  mocks.execute.mockResolvedValue(true);
  mocks.prepare.mockResolvedValue({
    season_id: "season",
    matchday_id: "j1",
    number: 1,
    status: "scheduled",
    revision: 0,
    created: true,
  });
});
afterEach(cleanup);
const tree = () => (
  <MemoryRouter>
    <FixTeamButton />
  </MemoryRouter>
);
let view: ReturnType<typeof render>;
const open = () => {
  view = render(tree());
  fireEvent.click(screen.getByRole("button", { name: "Fijar Equipo" }));
  return screen.getByRole("dialog", { name: "Fijar Equipo" });
};

it("confirms the six of the official save, prepares J1 when needed and fixes them for it", async () => {
  const dialog = open();
  expect(dialog).toHaveTextContent(
    /equipo oficial de la Jornada 1 \(la J1 se prepara ahora: todos contra todos\)/,
  );
  const listed = within(
    within(dialog).getByRole("list", { name: "Equipo que se fijará" }),
  ).getAllByRole("listitem");
  expect(listed.map((li) => li.textContent)).toEqual(
    [1, 2, 3, 4, 5, 6].map((n) => `Slot ${n}Nv. ${20 + n}`),
  );
  expect(dialog).toHaveTextContent(
    /Discord con su enlace público de Pokepast.es \(sin habilidad, naturaleza, IVs ni EVs\)/,
  );
  // Nothing happens until the explicit confirmation.
  expect(mocks.prepare).not.toHaveBeenCalled();
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Confirmar y fijar equipo" }),
  );
  await vi.waitFor(() => expect(mocks.execute).toHaveBeenCalledOnce());
  expect(mocks.prepare).toHaveBeenCalledExactlyOnceWith("season");
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/seasons/season/matchdays/j1/team-lock",
    { save_file_id: "league-save" },
    "PUT",
  );
  // The confirmed answer (also a «Reintentar» one) closes and announces it.
  mocks.success = true;
  view.rerender(tree());
  expect(mocks.notify).toHaveBeenCalledWith(
    expect.stringContaining("Equipo fijado para la J1"),
    "ok",
    { key: "command-ok" },
  );
  expect(
    screen.queryByRole("dialog", { name: "Fijar Equipo" }),
  ).not.toBeInTheDocument();
});

it("a prepared matchday is used as is; an open one warns that the lock is late", async () => {
  mocks.readiness = readiness({
    state: "open",
    can_prepare: false,
    matchday: { id: "day2", number: 2, status: "open", revision: 5 },
    next_number: 2,
  });
  const dialog = open();
  expect(dialog).toHaveTextContent(/Jornada 2/);
  expect(dialog).toHaveTextContent(/fuera de plazo/);
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Confirmar y fijar equipo" }),
  );
  await vi.waitFor(() => expect(mocks.execute).toHaveBeenCalledOnce());
  expect(mocks.prepare).not.toHaveBeenCalled();
  expect(mocks.execute.mock.calls[0][0]).toBe(
    "/v1/seasons/season/matchdays/day2/team-lock",
  );
});

it.each([
  [
    "fewer than six",
    () => (mocks.pc = pc([1, 2, 3, 4].map((n) => slot(n)))),
    /seis Pokémon .* ahora tiene 4/,
  ],
  [
    "no official League save",
    () =>
      (mocks.pc = {
        save: null,
        status: "no_current_save",
        pokemon: [],
        dead_box: 7,
      }),
    /no está registrada como partida oficial/,
  ],
  [
    "a finished League",
    () =>
      (mocks.readiness = readiness({
        state: "finished",
        can_prepare: false,
        next_number: null,
      })),
    /No hay ninguna jornada pendiente/,
  ],
  [
    "a viewer who cannot operate",
    () => (mocks.readiness = readiness({ can_operate: false })),
    /Solo los participantes activos/,
  ],
])(
  "with %s the button stays and the dialog explains why, without a confirmation",
  (_, arrange, text) => {
    arrange();
    const dialog = open();
    expect(within(dialog).getByRole("alert")).toHaveTextContent(text);
    expect(
      within(dialog).queryByRole("button", {
        name: "Confirmar y fijar equipo",
      }),
    ).not.toBeInTheDocument();
    expect(mocks.execute).not.toHaveBeenCalled();
    expect(mocks.prepare).not.toHaveBeenCalled();
  },
);

it("an existing lock is shown and replacing it says the announcement is updated", () => {
  mocks.overview = {
    season: { current_matchday_id: "day" },
    days: [{ id: "day", number: 1, status: "scheduled" }],
    locks: [
      {
        trainer_id: "t1",
        matchday_id: "day",
        locked_at: "2026-11-04T11:00:00Z",
      },
    ],
  };
  mocks.readiness = readiness({
    state: "scheduled",
    can_prepare: false,
    matchday: { id: "day", number: 1, status: "scheduled", revision: 0 },
  });
  const dialog = open();
  expect(screen.getByText(/^Team Lock oficial · J1 · /)).toBeVisible();
  expect(dialog).toHaveTextContent(
    /se sustituirá por este y su anuncio de Discord se actualizará/,
  );
});
