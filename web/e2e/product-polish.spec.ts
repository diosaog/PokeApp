import { test, expect } from "@playwright/test";
import { fixture, login, navigate, tid } from "./fixtures";

for (const width of [1440, 900, 390]) {
  test(`live public collection and bounded animation ${width}`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    const commands = await fixture(page);
    const requests: string[] = [],
      errors: string[] = [];
    page.on("request", (r) => requests.push(new URL(r.url()).pathname));
    page.on("pageerror", (e) => errors.push(e.message));
    await login(page);
    await navigate(page, "Entrenadores");
    await page.waitForLoadState("networkidle");
    requests.length = 0;
    await page.locator("a[href='/entrenadores/t4']").click();
    await expect(
      page.getByText("Aún no hay Team Lock.", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Equipo, cajas y muertos" }),
    ).toBeVisible();
    await expect(page.getByText("BLINDADO").first()).toBeVisible();
    await expect(page.getByText("REVIVIDO").first()).toBeVisible();
    await expect(page.getByText("ROBADO").first()).toBeVisible();
    await expect(page.locator(".live-collection-heading")).toContainText(
      "Revividos tras wipe: 2",
    );
    await expect(
      page.getByRole("button", { name: /Reserva · Caja 1/ }),
    ).toBeVisible();
    await page.locator(".party-panel").scrollIntoViewIfNeeded();
    await expect(page.locator(".party-slots img").first()).toHaveAttribute(
      "src",
      /animated.*gif/,
    );
    await expect(page.locator(".box-slots img").first()).toHaveAttribute(
      "src",
      /pokemon.*png/,
    );
    await page.getByRole("button", { name: /Reserva · Caja 1/ }).click();
    await expect(page.getByRole("dialog")).not.toContainText(
      /IVs|Habilidad|Naturaleza|Modesta/,
    );
    await expect(
      page.getByRole("dialog").locator(".pokemon-sprite"),
    ).toHaveAttribute("src", /animated.*gif/);
    await page.screenshot({
      path: info.outputPath(`public-detail-${width}.png`),
    });
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Caja siguiente" }).click();
    await expect(page.locator(".box-controls")).toContainText("Caja 8");
    await expect(page.locator(".dead-slots button")).toHaveCount(1);
    expect(
      requests.filter((p) => p.endsWith("/pc") || p.endsWith("/inventory")),
    ).toEqual([]);
    await page.screenshot({
      path: info.outputPath(`public-collection-${width}.png`),
      fullPage: true,
    });
    await navigate(page, "Entrenadores");
    await page.locator(`a[href='/entrenadores/${tid}']`).click();
    await expect(page.locator(".profile-inventory")).toContainText(
      "Inventario",
    );
    await expect(
      page
        .locator(".profile-inventory")
        .getByRole("button", { name: "Canjear" }),
    ).toBeVisible();
    await page
      .locator(".profile-inventory")
      .getByRole("button", { name: "Canjear" })
      .click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await page.locator(".profile-wipe summary").click();
    await expect(
      page.getByLabel("Cantidad de revividos tras wipe"),
    ).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`own-profile-${width}.png`),
      fullPage: true,
    });
    await navigate(page, "Tienda");
    await expect(
      page.getByRole("link", { name: "Abrir mi inventario →" }),
    ).toHaveAttribute("href", `/entrenadores/${tid}`);
    await expect(page.locator(".inventory-grid")).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    expect(commands).toEqual([]);
    expect(errors).toEqual([]);
  });
}

test("reduced motion stays static, and public unknown/error never invents boxes", async ({
  page,
}) => {
  await fixture(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await login(page);
  await navigate(page, "Entrenadores");
  await page.locator("a[href='/entrenadores/t4']").click();
  await expect(page.locator(".party-slots img").first()).toHaveAttribute(
    "src",
    /pokemon.*png/,
  );
  expect(
    await page
      .locator(".workspace")
      .evaluate((e) => getComputedStyle(e, "::after").animationName),
  ).toBe("none");
  await page.route("**/trainers/t4/collection", (route) =>
    route.fulfill({
      json: {
        status: "no_current_save",
        pokemon: [],
        revived_after_wipe: null,
      },
    }),
  );
  await login(page);
  await navigate(page, "Entrenadores");
  await page.locator("a[href='/entrenadores/t4']").click();
  await expect(
    page.getByText(
      "Este entrenador todavía no tiene una partida disponible para consulta.",
    ),
  ).toBeVisible();
  await expect(page.locator(".collection")).toHaveCount(0);
  await expect(page.locator(".live-collection-heading")).toContainText(
    "Sin observar",
  );
  await page.route("**/trainers/t4/collection", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: { code: "READ_UNAVAILABLE" } },
    }),
  );
  await login(page);
  await navigate(page, "Entrenadores");
  await page.locator("a[href='/entrenadores/t4']").click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.locator(".collection")).toHaveCount(0);
});

test("Home team animates only the visible party and respects reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await fixture(page);
  await login(page);
  await page.locator(".home-party").scrollIntoViewIfNeeded();
  await expect(
    page.locator(".home-sprites .pokemon-sprite").first(),
  ).toHaveAttribute("src", /animated.*gif/);
  expect(await page.locator(".home-sprites .pokemon-sprite").count()).toBe(6);
  expect(await page.locator(".box-slots").count()).toBe(0);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(
    page.locator(".home-sprites .pokemon-sprite").first(),
  ).toHaveAttribute("src", /pokemon.*png/);
});
