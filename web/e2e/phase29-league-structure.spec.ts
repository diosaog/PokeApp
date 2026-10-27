import { test, expect, type Page, type Route } from "@playwright/test";
import { fixture, login, navigate, overview, players, sid } from "./fixtures";

// Phase 29: one league or Liga A + Liga B per season, and the admin
// cancellation of a still-reversible robbery. Synthetic data only.
const api = "http://127.0.0.1:8000";
const headers = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Headers": "authorization,content-type,idempotency-key",
  "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
};
async function reply(route: Route, json: unknown) {
  if (route.request().method() === "OPTIONS")
    return route.fulfill({ status: 204, headers });
  return route.fulfill({ status: 200, headers, json });
}
// Uncaught errors and console errors, except the fixture's deliberate 404s
// for reads a screen does not need.
function watchConsole(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      !message.text().startsWith("Failed to load resource")
    )
      errors.push(message.text());
  });
  return errors;
}
async function fitsWidth(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
}

const draftSetup = {
  season: {
    id: sid,
    name: "Liga Horizonte",
    status: "draft",
    started_at: null,
  },
  initial_assignment_rule: "observed_deaths_v1",
  setup_revision: 7,
  roster_revision: 3,
  config_revision: 2,
  current_matchday_id: null,
  participants: players.map((p, index) => ({
    id: p.id,
    trainer_id: p.trainer_id,
    display_name: p.display_name,
    status: "active",
    seed_order: index + 1,
    stats_ready: true,
  })),
  config_versions: [
    {
      id: "draft-config",
      name: "Reglas de la Liga",
      version_number: 1,
      effective_from_matchday: 1,
      total_matchdays: 6,
      division_sizes: { A: 2, B: 2 },
      movement_count: 1,
      scoring: { "1": 10, "2": 8, "3": 6, "4": 4 },
      coin_rewards: { "1": 8, "2": 6, "3": 4, "4": 2 },
      rules: {
        team_lock_required: true,
        last_b_gets_steal: true,
        badge_reward_coins: 4,
        game_completion_reward_coins: 12,
      },
      roster_revision: 3,
      used: false,
      is_current: true,
    },
  ],
  divisions: [],
  memberships: [],
  first_matchday: null,
  readiness: {
    checks: { has_roster: true, has_valid_config: true, is_draft: true },
    blocking_reasons: ["has_initial_divisions"],
    can_activate: false,
  },
};

for (const width of [1440, 390]) {
  test(`admin chooses one league or Liga A + Liga B at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const errors = watchConsole(page);
    const commands = await fixture(page);
    await page.route(`**/v1/admin/seasons/${sid}/setup`, (route) =>
      reply(route, draftSetup),
    );
    await login(page);
    await navigate(page, "Administración");
    await page.getByRole("tab", { name: "Configuración", exact: true }).click();
    const choice = page.getByRole("group", {
      name: "Estructura de competición",
    });
    await expect(choice).toBeVisible();
    // The stored config has a B division: Liga A + Liga B is preselected.
    await expect(choice.getByLabel(/Liga A y Liga B/)).toBeChecked();
    await expect(page.getByLabel("Participantes en B")).toBeVisible();
    await expect(page.getByText("Último de B recibe robo")).toBeVisible();
    await choice.scrollIntoViewIfNeeded();
    await page.screenshot({
      path: info.outputPath(`structure-two-${width}.png`),
    });
    await choice.getByLabel(/Una Liga/).check();
    await expect(page.getByLabel("Participantes en A")).toHaveCount(0);
    await expect(page.getByLabel("Participantes en B")).toHaveCount(0);
    await expect(page.getByLabel("Ascensos / descensos")).toHaveCount(0);
    await expect(page.getByText("Último de B recibe robo")).toHaveCount(0);
    await expect(page.getByText(/Participantes en la Liga/)).toContainText(
      String(players.length),
    );
    await fitsWidth(page);
    await page.screenshot({
      path: info.outputPath(`structure-single-${width}.png`),
    });
    await page.getByRole("button", { name: "Guardar formato" }).click();
    await expect(page.getByText("Cambio confirmado.")).toBeVisible();
    expect(commands).toHaveLength(1);
    expect(commands[0].path).toBe(
      `/v1/admin/seasons/${sid}/config-versions/draft-config/replace-unused`,
    );
    expect(commands[0].body).toMatchObject({
      total_matchdays: 6,
      division_sizes: { A: players.length },
      movement_count: 0,
      rules: { last_b_gets_steal: false },
      expected_config_revision: 2,
      expected_roster_revision: 3,
    });
    expect(commands[0].body.division_sizes).not.toHaveProperty("B");
    expect(commands[0].key).toBeTruthy();
    expect(errors).toEqual([]);
  });

  test(`a matchday shows «Liga» for one league and División A/B for two at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const errors = watchConsole(page);
    let single = true;
    await fixture(page);
    // One league: a single division and every standing inside it.
    await page.route(`**/v1/read/seasons/${sid}/overview`, (route) =>
      reply(
        route,
        single
          ? {
              ...overview,
              divisions: [{ id: "division", code: "A", name: "Liga" }],
              snapshots: overview.snapshots.map((snapshot) => ({
                ...snapshot,
                standings: snapshot.standings.map((s) => ({
                  ...s,
                  division: "A",
                  division_position: s.position,
                })),
              })),
            }
          : overview,
      ),
    );
    await login(page);
    await navigate(page, "Liga");
    await page.getByRole("button", { name: "J3", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Liga", exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: /^División/ })).toHaveCount(
      0,
    );
    const table = page.locator(".table-scroll table");
    await expect(table).toHaveCount(1);
    await expect(table.locator("tbody tr")).toHaveCount(players.length);
    await expect(table.locator("tbody tr").first()).toContainText("Antonio");
    await fitsWidth(page);
    await page.screenshot({
      path: info.outputPath(`league-single-${width}.png`),
      fullPage: true,
    });
    // Two leagues: the overview lists only A, yet its standings hold B too,
    // so División B is never hidden.
    // The session is never stored in the browser: sign in again.
    single = false;
    await login(page);
    await navigate(page, "Liga");
    await page.getByRole("button", { name: "J3", exact: true }).click();
    for (const name of ["División A", "División B"])
      await expect(
        page.getByRole("heading", { name, exact: true }),
      ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Liga", exact: true }),
    ).toHaveCount(0);
    await expect(table).toHaveCount(2);
    await fitsWidth(page);
    await page.screenshot({
      path: info.outputPath(`league-two-${width}.png`),
      fullPage: true,
    });
    expect(errors).toEqual([]);
  });

  test(`admin cancels a reversible robbery; a decided one needs reconciliation at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const errors = watchConsole(page);
    const incidents = `/v1/admin/seasons/${sid}/incidents`;
    const reversible = "33333333-3333-4333-8333-333333333333";
    const posts: { path: string; body: unknown; key?: string }[] = [];
    let cancelled = false;
    const read = () => ({
      season_id: sid,
      season_status: "active",
      wallets: [
        {
          trainer_id: "t3",
          display_name: "Marcos",
          status: "active",
          balance: 8,
        },
        {
          trainer_id: "t4",
          display_name: "Elena",
          status: "active",
          balance: 40,
        },
      ],
      purchases: [],
      robberies: [
        {
          authorization_id: reversible,
          purchase_id: "22222222-2222-4222-8222-222222222222",
          requester: "Marcos",
          donor: "Elena",
          state: cancelled ? "CANCELLED" : "REQUESTED",
          source_obligation: null,
          destination_obligation: null,
          price: 50,
          cancellable: !cancelled,
          reconciliation_required: false,
          cancelled_by_admin: cancelled,
          created_at: "2026-10-26T10:00:00Z",
        },
        {
          authorization_id: "66666666-6666-4666-8666-666666666666",
          purchase_id: "77777777-7777-4777-8777-777777777777",
          requester: "Lucía",
          donor: "Antonio",
          state: "COMPETITIVELY_ADJUDICATED",
          source_obligation: "DONOR_PHYSICAL_PENDING",
          destination_obligation: "RECIPIENT_PHYSICAL_PENDING",
          price: 50,
          cancellable: false,
          reconciliation_required: true,
          cancelled_by_admin: false,
          created_at: "2026-10-25T10:00:00Z",
        },
      ],
      history: cancelled
        ? [
            {
              operation_id: "44444444-4444-4444-8444-444444444444",
              kind: "robbery_cancel",
              actor: "Antonio",
              target: "Marcos",
              purchase_id: "22222222-2222-4222-8222-222222222222",
              amount: 50,
              reason: "Robo solicitado por error",
              status: "cancelled",
              created_at: "2026-10-27T10:00:00Z",
            },
          ]
        : [],
    });
    await fixture(page);
    await page.route(`${api}${incidents}**`, async (route) => {
      const request = route.request();
      if (request.method() === "POST") {
        posts.push({
          path: new URL(request.url()).pathname,
          body: request.postDataJSON(),
          key: request.headers()["idempotency-key"],
        });
        cancelled = true;
        return reply(route, {
          operation_id: request.headers()["idempotency-key"],
          kind: "robbery_cancel",
          season_id: sid,
          trainer_id: "t3",
          purchase_id: "22222222-2222-4222-8222-222222222222",
          authorization_id: reversible,
          status: "cancelled",
          amount: 50,
          ledger_id: "55555555-5555-4555-8555-555555555555",
          balance_after: 58,
          replayed: false,
        });
      }
      return reply(route, read());
    });
    await login(page);
    await navigate(page, "Administración");
    await page
      .getByRole("navigation", { name: "Áreas de administración" })
      .getByRole("button", { name: /Economía e incidencias/ })
      .click();
    const robberies = page.locator(
      'section[aria-labelledby="incident-robberies"]',
    );
    await expect(
      robberies.getByRole("button", { name: "Anular robo" }),
    ).toHaveCount(1);
    await expect(robberies.getByText("Requiere conciliación")).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`robberies-${width}.png`),
      fullPage: true,
    });
    await robberies.getByRole("button", { name: "Anular robo" }).click();
    const dialog = page.getByRole("dialog", { name: "Anular robo" });
    await expect(dialog).toContainText("Marcos");
    await expect(dialog).toContainText("Elena");
    await expect(dialog).toContainText("50 PK₽");
    await expect(dialog).toContainText(
      "No se ha escrito nada en ninguna partida",
    );
    // Without a reason and the review check the form never submits.
    await dialog.getByRole("button", { name: "Confirmar anulación" }).click();
    expect(posts).toHaveLength(0);
    await dialog
      .getByLabel("Motivo (queda en el historial)")
      .fill("Robo solicitado por error");
    await dialog.getByRole("checkbox").check();
    await page.screenshot({
      path: info.outputPath(`robbery-cancel-${width}.png`),
    });
    await dialog.getByRole("button", { name: "Confirmar anulación" }).click();
    await expect(dialog).toBeHidden();
    expect(posts).toHaveLength(1);
    expect(posts[0].path).toBe(`${incidents}/robberies/${reversible}/cancel`);
    expect(posts[0].body).toEqual({ reason: "Robo solicitado por error" });
    expect(posts[0].key).toMatch(/^[0-9a-f-]{36}$/);
    // The console re-reads after the receipt: the robbery and history show it.
    await expect(
      robberies.getByText("Anulado por administración"),
    ).toBeVisible();
    await expect(
      robberies.getByRole("button", { name: "Anular robo" }),
    ).toHaveCount(0);
    await expect(page.getByText("Robo anulado")).toBeVisible();
    await fitsWidth(page);
    expect(errors).toEqual([]);
  });
}
