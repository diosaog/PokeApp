import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminAccountsPage } from "./admin-accounts";
const mocks = vi.hoisted(() => ({
  admin: true,
  execute: vi.fn(),
  hold: vi.fn(() => () => {}),
  read: vi.fn(),
}));
vi.mock("../state", () => ({
  useApp: () => ({
    me: { trainer_id: "owner", is_admin: mocks.admin },
    holdAdminNavigation: mocks.hold,
    adminOperationPending: false,
  }),
  useRead: mocks.read,
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  useCommand: () => ({
    execute: mocks.execute,
    pending: false,
    uncertain: false,
    error: null,
    success: false,
  }),
}));
vi.mock("./account-editor", () => ({
  PinForm: ({ adminTarget }: { adminTarget: string }) => (
    <p>PIN de {adminTarget}</p>
  ),
}));
beforeEach(() => {
  vi.clearAllMocks();
  mocks.admin = true;
  mocks.execute.mockResolvedValue(true);
  mocks.read.mockReturnValue({
    data: {
      items: [
        {
          trainer_id: "owner",
          display_name: "Antonio",
          globally_enabled: true,
          is_admin: true,
          revision: 0,
          provisioned: true,
        },
        {
          trainer_id: "other",
          display_name: "Ana",
          globally_enabled: true,
          is_admin: false,
          revision: 3,
          provisioned: true,
        },
      ],
      has_more: false,
    },
    isPending: false,
    error: null,
  });
});
afterEach(cleanup);
function page() {
  render(
    <MemoryRouter>
      <AdminAccountsPage />
    </MemoryRouter>,
  );
}
it("does not offer account management to ordinary trainers", () => {
  mocks.admin = false;
  page();
  expect(
    screen.queryByRole("button", { name: "Deshabilitar cuenta" }),
  ).toBeNull();
  expect(mocks.read.mock.calls[0][1]).toBe(false);
});
it("requires explicit confirmation and preserves the displayed revision", async () => {
  page();
  const buttons = screen.getAllByRole("button", {
    name: "Deshabilitar cuenta",
  });
  expect(buttons[0]).toBeDisabled();
  fireEvent.click(buttons[1]);
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Confirmar cambio de acceso" }),
  );
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/admin/accounts/other/status",
      { enabled: false, expected_revision: 3 },
      "PUT",
    ),
  );
});
it("offers a targeted PIN reset without deletion or role editing", () => {
  page();
  fireEvent.click(screen.getAllByRole("button", { name: "Gestionar PIN" })[1]);
  expect(screen.getByText("PIN de other")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Eliminar|Administrador/ }),
  ).toBeNull();
});

const detail = {
  trainer_id: "other",
  display_name: "Ana",
  globally_enabled: true,
  is_admin: false,
  provisioned: true,
  revision: 3,
  deleted: false,
  created_at: "2026-10-01T10:00:00Z",
  credential: { version: 2, reset_required: false },
  session_guard: null,
  pin_change_pending: false,
  personal_save: { game: "Y", uploaded_at: "2026-10-28T20:00:00Z" },
  seasons: [
    {
      season_id: "s1",
      name: "Prueba",
      status: "active",
      participant_status: "active",
      bound_game: "SN",
      save_uploaded_at: null,
      coin_balance: "16",
    },
  ],
  history: { seasons: 1, coin_transactions: 4, saves: 2 },
};
function openRepair() {
  mocks.read.mockImplementation((path: string) =>
    path === "/v1/admin/accounts/other"
      ? { data: detail, isPending: false, error: null }
      : {
          data: {
            items: [
              {
                trainer_id: "other",
                display_name: "Ana",
                globally_enabled: true,
                is_admin: false,
                revision: 3,
                provisioned: true,
              },
            ],
            has_more: false,
          },
          isPending: false,
          error: null,
        },
  );
  render(
    <MemoryRouter>
      <AdminAccountsPage />
    </MemoryRouter>,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Estado y herramientas" }),
  );
}

it("an account's real state is shown with its repair tools", () => {
  openRepair();
  expect(screen.getByText(/Pokémon Y · sincronizada/)).toBeInTheDocument();
  expect(
    screen.getByText(/Prueba \(En curso\).*compite con Pokémon Sol/),
  ).toBeInTheDocument();
  expect(screen.getByText(/Versión 2/)).toBeInTheDocument();
});

it("ending all sessions asks first and sends one command", async () => {
  openRepair();
  fireEvent.click(
    screen.getByRole("button", { name: "Cerrar todas sus sesiones" }),
  );
  expect(mocks.execute).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Confirmar cierre de sesiones" }),
  );
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/admin/accounts/other/revoke-sessions",
      {},
    ),
  );
});

it("deleting needs the exact name and keeps history under an anonymous name", async () => {
  openRepair();
  fireEvent.click(screen.getByRole("button", { name: "Borrar cuenta…" }));
  expect(
    screen.getByText(/se conserva a nombre de «Entrenador eliminado»/),
  ).toBeInTheDocument();
  const go = screen.getByRole("button", { name: "Borrar definitivamente" });
  expect(go).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Escribe Ana para confirmar"), {
    target: { value: "ana" },
  });
  expect(go).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Escribe Ana para confirmar"), {
    target: { value: "Ana" },
  });
  fireEvent.click(go);
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/admin/accounts/other/delete",
      {
        confirmation: "Ana",
      },
    ),
  );
});
