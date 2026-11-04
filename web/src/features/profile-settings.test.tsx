import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ProfileSettings } from "./profile-settings";
import { readFileSync } from "node:fs";

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  setMe: vi.fn(),
  logout: vi.fn(),
  accountsEnabled: true,
  pending: false,
}));
vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: { request: mocks.request },
}));
vi.mock("../state", () => ({
  queries: { invalidateQueries: vi.fn() },
  useApp: () => ({
    me: { trainer_id: "owner", display_name: "Antonio" },
    season: "season",
    accountsEnabled: mocks.accountsEnabled,
    adminOperationPending: mocks.pending,
    setMe: mocks.setMe,
    logout: mocks.logout,
    holdAdminNavigation: () => () => {},
  }),
  useRead: (path: string) => ({
    isPending: false,
    error: null,
    data:
      path === "/v1/accounts/owner"
        ? {
            trainer_id: "owner",
            display_name: "Antonio",
            photo_url: null,
            revision: 3,
          }
        : undefined,
  }),
}));
// jsdom has <dialog> but not its modal methods; the real Modal is exercised.
beforeAll(() => {
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});
beforeEach(() => {
  vi.clearAllMocks();
  mocks.accountsEnabled = true;
  mocks.pending = false;
  mocks.request.mockResolvedValue({ status: "changed" });
  localStorage.clear();
});
afterEach(cleanup);

function open(onClose = vi.fn()) {
  render(
    <MemoryRouter>
      <ProfileSettings onClose={onClose} />
    </MemoryRouter>,
  );
  return onClose;
}
const dialog = () => screen.getByRole("dialog", { name: "Mi perfil" });

it("groups every existing personal setting in three tabs", () => {
  open();
  const tabs = within(dialog()).getAllByRole("tab");
  expect(tabs.map((t) => t.textContent?.trim())).toEqual([
    "Perfil",
    "Seguridad",
    "Preferencias",
  ]);
  expect(screen.getByLabelText("Nombre de entrenador")).toBeVisible();
  expect(screen.getByLabelText("Foto de perfil")).toBeVisible();
  expect(screen.getByLabelText("PIN actual")).not.toBeVisible();
  fireEvent.click(screen.getByRole("tab", { name: "Seguridad" }));
  expect(screen.getByLabelText("PIN actual")).toBeVisible();
  expect(screen.getByLabelText("Nuevo PIN")).toBeVisible();
  fireEvent.click(screen.getByRole("tab", { name: "Preferencias" }));
  expect(screen.getByRole("group", { name: "Sonidos" })).toBeVisible();
  expect(screen.getByRole("slider")).toBeVisible();
  expect(screen.getByRole("group", { name: "Animaciones" })).toBeVisible();
});

it("no stylesheet rule can force a hidden tab panel back on screen", () => {
  // 079: jsdom ignores author CSS, so the tests above passed while a
  // `.profile-settings-body > section { display: grid }` rule showed every
  // panel at once in the real app. Guard the shipped stylesheet itself.
  // Vitest runs from web/; jsdom gives import.meta.url an http scheme.
  const shell = readFileSync("src/design/hub.css", "utf8");
  const rules = shell.match(/[^{}]+\{[^}]*\}/g) ?? [];
  const panelRules = rules.filter((rule) =>
    /profile-settings-body\s*>\s*section/.test(rule.split("{")[0]),
  );
  expect(panelRules.length).toBeGreaterThan(0);
  for (const rule of panelRules)
    if (/display\s*:(?!\s*none)/.test(rule))
      expect(rule.split("{")[0]).toMatch(/:not\(\[hidden\]\)/);
  expect(shell).toMatch(
    /\.profile-settings-body > section\[hidden\] \{\s*display: none;/,
  );
});

it("keyboard arrows move between tabs", () => {
  open();
  const perfil = screen.getByRole("tab", { name: "Perfil" });
  fireEvent.keyDown(perfil, { key: "ArrowRight" });
  expect(screen.getByRole("tab", { name: "Seguridad" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  fireEvent.keyDown(screen.getByRole("tab", { name: "Seguridad" }), {
    key: "ArrowLeft",
  });
  expect(perfil).toHaveAttribute("aria-selected", "true");
});

it("saves the name with the same request and revision as before", async () => {
  open();
  fireEvent.change(screen.getByLabelText("Nombre de entrenador"), {
    target: { value: "Nuevo" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar nombre" }));
  await waitFor(() => expect(mocks.request).toHaveBeenCalledOnce());
  const [path, init] = mocks.request.mock.calls[0];
  expect(path).toBe("/v1/account/name");
  expect(init.method).toBe("PUT");
  expect(JSON.parse(init.body)).toEqual({
    display_name: "Nuevo",
    expected_revision: 3,
  });
});

it("PIN changes keep the existing session-closing behaviour", async () => {
  open();
  fireEvent.click(screen.getByRole("tab", { name: "Seguridad" }));
  for (const [label, value] of [
    ["PIN actual", "0017"],
    ["Nuevo PIN", "0028"],
    ["Repetir nuevo PIN", "0028"],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Cambiar PIN" }));
  await waitFor(() => expect(mocks.logout).toHaveBeenCalledOnce());
  expect(mocks.request.mock.calls[0][0]).toBe("/v1/account/pin");
});

it("closes at once when nothing was typed", () => {
  const onClose = open();
  fireEvent.click(within(dialog()).getByRole("button", { name: "Cerrar" }));
  expect(onClose).toHaveBeenCalledOnce();
});

it("warns before dropping unsaved input, from any tab or Escape", () => {
  const onClose = open();
  fireEvent.click(screen.getByRole("tab", { name: "Seguridad" }));
  fireEvent.change(screen.getByLabelText("Nuevo PIN"), {
    target: { value: "12" },
  });
  fireEvent.click(screen.getByRole("tab", { name: "Preferencias" }));
  fireEvent(dialog(), new Event("cancel", { cancelable: true }));
  expect(onClose).not.toHaveBeenCalled();
  expect(screen.getByText("Tienes cambios sin guardar.")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Seguir editando" }));
  expect(screen.queryByText("Tienes cambios sin guardar.")).toBeNull();
  // Switching tabs kept what was typed.
  expect(screen.getByLabelText("Nuevo PIN")).toHaveValue("12");
  fireEvent.click(within(dialog()).getByRole("button", { name: "Cerrar" }));
  fireEvent.click(screen.getByRole("button", { name: "Descartar y cerrar" }));
  expect(onClose).toHaveBeenCalledOnce();
});

it("does not close while a request is still unconfirmed", () => {
  mocks.pending = true;
  const onClose = open();
  fireEvent.click(within(dialog()).getByRole("button", { name: "Cerrar" }));
  expect(onClose).not.toHaveBeenCalled();
  expect(
    screen.getByText(/Espera a que se confirme la operación en curso/),
  ).toBeVisible();
});

it("without accounts it still offers the app preferences", () => {
  mocks.accountsEnabled = false;
  open();
  expect(screen.queryByRole("tab")).toBeNull();
  expect(screen.queryByLabelText("Nombre de entrenador")).toBeNull();
  expect(screen.queryByLabelText("PIN actual")).toBeNull();
  fireEvent.click(
    within(screen.getByRole("group", { name: "Animaciones" })).getByRole(
      "button",
      { name: "Reducidas" },
    ),
  );
  expect(
    JSON.parse(localStorage.getItem("pokeapp.preferences.v1") || "{}"),
  ).toMatchObject({ motion: "reduced" });
});

it("links to the own trainer page", () => {
  const onClose = open();
  const link = screen.getByRole("link", {
    name: "Ver mi ficha de entrenador →",
  });
  expect(link).toHaveAttribute("href", "/entrenadores/owner");
  fireEvent.click(link);
  expect(onClose).toHaveBeenCalledOnce();
});
