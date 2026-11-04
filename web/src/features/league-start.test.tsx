import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import type { Model } from "../api/types";
import { OwnDeathHistory, trainerReasonText } from "./league-start";

type Own = Model<"OwnDeathHistoryRead">;
const mocks = vi.hoisted(() => ({
  data: null as Own | null,
  execute: vi.fn(),
  reads: [] as string[],
}));
vi.mock("../state", () => ({
  queries: { invalidateQueries: vi.fn() },
  useApp: () => ({ season: "season", me: { trainer_id: "t1" } }),
  useRead: (path: string) => {
    mocks.reads.push(path);
    return { data: mocks.data, isPending: false, error: null };
  },
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  useCommand: () => ({
    pending: false,
    uncertain: false,
    error: null,
    success: false,
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
const own = (changes: Partial<Own> = {}): Own => ({
  season_id: "season",
  season_player_id: "p1",
  trainer_id: "t1",
  revision: 1,
  known: false,
  blocking_reason: "death_history_baseline_required",
  actual_deaths: null,
  wipe_deaths: null,
  segment_deaths: null,
  dead_box_number: 7,
  source_sha256: "a".repeat(64),
  confirmed_at: null,
  current_matchday_id: null,
  can_confirm: true,
  confirm_blocker: null,
  proposed: { actual_deaths: 3, wipe_deaths: 0, segment_deaths: 3 },
  replayed: false,
  ...changes,
});
beforeEach(() => {
  vi.clearAllMocks();
  mocks.reads = [];
  mocks.data = own();
  mocks.execute.mockResolvedValue(true);
});
afterEach(cleanup);

it("the trainer confirms exactly the observed values, nothing typed, on their own history", async () => {
  render(<OwnDeathHistory />);
  expect(mocks.reads).toContain("/v1/seasons/season/death-history");
  const card = screen.getByRole("region", {
    name: /Historial de muertes de la Liga/,
  });
  expect(card).toHaveTextContent("Caja 7");
  expect(card).toHaveTextContent("3 muertes reales");
  expect(card).toHaveTextContent("0 revividos tras wipe");
  expect(card).toHaveTextContent("3 muertes de progresión actuales");
  expect(within(card).queryByRole("textbox")).not.toBeInTheDocument();
  expect(within(card).queryByRole("spinbutton")).not.toBeInTheDocument();
  fireEvent.click(
    within(card).getByRole("button", { name: "Confirmar historial" }),
  );
  const dialog = screen.getByRole("dialog", {
    name: "Confirmar mi historial de muertes",
  });
  expect(dialog).toHaveTextContent(/Solo puedes confirmar tu propio historial/);
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Confirmar estos valores" }),
  );
  await vi.waitFor(() => expect(mocks.execute).toHaveBeenCalledOnce());
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/seasons/season/death-history",
    {
      expected_revision: 1,
      source_sha256: "a".repeat(64),
      actual_deaths: 3,
      wipe_deaths: 0,
      segment_deaths: 3,
    },
    "PUT",
  );
});

it("a confirmed history needs nothing; exceptional cases say who acts", () => {
  mocks.data = own({
    known: true,
    blocking_reason: null,
    actual_deaths: 3,
    wipe_deaths: 0,
    segment_deaths: 3,
    can_confirm: false,
    confirm_blocker: "death_history_confirmed",
    proposed: null,
  });
  const view = render(<OwnDeathHistory />);
  expect(screen.queryByRole("region")).not.toBeInTheDocument();
  mocks.data = own({
    can_confirm: false,
    confirm_blocker: "death_history_admin_required",
    proposed: null,
  });
  view.rerender(<OwnDeathHistory />);
  expect(
    screen.getByText(
      /necesita una revisión de Administración: es un caso excepcional/,
    ),
  ).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  mocks.data = own({
    can_confirm: false,
    confirm_blocker: "save_missing",
    proposed: null,
    source_sha256: null,
  });
  view.rerender(<OwnDeathHistory />);
  expect(
    screen.getByText(/Registra tu partida oficial desde PokeApp Launcher/),
  ).toBeVisible();
});

it("the inline action only appears when the trainer can confirm", () => {
  const view = render(<OwnDeathHistory inline />);
  expect(
    screen.getByRole("button", { name: "Confirmar mi historial" }),
  ).toBeVisible();
  mocks.data = own({
    can_confirm: false,
    confirm_blocker: "death_history_pending_sync",
    proposed: null,
  });
  view.rerender(<OwnDeathHistory inline />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("reasons speak to the viewer in second person and to the others in third", () => {
  expect(trainerReasonText("save_missing", true)).toMatch(
    /^registra tu partida oficial/,
  );
  expect(trainerReasonText("save_missing", false)).toMatch(
    /^falta registrar su partida oficial/,
  );
  expect(trainerReasonText("badges_missing", false)).toBe(
    "necesita las dos primeras medallas para la J1",
  );
});
