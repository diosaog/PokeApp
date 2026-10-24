import { test, expect } from "@playwright/test";
import { fixture } from "./fixtures";

for (const width of [1440, 390]) {
  test(`controlled initial registration at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await fixture(page);
    await page.route("**/v1/auth/account-capabilities", (route) =>
      route.fulfill({
        json: {
          enabled: true,
          registration_enabled: true,
          renewal_enabled: true,
          bootstrap_required: true,
        },
      }),
    );
    let body: Record<string, string> | undefined;
    await page.route("**/v1/auth/register", (route) => {
      body = route.request().postDataJSON();
      return route.fulfill({
        json: {
          status: "registered",
          trainer_id: "10000000-0000-0000-0000-000000000001",
        },
      });
    });
    await page.goto("/");
    await page
      .getByRole("button", { name: "Crear cuenta", exact: true })
      .click();
    await page.getByLabel("Nombre de entrenador").fill("Bootstrap Fixture");
    await page.getByLabel("PIN de cuatro cifras").fill("1256");
    await page.getByLabel("Repetir PIN").fill("1256");
    await page
      .getByLabel("Código de acceso a la App")
      .fill("fictional-invitation");
    await page
      .getByLabel("Autorización de alta inicial")
      .fill("fictional-bootstrap");
    await expect(
      page.getByRole("button", { name: "Crear cuenta", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page
      .getByRole("button", { name: "Crear cuenta", exact: true })
      .click();
    await expect.poll(() => body?.bootstrap_token).toBe("fictional-bootstrap");
    expect(body?.access_code).toBe("fictional-invitation");
    expect(
      await page.evaluate(() => Object.values(sessionStorage).join()),
    ).not.toContain("fictional-bootstrap");
  });
}
