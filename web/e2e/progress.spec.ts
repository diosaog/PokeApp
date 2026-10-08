import { expect, test } from "@playwright/test";
import { fixture, login, navigate, overview } from "./fixtures";

test("current save progress distinguishes unknown, zero, sparse regions and Champion states on desktop/mobile", async ({
  page,
}) => {
  const commands = await fixture(page);
  let progress: object = { state: "unknown" };
  await page.route("**/v1/read/seasons/*/progress", (route) =>
    route.fulfill({ json: progress }),
  );
  await page.route("**/v1/read/seasons/*/overview", (route) =>
    route.fulfill({
      json: {
        ...overview,
        players: overview.players.map((p) => ({ ...p, progress })),
      },
    }),
  );
  await login(page);
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await navigate(page, "Inicio");
    await navigate(page, "Saves y Launcher");
    progress = { state: "unknown" };
    await page.getByRole("button", { name: "Actualizar progreso" }).click();
    await expect(page.getByText(/Progreso no observado/)).toBeVisible();
    await expect(page.getByText(/0 medallas/)).toHaveCount(0);
    for (const champion of [null, false, true]) {
      progress = {
        state: "observed",
        game: "HG",
        badges_count: 2,
        primary_region: "johto",
        regions: [
          { region: "johto", earned_badges: [] },
          { region: "kanto", earned_badges: [2, 7] },
        ],
        champion_defeated: champion,
        observed_at: "2026-10-08T12:00:00Z",
      };
      await page.getByRole("button", { name: "Actualizar progreso" }).click();
      await expect(page.getByText("2 medallas observadas")).toBeVisible();
      await expect(
        page.getByRole("img", { name: "Medalla 1 de Johto: no conseguida" }),
      ).toBeVisible();
      await expect(
        page.getByRole("img", { name: "Medalla 7 de Kanto: conseguida" }),
      ).toBeVisible();
      await expect(
        page.getByText(
          champion === true
            ? /Juego completado/
            : champion === false
              ? /aún no derrotado/
              : /sin observar/,
        ),
      ).toBeVisible();
    }
    progress = {
      ...progress,
      badges_count: 0,
      regions: [
        { region: "johto", earned_badges: [] },
        { region: "kanto", earned_badges: [] },
      ],
      champion_defeated: false,
    };
    await page.getByRole("button", { name: "Actualizar progreso" }).click();
    await expect(page.getByText("0 medallas observadas")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
  }
  await page.reload();
  await login(page);
  await navigate(page, "Entrenadores");
  await expect(page.getByText("0 medallas observadas")).toHaveCount(4);
  expect(commands).toHaveLength(0);
});

test("read failure does not turn cached completion into a new reliable observation", async ({
  page,
}) => {
  await fixture(page);
  await page.route("**/v1/read/seasons/*/progress", (route) =>
    route.fulfill({
      status: 503,
      json: { error: { code: "READ_UNAVAILABLE", message: "No disponible" } },
    }),
  );
  await login(page);
  await navigate(page, "Saves y Launcher");
  await expect(
    page.getByText(/Servicio temporalmente no disponible/),
  ).toBeVisible();
  await expect(
    page.getByText(/0 medallas|Juego completado|aún no derrotado/),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Actualizar progreso" }),
  ).toBeEnabled();
});
