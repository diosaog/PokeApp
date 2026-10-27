import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { IncidentCenter } from "./admin-incidents";

const mocks = vi.hoisted(() => ({
  data: undefined as Model<"IncidentOverview"> | undefined,
  error: null as unknown,
  execute: vi.fn(),
  live: vi.fn(),
}));
vi.mock("../state", () => ({
  useApp: () => ({ season: "s", holdAdminNavigation: () => () => {} }),
  useRead: (path: string, enabled: boolean, live?: number) => {
    mocks.live(path, live);
    return { data: mocks.data, error: mocks.error, isPending: false };
  },
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
    uncertain: false,
    error: null,
    success: false,
    execute: mocks.execute,
  }),
}));
afterEach(() => {
  cleanup();
  mocks.execute.mockReset();
  mocks.error = null;
});

const purchase = (over: Partial<Model<"IncidentPurchase">>) =>
  ({
    id: "p1",
    trainer_id: "t1",
    display_name: "Lucía",
    item_name: "Escudo Pokémon",
    item_code: "blindar_pokemon",
    total_price: 30,
    status: "pending",
    acquisition_type: "paid",
    purchased_at: "2026-10-20T10:00:00Z",
    linked_operation: false,
    cancellable: true,
    refundable: false,
    ...over,
  }) as Model<"IncidentPurchase">;
const overview = (): Model<"IncidentOverview"> => ({
  season_id: "s",
  season_status: "active",
  wallets: [
    { trainer_id: "t1", display_name: "Lucía", status: "active", balance: 20 },
  ],
  purchases: [
    purchase({}),
    purchase({
      id: "p2",
      status: "used",
      cancellable: false,
      refundable: true,
    }),
    purchase({
      id: "p3",
      item_name: "Robar Pokémon",
      linked_operation: true,
      cancellable: false,
    }),
  ],
  robberies: [],
  history: [],
});

it("says honestly when the center is not enabled on this server", () => {
  mocks.data = undefined;
  mocks.error = new ApiError(503, "INCIDENTS_UNAVAILABLE");
  render(<IncidentCenter />);
  expect(
    screen.getByRole("heading", {
      name: "Centro de incidencias pendiente de activar",
    }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Cancelar" })).toBeNull();
});

it("polls while open and offers only the actions the server allows", () => {
  mocks.data = overview();
  render(<IncidentCenter />);
  expect(mocks.live).toHaveBeenCalledWith(
    "/v1/admin/seasons/s/incidents",
    15000,
  );
  expect(screen.getAllByRole("button", { name: "Cancelar" })).toHaveLength(1);
  expect(screen.getAllByRole("button", { name: "Reembolsar" })).toHaveLength(1);
  // A purchase tied to a save operation shows why it cannot be reversed here.
  expect(
    screen.getByText("Vinculada a una operación de partida"),
  ).toBeInTheDocument();
});

it("cancels with a reason, a review and the impact on the wallet", async () => {
  mocks.data = overview();
  mocks.execute.mockResolvedValue(true);
  render(<IncidentCenter />);
  fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  const dialog = screen.getByRole("dialog", { name: "Cancelar compra" });
  expect(dialog).toHaveTextContent("20 → 50 PK₽");
  fireEvent.change(screen.getByLabelText("Motivo (queda en el historial)"), {
    target: { value: "Compra duplicada" },
  });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.submit(
    screen
      .getByRole("button", { name: "Confirmar cancelación" })
      .closest("form")!,
  );
  await vi.waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/admin/seasons/s/incidents/purchases/p1",
      { action: "cancel", reason: "Compra duplicada" },
    ),
  );
});

it("coin corrections never leave a wallet below zero", () => {
  mocks.data = overview();
  render(<IncidentCenter />);
  fireEvent.click(screen.getByRole("button", { name: "Corregir" }));
  const amount = screen.getByLabelText("Cantidad (negativa para restar)");
  const submit = screen.getByRole("button", { name: "Confirmar corrección" });
  fireEvent.change(amount, { target: { value: "-21" } });
  expect(submit).toBeDisabled();
  expect(screen.getByRole("status")).toHaveTextContent(/por debajo de cero/);
  fireEvent.change(amount, { target: { value: "0" } });
  expect(submit).toBeDisabled();
  fireEvent.change(amount, { target: { value: "-20" } });
  expect(submit).toBeEnabled();
  expect(screen.getByRole("status")).toHaveTextContent("20 → 0 PK₽");
});
