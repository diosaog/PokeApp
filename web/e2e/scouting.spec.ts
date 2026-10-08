import { test, expect } from "@playwright/test";
import { fixture, login, navigate, tid, sid } from "./fixtures";

test("a confirmed Team Lock invalidates only this season's public scouting cache", async ({
  page,
}) => {
  await fixture(page);
  await login(page);
  await navigate(page, "Entrenadores");
  await page
    .getByRole("link", { name: "Explorar equipos públicos", exact: true })
    .click();
  await expect(page.locator(".pokemon")).toHaveCount(6);
  await navigate(page, "Batallas");
  await page
    .getByRole("button", { name: "Fijar mi equipo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirmar mi equipo", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await navigate(page, "Entrenadores");
  const fresh = page.waitForResponse((r) =>
    new URL(r.url()).pathname.endsWith("/scouting"),
  );
  await page
    .getByRole("link", { name: "Explorar equipos públicos", exact: true })
    .click();
  await fresh;
  await expect(page.locator(".pokemon")).toHaveCount(6);
});

test("trainer entry chooses a public team without a scheduled battle or private fallback", async ({
  page,
}) => {
  const commands = await fixture(page);
  await login(page);
  await navigate(page, "Entrenadores");
  const reads: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "GET") reads.push(new URL(r.url()).pathname);
  });
  await page
    .getByRole("link", { name: "Explorar equipos públicos", exact: true })
    .click();
  await page.getByLabel("Entrenador a consultar").selectOption("t3");
  await expect(
    page.getByRole("heading", { name: "Equipos públicos", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Entrenador a consultar")).toHaveValue("t3");
  await expect(page.getByText("Objeto: Vidasfera")).toHaveCount(6);
  await expect(page.getByText("Esfera aural", { exact: true })).toHaveCount(6);
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(0);
  expect(
    reads.some(
      (p) =>
        p.endsWith("/pc") ||
        p.endsWith("/overview") ||
        p.endsWith("/team-preview"),
    ),
  ).toBe(false);
  await page.getByLabel("Entrenador a consultar").selectOption("t4");
  await expect(page.getByText(/No hay un Team Lock público/)).toBeVisible();
  await expect(page.locator(".pokemon")).toHaveCount(0);
  expect(commands).toHaveLength(0);
});

test("cached private battle details never appear in self scouting and selectors isolate teams", async ({
  page,
}) => {
  await fixture(page);
  await login(page);
  await navigate(page, "Batallas");
  await page.getByRole("tab", { name: "Batalla", exact: true }).click();
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(6);
  await navigate(page, "Entrenadores");
  await page
    .getByRole("link", { name: "Explorar equipos públicos", exact: true })
    .click();
  await expect(page.getByLabel("Entrenador a consultar")).toHaveValue(tid);
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(0);
  for (const id of ["rival-trainer", tid, "t4"]) {
    await page.getByLabel("Entrenador a consultar").selectOption(id);
    await expect(page.getByLabel("Entrenador a consultar")).toHaveValue(id);
    await expect(page.locator("main")).not.toContainText("Modesta");
  }
});

for (const width of [1440, 390])
  test(`public scouting and missing-data states fit ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await fixture(page);
    await login(page);
    await navigate(page, "Entrenadores");
    await page
      .getByRole("link", { name: "Explorar equipos públicos", exact: true })
      .click();
    await expect(page.getByLabel("Entrenador a consultar")).toHaveValue(tid);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`scouting-${width}.png`),
      fullPage: true,
    });
    await page.getByLabel("Entrenador a consultar").selectOption("t4");
    await expect(page.locator(".pokemon")).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
  });

test("a failed selected read does not retain old team; selection can recover", async ({
  page,
}) => {
  await fixture(page);
  await login(page);
  await navigate(page, "Entrenadores");
  await page
    .getByRole("link", { name: "Explorar equipos públicos", exact: true })
    .click();
  await expect(page.locator(".pokemon")).toHaveCount(6);
  await page.route(
    `**/seasons/${sid}/scouting?trainer_id=rival-trainer`,
    async (route) =>
      route.fulfill({
        status: 503,
        headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" },
        json: { detail: { code: "READ_UNAVAILABLE" } },
      }),
  );
  await page.getByLabel("Entrenador a consultar").selectOption("rival-trainer");
  await expect(page.locator(".pokemon")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Volver a elegir entrenador", exact: true })
    .click();
  await expect(page.getByLabel("Entrenador a consultar")).toHaveValue(tid);
});
