import { afterEach, beforeAll, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";

const mocks = vi.hoisted(() => ({ logout: vi.fn() }));
vi.mock("./state", () => ({
  queries: { invalidateQueries: vi.fn() },
  useViewer: () => "owner",
  useApp: () => ({
    me: {
      trainer_id: "owner",
      display_name: "Antonio",
      is_admin: false,
      globally_enabled: true,
    },
    restoring: false,
    season: "",
    setSeason: vi.fn(),
    logout: mocks.logout,
    adminOperationPending: false,
    holdAdminNavigation: () => () => {},
    accountsEnabled: true,
  }),
  useRead: (path: string) => ({
    isPending: false,
    error: null,
    data: path.startsWith("/v1/read/seasons")
      ? { items: [], next_offset: null }
      : path === "/v1/accounts/owner"
        ? {
            trainer_id: "owner",
            display_name: "Antonio",
            photo_url: null,
            revision: 1,
          }
        : undefined,
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
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function shell() {
  render(
    <MemoryRouter initialEntries={["/sin-ruta"]}>
      <App />
    </MemoryRouter>,
  );
}

it.each([
  ["browser", "Mozilla/5.0 Chrome/130"],
  ["Launcher", "Mozilla/5.0 Chrome/130 Electron PokeAppLauncher/0.26.11"],
])("«Mi perfil» opens the settings dialog in the %s", (_, agent) => {
  vi.stubGlobal("navigator", { ...navigator, userAgent: agent });
  shell();
  expect(screen.queryByRole("dialog")).toBeNull();
  const button = screen.getByRole("button", { name: "Mi perfil" });
  expect(button).toHaveAttribute("aria-haspopup", "dialog");
  fireEvent.click(button);
  expect(screen.getByRole("dialog", { name: "Mi perfil" })).toBeVisible();
  // No navigation: the current screen stays behind the dialog.
  expect(
    screen.getByRole("heading", { name: "Página no encontrada" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(mocks.logout).not.toHaveBeenCalled();
});

it("logout stays a separate sidebar control", () => {
  shell();
  fireEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  expect(mocks.logout).toHaveBeenCalledOnce();
  expect(screen.queryByRole("dialog")).toBeNull();
});
