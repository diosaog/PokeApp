import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SavesPage } from "./saves";

vi.mock("../state", () => ({
  useApp: () => ({ season: "", me: { trainer_id: "owner" } }),
  useRead: () => ({ data: undefined, isPending: false, error: null }),
  usePC: () => ({ data: undefined, isPending: false, error: null }),
  useMyPC: () => ({
    data: undefined,
    isPending: false,
    error: null,
    personal: true,
  }),
}));

const agent = (value: string) =>
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue(value);
const page = () =>
  render(
    <MemoryRouter>
      <SavesPage />
    </MemoryRouter>,
  );
const tab = (name: string) =>
  fireEvent.click(screen.getByRole("button", { name }));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("inside Launcher 0.25 the hub opens its native panels through the 27C routes", () => {
  agent("Mozilla/5.0 PokeAppLauncher/0.25.0");
  page();
  expect(
    screen.getByRole("link", { name: "Abrir Mi partida" }),
  ).toHaveAttribute("href", "/escritorio/partida");
  tab("Copias de seguridad");
  expect(
    screen.getByRole("link", { name: "Abrir copias de seguridad" }),
  ).toHaveAttribute("href", "/escritorio/copias");
  tab("Launcher");
  expect(screen.getByRole("link", { name: "Abrir Conexión" })).toHaveAttribute(
    "href",
    "/escritorio/nube",
  );
  // No update button an old Launcher cannot honour, no download inside it.
  expect(screen.queryByText("Buscar actualizaciones")).toBeNull();
  expect(screen.queryByRole("link", { name: /Descargar Launcher/ })).toBeNull();
});

it.each(["0.26.0", "0.26.0-preview.1", "1.0.0"])(
  "inside Launcher %s /saves is the native hub: no 27C links",
  (version) => {
    agent(`Mozilla/5.0 PokeAppLauncher/${version}`);
    page();
    expect(screen.queryByRole("link", { name: "Abrir Mi partida" })).toBeNull();
    tab("Launcher");
    expect(screen.getByText("Buscar actualizaciones")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Abrir Conexión" })).toBeNull();
  },
);

it("in a browser the hub offers the download, never the Launcher routes", () => {
  page();
  expect(screen.queryByRole("link", { name: "Abrir Mi partida" })).toBeNull();
  tab("Launcher");
  expect(
    screen.getByRole("link", { name: /Descargar Launcher/ }),
  ).toHaveAttribute("href", "/launcher/download");
});
