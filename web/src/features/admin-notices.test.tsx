import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import type { Model } from "../api/types";
import { ApiError } from "../api/client";
import { NoticesDesk } from "./admin-notices";

type Overview = Model<"SaveAuditOverview">;
const mocks = vi.hoisted(() => ({
  data: undefined as Overview | undefined,
  error: null as unknown,
  execute: vi.fn(async () => true),
}));
vi.mock("../state", () => ({
  useApp: () => ({
    season: "s",
    me: { is_admin: true },
    holdAdminNavigation: () => () => {},
  }),
  useRead: () => ({ data: mocks.data, error: mocks.error, isPending: false }),
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
    refresh: vi.fn(),
  }),
}));
afterEach(() => {
  cleanup();
  mocks.execute.mockClear();
  mocks.data = undefined;
  mocks.error = null;
});

const side = (revision: number) => ({
  save_file_id: "f",
  sha256: "a".repeat(64),
  uploaded_at: "2026-11-08T10:00:00Z",
  revision,
});
const base = {
  trainer_id: "t1",
  display_name: "Samu",
  game: "X",
  detected_at: "2026-11-08T10:00:00Z",
  updated_at: "2026-11-08T10:00:00Z",
  origin: "desconocido",
  summary: "Comparar partidas no prueba el origen.",
  operations: [],
  compared: {
    previous: side(4),
    current: side(5),
    inventory_status: "compared",
  },
  detector_version: 1,
  events: [],
};
const ivs: Overview["notices"][number] = {
  ...base,
  id: "n1",
  category: "pokemon",
  severity: "alta",
  status: "pending",
  title: "Los seis IVs han pasado a 31",
  pokemon: {
    key: "1:2",
    species: "Pokémon #25",
    form: 0,
    nickname: "Nido",
    level: 30,
    gender: "M",
    shiny: false,
    is_egg: false,
    location: { source: "box", box: 3, slot: 12 },
    previous_location: null,
    previous_species: null,
    item: null,
  },
  changes: [
    {
      field: "iv_hp",
      label: "IV de PS",
      kind: "iv",
      before: 10,
      after: 31,
      severity: "alta",
      reason: "Los IVs reales no cambian jugando.",
      holders: [],
    },
  ],
};
const capsules: Overview["notices"][number] = {
  ...base,
  id: "n2",
  category: "objetos",
  severity: "media",
  status: "pending",
  title: "Objeto con aumento sin verificar",
  pokemon: null,
  changes: [
    {
      field: "item_645",
      label: "Objeto",
      kind: "item",
      before: 0,
      after: 5,
      severity: "media",
      reason: "Sin compras registradas.",
      item: "Item #645",
      category: "Crianza",
      delta: 5,
      justified: 0,
      unjustified: 5,
      holders: [],
    },
  ],
};
const overview = (notices: Overview["notices"]): Overview => ({
  season_id: "s",
  season_status: "active",
  activated_at: "2026-11-08T09:00:00Z",
  pending_saves: 0,
  analyzed_saves: 1,
  last_analyzed_at: "2026-11-08T10:00:00Z",
  trainers: [{ trainer_id: "t1", display_name: "Samu" }],
  notices,
});

it("names exactly what changed: IVs before and after, with the reason", () => {
  mocks.data = overview([ivs]);
  render(<NoticesDesk />);
  expect(
    screen.getByRole("heading", {
      name: "1 aviso de gravedad alta por revisar",
    }),
  ).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: /Los seis IVs han pasado a 31/ }),
  );
  expect(screen.getByText("IV de PS")).toBeInTheDocument();
  expect(screen.getByText("+21")).toBeInTheDocument();
  expect(
    screen.getByText("Los IVs reales no cambian jugando."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Ninguna operación de PokeApp coincide con este cambio."),
  ).toBeInTheDocument();
});

it("shows object jumps with their registered origin", () => {
  mocks.data = overview([capsules]);
  render(<NoticesDesk />);
  fireEvent.click(screen.getByRole("button", { name: /Objeto con aumento/ }));
  expect(screen.getByText("Cápsula Habilidad")).toBeInTheDocument();
  expect(screen.getByText("Crianza")).toBeInTheDocument();
  const row = screen.getByText("Sin justificar").closest("li") as HTMLElement;
  expect(within(row).getByText("Incremento")).toBeInTheDocument();
  expect(within(row).getAllByText("+5")).toHaveLength(2);
  expect(within(row).getByText("Operaciones autorizadas")).toBeInTheDocument();
});

it("justifying needs an observation; the decision only reaches this notice", async () => {
  mocks.data = overview([capsules]);
  render(<NoticesDesk />);
  fireEvent.click(screen.getByRole("button", { name: /Objeto con aumento/ }));
  fireEvent.click(screen.getByRole("button", { name: "Justificar" }));
  const save = screen.getByRole("button", { name: "Guardar: Justificado" });
  expect(save).toBeDisabled();
  fireEvent.change(screen.getByRole("textbox"), {
    target: {
      value: "El entrenador confirma que las consiguió jugando",
    },
  });
  expect(save).toBeEnabled();
  fireEvent.click(save);
  expect(mocks.execute).toHaveBeenCalledWith(
    "/v1/admin/seasons/s/notices/n2/status",
    {
      status: "justified",
      note: "El entrenador confirma que las consiguió jugando",
    },
  );
});

it("filters by state and says when the system is not active yet", () => {
  mocks.data = overview([ivs, { ...capsules, status: "justified" }]);
  const { unmount } = render(<NoticesDesk />);
  expect(screen.queryByText("Objeto con aumento sin verificar")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Justificado" }));
  expect(
    screen.getByText("Objeto con aumento sin verificar"),
  ).toBeInTheDocument();
  expect(screen.queryByText("Los seis IVs han pasado a 31")).toBeNull();
  unmount();
  mocks.data = undefined;
  mocks.error = new ApiError(503, "NOTICES_UNAVAILABLE");
  render(<NoticesDesk />);
  expect(
    screen.getByRole("heading", {
      name: "Los avisos todavía no están activos",
    }),
  ).toBeInTheDocument();
});
