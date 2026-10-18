import { test, expect } from "@playwright/test";
import { fixture, login, navigate, pokemon, tid } from "./fixtures";

// Synthetic presentation fixtures only; never authentic-save acceptance proof.
for (const [game, name, width] of [
  ["OR", "Rubí Omega", 1440],
  ["AS", "Zafiro Alfa", 390],
] as const) {
  test(`ORAS current-save presentation ${game} ${width}`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    const commands = await fixture(page);
    const own = {
      ...pokemon,
      species: "Pokémon #479",
      nickname: "Calor",
      form: 1,
      types: ["Type #12", "Type #9"],
      item: "Item #752",
      item_generation: 6,
      moves: [{ name: "Move #621", pp: 5 }],
    };
    const { ability, nature, ivs, evs, ...publicMon } = own;
    const slots = (mon: typeof publicMon) => [
      { location: "Equipo · 1", pokemon: mon },
      {
        location: "Caja 31 · 30",
        pokemon: { ...mon, nickname: "Última caja" },
      },
      { location: "Caja 8 · 1", pokemon: { ...mon, nickname: "Recuerdo" } },
    ];
    const headers = { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" };
    await page.route("**/v1/read/seasons/*/pc", (route) =>
      route.fulfill({
        headers,
        json: {
          status: "ready",
          save: {
            id: "oras-save",
            game,
            parser_status: "parsed",
            uploaded_at: "2026-10-18T10:00:00Z",
          },
          pokemon: slots(own),
        },
      }),
    );
    await page.route("**/v1/read/seasons/*/trainers/*/collection", (route) =>
      route.fulfill({
        headers,
        json: {
          status: "ready",
          game,
          pokemon: slots(publicMon),
          revived_after_wipe: 0,
        },
      }),
    );
    await login(page);
    await expect(
      page.getByText(`Pokémon ${name}`, { exact: true }),
    ).toBeVisible();
    await navigate(page, "Mi PC");
    await page
      .getByRole("button", { name: "Calor · Equipo 1", exact: true })
      .click();
    const detail = page.getByRole("dialog");
    await expect(detail).toContainText("Forma 1");
    await expect(detail).toContainText("Eléctrico");
    await expect(detail).toContainText("Fuego");
    await expect(detail).toContainText("Cerco Dimensión");
    await expect(
      detail.getByRole("heading", { name: "IVs", exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`${game}-own.png`),
      fullPage: true,
    });
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Caja anterior" }).click();
    await expect(
      page.getByRole("heading", { name: "Caja 31", exact: true }),
    ).toBeVisible();
    await navigate(page, "Entrenadores");
    await page.locator("a[href='/entrenadores/rival-trainer']").click();
    await expect(
      page.getByText(`Pokémon ${name}`, { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Calor · Equipo 1", exact: true })
      .click();
    await expect(detail).toContainText("Forma 1");
    await expect(detail).not.toContainText("Habilidad");
    await expect(detail).not.toContainText("Naturaleza");
    await expect(
      detail.getByRole("heading", { name: "IVs", exact: true }),
    ).toHaveCount(0);
    await page.screenshot({
      path: info.outputPath(`${game}-public.png`),
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    expect(commands).toHaveLength(0);
  });
}
