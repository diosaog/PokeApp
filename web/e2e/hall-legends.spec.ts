import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate } from "./fixtures";

// Hall de la Fama › Leyendas (2026-11-18): each past champion's portrait and
// moving team fit every width without horizontal scroll, and every Pokémon,
// alternate forms included, shows real art and moves. Synthetic API only.
// POKEAPP_SHOT_DIR=<dir> also saves screenshots for a design review.
const shots = process.env.POKEAPP_SHOT_DIR;

async function openHall(page: Page) {
  await fixture(page);
  await page.route("**/v1/read/hall?*", (route) =>
    route.fulfill({ json: { items: [], next_offset: null } }),
  );
  await login(page);
  await navigate(page, "Hall de la Fama");
  await expect(page.getByRole("heading", { name: "Leyendas" })).toBeVisible();
}

for (const [label, width, height] of [
  ["escritorio", 1440, 900],
  ["portátil", 1280, 800],
  ["móvil", 390, 844],
] as const) {
  test(`Leyendas: retratos y equipos en movimiento (${label})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    const gifs: string[] = [];
    page.on("response", (response) => {
      if (response.url().endsWith(".gif") && response.ok())
        gifs.push(new URL(response.url()).pathname);
    });
    await openHall(page);
    const cards = page.locator(".legend-card");
    await expect(cards).toHaveCount(5);
    await expect(page.locator(".legend-team .pokemon-sprite")).toHaveCount(30);
    await expect(page.locator(".legend-team .unresolved")).toHaveCount(0);
    // Every card scrolled into view starts its own animations, forms too.
    for (let i = 0; i < 5; i++) await cards.nth(i).scrollIntoViewIfNeeded();
    await expect
      .poll(() => gifs.filter((g) => g.includes("/forms/")).sort())
      .toEqual(
        expect.arrayContaining([
          "/visuals/animated/v2/forms/386-form-1.gif",
          "/visuals/animated/v2/forms/479-form-2.gif",
          "/visuals/animated/v2/forms/65-form-1.gif",
          "/visuals/animated/v2/forms/323-form-1.gif",
        ]),
      );
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    // A trainer's portrait never overlaps any of their titles.
    const showcases = page.locator(".legend-showcase");
    await expect(showcases).toHaveCount(2);
    for (let s = 0; s < 2; s++) {
      const portrait = await showcases
        .nth(s)
        .locator(".legend-champion")
        .boundingBox();
      for (const card of await showcases.nth(s).locator(".legend-card").all()) {
        const box = (await card.boundingBox())!;
        const overlaps =
          portrait!.x < box.x + box.width &&
          box.x < portrait!.x + portrait!.width &&
          portrait!.y < box.y + box.height &&
          box.y < portrait!.y + portrait!.height;
        expect(overlaps).toBe(false);
      }
    }
    if (shots) {
      await page.locator(".legends").scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      await page
        .locator(".legends")
        .screenshot({ path: `${shots}/hall-legends-${width}.png` });
    }
  });
}
