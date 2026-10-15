import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, overview, pokemon } from "./fixtures";

async function readyImages(page: Page) {
  // Screenshot fixtures load below-fold assets too; production keeps lazy loading.
  await page
    .locator("main img")
    .evaluateAll((imgs) =>
      imgs.forEach((img) => ((img as HTMLImageElement).loading = "eager")),
    );
  await expect
    .poll(() =>
      page
        .locator("main img")
        .evaluateAll((imgs) =>
          imgs.every(
            (img) =>
              (img as HTMLImageElement).complete &&
              (img as HTMLImageElement).naturalWidth > 0,
          ),
        ),
    )
    .toBe(true);
}
for (const width of [1440, 900, 390]) {
  test(`product surfaces, local assets and safe empty states at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 960 });
    const commands = await fixture(page, false, undefined, {
        ...pokemon,
        moves: [
          ...pokemon.moves,
          { name: "Move #85", pp: 15 },
          { name: "Move #182", pp: 10 },
        ],
      }),
      errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const foreign: string[] = [];
    page.on("request", (r) => {
      // The owner's antivirus injects its own script into local HTTP pages.
      // Exclude that observed browser instrumentation, never application hosts.
      if (new URL(r.url()).hostname === "me.kis.v2.scr.kaspersky-labs.com")
        return;
      if (!["127.0.0.1", "localhost"].includes(new URL(r.url()).hostname))
        foreign.push(r.url());
    });
    await page.route("**/v1/read/seasons/*/overview", (route) =>
      route.fulfill({
        json: {
          ...overview,
          players: overview.players.map((p, i) => ({
            ...p,
            display_name: i === 0 ? "Anto" : p.display_name,
            progress: {
              state: "observed",
              game: "Pt",
              badges_count: 4,
              regions: [{ region: "sinnoh", earned_badges: [1, 2, 3, 4] }],
              champion_defeated: false,
            },
          })),
        },
      }),
    );
    await login(page);
    if (width === 390) {
      await page.getByRole("button", { name: "Abrir navegación" }).click();
      await page.getByRole("button", { name: "Cerrar navegación" }).click();
      await expect(
        page.getByRole("button", { name: "Abrir navegación" }),
      ).toHaveAttribute("aria-expanded", "false");
    }
    for (const [name, slug] of [
      ["Inicio", "home"],
      ["Liga", "league"],
      ["Batallas", "battle"],
      ["Entrenadores", "trainers"],
      ["Tienda", "shop"],
      ["Copa", "cup"],
      ["Hall de la Fama", "hall"],
      ["Juicios", "trials"],
      ["Saves y Launcher", "saves"],
      ["Administración", "admin"],
    ]) {
      await navigate(page, name);
      await expect(page.locator("main .loading")).toHaveCount(0);
      if (name === "Copa")
        await page.getByRole("link", { name: /Copa Equinoccio/ }).click();
      if (name === "Administración")
        await page
          .getByRole("tab", { name: "Configuración", exact: true })
          .click();
      if (name === "Batallas") {
        await page.getByRole("tab", { name: "Batalla", exact: true }).click();
        await expect(page.locator(".battle-pokemon")).toHaveCount(6);
        await expect(page.locator(".battle-moves .move-button")).toHaveCount(
          24,
        );
      }
      await readyImages(page);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        name,
      ).toBe(true);
      await expect(page.locator("main")).not.toContainText(
        /Pokémon #\d|Item #\d|Move #\d|Ability #\d|Nature #\d|\bDTO\b|receipt|parser_status/,
      );
      await page.screenshot({
        path: info.outputPath(`${slug}-${width}.png`),
        fullPage: true,
      });
    }
    // A missing Hall is an intentional empty state, not a synthetic champion.
    await page.route("**/v1/read/hall?*", (route) =>
      route.fulfill({ json: { items: [], next_offset: null } }),
    );
    await navigate(page, "Hall de la Fama");
    // Refetch by a new route page only if the cache is fresh; use reload/login to
    // prove a genuinely empty response without relying on cache timing.
    await page.reload();
    await login(page);
    await navigate(page, "Hall de la Fama");
    await expect(
      page.getByText("Tu próxima historia empieza aquí."),
    ).toBeVisible();
    await expect(page.locator(".hall-card")).toHaveCount(0);
    expect(commands).toHaveLength(0);
    expect(errors).toEqual([]);
    expect(foreign).toEqual([]);
  });
}
