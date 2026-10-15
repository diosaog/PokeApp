import { test, expect, type Page, type TestInfo } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";

// Opt-in: a real loopback API + disposable PostgreSQL, never intercepted routes.
const fixturePath = process.env.POKEAPP_PHASE13_FIXTURE;
const fixture = fixturePath
  ? JSON.parse(readFileSync(fixturePath, "utf8"))
  : {};
test.skip(!fixturePath, "Requires the isolated Phase13 API fixture");
test.describe.configure({ mode: "serial", timeout: 120_000 });
test.beforeEach(async ({ baseURL }) => {
  // Never send synthetic credentials or mutations to a hosted application.
  expect(["127.0.0.1", "localhost"]).toContain(new URL(baseURL!).hostname);
});

async function login(page: Page, name: string) {
  await page.goto("/");
  await page
    .getByLabel("Entrenador", { exact: true })
    .fill(`phase13-${name.toLowerCase()}`);
  await page.getByLabel("PIN", { exact: true }).fill("1313");
  await page.getByRole("button", { name: "Entrar a PokeApp" }).click();
  await expect(
    page.getByRole("heading", { name: `A por la siguiente, Staging ${name}.` }),
  ).toBeVisible();
  await page.evaluate(() => {
    (window as unknown as { phase13: string }).phase13 = "no-reload";
  });
}
async function navigate(page: Page, label: string) {
  const menu = page.getByRole("button", { name: "Abrir navegación" });
  if (await menu.isVisible()) await menu.click();
  await page
    .getByRole("navigation", { name: "Principal" })
    .getByRole("link", { name: label, exact: true })
    .click();
}
function monitor(page: Page) {
  const errors: string[] = [],
    requests: object[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => {
    if (r.url().includes("/v1/")) {
      requests.push({
        path: new URL(r.url()).pathname,
        method: r.request().method(),
        status: r.status(),
      });
      if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`);
    }
  });
  return async (info: TestInfo, label: string) => {
    expect(errors).toEqual([]);
    expect(
      await page.evaluate(
        () => (window as unknown as { phase13: string }).phase13,
      ),
    ).toBe("no-reload");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`${label}.png`),
      fullPage: true,
    });
    writeFileSync(
      info.outputPath("real-http-responses.json"),
      JSON.stringify(requests),
    );
    await info.attach("real-http-responses", {
      body: JSON.stringify(requests),
      contentType: "application/json",
    });
  };
}

test("Admin saves prospective reward rules and keeps rival projections public", async ({
  page,
}, info) => {
  const done = monitor(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "Admin");
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Configuración", exact: true }).click();
  await expect(
    page.getByLabel("Monedas por medalla", { exact: true }),
  ).toHaveValue("5");
  await page.getByLabel("Monedas por medalla", { exact: true }).fill("7");
  await page
    .getByLabel("Monedas por vencer al Campeón", { exact: true })
    .fill("15");
  const saved = page.waitForResponse(
    (r) => r.url().endsWith("/rules") && r.request().method() === "PUT",
  );
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  expect((await saved).status()).toBe(200);
  await expect(
    page.getByText("Cambio confirmado.", { exact: true }),
  ).toBeVisible();
  await navigate(page, "Entrenadores");
  await page
    .locator(`a[href="/entrenadores/${fixture.trainers.Alia}"]`)
    .click();
  await expect(page.locator(".pokemon")).toHaveCount(6);
  await page
    .getByRole("button", { name: "Ver detalles", exact: true })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toContainText("Rayo");
  await expect(page.getByRole("dialog")).not.toContainText("Static");
  await expect(page.getByRole("dialog")).not.toContainText("IVS");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cerrar", exact: true })
    .click();
  await done(info, "admin-public-rival-desktop");
});

test("Participant closes J1 and sees General, profile and J2 without F5", async ({
  page,
}, info) => {
  test.skip(
    !process.env.POKEAPP_PHASE13_CLOSE,
    "Requires completed API preparation after other browser scenarios",
  );
  const done = monitor(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "Alia");
  await navigate(page, "Liga");
  await page
    .getByRole("button", { name: "Cerrar jornada", exact: true })
    .click();
  const closed = page.waitForResponse(
    (r) => r.url().endsWith("/close") && r.request().method() === "POST",
  );
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Confirmar", exact: true })
    .click();
  expect((await closed).status()).toBe(200);
  await expect(
    page.getByRole("button", { name: "J2", exact: true }),
  ).toBeVisible();
  const row = page
    .locator(".league-standings tbody tr")
    .filter({ hasText: "Staging Alia" });
  await expect(row).toContainText("50");
  await page.getByRole("button", { name: "J1", exact: true }).click();
  await expect(
    page.getByText("Oficial · revisión 1", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Guardar resultados", exact: true }),
  ).toHaveCount(0);
  await navigate(page, "Entrenadores");
  await page
    .locator(`a[href="/entrenadores/${fixture.trainers.Alia}"]`)
    .click();
  await expect(
    page.getByRole("heading", { name: "50 PK₽", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Team Lock pendiente", { exact: true }),
  ).toBeVisible();
  await done(info, "closed-day-general-profile");
});

for (const width of [1440, 390])
  test(`Archived League and Hall remain readable at ${width}px`, async ({
    page,
  }, info) => {
    test.skip(
      !process.env.POKEAPP_PHASE13_HISTORY,
      "Requires completed League and Cup scenarios",
    );
    const done = monitor(page);
    await page.setViewportSize({ width, height: 900 });
    await login(page, "Alia");
    await page
      .getByRole("combobox", { name: "Temporada", exact: true })
      .selectOption(fixture.main_season_id);
    await navigate(page, "Liga");
    await expect(page.locator(".league-standings tbody tr")).toHaveCount(6);
    await page.getByRole("button", { name: "J1", exact: true }).click();
    await expect(
      page.getByText("Oficial · revisión 1", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Guardar resultados", exact: true }),
    ).toHaveCount(0);
    await navigate(page, "Entrenadores");
    await page
      .locator(`a[href="/entrenadores/${fixture.trainers.Alia}"]`)
      .click();
    await expect(
      page.getByText("Team Lock pendiente", { exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`archived-profile-${width}.png`),
      fullPage: true,
    });
    await navigate(page, "Hall de la Fama");
    await expect(
      page.locator(".hall-card").filter({ hasText: "Staging Cora" }),
    ).toHaveCount(1);
    await done(info, `frozen-hall-${width}`);
  });

test("Participant opens day, edits results and replaces on-time lock without reload", async ({
  page,
}, info) => {
  const done = monitor(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "Alia");
  await navigate(page, "Liga");
  await expect(page.locator(".league-standings tbody tr")).toHaveCount(6);
  // A resumed scenario may retain the already verified open command.
  await expect(
    page.getByRole("button", { name: /^(Abrir|Cerrar) jornada$/ }),
  ).toBeVisible();
  if (
    await page
      .getByRole("button", { name: "Abrir jornada", exact: true })
      .count()
  ) {
    await page
      .getByRole("button", { name: "Abrir jornada", exact: true })
      .click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Confirmar", exact: true })
      .click();
  }
  await expect(
    page.getByRole("button", { name: "Cerrar jornada", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "J1", exact: true }).click();
  const winner = page
    .getByRole("combobox")
    .filter({ has: page.locator("option", { hasText: "Sin resultado" }) })
    .first();
  await expect(winner).toBeVisible();
  const options = await winner
    .locator("option")
    .evaluateAll((nodes) =>
      nodes.map((n) => (n as HTMLOptionElement).value).filter(Boolean),
    );
  await winner.selectOption(options[0]);
  await page
    .getByRole("button", { name: "Guardar resultados", exact: true })
    .click();
  await expect(
    page.getByText("Cambio confirmado.", { exact: true }),
  ).toBeVisible();
  await expect(winner).toHaveValue(options[0]);
  await winner.selectOption(options[1]);
  await page
    .getByRole("button", { name: "Guardar resultados", exact: true })
    .click();
  await expect(winner).toHaveValue(options[1]);
  await navigate(page, "Batallas");
  await page.getByRole("tab", { name: "Batalla", exact: true }).click();
  await page
    .getByLabel("Entrenador", { exact: true })
    .selectOption(fixture.trainers.Alia);
  await expect(
    page.getByText("Team Lock a tiempo", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Static", { exact: true }).first()).toBeVisible();
  await page
    .getByRole("button", { name: "Fijar mi equipo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirmar mi equipo", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByText("Team Lock a tiempo", { exact: true }),
  ).toBeVisible();
  await navigate(page, "Entrenadores");
  await page
    .locator(`a[href="/entrenadores/${fixture.trainers.Alia}"]`)
    .click();
  await expect(
    page.getByText("Team Lock a tiempo", { exact: true }),
  ).toBeVisible();
  await done(info, "participant-results-lock-desktop");
});

test("Purchase and revive redemption refresh wallet, inventory and wipe state", async ({
  page,
}, info) => {
  const done = monitor(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "Alia");
  await navigate(page, "Tienda");
  const card = page
    .locator(".shop-card")
    .filter({ has: page.getByRole("heading", { name: /Revivir/i }) });
  await expect(card).toHaveCount(1);
  await card.getByRole("button", { name: "Comprar", exact: true }).click();
  await page.getByRole("dialog").getByRole("checkbox").check();
  const purchase = page.waitForResponse(
    (r) =>
      r.url().endsWith("/shop/purchases") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Confirmar compra", exact: true })
    .click();
  const receipt = await (await purchase).json();
  expect(receipt.balance_after).toBe("40");
  await expect(
    page.getByText("Pendiente de canjear", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Canjear", exact: true }).click();
  const target = page.getByLabel("Pokémon objetivo", { exact: true });
  const dead = await target
    .locator("option")
    .filter({ hasText: "Alia-11" })
    .getAttribute("value");
  expect(dead).toBeTruthy();
  await target.selectOption(dead!);
  await page
    .getByRole("button", { name: "Confirmar canje", exact: true })
    .click();
  await expect(page.getByText("Canjeado", { exact: true })).toBeVisible();
  await navigate(page, "Liga");
  await expect(
    page.locator(".league-standings tr").filter({ hasText: "Staging Alia" }),
  ).toContainText("40");
  await page
    .getByLabel("Cantidad de revividos tras wipe", { exact: true })
    .fill("1");
  await page
    .getByRole("button", { name: "Actualizar revividos", exact: true })
    .click();
  await expect(page.getByText("Cantidad registrada:")).toContainText("1");
  await navigate(page, "Entrenadores");
  await page
    .locator(`a[href="/entrenadores/${fixture.trainers.Alia}"]`)
    .click();
  await expect(
    page.getByRole("heading", { name: "40 PK₽", exact: true }),
  ).toBeVisible();
  await done(info, "economy-profile-desktop");
});

test("Mobile pending to late lock, replacement, self/rival privacy and main views", async ({
  page,
}, info) => {
  const done = monitor(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "Bruno");
  await navigate(page, "Entrenadores");
  await page
    .locator(`a[href="/entrenadores/${fixture.trainers.Bruno}"]`)
    .click();
  await expect(
    page.getByText("Team Lock pendiente", { exact: true }),
  ).toBeVisible();
  await navigate(page, "Batallas");
  await page.getByRole("tab", { name: "Batalla", exact: true }).click();
  await page
    .getByLabel("Entrenador", { exact: true })
    .selectOption(fixture.trainers.Bruno);
  for (let i = 0; i < 2; i++) {
    await page
      .getByRole("button", { name: "Fijar mi equipo", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Confirmar mi equipo", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(
      page.getByText("Team Lock tardío", { exact: true }),
    ).toBeVisible();
  }
  await expect(page.getByText("Static", { exact: true }).first()).toBeVisible();
  await page
    .getByLabel("Entrenador", { exact: true })
    .selectOption(fixture.trainers.Alia);
  await expect(page.getByText("Equipo público", { exact: true })).toBeVisible();
  await expect(page.getByText("Static", { exact: true })).toHaveCount(0);
  await navigate(page, "Entrenadores");
  await page
    .locator(`a[href="/entrenadores/${fixture.trainers.Bruno}"]`)
    .click();
  await expect(
    page.getByText("Team Lock tardío", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("mobile-late-lock-profile.png"),
    fullPage: true,
  });
  await navigate(page, "Tienda");
  await expect(
    page.getByText("Saldo disponible", { exact: true }),
  ).toBeVisible();
  await navigate(page, "Liga");
  await expect(page.locator(".league-standings tbody tr")).toHaveCount(6);
  await done(info, "mobile-general");
});
