import { test, expect } from "@playwright/test";
import { fixture, login, navigate, tid } from "./fixtures";

// Artistic Evolution: sounds and animations are on by default, can be changed
// from the own profile, persist in this browser and never break the page.
test("audio-visual preferences default on, persist and apply", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await fixture(page);
  await login(page);
  await expect(page.locator("html")).toHaveAttribute("data-motion", "full");
  const mute = page.getByRole("button", { name: "Silenciar sonidos" });
  await expect(mute).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.locator(".home-sprites .pokemon-sprite").first(),
  ).toHaveAttribute("src", /animated.*gif/);

  await navigate(page, "Entrenadores");
  await page.locator(`a[href='/entrenadores/${tid}']`).first().click();
  const settings = page.locator(".prefs-card");
  await expect(settings.getByRole("heading")).toHaveText("Ajustes de la app");
  await settings
    .getByRole("group", { name: "Animaciones" })
    .getByRole("button", { name: "Reducidas" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-motion", "reduced");
  await settings
    .getByRole("group", { name: "Sonidos" })
    .getByRole("button", { name: "Desactivados" })
    .click();
  await expect(
    page.getByRole("button", { name: "Activar sonidos" }),
  ).toHaveAttribute("aria-pressed", "false");
  await expect(settings.getByRole("slider")).toBeDisabled();

  // Same browser, new visit: the choices are still there and applied.
  await login(page);
  await expect(page.locator("html")).toHaveAttribute("data-motion", "reduced");
  await expect(
    page.locator(".home-sprites .pokemon-sprite").first(),
  ).toHaveAttribute("src", /pokemon.*png/);
  expect(
    await page
      .locator(".home-stage")
      .evaluate((e) => getComputedStyle(e, "::before").animationName),
  ).toBe("none");
  await expect(
    page.getByRole("button", { name: "Activar sonidos" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      JSON.parse(localStorage.getItem("pokeapp.preferences.v1") || "{}"),
    ),
  ).toEqual({ sound: false, volume: 0.5, motion: "reduced" });
  // Turning sound back on from the sidebar plays only after a gesture: no errors.
  await page.getByRole("button", { name: "Activar sonidos" }).click();
  await expect(mute).toBeVisible();
  expect(errors).toEqual([]);
});

test("the system reduced-motion request wins over the default", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await fixture(page);
  await login(page);
  await expect(page.locator("html")).toHaveAttribute("data-motion", "reduced");
});
