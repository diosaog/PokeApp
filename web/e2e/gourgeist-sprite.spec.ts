// Synthetic team; all API calls intercepted. Actual app and local sprite files.
import { test, expect } from "@playwright/test";
import { fixture, login, pokemon, tid } from "./fixtures";

test("Jalowin keeps form 2 and loads its Gourgeist Large sprite in My Team", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await fixture(
    page,
    false,
    process.env.POKEAPP_E2E_API_ORIGIN || "http://127.0.0.1:8000",
  );
  await page.route("**/v1/**/pc", (route) =>
    route.fulfill({
      headers: {
        "Access-Control-Allow-Origin":
          route.request().headers()["origin"] || "*",
      },
      json: {
        status: "ready",
        save: {
          id: "synthetic-y",
          game: "Y",
          uploaded_at: "2026-11-04T12:00:00Z",
        },
        pokemon: Array.from({ length: 6 }, (_, i) => ({
          location: `Equipo · ${i + 1}`,
          pokemon:
            i === 0
              ? {
                  ...pokemon,
                  species: "Gourgeist",
                  nickname: "Jalowin",
                  form: 2,
                }
              : pokemon,
        })),
      },
    }),
  );
  await login(page);
  await page.goto(`/entrenadores/${tid}`);
  const panel = page.locator(".party-panel");
  await expect(panel.getByText("Jalowin", { exact: true })).toBeVisible();
  await expect(panel.getByText("Forma 2", { exact: true })).toBeVisible();
  const sprite = panel.getByAltText("Gourgeist", { exact: true });
  await expect(sprite).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/711-form-2.png",
  );
  await expect
    .poll(() =>
      sprite.evaluate(
        (image: HTMLImageElement) => image.complete && image.naturalWidth > 0,
      ),
    )
    .toBe(true);
  await expect(panel.locator("img.pokemon-sprite")).toHaveCount(6);
  await expect(panel.locator(".pokemon-sprite.unresolved")).toHaveCount(0);
  await panel.screenshot({ path: info.outputPath("jalowin-form-2.png") });
});
