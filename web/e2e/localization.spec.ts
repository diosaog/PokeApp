import { test, expect } from "@playwright/test";
import { fixture, login, navigate, pokemon, tid } from "./fixtures";

const numeric = {
  ...pokemon,
  species: "Pokémon #635",
  nickname: "",
  types: ["Dark", "Dragon"],
  moves: [
    { name: "Move #85", pp: 15 },
    { name: "dark-pulse", pp: 15 },
  ],
  item: "Item #234",
  ability: "Ability #26",
  nature: "Nature #10",
};

for (const width of [1440, 390]) {
  test(`Spanish PC, self/rival profile and preview at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    const paths: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (r) => paths.push(new URL(r.url()).pathname));
    const commands = await fixture(page, false, undefined, numeric);
    await login(page);
    await navigate(page, "Mi PC");
    await page.getByLabel("Buscar Pokémon").fill("Hydreigon");
    await expect(page.locator(".pokemon")).toHaveCount(12);
    await page
      .getByRole("button", { name: /Hydreigon/ })
      .first()
      .click();
    const dialog = page.getByRole("dialog");
    for (const name of [
      "Restos",
      "Rayo",
      "Pulso Umbrío",
      "Levitación",
      "Miedosa",
    ])
      await expect(dialog.getByText(name, { exact: true })).toBeVisible();
    await expect(dialog).not.toContainText(
      /#635|#234|#85|#26|#10|Thunderbolt|\bspa\b/,
    );
    await page.screenshot({
      path: info.outputPath(`spanish-pc-${width}.png`),
      fullPage: true,
    });
    await page.keyboard.press("Escape");
    await navigate(page, "Entrenadores");
    await page.locator(`a[href='/entrenadores/${tid}']`).click();
    await page.getByRole("button", { name: "Ver detalles" }).first().click();
    await expect(dialog.getByText("Levitación", { exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await navigate(page, "Entrenadores");
    paths.length = 0;
    await page.locator("a[href='/entrenadores/rival-trainer']").click();
    await page.getByRole("button", { name: "Ver detalles" }).first().click();
    await expect(dialog.getByText("Restos", { exact: true })).toBeVisible();
    await expect(dialog).not.toContainText(
      /Levitación|Miedosa|Habilidad|Naturaleza|IVS|EVS/,
    );
    expect(paths.some((p) => p.endsWith("/pc"))).toBe(false);
    await page.keyboard.press("Escape");
    await navigate(page, "Batallas");
    await expect(page.getByText("Objeto: Restos")).toHaveCount(12);
    await expect(page.locator("main")).not.toContainText(
      /Ability|Nature|Levitación|Miedosa/,
    );
    await page.getByRole("tab", { name: "Batalla", exact: true }).click();
    await expect(page.getByText("Levitación", { exact: true })).toHaveCount(6);
    await page
      .getByLabel("Entrenador", { exact: true })
      .selectOption("rival-trainer");
    await expect(page.getByText("Levitación", { exact: true })).toHaveCount(0);
    expect(commands).toHaveLength(0);
    expect(errors).toEqual([]);
  });
}

test("X/Y species and names survive public scouting and inventory selection", async ({
  page,
}) => {
  const commands = await fixture(page, false, undefined, {
    ...numeric,
    species: "#658",
  });
  await login(page);
  await navigate(page, "Entrenadores");
  await page
    .getByRole("link", { name: "Explorar equipos públicos", exact: true })
    .click();
  await page.getByLabel("Entrenador a consultar").selectOption("rival-trainer");
  await expect(page.locator(".pokemon").first()).toContainText("Greninja");
  await expect(page.getByText("Rayo", { exact: true })).toHaveCount(6);
  await expect(page.locator("main")).not.toContainText(
    /Levitación|Miedosa|#658|Move #/,
  );
  await navigate(page, "Tienda");
  await page.getByRole("button", { name: "Canjear", exact: true }).click();
  await expect(page.getByLabel("Pokémon objetivo")).toContainText("Greninja");
  await expect(page.getByRole("dialog")).not.toContainText("#658");
  expect(commands).toHaveLength(0);
});
