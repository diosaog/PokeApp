// Phase27B visual review: every real route at desktop and phone width, with the
// synthetic fixture only. Screenshots go to POKEAPP_GALLERY_DIR (outside git).
import { test, expect } from "@playwright/test";
import { fixture, login, tid } from "./fixtures";

const routes: [string, string][] = [
  ["inicio", "/"],
  ["liga", "/liga"],
  ["batallas", "/battle"],
  ["copa", "/copa"],
  ["entrenadores", "/entrenadores"],
  ["scouting", "/entrenadores/scouting"],
  ["perfil-inventario", `/entrenadores/${tid}`],
  ["pc", "/pc"],
  ["tienda", "/tienda"],
  ["hall", "/hall"],
  ["juicios", "/juicios"],
  ["saves", "/saves"],
  ["admin", "/admin"],
];
const out = process.env.POKEAPP_GALLERY_DIR;

for (const width of [1440, 390]) {
  test(`design gallery at ${width}px`, async ({ page }) => {
    test.skip(!out, "set POKEAPP_GALLERY_DIR to capture the gallery");
    await page.setViewportSize({ width, height: width > 600 ? 900 : 844 });
    await fixture(page);
    await page.goto("/");
    await page.screenshot({ path: `${out}/${width}-00-login.png` });
    await login(page);
    for (const [index, [name, path]] of routes.entries()) {
      // Client-side navigation keeps the in-memory session, like a user click.
      await page.evaluate((to) => {
        window.history.pushState({}, "", to);
        window.dispatchEvent(new PopStateEvent("popstate"));
      }, path);
      await expect(page.locator("main#main")).toBeVisible();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(450);
      await page.screenshot({
        path: `${out}/${width}-${String(index + 1).padStart(2, "0")}-${name}.png`,
        fullPage: true,
      });
    }
    await page.evaluate(() => {
      window.history.pushState({}, "", "/tienda");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    const buy = page.getByRole("button", { name: "Comprar" }).first();
    if (await buy.isEnabled()) {
      await buy.click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.waitForTimeout(300);
      await page.screenshot({ path: `${out}/${width}-20-tienda-compra.png` });
    }
  });
}

// Production has accounts and registration on: the screens only that mode shows
// (registration, Cuentas), the not-found route and the phone menu.
for (const width of [1440, 390]) {
  test(`design gallery with accounts at ${width}px`, async ({ page }) => {
    test.skip(!out, "set POKEAPP_GALLERY_DIR to capture the gallery");
    await page.setViewportSize({ width, height: width > 600 ? 900 : 844 });
    await fixture(page);
    await page.route("**/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      const json = (value: unknown) =>
        route.fulfill({
          json: value,
          headers: { "Access-Control-Allow-Origin": "*" },
        });
      if (path === "/v1/auth/account-capabilities")
        return json({
          enabled: true,
          registration_enabled: true,
          renewal_enabled: true,
        });
      if (path === "/v1/admin/accounts")
        return json({
          items: [
            {
              trainer_id: tid,
              display_name: "Antonio",
              globally_enabled: true,
              is_admin: true,
              revision: 0,
              provisioned: true,
            },
            {
              trainer_id: "t4",
              display_name: "Elena",
              globally_enabled: true,
              is_admin: false,
              revision: 0,
              provisioned: true,
            },
          ],
          has_more: false,
          offset: 0,
        });
      return route.fallback();
    });
    await page.goto("/");
    await page
      .getByRole("button", { name: "Crear cuenta", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Crea tu cuenta de entrenador" }),
    ).toBeVisible();
    await page.screenshot({ path: `${out}/${width}-30-registro.png` });
    await login(page);
    for (const [name, path] of [
      ["31-cuentas", "/admin/cuentas"],
      ["32-no-encontrada", "/ruta-inexistente"],
    ]) {
      await page.evaluate((to) => {
        window.history.pushState({}, "", to);
        window.dispatchEvent(new PopStateEvent("popstate"));
      }, path);
      await expect(page.locator("main#main")).toBeVisible();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(450);
      await page.screenshot({
        path: `${out}/${width}-${name}.png`,
        fullPage: true,
      });
    }
    const menu = page.getByRole("button", { name: "Abrir navegación" });
    if (await menu.isVisible()) {
      await menu.click();
      await page.waitForTimeout(300);
    }
    await expect(
      page
        .getByRole("navigation", { name: "Principal" })
        .getByRole("link", { name: "Cuentas", exact: true }),
    ).toBeVisible();
    await page.screenshot({ path: `${out}/${width}-33-menu.png` });
  });
}
