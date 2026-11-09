// Normativa in a real browser (real CSS): reachable by every trainer, the
// index moves between chapters and nothing is cut at either width.
// Synthetic fixtures only.
import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, tid } from "./fixtures";

const shots = process.env.POKEAPP_NORMATIVA_SHOTS;
const noSideScroll = (page: Page) =>
  page.evaluate(
    () =>
      document.documentElement.scrollWidth <=
      document.documentElement.clientWidth,
  );
// Text cut inside its own box: wider content than the box it lives in.
const clipped = (page: Page) =>
  page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>(".rulebook *:not(.sr-only)")]
      .filter(
        (el) =>
          el.scrollWidth > el.clientWidth + 1 &&
          getComputedStyle(el).overflowX === "hidden" &&
          el.clientWidth > 0,
      )
      .map((el) => el.className || el.tagName),
  );

async function open(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await fixture(page);
  await login(page);
  await navigate(page, "Normativa");
  await expect(
    page.getByRole("heading", { level: 1, name: "Normativa" }),
  ).toBeVisible();
}
async function capture(page: Page, name: string) {
  if (!shots) return;
  await page.evaluate(async () => {
    // Force lazy images in, light the climb, then capture from the top.
    document
      .querySelectorAll<HTMLImageElement>('.rulebook img[loading="lazy"]')
      .forEach((img) => (img.loading = "eager"));
    document.querySelector(".nv-climb")?.scrollIntoView({ block: "center" });
    await new Promise((done) => setTimeout(done, 1500));
    await Promise.all(
      [...document.images].map((img) => img.decode().catch(() => undefined)),
    );
    window.scrollTo(0, 0);
    await new Promise((done) => setTimeout(done, 200));
  });
  await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true });
}

for (const [width, height] of [
  [1440, 900],
  [1100, 760],
] as const)
  test(`desktop ${width}: index, chapters and layout`, async ({ page }) => {
    await open(page, width, height);
    expect(await noSideScroll(page)).toBe(true);
    expect(await clipped(page)).toEqual([]);
    const index = page.getByRole("navigation", {
      name: "Capítulos de la Normativa",
    });
    await index.getByRole("link", { name: /Sistema competitivo/ }).click();
    await expect(page).toHaveURL(/#nv-competicion$/);
    await expect(
      page.getByRole("heading", { level: 2, name: "Sistema competitivo" }),
    ).toBeInViewport();
    await expect(
      index.getByRole("link", { name: /Sistema competitivo/ }),
    ).toHaveAttribute("aria-current", "true");
    await index.getByRole("link", { name: /Normas Nuzlocke/ }).click();
    await expect(
      page.getByRole("heading", { level: 2, name: "Normas Nuzlocke" }),
    ).toBeInViewport();
    await capture(page, `normativa-${width}`);
  });

test("narrow: one column, chips index, no sideways scroll", async ({
  page,
}) => {
  await open(page, 390, 844);
  expect(await noSideScroll(page)).toBe(true);
  expect(await clipped(page)).toEqual([]);
  const index = page.getByRole("navigation", {
    name: "Capítulos de la Normativa",
  });
  await index.getByRole("link", { name: /Límites de nivel/ }).click();
  await expect(
    page.getByRole("heading", { level: 2, name: "Límites de nivel" }),
  ).toBeInViewport();
  await expect(page.locator(".nv-level").last()).toContainText("82");
  await capture(page, "normativa-390");
});

test("a trainer without administration rights can open it", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await fixture(page);
  await page.route("**/v1/me", (route) =>
    route.fulfill({
      json: {
        trainer_id: tid,
        display_name: "Antonio",
        slug: "anto",
        is_admin: false,
        globally_enabled: true,
      },
    }),
  );
  await login(page);
  const menu = page.getByRole("navigation", { name: "Principal" });
  await expect(menu.getByRole("link", { name: "Administración" })).toHaveCount(
    0,
  );
  await navigate(page, "Normativa");
  await expect(page).toHaveURL(/\/normativa$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Normativa" }),
  ).toBeVisible();
});

test("the level climb reaches its full height", async ({ page }) => {
  await open(page, 1440, 900);
  await page.locator(".nv-climb").scrollIntoViewIfNeeded();
  await expect(page.locator(".nv-climb")).toHaveAttribute("data-state", "lit");
  const heights = () =>
    page
      .locator(".nv-bar")
      .evaluateAll((bars) =>
        bars.map((bar) => Math.round(bar.getBoundingClientRect().height)),
      );
  await expect
    .poll(heights)
    .toEqual(
      [14, 30, 38, 41, 44, 50, 58, 70, 78, 82].map((level) =>
        Math.round(level * 3.05),
      ),
    );
  const flags = await page.locator(".nv-flag").allTextContents();
  expect(flags).toEqual(["J1", "J2", "J3", "J4"]);
  if (shots)
    await page
      .locator(".nv-climb")
      .screenshot({ path: `${shots}/normativa-climb.png` });
});

test("the score calculator answers with exact tenths", async ({ page }) => {
  await open(page, 1280, 800);
  const calc = page.locator(".nv-calc");
  await calc.getByRole("button", { name: "Añadir victorias" }).click();
  await calc.getByRole("button", { name: "Añadir muertes ordinarias" }).click();
  await expect(calc.locator(".nv-calc-result strong")).toHaveText("2,8");
});

test("a direct link opens its chapter", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await fixture(page);
  await login(page);
  await page.goto("/normativa#nv-comodines");
  await expect(
    page.getByRole("heading", {
      level: 2,
      name: "Interacciones y comodines",
    }),
  ).toBeInViewport();
});
