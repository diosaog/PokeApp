import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, tid } from "./fixtures";

// Owner 2026-11-18: every popup is one large, ordered panel with a fixed
// heading, a body that scrolls on its own and comfortable choices.
async function fits(page: Page) {
  return page.getByRole("dialog").evaluate((dialog) => {
    const box = dialog.getBoundingClientRect();
    const heading = dialog.querySelector(".dialog-heading")!;
    const body = dialog.querySelector(".dialog-body")!;
    return {
      inside:
        box.left >= 0 &&
        box.top >= 0 &&
        box.right <= innerWidth + 1 &&
        box.bottom <= innerHeight + 1,
      width: box.width,
      headingFirst: dialog.firstElementChild === heading,
      bodyScrolls: getComputedStyle(body).overflowY === "auto",
      pageScrollsSideways: document.documentElement.scrollWidth > innerWidth + 1,
    };
  });
}

for (const width of [1440, 390]) {
  test(`popups are large, ordered panels at ${width}`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const commands = await fixture(page);
    await login(page);

    // Canjear: the Pokémon chooser is the wide size, with big cards.
    await navigate(page, "Entrenadores");
    await page.locator(`a[href='/entrenadores/${tid}']`).click();
    await page
      .locator(".profile-inventory")
      .getByRole("button", { name: "Canjear" })
      .first()
      .click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    let layout = await fits(page);
    expect(layout).toMatchObject({
      inside: true,
      headingFirst: true,
      bodyScrolls: true,
      pageScrollsSideways: false,
    });
    if (width > 1000) expect(layout.width).toBeGreaterThan(1000);
    await page.screenshot({ path: info.outputPath(`canjear-${width}.png`) });
    const card = dialog.locator(".pokemon-selector-card:not(:disabled)").first();
    if (await card.count()) {
      await card.click();
      await expect(dialog.locator(".selector-confirmation")).toBeVisible();
      await page.screenshot({
        path: info.outputPath(`canjear-confirm-${width}.png`),
      });
    }
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);

    // Comprar: a medium confirmation with its price and one clear action.
    await navigate(page, "Tienda");
    await page.getByRole("button", { name: /Comprar/ }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    layout = await fits(page);
    expect(layout).toMatchObject({ inside: true, headingFirst: true });
    await page.screenshot({ path: info.outputPath(`comprar-${width}.png`) });
    await page.keyboard.press("Escape");
    expect(commands).toEqual([]);
  });
}
