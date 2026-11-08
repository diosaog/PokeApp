import { test, expect, type Page } from "@playwright/test";
import { fixture, login, sid } from "./fixtures";

// Administración › Avisos with synthetic data: what changed, why it is
// suspicious and the administrator's decision. Screenshots are optional.
const api = "http://127.0.0.1:8000";
const notices = `/v1/admin/seasons/${sid}/notices`;
const out = process.env.POKEAPP_GALLERY_DIR;

const side = (revision: number, at: string) => ({
  save_file_id: "99999999-9999-4999-8999-99999999999" + revision,
  sha256: "f4".repeat(32),
  uploaded_at: at,
  revision,
});
const compared = {
  previous: side(4, "2026-11-07T18:21:00Z"),
  current: side(5, "2026-11-08T10:02:00Z"),
  inventory_status: "compared",
};
const summary =
  "Comparar partidas no prueba el origen: un cambio externo que deje el mismo resultado que una acción legítima no se puede distinguir.";
const ivReason =
  "Los IVs reales no cambian jugando y no consta ninguna Chapa aplicada por PokeApp que lo explique.";
const stats: [string, string, number][] = [
  ["hp", "PS", 12],
  ["atk", "Ataque", 7],
  ["defense", "Defensa", 21],
  ["spa", "At. Esp.", 3],
  ["spd", "Def. Esp.", 16],
  ["spe", "Velocidad", 25],
];
const ivChanges = stats.map(([id, name, before]) => ({
  field: `iv_${id}`,
  label: `IV de ${name}`,
  kind: "iv",
  before,
  after: 31,
  severity: "alta",
  reason: ivReason,
  holders: [],
}));
const pokemon = {
  key: "1:2",
  species: "Pokémon #448",
  form: 0,
  nickname: "Aura",
  level: 42,
  gender: "M",
  shiny: false,
  is_egg: false,
  location: { source: "box", box: 3, slot: 12 },
  previous_location: null,
  previous_species: null,
  item: "Item #234",
};
function overview(status: string) {
  const common = {
    trainer_id: "t1",
    display_name: "Samu",
    game: "OR",
    detected_at: "2026-11-08T10:02:30Z",
    updated_at: "2026-11-08T10:02:30Z",
    origin: "desconocido",
    summary,
    operations: [],
    compared,
    detector_version: 1,
    events: [],
  };
  return {
    season_id: sid,
    season_status: "active",
    activated_at: "2026-11-08T09:00:00Z",
    pending_saves: 1,
    analyzed_saves: 12,
    last_analyzed_at: "2026-11-08T10:02:30Z",
    trainers: [
      { trainer_id: "t1", display_name: "Samu" },
      { trainer_id: "t2", display_name: "Aaron" },
    ],
    notices: [
      {
        ...common,
        id: "11111111-1111-4111-8111-111111111111",
        category: "pokemon",
        severity: "alta",
        status: "pending",
        title: "Los seis IVs han pasado a 31",
        pokemon,
        changes: [
          ...ivChanges,
          {
            field: "nature",
            label: "Naturaleza",
            kind: "nature",
            before: "Nature #3",
            after: "Nature #15",
            severity: "alta",
            reason:
              "La naturaleza no cambia jugando y no consta ninguna Menta aplicada por PokeApp.",
            holders: [],
          },
        ],
      },
      {
        ...common,
        id: "22222222-2222-4222-8222-222222222222",
        display_name: "Aaron",
        trainer_id: "t2",
        category: "objetos",
        severity: "media",
        status,
        origin: "parcialmente justificado",
        title: "2 objetos con aumento sin verificar",
        pokemon: null,
        operations: [
          {
            kind: "delivery",
            label: "Cápsula Habilidad",
            at: "2026-11-08T09:40:00Z",
            detail:
              "Entrega de una compra de la Tienda, auditada por el servidor.",
          },
        ],
        changes: [
          {
            field: "item_645",
            label: "Objeto",
            kind: "item",
            before: 0,
            after: 5,
            severity: "media",
            reason:
              "Solo 1 de las 5 unidades consta como entregada por PokeApp; el resto no tiene origen verificado.",
            item: "Item #645",
            delta: 5,
            justified: 1,
            unjustified: 4,
            holders: ["Aura"],
          },
          {
            field: "item_1",
            label: "Objeto",
            kind: "item",
            before: 0,
            after: 1,
            severity: "media",
            reason:
              "Sin compras, recompensas ni entregas registradas en PokeApp que lo expliquen.",
            item: "Item #1",
            delta: 1,
            justified: 0,
            unjustified: 1,
            holders: [],
          },
        ],
      },
      {
        ...common,
        id: "33333333-3333-4333-8333-333333333333",
        category: "pokemon",
        severity: "baja",
        status: "pending",
        title: "Especie modificada",
        pokemon: {
          ...pokemon,
          key: "3:4",
          species: "Pokémon #6",
          nickname: "",
          level: 18,
        },
        changes: [
          {
            field: "species",
            label: "Especie",
            kind: "species",
            before: "Pokémon #4",
            after: "Pokémon #6",
            severity: "baja",
            reason:
              "El cambio de especie no coincide con las evoluciones estándar; en una partida aleatorizada puede ser legítimo.",
            holders: [],
          },
        ],
      },
    ],
  };
}

async function open(page: Page) {
  const posts: { path: string; body: unknown }[] = [];
  let status = "pending";
  await fixture(page);
  const headers = {
    "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
    "Access-Control-Allow-Headers":
      "authorization,content-type,idempotency-key",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  };
  await page.route(`${api}${notices}**`, async (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS")
      return route.fulfill({ status: 204, headers });
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/summary"))
      return route.fulfill({
        status: 200,
        headers,
        json: { season_id: sid, pending: 3, pending_high: 1 },
      });
    if (request.method() === "POST") {
      posts.push({ path, body: request.postDataJSON() });
      status = "justified";
      return route.fulfill({
        status: 200,
        headers,
        json: overview(status).notices[1],
      });
    }
    return route.fulfill({ status: 200, headers, json: overview(status) });
  });
  await login(page);
  const menu = page.getByRole("button", { name: "Abrir navegación" });
  if (await menu.isVisible()) await menu.click();
  await page
    .getByRole("navigation", { name: "Principal" })
    .getByRole("link", { name: /^Avisos/ })
    .click();
  return posts;
}

for (const width of [1440, 390]) {
  test(`avisos explain the change and keep the decision at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const posts = await open(page);
    await expect(
      page.getByRole("heading", {
        name: "1 aviso de gravedad alta por revisar",
      }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: /Los seis IVs han pasado a 31/ })
      .click();
    await expect(page.getByText("IV de Ataque")).toBeVisible();
    await expect(page.getByText("+24")).toBeVisible();
    await page.waitForTimeout(600); // the meters finish their one animation
    if (out)
      await page.screenshot({
        path: `${out}/notices-${width}-ivs.png`,
        fullPage: true,
      });
    await page.getByRole("button", { name: /2 objetos con aumento/ }).click();
    await expect(
      page.getByText("Cápsula Habilidad", { exact: true }).first(),
    ).toBeVisible();
    if (out)
      await page.screenshot({
        path: `${out}/notices-${width}-objects.png`,
        fullPage: true,
      });
    await page.getByRole("button", { name: "Justificar" }).click();
    await page
      .getByRole("textbox")
      .fill("El entrenador confirma que las consiguió jugando");
    await page.getByRole("button", { name: "Guardar: Justificado" }).click();
    await expect.poll(() => posts.length).toBe(1);
    expect(posts[0].body).toEqual({
      status: "justified",
      note: "El entrenador confirma que las consiguió jugando",
    });
  });
}
