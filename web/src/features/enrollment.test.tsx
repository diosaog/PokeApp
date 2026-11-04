import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
  waitFor,
} from "@testing-library/react";
import type { Model } from "../api/types";
import { Enrollment } from "./enrollment";

const mocks = vi.hoisted(() => ({
  preview: null as Model<"EnrollmentPreview"> | null,
  error: null as Error | null,
  execute: vi.fn(),
  retry: vi.fn(),
  hold: vi.fn(),
  pending: false,
  uncertain: false,
}));
vi.mock("../state", () => ({
  useApp: () => ({ season: "season", holdAdminNavigation: mocks.hold }),
  useRead: () => ({
    data: mocks.preview,
    error: mocks.error,
    isPending: false,
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
      <button onClick={onClose}>Cerrar</button>
      {children}
    </div>
  ),
  useCommand: () => ({
    execute: mocks.execute,
    retry: mocks.retry,
    pending: mocks.pending,
    uncertain: mocks.uncertain,
    error: null,
    success: false,
  }),
}));
beforeEach(() => {
  vi.clearAllMocks();
  mocks.pending = false;
  mocks.uncertain = false;
  mocks.error = null;
  mocks.execute.mockResolvedValue(true);
  mocks.hold.mockReturnValue(() => {});
  mocks.preview = {
    season_id: "season",
    season_name: "ChampionsLocke",
    eligible_trainers: [{ id: "entrant", display_name: "Elena" }],
    first_matchday_number: 2,
    matchday_id: "day2",
    matchday_status: "open",
    closed_matchdays: 1,
    initial_coins: 10,
    initial_points: "0",
    new_matchups: 5,
    preview_hash: "a".repeat(64),
  };
});
afterEach(cleanup);
function review() {
  fireEvent.change(screen.getByLabelText("Entrenador"), {
    target: { value: "entrant" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar incorporación" }),
  );
  return screen.getByRole("dialog");
}
it("shows the authoritative active-day summary and sends only trainer and preview hash", async () => {
  render(<Enrollment />);
  const dialog = review();
  for (const text of [
    "Puntos iniciales: 0.",
    "Jornadas completadas: 1.",
    "Monedas iniciales: 10.",
    "Participará desde: J2 (en curso).",
    "Nuevos enfrentamientos: 5.",
  ])
    expect(within(dialog).getByText(text)).toBeInTheDocument();
  expect(within(dialog).queryByRole("spinbutton")).not.toBeInTheDocument();
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Confirmar incorporación" }),
  );
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/admin/seasons/season/enrollment",
      { trainer_id: "entrant", preview_hash: "a".repeat(64) },
    ),
  );
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
});
it("keeps a reviewed summary frozen and requires a fresh review after a League change", () => {
  const view = render(<Enrollment />);
  review();
  mocks.preview = {
    ...mocks.preview!,
    preview_hash: "b".repeat(64),
    initial_coins: 20,
    first_matchday_number: 3,
  };
  view.rerender(<Enrollment />);
  expect(
    screen.getByRole("button", { name: "Confirmar incorporación" }),
  ).toBeDisabled();
  expect(screen.getByRole("alert")).toHaveTextContent("La Liga ha cambiado");
  expect(screen.getByText("Monedas iniciales: 10.")).toBeInTheDocument();
  expect(mocks.execute).not.toHaveBeenCalled();
});
it("shows J1 with zero coins before any closed day and a prepared next day correctly", () => {
  mocks.preview = {
    ...mocks.preview!,
    first_matchday_number: 1,
    matchday_status: "scheduled",
    closed_matchdays: 0,
    initial_coins: 0,
  };
  render(<Enrollment />);
  review();
  expect(screen.getByText("Monedas iniciales: 0.")).toBeInTheDocument();
  expect(
    screen.getByText("Participará desde: J1 (preparada)."),
  ).toBeInTheDocument();
});
it("holds navigation and locks the selected request while an outcome is uncertain", () => {
  const view = render(<Enrollment />);
  review();
  mocks.uncertain = true;
  view.rerender(<Enrollment />);
  expect(mocks.hold).toHaveBeenCalled();
  expect(
    screen.getByRole("button", { name: "Confirmar incorporación" }),
  ).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});
it("guides the admin to existing account registration when no eligible account exists", () => {
  mocks.preview = { ...mocks.preview!, eligible_trainers: [] };
  render(<Enrollment />);
  expect(screen.getByText(/No hay cuentas disponibles/)).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Revisar incorporación" }),
  ).toBeDisabled();
});
