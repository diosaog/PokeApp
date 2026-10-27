import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, tid } from "./fixtures";

// Phase 28: one navigation for web and Launcher. Inside the Launcher (its user
// agent marker) the sidebar is the browser's; items, deliveries and saves open
// the Launcher's native views through fixed routes the Launcher watches.
const launcherAgent =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 PokeAppLauncher/0.26.0";

async function sidebar(page: Page) {
  return page
    .getByRole("navigation", { name: "Principal" })
    .locator(".nav-group-label")
    .allTextContents();
}

test("the browser sidebar has no desktop group and old links land in Saves y Launcher", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1365, height: 900 });
  await fixture(page);
  await login(page);
  const groups = await sidebar(page);
  expect(groups).not.toContain("ESCRITORIO");
  // In-app navigation (a reload would end the memory-only session).
  await page.evaluate(() => {
    history.pushState({}, "", "/escritorio/copias");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  await expect(page).toHaveURL(/\/saves$/);
  await expect(
    page.getByRole("heading", { name: "Saves y Launcher" }),
  ).toBeVisible();
  for (const tab of ["Copias de seguridad", "Launcher", "Mis partidas"]) {
    await page.getByRole("button", { name: tab, exact: true }).click();
    await expect(
      page.getByRole("button", { name: tab, exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
  }
});

test.describe("inside PokeApp Launcher", () => {
  test.use({ userAgent: launcherAgent });
  test("same sidebar, contextual doors and only data-free bridge requests", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1365, height: 900 });
    // The Launcher intercepts these; a plain browser must not load them.
    const bridge: string[] = [];
    await page.route("**/__launcher/**", (route) => {
      bridge.push(new URL(route.request().url()).pathname);
      // 204: the document stays, as when the Launcher cancels the navigation.
      return route.fulfill({ status: 204 });
    });
    await fixture(page);
    await login(page);
    const groups = await sidebar(page);
    expect(groups).not.toContain("ESCRITORIO");
    expect(
      await page
        .getByRole("navigation", { name: "Principal" })
        .getByRole("link", { name: "Saves y Launcher", exact: true })
        .getAttribute("href"),
    ).toBe("/saves");
    await navigate(page, "Entrenadores");
    await page.locator(`a[href='/entrenadores/${tid}']`).click();
    const items = page
      .locator(".profile-inventory")
      .getByRole("link", { name: "Añadir a la bolsa" });
    await expect(items).toHaveCount(2);
    expect(
      await items.evaluateAll((a) => a.map((e) => e.getAttribute("href"))),
    ).toEqual([
      "/escritorio/objetos/rare_candy",
      "/escritorio/objetos/heart_scale",
    ]);
    await page.screenshot({
      path: test.info().outputPath("launcher-inventory.png"),
    });
    // Only the fixed session path, with no query, token or data.
    expect(bridge).toContain("/__launcher/session");
    expect(bridge.every((path) => path === "/__launcher/session")).toBe(true);
    expect(await page.evaluate(() => sessionStorage.length)).toBe(0);
    expect(
      await page.evaluate(() =>
        Object.keys(localStorage).filter((k) => /token|session|pin/i.test(k)),
      ),
    ).toEqual([]);
  });
});
