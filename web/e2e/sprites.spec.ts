import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, pokemon } from "./fixtures";

// Reproduce the observed legacy prefix and public species/form/level only.
// Authentication/PC responses are synthetic; sprite requests are real assets.
async function pcFixture(page: Page) {
  const commands = await fixture(
    page,
    false,
    process.env.POKEAPP_E2E_API_ORIGIN || "http://127.0.0.1:8000",
  );
  const make = (id: number, form = 0, level = 5) => ({
    ...pokemon,
    species: `Pok\u00c3\u00a9mon #${id}`,
    nickname: "",
    form,
    level,
  });
  await page.route("**/pc", (route) =>
    route.fulfill({
      json: {
        save: {
          id: "sprite-fixture",
          parser_status: "parsed",
          parser_version: "fixture",
          uploaded_at: "2026-10-28T12:00:00Z",
        },
        status: "ready",
        pokemon: [
          ...[make(647, 0, 6), make(718, 0, 5), make(371, 0, 10)].map(
            (p, i) => ({ location: `Equipo · ${i + 1}`, pokemon: p }),
          ),
          ...[
            make(647, 1),
            make(718, 4),
            make(26, 1),
            make(6, 2),
            make(722),
            make(807),
            make(647, 255),
          ].map((p, i) => ({ location: `Caja 1 · ${i + 1}`, pokemon: p })),
        ],
      },
    }),
  );
  await login(page);
  await navigate(page, "Mi PC");
  return commands;
}

for (const width of [1440, 390]) {
  test(`real PC sprites, forms and Gen7 at ${width}`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const commands = await pcFixture(page);
    for (const name of ["Keldeo", "Zygarde", "Bagon"]) {
      const image = page
        .locator(".party-panel")
        .getByRole("img", { name, exact: true });
      await expect(image).toBeVisible();
      await expect
        .poll(() =>
          image.evaluate(
            (e: HTMLImageElement) => e.complete && e.naturalWidth > 0,
          ),
        )
        .toBe(true);
    }
    await expect(page.locator(".party-panel .unresolved")).toHaveCount(0);
    for (const file of [
      "647-form-1",
      "718-form-4",
      "26-form-1",
      "6-form-2",
      "722",
      "807",
    ]) {
      const image = page.locator(`.box-slots img[src$='/${file}.png']`);
      await image.scrollIntoViewIfNeeded();
      await expect
        .poll(() =>
          image.evaluate(
            (e: HTMLImageElement) => e.complete && e.naturalWidth > 0,
          ),
        )
        .toBe(true);
    }
    await expect(
      page.getByLabel("Imagen de esta forma no disponible"),
    ).toBeVisible();
    expect(await page.locator(".box-slots img[src$='.gif']").count()).toBe(0);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.locator(".party-panel").scrollIntoViewIfNeeded();
    for (const id of [647, 718, 371])
      await expect(
        page.locator(`.party-panel img[src$='/${id}.png']`),
      ).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`pc-sprites-${width}.png`),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Bagon · Equipo 3", exact: true })
      .click();
    const detail = page
      .getByRole("dialog")
      .getByRole("img", { name: "Bagon", exact: true });
    await expect
      .poll(() =>
        detail.evaluate(
          (e: HTMLImageElement) => e.complete && e.naturalWidth > 0,
        ),
      )
      .toBe(true);
    await page.keyboard.press("Escape");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
    expect(commands).toEqual([]);
  });
}

test("missing animation retains the genuine static sprite", async ({
  page,
}) => {
  await page.route("**/visuals/animated/v1/647.gif", (route) =>
    route.fulfill({ status: 404, body: "" }),
  );
  const failedAnimation = page.waitForResponse((response) =>
    response.url().endsWith("/visuals/animated/v1/647.gif"),
  );
  await pcFixture(page);
  expect((await failedAnimation).status()).toBe(404);
  const image = page
    .locator(".party-panel")
    .getByRole("img", { name: "Keldeo", exact: true });
  await expect(image).toHaveAttribute("src", "/visuals/v1/pokemon/647.png");
  await expect
    .poll(() =>
      image.evaluate((e: HTMLImageElement) => e.complete && e.naturalWidth > 0),
    )
    .toBe(true);
  await expect(page.locator(".party-panel .unresolved")).toHaveCount(0);
});

test("asset failure remains distinct from an unmapped form", async ({
  page,
}) => {
  const warnings: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "warning") warnings.push(m.text());
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/visuals/v1/pokemon/371.png", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await pcFixture(page);
  await expect(
    page.getByRole("img", { name: "No se pudo cargar la imagen de Bagon" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Imagen de esta forma no disponible"),
  ).toBeAttached();
  expect(warnings.some((w) => w.includes("pokemon_sprite_load_failed"))).toBe(
    true,
  );
});
