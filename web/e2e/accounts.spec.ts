import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, tid } from "./fixtures";

async function accountRoutes(page: Page, { empty = false, admin = true } = {}) {
  await fixture(page);
  const calls: { path: string; body: unknown; key: string | undefined }[] = [];
  let name = "Antonio",
    revision = 0,
    photo: string | null = null,
    enabled = true;
  await page.route("**/v1/**", async (route) => {
    const req = route.request(),
      url = new URL(req.url()),
      path = url.pathname;
    const json = (value: unknown) =>
      route.fulfill({
        json: value,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store",
        },
      });
    if (req.method() === "OPTIONS")
      return route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
          "Access-Control-Allow-Headers":
            "Authorization,Content-Type,Idempotency-Key",
        },
      });
    if (path === "/v1/auth/account-capabilities")
      return json({ enabled: true });
    if (path === "/v1/me")
      return json({
        trainer_id: tid,
        display_name: name,
        is_admin: admin,
        globally_enabled: true,
      });
    if (empty && path === "/v1/read/seasons")
      return json({ items: [], offset: 0, has_more: false });
    if (path === "/v1/auth/register") {
      calls.push({
        path,
        body: req.postDataJSON(),
        key: req.headers()["idempotency-key"],
      });
      return json({ trainer_id: tid, status: "registered" });
    }
    if (path === "/v1/accounts")
      return json({
        items: [
          { trainer_id: tid, display_name: name, photo_url: photo, revision },
          {
            trainer_id: "t4",
            display_name: "Elena",
            photo_url: null,
            revision: null,
          },
        ],
        has_more: false,
        offset: 0,
      });
    if (path.startsWith("/v1/accounts/"))
      return json({
        trainer_id: path.split("/").pop(),
        display_name: path.endsWith(tid) ? name : "Elena",
        photo_url: path.endsWith(tid) ? photo : null,
        revision: path.endsWith(tid) ? revision : null,
      });
    if (path === "/v1/account/name") {
      const body = req.postDataJSON();
      calls.push({ path, body, key: req.headers()["idempotency-key"] });
      name = body.display_name;
      revision++;
      return json({ trainer_id: tid, revision });
    }
    if (path === "/v1/account/photo") {
      calls.push({
        path,
        body: "image bytes",
        key: req.headers()["idempotency-key"],
      });
      photo = "/visuals/v1/trainers/ANTO.png";
      revision++;
      return json({ trainer_id: tid, revision });
    }
    if (path === "/v1/account/pin") {
      calls.push({
        path,
        body: "redacted",
        key: req.headers()["idempotency-key"],
      });
      return json({ status: "changed", sign_in_required: true });
    }
    if (path === "/v1/admin/accounts")
      return json({
        items: [
          {
            trainer_id: tid,
            display_name: name,
            globally_enabled: true,
            is_admin: true,
            revision,
            provisioned: true,
          },
          {
            trainer_id: "t4",
            display_name: "Elena",
            globally_enabled: enabled,
            is_admin: false,
            revision: 0,
            provisioned: true,
          },
        ],
        has_more: false,
        offset: 0,
      });
    if (path === "/v1/admin/accounts/t4/status") {
      const body = req.postDataJSON();
      enabled = body.enabled;
      calls.push({ path, body, key: req.headers()["idempotency-key"] });
      return json({ trainer_id: "t4", revision: 1, globally_enabled: enabled });
    }
    return route.fallback();
  });
  return calls;
}

for (const width of [1440, 390])
  test(`account registration and independent profile ${width}`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    const calls = await accountRoutes(page, { empty: true, admin: false });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("/");
    await page
      .getByRole("button", { name: "Crear cuenta", exact: true })
      .click();
    await page.getByLabel("Nombre de entrenador").fill("Antonio");
    await page.getByLabel("PIN de cuatro cifras").fill("0017");
    await page.getByLabel("Repetir PIN", { exact: true }).fill("0017");
    await page
      .getByLabel("Código de acceso a la App")
      .fill("fixture-invitation");
    await page
      .getByRole("button", { name: "Crear cuenta", exact: true })
      .click();
    await expect(
      page.getByText("Cuenta creada.", { exact: false }),
    ).toBeVisible();
    await page.getByLabel("PIN", { exact: true }).fill("0017");
    await page.getByRole("button", { name: "Entrar a PokeApp" }).click();
    await expect(page.getByRole("banner")).toBeVisible();
    await navigate(page, "Entrenadores");
    await page
      .locator(`a[href='/entrenadores/${tid}']`)
      .filter({ hasText: "Ver perfil" })
      .click();
    await expect(
      page.getByText("Cuenta de entrenador.", { exact: false }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Editar mi perfil", exact: true })
      .click();
    await page.getByLabel("Nombre de entrenador").fill("Antonio Nuevo");
    await page.getByRole("button", { name: "Guardar nombre" }).click();
    await expect(
      page.getByRole("heading", { name: "Antonio Nuevo", exact: true }),
    ).toBeVisible();
    await page.getByLabel("Foto de perfil").setInputFiles({
      name: "portrait.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j2ioAAAAASUVORK5CYII=",
        "base64",
      ),
    });
    await page.getByRole("button", { name: "Guardar foto" }).click();
    await expect(page.locator("main .trainer-photo img")).toHaveAttribute(
      "src",
      "/visuals/v1/trainers/ANTO.png",
    );
    await page.screenshot({
      path: info.outputPath(`profile-${width}.png`),
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.getByLabel("PIN actual").fill("0017");
    await page.getByLabel("Nuevo PIN", { exact: true }).fill("0028");
    await page.getByLabel("Repetir nuevo PIN").fill("0028");
    await page
      .getByRole("button", { name: "Cambiar PIN", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Entrar a PokeApp" }),
    ).toBeVisible();
    expect(calls.map((c) => c.path)).toEqual([
      "/v1/auth/register",
      "/v1/account/name",
      "/v1/account/photo",
      "/v1/account/pin",
    ]);
    expect(errors).toEqual([]);
  });

test("existing season collection and Admin account confirmation remain separate", async ({
  page,
}) => {
  const calls = await accountRoutes(page);
  await login(page);
  await navigate(page, "Entrenadores");
  await page.locator("a[href='/entrenadores/t4']").click();
  await expect(
    page.getByRole("heading", { name: "Equipo, cajas y muertos" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Editar mi perfil" }),
  ).toHaveCount(0);
  await expect(page.getByText("BLINDADO").first()).toBeVisible();
  await navigate(page, "Cuentas");
  const disable = page.getByRole("button", { name: "Deshabilitar cuenta" });
  await expect(disable.first()).toBeDisabled();
  await disable.last().click();
  expect(calls).toHaveLength(0);
  await page
    .getByRole("button", { name: "Confirmar cambio de acceso" })
    .click();
  await expect(page.getByText("Deshabilitada", { exact: true })).toBeVisible();
  expect(calls).toHaveLength(1);
  expect(calls[0].path).toBe("/v1/admin/accounts/t4/status");
});
