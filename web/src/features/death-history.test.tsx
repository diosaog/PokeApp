import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { Model } from "../api/types";
import { DeathHistory } from "./death-history";

const mocks = vi.hoisted(() => ({
  data: {} as Model<"DeathHistoryRead">,
  execute: vi.fn(),
  hold: vi.fn(() => () => {}),
  uncertain: false,
}));
vi.mock("../state", () => ({
  useApp: () => ({ holdAdminNavigation: mocks.hold }),
  useRead: () => ({
    data: mocks.data,
    isPending: false,
    isFetching: false,
    error: null,
  }),
}));
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
  }),
}));
const setup = {
  season: { id: "season", status: "active" },
  participants: [{ id: "player", display_name: "Anto" }],
} as Model<"SeasonSetup">;
beforeEach(() => {
  vi.clearAllMocks();
  mocks.uncertain = false;
  mocks.execute.mockResolvedValue(true);
  mocks.data = {
    season_id: "season",
    season_player_id: "player",
    trainer_id: "trainer",
    revision: 4,
    replayed: false,
    known: false,
    blocking_reason: null,
    actual_deaths: null,
    wipe_deaths: null,
    death_penalty_tenths: null,
    source_save_id: "save",
    source_sha256: "a".repeat(64),
    identity_revision_id: "identity",
    wipe_revision: 2,
    wipe_counter: 5,
    current_matchday_id: "day",
    segment_deaths: null,
    can_reconcile: true,
    recorded_deaths: 3,
    observed_dead_entities: [
      {
        pokemon_entity_id: "entity",
        currently_dead: false,
        has_recorded_death: true,
        display_name: "Pikachu",
      },
    ],
  };
});
afterEach(cleanup);
const open = () =>
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar historial · Anto" }),
  );
function fill() {
  for (const [label, value] of [
    ["Muertos", "7"],
    ["Muertes revividas tras wipe", "5"],
    ["Muertes de la progresión actual", "6"],
    ["Motivo de la confirmación", "Revisión del tramo J2"],
    [
      "Evidencia del historial y del tramo de progresión",
      "Capturas verificadas del historial",
    ],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByLabelText(/He revisado la partida/));
}
it("never turns unknown counts or empty inputs into zero", () => {
  render(<DeathHistory setup={setup} />);
  open();
  expect(screen.getByText("Desconocido")).toBeInTheDocument();
  for (const label of [
    "Muertos",
    "Muertes revividas tras wipe",
    "Muertes de la progresión actual",
  ])
    expect(screen.getByLabelText(label)).toHaveValue(null);
  fireEvent.click(screen.getByLabelText(/He revisado la partida/));
  fireEvent.submit(screen.getByLabelText("Muertos").closest("form")!);
  expect(mocks.execute).not.toHaveBeenCalled();
});
it("submits explicit counts and revival evidence bound to the reviewed source and revision", () => {
  render(<DeathHistory setup={setup} />);
  open();
  fill();
  fireEvent.click(screen.getByLabelText(/Confirmo que Pikachu fue revivido/));
  fireEvent.submit(screen.getByLabelText("Muertos").closest("form")!);
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/season/participants/player/death-history",
    {
      actual_deaths: 7,
      wipe_deaths: 5,
      segment_deaths: 6,
      source_sha256: "a".repeat(64),
      expected_revision: 4,
      reason: "Revisión del tramo J2",
      evidence: "Capturas verificadas del historial",
      revived_entity_ids: ["entity"],
    },
    "PUT",
  );
});
it("blocks changed evidence until it is explicitly reviewed", () => {
  const view = render(<DeathHistory setup={setup} />);
  open();
  fill();
  mocks.data = { ...mocks.data, revision: 5, source_sha256: "b".repeat(64) };
  view.rerender(<DeathHistory setup={setup} />);
  expect(
    screen.getByRole("button", { name: "Confirmar historial auditado" }),
  ).toBeDisabled();
  fireEvent.submit(screen.getByLabelText("Muertos").closest("form")!);
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar evidencia actual" }),
  );
  expect(screen.getByLabelText("Muertos")).toHaveValue(7);
  fireEvent.submit(screen.getByLabelText("Muertos").closest("form")!);
  expect(mocks.execute.mock.lastCall![1]).toEqual(
    expect.objectContaining({
      expected_revision: 5,
      source_sha256: "b".repeat(64),
    }),
  );
});
it("does not allow reconciliation with incomplete source evidence", () => {
  mocks.data = { ...mocks.data, can_reconcile: false, source_sha256: null };
  render(<DeathHistory setup={setup} />);
  open();
  expect(
    screen.getByRole("button", { name: "Confirmar historial auditado" }),
  ).toBeDisabled();
  expect(screen.getByLabelText("Muertos")).toBeDisabled();
});

it("does not substitute zero for an unavailable wipe counter or revision", () => {
  mocks.data = {
    ...mocks.data,
    wipe_counter: null,
    wipe_revision: null,
    blocking_reason: "death_history_wipe_state_unavailable",
  };
  render(<DeathHistory setup={setup} />);
  open();
  expect(
    screen.getByRole("button", { name: "Confirmar historial auditado" }),
  ).toBeDisabled();
  expect(screen.getByLabelText("Muertes revividas tras wipe")).toHaveValue(
    null,
  );
  expect(screen.getByText(/El contador de wipe actual es/)).toHaveTextContent(
    "Desconocido",
  );
  expect(screen.getByRole("alert")).toHaveTextContent(/no se supondrá un cero/);
});
