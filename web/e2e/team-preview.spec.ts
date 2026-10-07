import { test, expect } from "@playwright/test";
import { fixture, login, navigate, tid } from "./fixtures";

test("spectator chooses unscheduled Lucía and Marcos with public fields only", async ({
  page,
}) => {
  await fixture(page);
  await login(page);
  await navigate(page, "Batallas");
  await page.getByLabel("Primer entrenador").selectOption("rival-trainer");
  await page.getByLabel("Segundo entrenador").selectOption("t3");
  await expect(page.locator(".battle-side h2")).toHaveText(["Lucía", "Marcos"]);
  await expect(page.getByText("Equipo público", { exact: true })).toHaveCount(
    2,
  );
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Objeto: Vidasfera")).toHaveCount(12);
});

test("battle self has private lock details; rival and spectator never retain them", async ({
  page,
}) => {
  await fixture(page);
  await login(page);
  await navigate(page, "Batallas");
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(0);
  await page.getByRole("tab", { name: "Batalla", exact: true }).click();
  await expect(page.locator("main select")).toHaveCount(1);
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(6);
  await expect(
    page.getByRole("heading", { name: "IVS", exact: true }),
  ).toHaveCount(6);
  await page
    .getByLabel("Entrenador", { exact: true })
    .selectOption("rival-trainer");
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(0);
  await page.getByLabel("Entrenador", { exact: true }).selectOption(tid);
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(6);
  await page.getByRole("tab", { name: "Espectador", exact: true }).click();
  await expect(page.getByText("Foco interno", { exact: true })).toHaveCount(0);
});

test("missing lock warns without a save fallback or a League result blocker", async ({
  page,
}) => {
  const commands = await fixture(page);
  const initialReads = Promise.all([
    page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/pc")),
    page.waitForResponse((r) =>
      new URL(r.url()).pathname.endsWith("/overview"),
    ),
  ]);
  await login(page);
  await initialReads;
  const reads: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "GET") reads.push(new URL(r.url()).pathname);
  });
  await navigate(page, "Batallas");
  await page.getByLabel("Segundo entrenador").selectOption("t4");
  await expect(page.getByRole("alert")).toContainText("Falta el Team Lock");
  await expect(page.getByRole("alert")).toContainText(
    "Puedes continuar en la Liga",
  );
  expect(reads.some((p) => p.endsWith("/pc") || p.endsWith("/overview"))).toBe(
    false,
  );
  expect(commands).toHaveLength(0);
  await navigate(page, "Liga");
  await page.getByRole("button", { name: "J4", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Tu Team Lock está pendiente",
  );
  await expect(
    page.getByRole("button", { name: /Guardar resultados/ }),
  ).toBeEnabled();
});

test("explicit Team Lock retry preserves its request and refreshes the preview", async ({
  page,
}) => {
  await fixture(page);
  const requests: { body: unknown; key: string | undefined }[] = [];
  await page.route("**/team-lock", async (route) => {
    if (route.request().method() === "OPTIONS") return route.fallback();
    requests.push({
      body: route.request().postDataJSON(),
      key: route.request().headers()["idempotency-key"],
    });
    await route.fulfill({
      status: requests.length === 1 ? 503 : 200,
      headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" },
      json:
        requests.length === 1
          ? { detail: { code: "SERVICE_UNAVAILABLE" } }
          : { ok: true },
    });
  });
  await login(page);
  await navigate(page, "Batallas");
  await page.getByRole("button", { name: "Fijar mi equipo" }).click();
  await page.getByRole("button", { name: "Confirmar mi equipo" }).click();
  await expect(
    page.getByRole("button", { name: "Reintentar la misma solicitud" }),
  ).toBeVisible();
  expect(requests).toHaveLength(1);
  const refresh = page.waitForResponse((r) =>
    new URL(r.url()).pathname.endsWith("/team-preview"),
  );
  await page
    .getByRole("button", { name: "Reintentar la misma solicitud" })
    .click();
  await refresh;
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(requests).toHaveLength(2);
  expect(requests[0].key).toBeTruthy();
  expect(requests[1]).toEqual(requests[0]);
  expect(requests[0].body).toEqual({ save_file_id: "save" });
});

for (const width of [1440, 390]) {
  test(`Team Preview selectors and warning fit at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await fixture(page);
    await login(page);
    await navigate(page, "Batallas");
    await page.getByLabel("Segundo entrenador").selectOption("t4");
    await expect(page.getByRole("alert")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`team-preview-${width}.png`),
      fullPage: true,
    });
  });
}
