// Synthetic team; all API calls intercepted. Actual app and local sprite files.
import { test, expect } from "@playwright/test";
import { fixture, login, pokemon, tid, pid, sid, overview } from "./fixtures";

test("Observed points need no confirmation and Home preserves Jalowin", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const commands = await fixture(
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
  await page.route(`**/v1/read/seasons/${sid}/league`, (route) =>
    route.fulfill({
      headers: {
        "Access-Control-Allow-Origin":
          route.request().headers()["origin"] || "*",
      },
      json: {
        season: overview.season,
        days: overview.days,
        rows: [
          {
            season_player_id: pid,
            trainer_id: tid,
            display_name: "Antonio",
            status: "active",
            total_points: "0",
            coin_balance: "4",
            dead_count: 0,
            historical_deaths_source: "audited_event_history",
          },
        ],
      },
    }),
  );
  await page.route(`**/v1/seasons/${sid}/death-history`, (route) => {
    expect(route.request().method()).toBe("GET");
    return route.fulfill({
      headers: {
        "Access-Control-Allow-Origin":
          route.request().headers()["origin"] || "*",
      },
      json: {
        season_id: sid,
        season_player_id: pid,
        trainer_id: tid,
        known: true,
        revision: 2,
        actual_deaths: 0,
        wipe_deaths: 0,
        segment_deaths: 0,
        confirmed_at: null,
        can_confirm: false,
        confirm_blocker: "death_history_confirmed",
        proposed: null,
        blocking_reason: null,
        dead_box_number: 7,
        source_sha256: "a".repeat(64),
        current_matchday_id: null,
      },
    });
  });
  await login(page);
  const home = page.getByLabel("Equipo de tu partida");
  await expect(home.getByAltText("Gourgeist")).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/711-form-2.png",
  );
  await expect(home.getByText(/Forma \d/)).toHaveCount(0);
  await expect
    .poll(() =>
      home
        .locator("img.pokemon-sprite")
        .evaluateAll(
          (images) =>
            images.length === 6 &&
            images.every(
              (image) =>
                (image as HTMLImageElement).complete &&
                (image as HTMLImageElement).naturalWidth > 0,
            ),
        ),
    )
    .toBe(true);
  await expect(
    page.getByRole("link", { name: /confirmar mi historial/i }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Puntos", { exact: true }).locator("..").locator("strong"),
  ).toHaveText("0");
  await page.screenshot({
    path: info.outputPath("automatic-points-home.png"),
    fullPage: true,
  });
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
  await expect(
    page.getByRole("button", { name: /confirmar.*historial/i }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Puntos", { exact: true }).locator("..").locator("strong"),
  ).toHaveText("0");
  expect(commands.filter(({ path }) => !path.startsWith("/v1/auth/"))).toEqual(
    [],
  );
  await panel.screenshot({ path: info.outputPath("jalowin-form-2.png") });
});
