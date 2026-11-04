// Synthetic team; all API calls intercepted. Actual app and local sprite files.
import { test, expect } from "@playwright/test";
import { fixture, login, pokemon, tid, pid, sid, overview } from "./fixtures";

test("Home hides form labels, preserves Jalowin and refreshes points after own history confirmation", async ({
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
  let confirmed = false;
  let leagueReads = 0;
  const confirms: unknown[] = [];
  const headers = (origin?: string) => ({
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET,PUT,OPTIONS",
    "Access-Control-Allow-Headers":
      "authorization,content-type,idempotency-key",
  });
  await page.route(`**/v1/read/seasons/${sid}/league`, (route) => {
    leagueReads++;
    return route.fulfill({
      headers: headers(route.request().headers()["origin"]),
      json: {
        season: overview.season,
        days: overview.days,
        rows: [
          {
            season_player_id: pid,
            trainer_id: tid,
            display_name: "Antonio",
            status: "active",
            total_points: confirmed ? "0" : null,
            coin_balance: "4",
            dead_count: 0,
            historical_deaths_source: confirmed
              ? "audited_event_history"
              : "death_history_baseline_required",
          },
        ],
      },
    });
  });
  await page.route(`**/v1/seasons/${sid}/death-history`, (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS")
      return route.fulfill({
        status: 204,
        headers: headers(request.headers()["origin"]),
      });
    if (request.method() === "PUT") {
      confirms.push(request.postDataJSON());
      expect(request.headers()["idempotency-key"]).toBeTruthy();
      confirmed = true;
    }
    return route.fulfill({
      headers: headers(request.headers()["origin"]),
      json: {
        season_id: sid,
        season_player_id: pid,
        trainer_id: tid,
        revision: confirmed ? 3 : 2,
        known: confirmed,
        blocking_reason: confirmed ? null : "death_history_baseline_required",
        actual_deaths: confirmed ? 0 : null,
        wipe_deaths: confirmed ? 0 : null,
        segment_deaths: confirmed ? 0 : null,
        dead_box_number: 7,
        source_sha256: "a".repeat(64),
        confirmed_at: confirmed ? "2026-11-04T12:00:00Z" : null,
        current_matchday_id: null,
        can_confirm: !confirmed,
        confirm_blocker: confirmed ? "death_history_confirmed" : null,
        proposed: confirmed
          ? null
          : { actual_deaths: 0, wipe_deaths: 0, segment_deaths: 0 },
        replayed: false,
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
  await expect(
    page.getByText(/Tus puntos oficiales aparecen como/),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("home-no-form-label.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: /Ir a confirmar mi historial/ }).click();
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
  await page
    .getByRole("button", { name: "Confirmar historial de muertes" })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Confirmar mi historial de muertes",
  });
  await expect(dialog).toContainText("0 muertes reales");
  const before = leagueReads;
  await dialog.getByRole("button", { name: "Confirmar estos valores" }).click();
  await expect(dialog).toBeHidden();
  expect(confirms).toEqual([
    {
      expected_revision: 2,
      source_sha256: "a".repeat(64),
      actual_deaths: 0,
      wipe_deaths: 0,
      segment_deaths: 0,
    },
  ]);
  await expect.poll(() => leagueReads).toBeGreaterThan(before);
  await expect(
    page.getByText("Puntos", { exact: true }).locator("..").locator("strong"),
  ).toHaveText("0");
});
