import { test, expect } from "@playwright/test";
import { fixture, sid, tid } from "./fixtures";

// Cold deep links matter: navigating via Home would warm the overview cache.
for (const namesAvailable of [true, false]) {
  test(`Shop reads only its own data, then one names list on redemption (${namesAvailable ? "available" : "unavailable"})`, async ({
    page,
  }) => {
    await fixture(page);
    const reads: string[] = [];
    // Development StrictMode may cancel its first mount's request. Count
    // completed responses; hosted cold-context evidence uses the production build.
    page.on("response", (response) => {
      const request = response.request();
      if (request.method() === "GET" && request.url().includes("/v1/"))
        reads.push(new URL(request.url()).pathname);
    });
    const headers = { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" };
    await page.route(`**/v1/read/seasons/${sid}/inventory`, (route) =>
      route.fulfill({
        headers,
        json: {
          purchases: [
            {
              id: "gift",
              shop_item_id: "steal",
              item_code: "robar_pokemon",
              item_name: "Robo",
              status: "pending",
              acquisition_type: "purchase",
              total_price: 30,
              purchased_at: "2026-10-07T12:00:00Z",
            },
          ],
          targets: Array.from({ length: 7 }, (_, i) => ({
            pokemon_entity_id: `entity-${i}`,
            trainer_id:
              i === 0 ? tid : i === 6 ? "missing-name" : "rival-trainer",
            visibility: i === 0 ? "own" : "public_team_lock",
            can_shield: false,
            location: `Equipo ${i}`,
            pokemon: {
              species: "Eevee",
              nickname: `Objetivo ${i}`,
              item: "",
              is_shiny: false,
            },
          })),
        },
      }),
    );
    let releaseNames!: () => void;
    const pendingNames = new Promise<void>((resolve) => {
      releaseNames = resolve;
    });
    await page.route("**/v1/read/trainers", async (route) => {
      await pendingNames;
      await route.fulfill({
        headers,
        status: namesAvailable ? 200 : 403,
        json: namesAvailable
          ? [
              { id: tid, display_name: "Antonio" },
              { id: "rival-trainer", display_name: "Lucía" },
            ]
          : { detail: { code: "FORBIDDEN" } },
      });
    });
    await page.goto("/tienda");
    await page.getByLabel("Entrenador", { exact: true }).fill("Antonio");
    await page.getByLabel("PIN", { exact: true }).fill("1234");
    await page.getByRole("button", { name: "Entrar a PokeApp" }).click();
    await expect(
      page.getByRole("link", { name: "Abrir mi inventario →" }),
    ).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(
      reads
        .filter((path) => path.startsWith(`/v1/read/seasons/${sid}/`))
        .sort(),
    ).toEqual([`/v1/read/seasons/${sid}/shop`]);
    expect(reads).not.toContain("/v1/read/trainers");
    await page.getByRole("link", { name: "Abrir mi inventario →" }).click();
    await expect(
      page.getByRole("button", { name: "Canjear", exact: true }),
    ).toBeVisible();
    await page.waitForLoadState("networkidle");
    reads.length = 0;
    await page.getByRole("button", { name: "Canjear", exact: true }).click();
    // A robbery first picks the rival, then one of their public Pokémon.
    // Rivals come from the public targets (never your own), so they show
    // before the names list arrives and stay when it is unavailable.
    const rivals = page
      .getByRole("dialog", { name: "Elige un entrenador" })
      .locator(".trainer-selector-card");
    await expect(rivals).toHaveCount(2);
    await expect(rivals.nth(0)).toContainText("Entrenador");
    const response = page.waitForResponse(
      (r) => new URL(r.url()).pathname === "/v1/read/trainers",
    );
    releaseNames();
    await response;
    await expect(rivals.nth(0)).toContainText(
      namesAvailable ? "Lucía" : "Entrenador",
    );
    await expect(rivals.nth(1)).toContainText("Entrenador");
    await rivals.nth(0).click();
    const cards = page.locator(".pokemon-selector-card");
    await expect(cards).toHaveCount(5);
    await expect(page.locator(".pokemon-selector")).not.toContainText(
      "Objetivo 0",
    );
    await cards.filter({ hasText: "Objetivo 1" }).click();
    await expect(page.getByRole("button", { name: "Sí, robar" })).toBeEnabled();
    await expect(page.locator(".selector-confirmation")).toContainText(
      namesAvailable ? "de Lucía" : "de Entrenador",
    );
    expect(reads.filter((path) => path === "/v1/read/trainers")).toHaveLength(
      1,
    );
    expect(reads.some((path) => path.endsWith("/overview"))).toBe(false);
    if (namesAvailable) {
      await page.getByRole("button", { name: "Cerrar", exact: true }).click();
      await page.getByRole("button", { name: "Canjear", exact: true }).click();
      await expect(rivals.nth(0)).toContainText("Lucía");
      expect(reads.filter((path) => path === "/v1/read/trainers")).toHaveLength(
        1,
      );
    }
  });
}
