import { test, expect } from "@playwright/test";
import {
  fixture,
  login,
  navigate,
  sid,
  tid,
  day,
  overview,
  players,
  pokemon,
} from "./fixtures";

for (const width of [1440, 390])
  test(`trainer cards open safe visual profiles and reuse own PC at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const commands = await fixture(page),
      reads: string[] = [];
    await login(page);
    await navigate(page, "Entrenadores");
    page.on("request", (r) => {
      if (r.method() === "GET") reads.push(new URL(r.url()).pathname);
    });
    await page.locator(`a[href="/entrenadores/rival-trainer"]`).click();
    await expect(
      page.getByRole("heading", { name: "Lucía", exact: true }),
    ).toBeVisible();
    // The official (Team Lock) team; the live save collection below is separate.
    await expect(page.locator(".public-party .pokemon")).toHaveCount(6);
    await expect(page.getByRole("link", { name: "Abrir mi PC" })).toHaveCount(
      0,
    );
    await page.locator(".public-party button").first().click();
    const modal = page.getByRole("dialog");
    await expect(modal).toContainText("Esfera Aural");
    await expect(modal).not.toContainText("Foco interno");
    await expect(modal).not.toContainText("IVs");
    expect(
      reads.some((p) => p.endsWith("/pc") || p.endsWith("/team-preview")),
    ).toBe(false);
    await page.screenshot({
      path: info.outputPath(`rival-detail-${width}.png`),
      fullPage: true,
    });
    await modal.getByRole("button", { name: "Cerrar", exact: true }).click();
    await navigate(page, "Entrenadores");
    await page.locator('a[href="/entrenadores/t4"]').click();
    await expect(page.getByText(/^Aún no hay Team Lock./)).toBeVisible();
    await expect(page.locator(".public-party .pokemon")).toHaveCount(0);
    await navigate(page, "Entrenadores");
    await page.locator(`a[href="/entrenadores/${tid}"]`).click();
    await expect(
      page.getByRole("heading", { name: "Antonio", exact: true }),
    ).toBeVisible();
    await page.locator(".party-slots button").first().click();
    await expect(modal).toContainText("Foco interno");
    await expect(modal).toContainText("IVs");
    await modal.getByRole("button", { name: "Cerrar", exact: true }).click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`self-profile-${width}.png`),
      fullPage: true,
    });
    await expect(
      page.getByRole("link", { name: "Mi PC", exact: true }),
    ).toHaveCount(0);
    // Both old bookmarks and same-origin Launcher links use this route.
    await page.goto("/pc");
    await expect(page).toHaveURL(new RegExp(`/entrenadores/${tid}$`));
    await expect(page.locator(".party-slots button")).toHaveCount(6);
    expect(
      commands.filter((c) => !c.path.startsWith("/v1/auth/")),
    ).toHaveLength(0);
  });

test("own profile uses the newer synced save and retains held item context", async ({
  page,
}) => {
  await fixture(page);
  const pc = (nickname: string, uploaded_at: string) => ({
    status: "ready",
    save: {
      id: "save",
      game: "Y",
      uploaded_at,
      parser_status: "parsed",
      parser_version: "fixture",
    },
    pokemon: [
      {
        location: "Equipo · 1",
        pokemon: {
          ...pokemon,
          nickname,
          item: "Item #158",
          item_generation: 6,
        },
      },
    ],
  });
  for (const [url, value] of [
    [`**/v1/me/pc`, pc("Reciente", "2026-11-01T12:00:00Z")],
    [`**/v1/read/seasons/${sid}/pc`, pc("Anterior", "2026-10-29T12:00:00Z")],
  ] as const) {
    await page.route(url, (route) =>
      route.request().method() === "OPTIONS"
        ? route.fallback()
        : route.fulfill({
            json: value,
            headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:5173" },
          }),
    );
  }
  await login(page);
  await navigate(page, "Entrenadores");
  await page.locator(`a[href="/entrenadores/${tid}"]`).click();
  await expect(page.locator(".party-slots")).toContainText("Reciente");
  await expect(page.locator(".party-slots")).not.toContainText("Anterior");
  await page.locator(".party-slots button").first().click();
  await expect(page.getByRole("dialog")).toContainText("Baya Zidra");
});

test("four Shop categories use metadata, without new HTTP reads or name matching", async ({
  page,
}) => {
  await fixture(page);
  let reads = 0;
  await page.route(`**/v1/read/seasons/${sid}/shop`, (route) => {
    if (route.request().method() === "OPTIONS") return route.fallback();
    reads++;
    return route.fulfill({
      json: {
        balance: "123",
        season_status: "active",
        promotions: [],
        items: ["comodines", "bayas", "competitivos", "crianza"].map(
          (category, i) => ({
            id: `item-${i}`,
            code: `item-${i}`,
            name: `Vale especial ${String.fromCharCode(65 + i)}`,
            description: "Nombre sin categoría",
            category,
            base_price: 5,
          }),
        ),
      },
    });
  });
  await login(page);
  await navigate(page, "Tienda");
  await expect(
    page.getByRole("heading", { name: "Vale especial A" }),
  ).toBeVisible();
  const initial = reads;
  for (const [i, name] of [
    "Comodines",
    "Bayas",
    "Competitivos",
    "Crianza",
  ].entries()) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(
      page.getByRole("heading", {
        name: `Vale especial ${String.fromCharCode(65 + i)}`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".shop-card")).toHaveCount(1);
  }
  expect(reads).toBe(initial);
});

test("eligible participant opens and closes with current revisions and sees refreshed League without reload", async ({
  page,
}) => {
  const commands = await fixture(page);
  let state = "scheduled",
    revision = 2,
    resultRevision = 3,
    leagueReads = 0;
  await page.route("**/v1/me", (route) =>
    route.fulfill({
      json: {
        trainer_id: tid,
        display_name: "Antonio",
        is_admin: false,
        globally_enabled: true,
      },
    }),
  );
  await page.route(`**/v1/read/seasons/${sid}/league`, (route) => {
    leagueReads++;
    return route.fulfill({
      json: {
        season: overview.season,
        days: overview.days.map((d) =>
          d.id === day ? { ...d, status: state } : d,
        ),
        rows: players.map((p) => ({
          season_player_id: p.id,
          trainer_id: p.trainer_id,
          display_name: p.display_name,
          status: "active",
          total_points: "0",
          coin_balance: "0",
          dead_count: null,
        })),
      },
    });
  });
  await page.route(`**/v1/seasons/${sid}/championship`, (route) =>
    route.fulfill({
      json: {
        season_id: sid,
        state: "incomplete",
        setup_revision: 7,
        players: [],
        tied_player_ids: [],
        champion_trainer_id: null,
      },
    }),
  );
  await page.route(`**/v1/seasons/${sid}/matchdays/${day}**`, (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") return route.fallback();
    const path = new URL(request.url()).pathname;
    if (request.method() === "GET")
      return route.fulfill({
        json: {
          season_id: sid,
          matchday_id: day,
          current_matchday_id: day,
          state,
          revision,
          results_revision: resultRevision,
          snapshot_revision: 0,
          matches: [],
        },
      });
    commands.push({
      path,
      body: request.postDataJSON(),
      key: request.headers()["idempotency-key"],
    });
    state = path.endsWith("/open") ? "open" : "closed";
    revision++;
    resultRevision++;
    return route.fulfill({
      json: { operation_id: "accepted", replayed: false },
    });
  });
  await login(page);
  await navigate(page, "Liga");
  // Liga › General: opening sits right below the standings.
  await page
    .getByRole("button", { name: "Abrir jornada 4", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Confirmar apertura", exact: true })
    .click();
  // The opened matchday's own tab ends with its closing control.
  await expect(
    page.getByRole("button", { name: "Cerrar jornada 4", exact: true }),
  ).toBeVisible();
  expect(commands[0].body).toEqual({ expected_revision: 2 });
  await page
    .getByRole("button", { name: "Cerrar jornada 4", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Confirmar cierre", exact: true })
    .click();
  await page.getByRole("button", { name: "GENERAL", exact: true }).click();
  await expect(
    page.getByText("Liga pendiente de completar", { exact: true }),
  ).toBeVisible();
  expect(commands[1].body).toEqual({ expected_results_revision: 4 });
  expect(leagueReads).toBeGreaterThanOrEqual(3);
  expect(commands.every((c) => !c.path.includes("/admin/"))).toBe(true);
});

test("residual championship form uses only server candidates and requires an audited decision", async ({
  page,
}) => {
  const commands = await fixture(page);
  await page.route(`**/v1/admin/seasons/${sid}/championship`, (route) =>
    route.fulfill({
      json: {
        season_id: sid,
        state: "residual_required",
        setup_revision: 7,
        input_hash: "a".repeat(64),
        players: players.map((p) => ({
          season_player_id: p.id,
          trainer_id: p.trainer_id,
          display_name: p.display_name,
          total_points: "5.00",
          adjusted_deaths: 0,
        })),
        tied_player_ids: players.slice(1, 3).map((p) => p.id),
        champion_trainer_id: null,
        resolution_type: null,
      },
    }),
  );
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Zona de riesgo" }).click();
  const select = page.getByLabel("Ganador del desempate externo");
  await expect(select).toHaveValue("");
  await expect(select.locator("option")).toHaveCount(3);
  await select.selectOption(players[2].id);
  await page
    .getByLabel("Resultado y motivo del desempate")
    .fill("Desempate externo acordado");
  await page
    .getByRole("button", { name: "Registrar ganador del desempate" })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(commands[0].path).toBe(
    `/v1/admin/seasons/${sid}/championship/residual`,
  );
  expect(commands[0].body).toMatchObject({
    winner_season_player_id: players[2].id,
    reason: "Desempate externo acordado",
    input_hash: "a".repeat(64),
  });
});
