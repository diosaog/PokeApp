import { test, expect } from "@playwright/test";
import { fixture, login, navigate, sid, tid } from "./fixtures";

for (const width of [1440, 390]) {
  test(`item application states remain read-only at ${width}`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const commands = await fixture(page);
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const statuses = [
      "PREPARED",
      "APPLIED_VERIFIED",
      "FAILED_RECOVERABLE",
      "RECOVERY_REQUIRED",
      "BLOCKED_UNCERTAIN",
    ];
    const headers = { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" };
    await page.route(`**/v1/read/seasons/${sid}/inventory`, (route) =>
      route.fulfill({
        headers,
        // The API projects each purchase's physical state into the inventory.
        json: {
          physical_items: true,
          purchases: statuses.map((status, i) => ({
            id: `item-${i}`,
            shop_item_id: `catalog-${i}`,
            item_name: `Revivir Pokémon ${i + 1}`,
            item_code: "revivir_pokemon",
            acquisition_type: "paid",
            status: i === 1 ? "used" : "pending",
            physical_state: status,
            total_price: 12,
            purchased_at: "2026-10-25T10:00:00Z",
          })),
          targets: [],
        },
      }),
    );
    await page.route(`**/v1/launcher/seasons/${sid}/item-uses`, (route) =>
      route.fulfill({
        headers,
        json: {
          physical_application_enabled: false,
          items: statuses.map((status, i) => ({
            purchase_id: `item-${i}`,
            season_id: sid,
            trainer_id: tid,
            status,
          })),
        },
      }),
    );
    await login(page);
    await navigate(page, "Tienda");
    await page.getByRole("link", { name: "Abrir mi inventario →" }).click();
    for (const label of [
      "Aplicación pendiente",
      "Aplicación verificada",
      "Error recuperable",
      "Recuperación necesaria",
      "Operación bloqueada",
    ])
      await expect(page.getByText(label, { exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Canjear", exact: true }),
    ).toHaveCount(0);
    expect(
      commands.filter(
        (c) => c.path.includes("redemptions") || c.path.includes("item-use"),
      ),
    ).toHaveLength(0);
    expect(errors).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`inventory-${width}.png`),
      fullPage: true,
    });
  });
}
