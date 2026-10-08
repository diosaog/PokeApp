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
      page.getByRole("button", { name: "Canjear", exact: true }),
    ).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(
      reads
        .filter((path) => path.startsWith(`/v1/read/seasons/${sid}/`))
        .sort(),
    ).toEqual([
      `/v1/read/seasons/${sid}/inventory`,
      `/v1/read/seasons/${sid}/shop`,
    ]);
    expect(reads).not.toContain("/v1/read/trainers");
    await page.getByRole("button", { name: "Canjear", exact: true }).click();
    const targets = page.getByRole("combobox", { name: "Pokémon objetivo" });
    await expect(targets.locator("option")).toHaveCount(7);
    await expect(targets).not.toContainText("Objetivo 0");
    await expect(targets).toContainText("Objetivo 1 · Entrenador");
    await targets.selectOption("entity-1");
    const response = page.waitForResponse(
      (r) => new URL(r.url()).pathname === "/v1/read/trainers",
    );
    releaseNames();
    await response;
    await expect(targets).toContainText(
      namesAvailable ? "Objetivo 1 · Lucía" : "Objetivo 1 · Entrenador",
    );
    await expect(targets).toContainText("Objetivo 6 · Entrenador");
    await expect(targets).toHaveValue("entity-1");
    await expect(
      page.getByRole("button", { name: "Confirmar canje" }),
    ).toBeEnabled();
    expect(reads.filter((path) => path === "/v1/read/trainers")).toHaveLength(
      1,
    );
    expect(reads.some((path) => path.endsWith("/overview"))).toBe(false);
    if (namesAvailable) {
      await page.getByRole("button", { name: "Cerrar", exact: true }).click();
      await page.getByRole("button", { name: "Canjear", exact: true }).click();
      await expect(targets).toContainText("Objetivo 1 · Lucía");
      expect(reads.filter((path) => path === "/v1/read/trainers")).toHaveLength(
        1,
      );
    }
  });
}
