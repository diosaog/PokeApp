import { test, expect } from "@playwright/test";
import { fixture, login, navigate, overview, pokemon, tid } from "./fixtures";

for (const width of [1440, 390]) {
  test(`product collection and public privacy at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    const commands = await fixture(page),
      errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.route("**/v1/read/seasons/*/overview", (route) =>
      route.fulfill({
        headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" },
        json: {
          ...overview,
          players: overview.players.map((p) => ({
            ...p,
            progress: {
              state: "observed",
              badges_count: 4,
              regions: [{ region: "sinnoh", earned_badges: [1, 2, 3, 4] }],
              champion_defeated: false,
            },
          })),
        },
      }),
    );
    await page.route("**/v1/read/seasons/*/pc", (route) =>
      route.fulfill({
        headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" },
        json: {
          status: "ready",
          save: {
            id: "save",
            uploaded_at: "2026-10-15T10:00:00Z",
            parser_status: "parsed",
          },
          pokemon: [
            ...Array.from({ length: 12 }, (_, i) => ({
              location: i < 6 ? `Equipo · ${i + 1}` : `Caja 1 · ${i - 5}`,
              pokemon,
            })),
            {
              location: "Caja 2 · 1",
              pokemon: { ...pokemon, species: "#700", nickname: "Sylveon" },
            },
          ],
        },
      }),
    );
    await login(page);
    await navigate(page, "Entrenadores");
    await expect(page.locator(".trainer-card")).toHaveCount(4);
    await expect(page.locator(".trainer-card").first()).toContainText(
      "Antonio",
    );
    await expect(
      page.locator(".trainer-card").first().locator(".stat-pill span"),
    ).toHaveText(["Puntos", "Monedas", "Muertos"]);
    await expect
      .poll(() =>
        page
          .locator(".trainer-card")
          .first()
          .locator(".game-badge img")
          .evaluateAll((images) =>
            images.every(
              (img) =>
                (img as HTMLImageElement).complete &&
                (img as HTMLImageElement).naturalWidth > 0,
            ),
          ),
      )
      .toBe(true);
    await expect(page.locator(".trainer-card > .button").first()).toHaveCSS(
      "background-color",
      "rgb(127, 216, 203)",
    );
    await page.screenshot({
      path: info.outputPath(`trainers-${width}.png`),
      fullPage: true,
    });
    await page.locator(`a[href='/entrenadores/${tid}']`).click();
    await expect(
      page.getByRole("heading", { name: "Equipo", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Caja siguiente" }).click();
    await expect(
      page.getByRole("heading", { name: "Caja 2", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: /Sylveon · Caja 2/ }).click();
    await expect(page.getByRole("dialog")).toContainText("Modesta");
    await expect
      .poll(() =>
        page
          .getByRole("dialog")
          .locator(".pokemon-sprite")
          .evaluate((img: HTMLImageElement) => img.naturalWidth),
      )
      .toBeGreaterThan(0);
    await page.screenshot({
      path: info.outputPath(`popup-${width}.png`),
      fullPage: false,
    });
    expect(
      await page.getByRole("dialog").evaluate((el) => {
        const r = el.getBoundingClientRect();
        return (
          r.top >= 0 &&
          r.bottom <= innerHeight &&
          r.left >= 0 &&
          r.right <= innerWidth
        );
      }),
    ).toBe(true);
    await expect(
      page.getByRole("button", { name: "Cerrar", exact: true }),
    ).toBeFocused();
    await page.keyboard.press("Escape");
    await navigate(page, "Entrenadores");
    const reads: string[] = [];
    page.on("request", (r) => reads.push(new URL(r.url()).pathname));
    await page.locator("a[href='/entrenadores/rival-trainer']").click();
    await expect(
      page.getByText("Las cajas de este entrenador son privadas."),
    ).toBeVisible();
    await page.locator(".public-party button").first().click();
    await expect(page.getByRole("dialog")).not.toContainText(
      /Modesta|Foco interno|IVs|EVs/,
    );
    expect(
      reads.some((p) => p.endsWith("/pc") || p.endsWith("/inventory")),
    ).toBe(false);
    await page.keyboard.press("Escape");
    await navigate(page, "Mi PC");
    await expect(page.locator(".box-slots .pokemon")).toHaveCount(6);
    await page.getByRole("button", { name: "Caja siguiente" }).click();
    await expect(page.locator(".box-slots .pokemon")).toHaveCount(1);
    await page.screenshot({
      path: info.outputPath(`pc-${width}.png`),
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    expect(commands).toHaveLength(0);
    expect(errors).toEqual([]);
  });
}
