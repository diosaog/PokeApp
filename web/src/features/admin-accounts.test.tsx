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
