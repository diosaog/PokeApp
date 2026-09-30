import { test, expect } from "@playwright/test";
import { fixture, login, navigate, sid, cid } from "./fixtures";

test("long unbroken names fit desktop and mobile screens", async ({ page }) => {
  await fixture(page, true);
  await page.goto("/");
  await page.getByLabel("Entrenador", { exact: true }).fill("Antonio");
  await page.getByLabel("PIN", { exact: true }).fill("1234");
  await page.getByRole("button", { name: "Entrar a PokeApp" }).click();
  await expect(
    page.getByRole("heading", { name: /^A por la siguiente/ }),
  ).toBeVisible();
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    for (const name of [
      "Inicio",
      "Liga",
      "Battle",
      "Entrenadores",
      "Mi PC",
      "Tienda",
      "Copa",
      "Hall de la Fama",
      "Juicios",
      "Administración",
      "Saves y Launcher",
    ]) {
      await navigate(page, name);
      await expect(page.locator("main .loading")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        `${name} at ${viewport.width}`,
      ).toBe(true);
    }
  }
});

test("login, official league, Team Lock, PC dialog, purchase, admin CAS, Cup Bo3, Hall and logout", async ({
  page,
}) => {
  const commands = await fixture(page);
  await login(page);
  await expect(page.getByText("128", { exact: false }).first()).toBeVisible();
  await navigate(page, "Liga");
  await page.getByRole("button", { name: "J3", exact: true }).click();
  await expect(page.getByText("Oficial · revisión 1")).toBeVisible();
  await navigate(page, "Battle");
  await page.getByRole("button", { name: "Fijar mi equipo" }).click();
  await page.getByRole("button", { name: "Confirmar mi equipo" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(commands.at(-1)?.body).toEqual({ save_file_id: "save" });
  await navigate(page, "Mi PC");
  await page.getByRole("button", { name: /Aura/ }).first().click();
  await expect(
    page.getByRole("dialog").getByText("Foco interno"),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await navigate(page, "Tienda");
  await page
    .getByRole("button", { name: "Comprar", exact: true })
    .first()
    .click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Confirmar compra" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(commands.at(-1)?.key).toBeTruthy();
  expect(commands.at(-1)?.body).toEqual({
    item_id: "item",
    confirm_base_price: true,
  });
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Configuración", exact: true }).click();
  await page.getByLabel("Nombre", { exact: true }).fill("Liga revisada");
  await page.getByRole("button", { name: "Guardar nombre" }).click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(commands.at(-1)?.body).toEqual({
    name: "Liga revisada",
    expected_revision: 7,
  });
  await navigate(page, "Copa");
  await page.getByRole("link", { name: /Copa Equinoccio/ }).click();
  await page
    .getByLabel("Resultado Dúo Aurora / Dúo Eclipse")
    .selectOption("2:1");
  await page.getByRole("button", { name: "Guardar resultados" }).click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(commands.at(-1)?.body).toEqual({
    expected_revision: 4,
    results: [{ match_id: "cup-match", score_a: 2, score_b: 1 }],
  });
  await navigate(page, "Hall de la Fama");
  await expect(
    page.getByText("Antonio & Lucía", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Ver esta Copa" }),
  ).toHaveAttribute("href", `/copa/${cid}?season=${sid}`);
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(
    page.getByRole("button", { name: "Entrar a PokeApp" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => ({
      local: Object.keys(localStorage),
      session: Object.keys(sessionStorage),
    })),
  ).toEqual({ local: [], session: [] });
});
test("conflicts stay visible without silent CAS retry", async ({ page }) => {
  await fixture(page);
  await page.route("**/shop/purchases", (route) =>
    route.fulfill({
      status: 409,
      headers: {
        "Access-Control-Allow-Origin":
          route.request().headers()["origin"] || "http://127.0.0.1:5173",
      },
      json: { detail: { code: "INSUFFICIENT_FUNDS" } },
    }),
  );
  await login(page);
  await navigate(page, "Tienda");
  await page
    .getByRole("button", { name: "Comprar", exact: true })
    .first()
    .click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Confirmar compra" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "INSUFFICIENT_FUNDS",
  );
  await expect(page.getByRole("dialog")).toBeVisible();
});
test("admin can repair unused configuration and cancel provisional editing with CAS", async ({
  page,
}) => {
  const commands = await fixture(page);
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Configuración", exact: true }).click();
  await page.getByLabel("Versión a configurar").selectOption("config");
  await page
    .getByLabel("Nombre de versión", { exact: true })
    .fill("Base corregida");
  await page
    .getByLabel("Motivo de reemplazo")
    .fill("Ajustar el borrador antes de usarlo");
  await page
    .getByRole("button", { name: "Reemplazar versión sin usar" })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(commands.at(-1)?.path).toContain("/config/replace-unused");
  expect(commands.at(-1)?.body).toMatchObject({
    expected_config_revision: 2,
    expected_roster_revision: 3,
    division_sizes: { A: 2, B: 2 },
    reason: "Ajustar el borrador antes de usarlo",
  });
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await page
    .getByRole("button", { name: "Cancelar edición", exact: true })
    .click();
  await page
    .getByLabel("Motivo de cancelación")
    .fill("Revisar los enfrentamientos");
  await page
    .getByRole("button", { name: "Confirmar cancelación de edición" })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(commands.at(-1)?.body).toEqual({
    expected_revision: 2,
    reason: "Revisar los enfrentamientos",
  });
  await page
    .locator("main")
    .getByRole("link", { name: "Liga", exact: true })
    .click();
  await expect(page).toHaveURL(/\/liga$/);
  await expect(
    page.getByRole("button", { name: "GENERAL", exact: true }),
  ).toBeVisible();
});
test("inventory redemption and manual Discord verdict preserve IDs, revision and decimal points", async ({
  page,
}) => {
  const commands = await fixture(page);
  await login(page);
  await navigate(page, "Tienda");
  await page.getByRole("button", { name: "Canjear", exact: true }).click();
  await page.getByLabel("Pokémon objetivo").selectOption("confirmed-entity");
  await page.getByRole("button", { name: "Confirmar canje" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(commands.at(-1)?.body).toEqual({
    pokemon_entity_id: "confirmed-entity",
  });
  expect(commands.at(-1)?.path).toContain("/owned-purchase/redemptions");
  await navigate(page, "Juicios");
  await page.getByRole("button", { name: /Revisión de resultado/ }).click();
  await page
    .getByRole("button", { name: "Registrar decisión", exact: true })
    .click();
  const decision = page.getByRole("dialog", {
    name: "Registrar decisión de Discord",
    exact: true,
  });
  await decision
    .getByLabel("Resumen de la decisión")
    .fill("Acuerdo explícito de Discord");
  await decision.getByRole("checkbox", { name: "Reducción de puntos" }).check();
  await decision.getByLabel("Puntos exactos").fill("1.25");
  await decision
    .getByRole("button", { name: "Confirmar", exact: true })
    .click();
  await expect(decision).toHaveCount(0);
  expect(commands.at(-1)?.body).toEqual({
    expected_case_revision: 2,
    verdict: "guilty",
    decision_summary: "Acuerdo explícito de Discord",
    sanctions: [{ type: "points_reduction", amount: "1.25" }],
  });
});
for (const [label, width, height] of [
  ["desktop", 1440, 1000],
  ["laptop", 1280, 800],
  ["tablet", 768, 1024],
  ["mobile", 390, 844],
] as const) {
  test(`responsive ${label}: all feature layouts and screenshots`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height });
    await fixture(page);
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await login(page);
    for (const [name, file] of [
      ["Inicio", "home"],
      ["Liga", "league"],
      ["Battle", "battle"],
      ["Entrenadores", "trainers"],
      ["Mi PC", "pc"],
      ["Tienda", "shop"],
      ["Copa", "cup"],
      ["Hall de la Fama", "hall"],
      ["Juicios", "trials"],
      ["Administración", "admin"],
      ["Saves y Launcher", "saves"],
    ]) {
      if (name !== "Inicio") await navigate(page, name);
      await expect(page.locator("main h1")).toBeVisible();
      await expect(page.getByText("Cargando datos…")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBe(true);
      await page.screenshot({
        path: testInfo.outputPath(`${label}-${file}.png`),
        fullPage: true,
      });
    }
    expect(errors).toEqual([]);
  });
}
