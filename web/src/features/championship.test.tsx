import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Model } from "../api/types";
import { ChampionshipReview } from "./championship";

const mocks = vi.hoisted(() => ({
  data: null as Model<"ChampionshipRead"> | null,
  refetch: vi.fn(),
  execute: vi.fn(),
}));
vi.mock("../state", () => ({
  useApp: () => ({ season: "season" }),
  useRead: () => ({
    data: mocks.data,
    isPending: false,
    isFetching: false,
    error: null,
    refetch: mocks.refetch,
  }),
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
afterEach(cleanup);
beforeEach(() => {
  mocks.execute.mockReset();
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
  expect(screen.getByText("-0.000000000000000001")).toBeInTheDocument();
  expect(screen.getByText("0.000000000000000001")).toBeInTheDocument();
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
    "championship_triple_unresolved",
    /todavía no permite registrar esta resolución/,
  ],
  ["championship_many_tied", /todavía no aplica esa regla a este caso/],
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
