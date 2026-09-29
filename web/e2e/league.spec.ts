import { test, expect } from "@playwright/test";
import { fixture, login, navigate, overview, players, day } from "./fixtures";

for (const state of [
  "no-days",
  "current-first",
  "closed-plus-current",
  "final-closed",
]) {
  test(`GENERAL and reached days: ${state}`, async ({ page }) => {
    await fixture(page);
    const general = {
      season: {
        ...overview.season,
        current_matchday_id: state === "no-days" ? null : day,
      },
      days:
        state === "no-days"
          ? []
          : [
              {
                id: day,
                number: state === "current-first" ? 1 : 4,
                status: state === "final-closed" ? "closed" : "open",
              },
              ...(state === "current-first"
                ? []
                : [{ id: "old-day", number: 3, status: "closed" }]),
              // Deliberately overbroad transport fixture: frontend must still hide future days.
              { id: "future", number: 5, status: "scheduled" },
            ],
      rows: players.map((p, i) => ({
        season_player_id: p.id,
        trainer_id: p.trainer_id,
        display_name: p.display_name,
        status: i === 0 ? "retired" : p.status,
        total_points:
          i < 2
            ? "5.12345678901234567890123456789"
            : "-9007199254740993.123456789",
        points_source_matchday_id:
          state === "no-days" || state === "current-first" ? null : "old-day",
        coin_balance: i === 0 ? "-4294967294" : "12",
        dead_count: i === 0 ? null : i === 1 ? 0 : 5,
        dead_count_source: i === 0 ? "unknown" : "observed_current_save",
        dead_count_observed_at: i === 0 ? null : "2026-09-29T12:00:00Z",
      })),
    };
    let generalReads = 0,
      dailyReads = 0;
    page.on("request", (request) => {
      if (request.url().endsWith("/league")) generalReads++;
      if (request.url().endsWith("/overview")) dailyReads++;
    });
    await page.route("**/v1/read/seasons/*/league", (route) =>
      route.fulfill({ json: general }),
    );
    await login(page);
    await expect(page.getByText("128", { exact: false }).first()).toBeVisible();
    const before = dailyReads;
    await navigate(page, "Liga");
    await expect(
      page.getByRole("heading", { name: "Clasificación general" }),
    ).toBeVisible();
    expect(dailyReads).toBe(before); // GENERAL does not require the 13-read overview.
    // React StrictMode may cancel the first mount's GET and mount again in dev.
    expect(generalReads).toBeGreaterThan(0);
    expect(generalReads).toBeLessThanOrEqual(2);
    await expect(
      page.getByRole("button", { name: "GENERAL", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    await expect(
      page.getByRole("button", { name: "J5", exact: true }),
    ).toHaveCount(0);
    await expect(page.getByRole("columnheader")).toHaveText([
      "Entrenador",
      "Puntos totales",
      "Monedas",
      "Pokémon muertos",
    ]);
    await expect(
      page.getByRole("cell", { name: /^5\.12345678901234567890123456789/ }),
    ).toHaveCount(2);
    await expect(
      page.getByRole("cell", { name: /^-9007199254740993\.123456789/ }),
    ).toHaveCount(2);
    await expect(page.getByText("-4294967294", { exact: true })).toBeVisible();
    await expect(page.getByText("Desconocido", { exact: true })).toBeVisible();
    await expect(page.getByText(/Retirado/)).toBeVisible();
    const visibleDays = page
      .getByRole("navigation", { name: "Vistas de Liga" })
      .getByRole("button");
    await expect(visibleDays).toHaveCount(
      state === "no-days" ? 1 : state === "current-first" ? 2 : 3,
    );
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 900 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBe(true);
    }
    if (state === "closed-plus-current") {
      await page.getByRole("button", { name: "J3", exact: true }).click();
      await expect(page.locator(".podium .card")).toHaveCount(3);
      await expect(
        page.getByRole("heading", { name: "División A", exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "División B", exact: true }),
      ).toBeVisible();
      await page.getByRole("button", { name: "J4", exact: true }).click();
      await expect(
        page.getByText("Aún sin clasificación oficial"),
      ).toBeVisible();
      await page.getByRole("button", { name: "GENERAL", exact: true }).click();
      await expect(
        page.getByRole("heading", { name: "Clasificación general" }),
      ).toBeVisible();
      await page.screenshot({
        path: "test-results/league-general-mobile.png",
        fullPage: true,
      });
    }
  });
}
