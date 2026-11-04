import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { BattlePage } from "./team-preview";
import { TeamLockWarning } from "./team-lock-warning";

const mocks = vi.hoisted(() => ({
  season: "season",
  missing: false,
  unsynced: false,
  day: true,
  error: null as Error | null,
  reads: vi.fn(),
  pc: vi.fn(),
  execute: vi.fn(),
  invalidations: vi.fn(),
}));
vi.mock("../state", () => ({
  useApp: () => ({ season: mocks.season, me: { trainer_id: "owner" } }),
  queries: { invalidateQueries: mocks.invalidations },
  // Sprite generation per trainer: no season progress in these fixtures.
  useOverview: () => ({ data: { players: [] } }),
  usePC: () => {
    mocks.pc();
    return { data: { save: null, status: "no_current_save" } };
  },
  useRead: (path: string) => {
    mocks.reads(path);
    const params = new URL(path, "https://example.invalid").searchParams;
    const mode = params.get("mode") || "spectator";
    const first = params.get("trainer_id") || "owner";
    const second =
      params.get("second_trainer_id") ||
      (first === "owner" ? "rival" : "owner");
    const mon = {
      species: "Pikachu",
      nickname: "Fijado",
      moves: [{ name: "Impactrueno" }],
      item: "Baya",
    };
    return {
      isPending: false,
      error: mocks.error,
      data: {
        season: { id: mocks.season, status: "active" },
        mode,
        day: mocks.day ? { id: "day", number: 1, status: "open" } : null,
        trainers: [
          { trainer_id: "owner", display_name: "Antonio", status: "active" },
          { trainer_id: "rival", display_name: "Lucía", status: "active" },
          { trainer_id: "third", display_name: "Marcos", status: "active" },
        ],
        // 079: every selected trainer has an entry, with or without a day.
        teams: (mode === "spectator" ? [first, second] : [first]).map((id) => ({
          trainer_id: id,
          visibility: mode === "battle" && id === "owner" ? "self" : "public",
          provisional:
            (mocks.missing || !mocks.day) && !mocks.unsynced
              ? {
                  source: "league",
                  team: [{ ...mon, nickname: "Actual" }],
                }
              : null,
          unavailable_reason: mocks.unsynced ? "no_synced_save" : null,
          lock:
            mocks.missing || !mocks.day
              ? null
              : {
                  locked_at: "2026-10-07T10:00:00Z",
                  is_late: false,
                  team: Array.from({ length: 6 }, () =>
                    mode === "battle" && id === "owner"
                      ? {
                          ...mon,
                          ability: "Estática privada",
                          nature: "Miedosa privada",
                          ivs: null,
                          evs: null,
                        }
                      : mon,
                  ),
                },
        })),
      },
    };
  },
}));
vi.mock("./core", () => ({
  WithSeason: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Pokemon: ({ pokemon }: { pokemon: { nickname: string } }) => (
    <span>{pokemon.nickname}</span>
  ),
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  useCommand: () => ({
    pending: false,
    uncertain: false,
    error: null,
    success: false,
    execute: mocks.execute,
  }),
}));
const show = () =>
  render(
    <MemoryRouter>
      <BattlePage />
    </MemoryRouter>,
  );
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  mocks.season = "season";
  mocks.missing = false;
  mocks.unsynced = false;
  mocks.day = true;
  mocks.error = null;
});

it("spectator has two independent public selectors without a scheduled match", () => {
  show();
  expect(screen.getAllByRole("combobox")).toHaveLength(2);
  fireEvent.change(screen.getByLabelText("Primer entrenador"), {
    target: { value: "rival" },
  });
  fireEvent.change(screen.getByLabelText("Segundo entrenador"), {
    target: { value: "third" },
  });
  expect(mocks.reads).toHaveBeenLastCalledWith(
    "/v1/read/seasons/season/team-preview?mode=spectator&trainer_id=rival&second_trainer_id=third",
  );
  expect(screen.getAllByText("Team Lock oficial")).toHaveLength(2);
  expect(screen.queryByText("Estática privada")).not.toBeInTheDocument();
  expect(mocks.pc).not.toHaveBeenCalled();
});
it("battle has one selector; self details disappear on rival or spectator switch", () => {
  show();
  fireEvent.click(screen.getByRole("tab", { name: "Batalla" }));
  expect(screen.getAllByRole("combobox")).toHaveLength(1);
  expect(screen.getAllByText("Estática privada")).toHaveLength(6);
  fireEvent.change(screen.getByLabelText("Entrenador"), {
    target: { value: "rival" },
  });
  expect(screen.queryByText("Estática privada")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Entrenador"), {
    target: { value: "owner" },
  });
  fireEvent.click(screen.getByRole("tab", { name: "Espectador" }));
  expect(screen.queryByText("Estática privada")).not.toBeInTheDocument();
  expect(screen.getAllByText("Team Lock oficial")).toHaveLength(2);
});
it("without a Team Lock the current party is shown, clearly provisional", () => {
  mocks.missing = true;
  show();
  expect(
    screen.getAllByText("Provisional · equipo actual sin fijar"),
  ).toHaveLength(2);
  expect(screen.getAllByText(/No es un Team Lock/)).toHaveLength(2);
  expect(screen.getAllByText("Actual")).toHaveLength(2);
  // Never presented as an official lock.
  expect(screen.queryByText("Team Lock oficial")).not.toBeInTheDocument();
  expect(screen.queryByText("Fijado")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Fijar Equipo" })).toBeEnabled();
  expect(mocks.pc).not.toHaveBeenCalled();
});
it("with no prepared matchday Team Preview stays available and can fix a team", () => {
  mocks.day = false;
  show();
  expect(
    screen.getByText("Sin jornada preparada · equipos actuales"),
  ).toBeVisible();
  expect(
    screen.getAllByText("Provisional · equipo actual sin fijar"),
  ).toHaveLength(2);
  expect(screen.getByRole("button", { name: "Fijar Equipo" })).toBeEnabled();
  expect(mocks.pc).not.toHaveBeenCalled();
});
it("a trainer who never synchronized gets a useful empty state, never an invented team", () => {
  mocks.missing = true;
  mocks.unsynced = true;
  show();
  expect(
    screen.getAllByText("Aún no ha sincronizado ninguna partida."),
  ).toHaveLength(2);
  expect(screen.queryByText("Actual")).not.toBeInTheDocument();
});
it("season change resets private mode and selections", () => {
  const view = show();
  fireEvent.click(screen.getByRole("tab", { name: "Batalla" }));
  mocks.season = "other";
  view.rerender(
    <MemoryRouter>
      <BattlePage />
    </MemoryRouter>,
  );
  expect(screen.getByRole("tab", { name: "Espectador" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.queryByText("Estática privada")).not.toBeInTheDocument();
  expect(mocks.reads).toHaveBeenLastCalledWith(
    "/v1/read/seasons/other/team-preview?mode=spectator",
  );
});
it("read failure shows an error instead of an invented empty lock", () => {
  mocks.error = new Error("unavailable");
  show();
  expect(screen.getByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText(/Falta el Team Lock/)).not.toBeInTheDocument();
  expect(mocks.pc).not.toHaveBeenCalled();
});
it("league warning offers preview but leaves result controls available", () => {
  render(
    <MemoryRouter>
      <TeamLockWarning own />
      <button>Registrar resultado</button>
    </MemoryRouter>,
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Tu Team Lock está pendiente",
  );
  expect(screen.getByRole("link")).toHaveAttribute("href", "/battle");
  expect(
    screen.getByRole("button", { name: "Registrar resultado" }),
  ).toBeEnabled();
});
