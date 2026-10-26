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
import { Inventory, itemUseLabels, transferLabels } from "./inventory";

const mocks = vi.hoisted(() => ({
  shop: {} as Model<"ShopRead">,
  inventory: {} as Model<"InventoryRead">,
  itemUses: {
    items: [],
    physical_application_enabled: false,
  } as Model<"ItemUseListResponse">,
  transfers: {
    items: [],
    transfer_enabled: false,
  } as Model<"TransferListResponse">,
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
          : path.endsWith("/item-uses")
            ? mocks.itemUses
            : path.endsWith("/transfers")
              ? mocks.transfers
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
  mocks.itemUses = { items: [], physical_application_enabled: false };
  mocks.transfers = { items: [], transfer_enabled: false };
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
it.each(Object.entries(itemUseLabels))(
  "shows %s without consuming a physical entitlement",
  (status, label) => {
    mocks.inventory = {
      targets: [],
      purchases: [
        {
          id: "physical",
          shop_item_id: "revive",
          item_name: "Revivir Pokémon",
          item_code: "revivir_pokemon",
          acquisition_type: "paid",
          status: "pending",
          physical_state: status,
          total_price: 12,
          purchased_at: "2026-10-25T10:00:00Z",
        },
      ],
    };
    render(<Inventory />);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Canjear" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Canjeado")).not.toBeInTheDocument();
    expect(mocks.execute).not.toHaveBeenCalled();
  },
);
it("renders exact large and negative wallets and allows explicit post-League purchases", async () => {
  const view = render(
    <MemoryRouter>
      <ShopPage />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Competitivos" }));
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
  fireEvent.click(screen.getByRole("button", { name: "Competitivos" }));
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
  fireEvent.click(screen.getByRole("button", { name: "Competitivos" }));
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
  expect(screen.getByRole("button", { name: "Competitivos" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Competitivos" }));
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
    screen.getByRole("button", { name: /Pikachu.*Equipo 1/ }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Gastly|Eevee/ }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/cambio fÃ­sico/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Pikachu.*Equipo 1/ }));
  fireEvent.click(screen.getByRole("button", { name: "Sí, blindar" }));
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/seasons/season/shop/purchases/gift/redemptions",
      { pokemon_entity_id: "eligible" },
    ),
  );
});

const robbery = {
  id: "steal",
  shop_item_id: "robar",
  item_name: "Robar Pokémon",
  item_code: "robar_pokemon",
  acquisition_type: "paid",
  status: "pending",
  physical_state: "AVAILABLE",
  total_price: 40,
  purchased_at: "2026-10-25T10:00:00Z",
} as Model<"PurchaseRead">;
const leg = (
  status: Model<"TransferSummary">["status"],
  side: "source" | "destination" = "destination",
) =>
  ({
    authorization_id: "aid",
    side,
    status,
    purchase_id: side === "destination" ? "steal" : null,
    pokemon_entity_id: "rival",
    claimed: false,
    apply_started: false,
    verified: false,
    accepted_save_id: null,
    expires_at: "2026-10-25T11:00:00Z",
    created_at: "2026-10-25T10:00:00Z",
  }) as Model<"TransferSummary">;

it("keeps robbery unavailable unless the backend enables this account", () => {
  mocks.inventory = { purchases: [robbery], targets: [] };
  render(<Inventory />);
  expect(screen.getByText(/aún no está\s+habilitada/)).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Canjear" }),
  ).not.toBeInTheDocument();
});

it("requests an enabled robbery through the paired transfer route only", async () => {
  mocks.transfers = { items: [], transfer_enabled: true };
  mocks.trainers = [
    { id: "rival", display_name: "Rival" },
  ] as Model<"TrainerRead">[];
  mocks.inventory = {
    purchases: [robbery],
    targets: [
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
  fireEvent.click(screen.getByRole("button", { name: "Canjear" }));
  fireEvent.click(screen.getByRole("button", { name: /Rival/ }));
  fireEvent.click(screen.getByRole("button", { name: /Eevee/ }));
  fireEvent.click(screen.getByRole("button", { name: "Sí, robar" }));
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/seasons/season/shop/purchases/steal/transfer",
      { pokemon_entity_id: "rival" },
    ),
  );
  expect(mocks.paths).toHaveBeenCalledWith(
    expect.arrayContaining(["/v1/seasons/season/transfers"]),
  );
});

it.each(Object.entries(transferLabels))(
  "shows transfer %s without claiming an unconfirmed robbery",
  (status, label) => {
    mocks.transfers = {
      items: [leg(status as Model<"TransferSummary">["status"])],
      transfer_enabled: true,
    };
    mocks.inventory = { purchases: [robbery], targets: [] };
    render(<Inventory />);
    expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(screen.queryAllByText("Robo completado").length > 0).toBe(
      status === "COMMITTED",
    );
    expect(
      screen.queryByRole("button", { name: "Canjear" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cancelar robo" }) !== null,
    ).toBe(
      ["REQUESTED", "PREPARING", "WAITING_OTHER", "PENDING_SOURCE"].includes(
        status,
      ),
    );
  },
);

it("tells the victim to use the Launcher and offers no web cancellation", () => {
  mocks.transfers = {
    items: [leg("WAITING_OTHER", "source")],
    transfer_enabled: true,
  };
  render(<Inventory />);
  expect(screen.getByText(/No necesita tu aprobación/)).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Cancelar robo" }),
  ).not.toBeInTheDocument();
});

it("separates the decided robbery from each save's pending delivery", () => {
  mocks.transfers = {
    items: [
      {
        ...leg("COMPETITIVELY_ADJUDICATED", "source"),
        obligation: "DONOR_PHYSICAL_PENDING",
      },
      {
        ...leg("COMPETITIVELY_ADJUDICATED"),
        authorization_id: "other",
        obligation: "RECIPIENT_PHYSICAL_PENDING",
      },
    ],
    transfer_enabled: true,
  };
  render(<Inventory />);
  expect(screen.getAllByText("Robo adjudicado · definitivo")).toHaveLength(2);
  expect(screen.getByText(/Retirada pendiente/)).toBeInTheDocument();
  expect(screen.getByText(/Pendiente de recepción/)).toBeInTheDocument();
  expect(screen.queryAllByText(/Robo completado/)).toHaveLength(0);
  expect(
    screen.queryByRole("button", { name: "Cancelar robo" }),
  ).not.toBeInTheDocument();
});

it("withdraws a requested robbery before any application", async () => {
  mocks.transfers = { items: [leg("PENDING_SOURCE")], transfer_enabled: true };
  render(<Inventory />);
  fireEvent.click(screen.getByRole("button", { name: "Cancelar robo" }));
  await waitFor(() =>
    expect(mocks.execute).toHaveBeenCalledWith(
      "/v1/seasons/season/transfers/aid/cancel",
      {},
    ),
  );
});

const unlimited = [
  {
    code: "rare_candy",
    item_id: 50,
    name: "Rare Candy",
    label: "Caramelo Raro",
    description: "Gratis e ilimitado.",
    availability: "unlimited",
  },
  {
    code: "heart_scale",
    item_id: 93,
    name: "Heart Scale",
    label: "Escama Corazón",
    description: "Gratis e ilimitada.",
    availability: "unlimited",
  },
] as Model<"InventoryRead">["unlimited_items"];

it("shows Rare Candy and Heart Scale as infinite and free with no purchase action", () => {
  mocks.inventory = { purchases: [], targets: [], unlimited_items: unlimited };
  render(<Inventory />);
  expect(screen.getByText("Caramelo Raro")).toBeInTheDocument();
  expect(screen.getByText("Escama Corazón")).toBeInTheDocument();
  expect(screen.getAllByText("∞ · Gratis")).toHaveLength(2);
  expect(screen.getAllByText(/Disponible en PokeApp Launcher/)).toHaveLength(2);
  expect(
    screen.queryByRole("link", { name: "Añadir a mi partida" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Canjear" }),
  ).not.toBeInTheDocument();
  expect(mocks.execute).not.toHaveBeenCalled();
});

it("inside the Launcher links each infinite item to the native quick-item panel", () => {
  const agent = vi
    .spyOn(navigator, "userAgent", "get")
    .mockReturnValue("Mozilla/5.0 PokeAppLauncher/0.23.0");
  mocks.inventory = { purchases: [], targets: [], unlimited_items: unlimited };
  render(<Inventory />);
  const links = screen.getAllByRole("link", { name: "Añadir a mi partida" });
  expect(links.map((a) => a.getAttribute("href"))).toEqual([
    "/__launcher/quick-items/rare_candy",
    "/__launcher/quick-items/heart_scale",
  ]);
  expect(mocks.execute).not.toHaveBeenCalled();
  agent.mockRestore();
});
