import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Model } from "../api/types";
import { ShopPage } from "./core";
import { Inventory } from "./inventory";

const mocks = vi.hoisted(() => ({
  shop: {} as Model<"ShopRead">,
  inventory: {} as Model<"InventoryRead">,
  execute: vi.fn(),
  paths: vi.fn(),
  uncertain: false,
  trainers: [{ id: "owner", display_name: "Antonio" }] as
    Model<"TrainerRead">[] | undefined,
}));
vi.mock("../state", () => ({
  useApp: () => ({ season: "season", me: { trainer_id: "owner" } }),
  useRead: (path: string) => ({
    data:
      path === "/v1/read/trainers"
        ? mocks.trainers
        : path.endsWith("/shop")
          ? mocks.shop
          : mocks.inventory,
    isPending: false,
    error: null,
  }),
  useOverview: () => ({
    data: { players: [{ trainer_id: "owner", display_name: "Antonio" }] },
  }),
  usePC: () => ({}),
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
  useCommand: (paths: string[]) => {
    mocks.paths(paths);
    return {
      pending: false,
      uncertain: mocks.uncertain,
      error: null,
      success: false,
      execute: mocks.execute,
    };
  },
}));
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  mocks.uncertain = false;
  mocks.trainers = [{ id: "owner", display_name: "Antonio" }];
  mocks.execute.mockResolvedValue(true);
  mocks.shop = {
    balance: "9007199254740993",
    season_status: "archived",
    promotions: [],
    items: [
      {
        id: "item",
        code: "blindar_pokemon",
        name: "Escudo",
        category: "competitivos",
        description: "Protección",
        base_price: 30,
      },
    ],
  };
  mocks.inventory = { purchases: [], targets: [] };
});
it("renders exact large and negative wallets and allows explicit post-League purchases", async () => {
  const view = render(
    <MemoryRouter>
      <ShopPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("9007199254740993 PK₽")).toBeInTheDocument();
  expect(screen.getByText(/La Liga ha terminado/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Comprar" }));
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar compra" }));
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/seasons/season/shop/purchases",
      { item_id: "item", confirm_base_price: true },
    ),
  );
  mocks.shop.balance = "-9007199254740993";
  view.rerender(
    <MemoryRouter>
      <ShopPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("-9007199254740993 PK₽")).toBeInTheDocument();
  expect(mocks.paths).toHaveBeenCalledWith(
    expect.arrayContaining([
      "/v1/read/seasons/season/shop",
      "/v1/read/seasons/season/league",
    ]),
  );
});
it("shows pending promotions without inventing activation dates or enabling their price", () => {
  mocks.shop.promotions = [
    {
      id: "offer",
      shop_item_id: "item",
      status: "pending",
      effective_price: 3,
      stock_total: 2,
      stock_used: 0,
      activates_at: null,
      ends_at: null,
    },
  ];
  render(
    <MemoryRouter>
      <ShopPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("Próxima promoción")).toBeInTheDocument();
  expect(screen.getByText(/3 PK₽ · Aún no disponible/)).toBeInTheDocument();
  expect(screen.queryByText(/Desde/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Comprar" })).toBeDisabled();
});
it("uses only the authoritative active offer ID for its promotional price", async () => {
  mocks.shop.promotions = [
    {
      id: "offer",
      shop_item_id: "item",
      status: "active",
      effective_price: 3,
      stock_total: 2,
      stock_used: 1,
      activates_at: null,
      ends_at: null,
    },
  ];
  render(
    <MemoryRouter>
      <ShopPage />
    </MemoryRouter>,
  );
  expect(
    screen.getByText(/Promoción activa · 1 disponibles/),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Comprar" }));
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Confirmar compra" }));
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/seasons/season/shop/promotions/offer/purchases",
      {},
    ),
  );
});
it("redeems a reward voucher only against a server-approved owned target without physical-save copy", async () => {
  mocks.inventory = {
    purchases: [
      {
        id: "gift",
        shop_item_id: "voucher",
        item_name: "Vale de blindaje por robo",
        item_code: "robbery_shield_voucher",
        acquisition_type: "reward",
        status: "pending",
        total_price: 0,
        purchased_at: "2026-10-07T12:00:00Z",
      },
    ],
    targets: [
      {
        pokemon_entity_id: "eligible",
        trainer_id: "owner",
        visibility: "own",
        can_shield: true,
        location: "Equipo 1",
        pokemon: {
          species: "Pikachu",
          nickname: "",
          item: "",
          is_shiny: false,
        },
      },
      {
        pokemon_entity_id: "shielded",
        trainer_id: "owner",
        visibility: "own",
        can_shield: false,
        location: "Equipo 2",
        pokemon: { species: "Gastly", nickname: "", item: "", is_shiny: false },
      },
      {
        pokemon_entity_id: "rival",
        trainer_id: "rival",
        visibility: "public_team_lock",
        can_shield: false,
        location: "Equipo rival",
        pokemon: { species: "Eevee", nickname: "", item: "", is_shiny: false },
      },
    ],
  };
  render(<Inventory />);
  expect(screen.getByText("Vale de recompensa")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Canjear" }));
  expect(
    screen.getByRole("option", { name: /Pikachu · Antonio/ }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("option", { name: /Gastly|Eevee/ }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/cambio físico/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "eligible" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Confirmar canje" }));
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/seasons/season/shop/purchases/gift/redemptions",
      { pokemon_entity_id: "eligible" },
    ),
  );
});
