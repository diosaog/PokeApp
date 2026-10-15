import { test, expect } from "@playwright/test";
import { fixture, login, navigate, pokemon, tid } from "./fixtures";

for (const width of [1440, 390]) {
  test(`inline move, horizontal detail, IVs and focus at ${width}px`, async ({
    page,
  }, info) => {
    const commands = await fixture(page, false, undefined, {
      ...pokemon,
      moves: [
        { name: "Move #85", pp: 15 },
        { name: "Move #53", pp: 15 },
        { name: "Move #57", pp: 15 },
        { name: "Move #182", pp: 10 },
      ],
      ivs: { hp: 0, atk: 31, defense: 17, spa: 24, spd: 9, spe: 30 },
      evs: { hp: 252, atk: 252, defense: 0, spa: 0, spd: 0, spe: 4 },
    });
    await page.setViewportSize({ width, height: 1000 });
    await login(page);
    await navigate(page, "Batallas");
    await page.getByRole("tab", { name: "Batalla", exact: true }).click();
    const trigger = page.getByRole("button", { name: "Ver Rayo" }).first();
    await trigger.focus();
    await page.keyboard.press("Enter");
    const expansion = page.getByRole("region", { name: "Detalles de Rayo" });
    await expect(expansion).toContainText("Precisión");
    const buttonRect = await trigger.boundingBox(),
      detailRect = await expansion.boundingBox();
    expect(detailRect!.y).toBeGreaterThan(
      buttonRect!.y + buttonRect!.height - 5,
    );
    expect(detailRect!.height).toBeLessThan(width === 390 ? 230 : 290);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.screenshot({ path: info.outputPath(`inline-${width}.png`) });
    await page.keyboard.press("Escape");
    await expect(trigger).toBeFocused();
    await expect(expansion).toHaveCount(0);
    await page.getByText("Ver IVs", { exact: true }).first().click();
    await expect(
      page.getByRole("meter", { name: "PS" }).first(),
    ).toHaveAttribute("aria-valuenow", "0");
    await expect(page.locator("main")).not.toContainText(/EVs|252/);
    await navigate(page, "Entrenadores");
    await page.locator(`a[href='/entrenadores/${tid}']`).click();
    await expect(page.locator(".party-slots button").first()).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`profile-${width}.png`),
      fullPage: true,
    });
    await page.locator(".party-slots button").first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("meter")).toHaveCount(6);
    await expect(dialog).not.toContainText(
      /EVs|252|Potencia|Precisión|Descripción/,
    );
    await expect(dialog.getByRole("button")).toHaveCount(1);
    const identity = await dialog.locator(".detail-identity").boundingBox();
    const data = await dialog.locator(".detail-data").boundingBox();
    const moves = await dialog.locator(".detail-moves").boundingBox();
    if (width > 1000) {
      expect(identity!.x + identity!.width).toBeLessThan(data!.x);
      expect(data!.x + data!.width).toBeLessThan(moves!.x);
    } else {
      expect(data!.y).toBeGreaterThan(identity!.y);
      expect(moves!.y).toBeGreaterThan(data!.y);
    }
    await page.screenshot({ path: info.outputPath(`iv-detail-${width}.png`) });
    expect(
      await dialog.evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
    ).toBe(true);
    expect(commands).toHaveLength(0);
  });
}

test("all type move treatments retain readable contrast, sections remain distinct", async ({
  page,
}) => {
  await fixture(page);
  await login(page);
  await navigate(page, "Batallas");
  const ratios = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    const context = canvas.getContext("2d")!;
    const luminance = (color: string) => {
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      const v = Array.from(context.getImageData(0, 0, 1, 1).data)
        .slice(0, 3)
        .map((n) => {
          const c = n / 255;
          return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        });
      return v[0] * 0.2126 + v[1] * 0.7152 + v[2] * 0.0722;
    };
    const clone = document
      .querySelector(".move-disclosure")!
      .cloneNode(true) as HTMLElement;
    document.querySelector("main")!.append(clone);
    const values = [
      "normal",
      "fighting",
      "flying",
      "poison",
      "ground",
      "rock",
      "bug",
      "ghost",
      "steel",
      "fire",
      "water",
      "grass",
      "electric",
      "psychic",
      "ice",
      "dragon",
      "dark",
      "fairy",
      "unknown",
    ].map((type) => {
      clone.className = `move-disclosure type-${type}`;
      const button = clone.querySelector("button")!;
      const s = getComputedStyle(button),
        small = getComputedStyle(button.querySelector("small")!);
      const bg = luminance(s.backgroundColor);
      return {
        type,
        text: (luminance(s.color) + 0.05) / (bg + 0.05),
        pp: (luminance(small.color) + 0.05) / (bg + 0.05),
      };
    });
    clone.remove();
    return values;
  });
  for (const ratio of ratios) {
    expect(ratio.text, ratio.type).toBeGreaterThanOrEqual(4.5);
    expect(ratio.pp, ratio.type).toBeGreaterThanOrEqual(4.5);
  }
  const accents = new Set<string>();
  for (const name of [
    "Inicio",
    "Liga",
    "Batallas",
    "Entrenadores",
    "Mi PC",
    "Tienda",
    "Copa",
    "Hall de la Fama",
    "Juicios",
    "Saves y Launcher",
    "Administración",
  ]) {
    await navigate(page, name);
    accents.add(
      await page
        .locator(".app-shell")
        .evaluate((e) =>
          getComputedStyle(e).getPropertyValue("--accent").trim(),
        ),
    );
  }
  expect(accents.size).toBe(11);
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(
    await page
      .locator(".card")
      .first()
      .evaluate((e) => getComputedStyle(e).transitionDuration),
  ).toBe("0s");
});
