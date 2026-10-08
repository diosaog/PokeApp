import { test, expect, type Route } from "@playwright/test";
import { fixture, login, navigate, sid, tid, pokemon } from "./fixtures";

const headers = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Headers": "authorization,content-type,idempotency-key",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
};
async function reply(route: Route, json: unknown, status = 200) {
  return route.fulfill({ status, headers, json });
}

test("archived wallet stays exact; pending offers wait for server activation", async ({
  page,
}) => {
  const commands = await fixture(page);
  let active = false;
  await page.route(`**/v1/read/seasons/${sid}/shop`, (route) =>
    reply(route, {
      balance: "9007199254740993",
      season_status: "archived",
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
      promotions: [
        {
          id: "offer",
          shop_item_id: "item",
          status: active ? "active" : "pending",
          effective_price: 3,
          stock_total: 2,
          stock_used: 0,
          activates_at: null,
          ends_at: null,
        },
      ],
    }),
  );
  await login(page);
  await navigate(page, "Tienda");
  await page.getByRole("button", { name: "Competitivos", exact: true }).click();
  await expect(page.getByText("9007199254740993 PK₽")).toBeVisible();
  await expect(page.getByText(/La Liga ha terminado/)).toBeVisible();
  await expect(page.getByText("Próxima promoción")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Comprar", exact: true }),
  ).toBeDisabled();
  active = true;
  await page.reload();
  await login(page);
  await navigate(page, "Tienda");
  await page.getByRole("button", { name: "Competitivos", exact: true }).click();
  await expect(page.getByText(/Promoción activa/)).toBeVisible();
  await page.getByRole("button", { name: "Comprar", exact: true }).click();
  await page.getByRole("button", { name: "Confirmar compra" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(commands.at(-1)?.path).toBe(
    `/v1/seasons/${sid}/shop/promotions/offer/purchases`,
  );
  expect(commands.at(-1)?.body).toEqual({});
});

test("reward voucher filters targets and retries an uncertain redemption with the original key/body", async ({
  page,
}) => {
  await fixture(page);
  let used = false;
  const attempts: { key?: string; body: unknown }[] = [];
  await page.route(`**/v1/read/seasons/${sid}/inventory`, (route) =>
    reply(route, {
      purchases: [
        {
          id: "gift",
          shop_item_id: "voucher",
          item_code: "robbery_shield_voucher",
          item_name: "Vale de blindaje por robo",
          status: used ? "used" : "pending",
          acquisition_type: "reward",
          total_price: 0,
          purchased_at: "2026-10-07T12:00:00Z",
        },
      ],
      targets: [
        {
          pokemon_entity_id: "eligible",
          trainer_id: tid,
          visibility: "own",
          can_shield: true,
          location: "Equipo 1",
          pokemon,
        },
        {
          pokemon_entity_id: "shielded",
          trainer_id: tid,
          visibility: "own",
          can_shield: false,
          location: "Equipo 2",
          pokemon: { ...pokemon, nickname: "Ya protegido" },
        },
        {
          pokemon_entity_id: "rival",
          trainer_id: "rival",
          visibility: "public_team_lock",
          can_shield: false,
          location: "Equipo rival",
          pokemon: { ...pokemon, nickname: "Rival" },
        },
      ],
    }),
  );
  await page.route(
    `**/v1/seasons/${sid}/shop/purchases/gift/redemptions`,
    async (route) => {
      if (route.request().method() === "OPTIONS")
        return route.fulfill({ status: 204, headers });
      attempts.push({
        key: route.request().headers()["idempotency-key"],
        body: route.request().postDataJSON(),
      });
      if (attempts.length === 1)
        return reply(
          route,
          { detail: { code: "TEMPORARILY_UNAVAILABLE" } },
          503,
        );
      used = true;
      return reply(route, {
        redemption_id: "receipt",
        physical_effect_status: "not_required",
      });
    },
  );
  await login(page);
  await navigate(page, "Tienda");
  await expect(page.getByText("Vale de recompensa")).toBeVisible();
  await page.getByRole("button", { name: "Canjear", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Pokémon objetivo" }).locator("option"),
  ).toHaveCount(2);
  await expect(page.getByText(/cambio físico/)).toHaveCount(0);
  await page
    .getByRole("combobox", { name: "Pokémon objetivo" })
    .selectOption("eligible");
  await page.getByRole("button", { name: "Confirmar canje" }).click();
  await expect(
    page.getByRole("button", { name: "Reintentar la misma solicitud" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Confirmar canje" }),
  ).toBeDisabled();
  expect(attempts).toHaveLength(1);
  await page
    .getByRole("button", { name: "Reintentar la misma solicitud" })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(attempts).toHaveLength(2);
  expect(attempts[1]).toEqual(attempts[0]);
  expect(attempts[0].body).toEqual({ pokemon_entity_id: "eligible" });
  expect(attempts[0].key).toBeTruthy();
});

test("admin persists prospective observed-save rewards with current rule revisions", async ({
  page,
}) => {
  const commands = await fixture(page);
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Configuración", exact: true }).click();
  await expect(page.getByLabel("Monedas por medalla")).toHaveValue("4");
  await expect(page.getByLabel("Monedas por vencer al Campeón")).toHaveValue(
    "12",
  );
  for (const [label, value] of [
    ["Monedas por medalla", "7"],
    ["Monedas por vencer al Campeón", "20"],
  ])
    await page.getByLabel(label, { exact: true }).fill(value);
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  await expect
    .poll(() => commands.at(-1)?.path)
    .toBe(`/v1/admin/seasons/${sid}/rules`);
  expect(commands.at(-1)?.body).toEqual({
    expected_revision: 0,
    expected_config_revision: 2,
    badge_reward_coins: 7,
    game_completion_reward_coins: 20,
  });
});
