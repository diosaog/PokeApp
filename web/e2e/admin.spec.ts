import { test, expect, type Page, type Route } from "@playwright/test";
import type { Model } from "../src/api/types";
import {
  fixture,
  login,
  navigate,
  sid,
  tid,
  pid,
  day,
  overview,
  players,
} from "./fixtures";

type Setup = Model<"SeasonSetup">;
const configPath = `/v1/admin/seasons/${sid}/config-versions`;
const headers = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Headers": "authorization,content-type,idempotency-key",
  "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
};
async function reply(route: Route, json: unknown, status = 200) {
  if (route.request().method() === "OPTIONS")
    return route.fulfill({ status: 204, headers });
  return route.fulfill({ status, headers, json });
}
function setup(state: Setup["season"]["status"] = "active"): Setup {
  return {
    season: {
      id: sid,
      name: "Liga Horizonte",
      status: state,
      started_at: state === "draft" ? null : "2026-10-01T12:00:00Z",
    },
    initial_assignment_rule: null,
    setup_revision: 7,
    roster_revision: 3,
    config_revision: 2,
    current_matchday_id: state === "draft" ? null : day,
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
        id: "current-config",
        name: "Reglas de Antonio",
        version_number: 1,
        effective_from_matchday: 1,
        total_matchdays: 8,
        division_sizes: { A: 2, B: 2 },
        movement_count: 1,
        scoring: { "1": 10, "2": 8, "3": 6, "4": 4 },
        coin_rewards: { "1": 8, "2": 6, "3": 4, "4": 2 },
        rules: {
          team_lock_required: true,
          last_b_gets_steal: false,
          badge_reward_coins: 0,
          game_completion_reward_coins: 37,
        },
        roster_revision: 3,
        used: true,
        is_current: true,
      },
    ],
    divisions: [],
    memberships: [],
    first_matchday: null,
    readiness: {
      checks: {
        has_roster: true,
        has_valid_config: true,
        has_initial_divisions: true,
        memberships_complete: true,
        first_matchday_prepared: true,
        match_pairs_complete: true,
        pointer_valid: true,
        no_other_active_season: true,
        is_draft: state === "draft",
      },
      blocking_reasons: state === "draft" ? [] : ["is_draft"],
      can_activate: state === "draft",
    },
  };
}
async function adminFixture(
  page: Page,
  read: () => Setup = () => setup(),
  prepare?: () => Promise<void>,
) {
  const commands = await fixture(page);
  await page.route(`**/v1/admin/seasons/${sid}/setup`, (route) =>
    reply(route, read()),
  );
  await page.route(`**/v1/admin/seasons/${sid}/championship`, (route) =>
    reply(route, {
      season_id: sid,
      season_status: read().season.status,
      setup_revision: read().setup_revision,
      state: "incomplete",
      players: [],
      tied_player_ids: [],
      champion_trainer_id: null,
      champion_season_player_id: null,
      resolution_type: null,
      input_hash: null,
      certificate_id: null,
    }),
  );
  await prepare?.();
  await login(page);
  await navigate(page, "Administración");
  return commands;
}
async function configuration(page: Page) {
  await page.getByRole("tab", { name: "Configuración", exact: true }).click();
  await expect(
    page.getByLabel("Nombre de versión", { exact: true }),
  ).toBeVisible();
}

test("new configuration preserves current zero rewards and sends exact revisions and settings", async ({
  page,
}) => {
  const commands = await adminFixture(page);
  await configuration(page);
  await expect(page.getByLabel("Monedas por medalla observada")).toHaveValue(
    "0",
  );
  await expect(
    page.getByLabel("Monedas por vencer al Campeón del juego"),
  ).toHaveValue("37");
  await expect(
    page.getByText(/Ocho medallas o finalizar esta Liga de PokeApp no bastan/),
  ).toBeVisible();
  await page
    .getByLabel("Nombre de versión", { exact: true })
    .fill("Siguiente tramo");
  await page.getByLabel("Primera jornada", { exact: true }).fill("5");
  await page
    .getByRole("button", { name: "Crear versión", exact: true })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(commands).toHaveLength(1);
  expect(commands[0].path).toBe(configPath);
  expect(commands[0].key).toBeTruthy();
  expect(commands[0].body).toEqual({
    name: "Siguiente tramo",
    effective_from_matchday: 5,
    total_matchdays: 8,
    division_sizes: { A: 2, B: 2 },
    movement_count: 1,
    scoring: { "1": 10, "2": 8, "3": 6, "4": 4 },
    coin_rewards: { "1": 8, "2": 6, "3": 4, "4": 2 },
    rules: {
      team_lock_required: true,
      last_b_gets_steal: false,
      badge_reward_coins: 0,
      game_completion_reward_coins: 37,
    },
    expected_config_revision: 2,
    expected_roster_revision: 3,
  });
});

test("invalid reward integers never submit a configuration", async ({
  page,
}) => {
  const commands = await adminFixture(page);
  await configuration(page);
  await page
    .getByLabel("Nombre de versión", { exact: true })
    .fill("Revisión económica");
  await page.getByLabel("Primera jornada", { exact: true }).fill("5");
  for (const label of [
    "Monedas por medalla observada",
    "Monedas por vencer al Campeón del juego",
  ]) {
    const input = page.getByLabel(label);
    for (const value of ["-1", "0.5", "2147483648", ""]) {
      await input.fill(value);
      await page
        .getByRole("button", { name: "Crear versión", exact: true })
        .click();
      expect(
        await input.evaluate((node: HTMLInputElement) => node.validity.valid),
      ).toBe(false);
      expect(commands).toHaveLength(0);
    }
    await input.fill("0");
  }
});

test("a stale configuration requires refresh and deliberate review before a new command", async ({
  page,
}) => {
  let latest = setup();
  const attempts: { key?: string; body: Record<string, unknown> }[] = [];
  await adminFixture(page, () => latest);
  await page.route(`**${configPath}`, async (route) => {
    if (route.request().method() === "OPTIONS") return reply(route, null);
    attempts.push({
      key: route.request().headers()["idempotency-key"],
      body: route.request().postDataJSON(),
    });
    if (attempts.length === 1) {
      latest = structuredClone(latest);
      latest.config_revision = 3;
      latest.roster_revision = 4;
      latest.config_versions[0].rules.badge_reward_coins = 21;
      latest.config_versions[0].rules.game_completion_reward_coins = 0;
      return reply(route, { detail: { code: "STALE_REVISION" } }, 409);
    }
    return reply(route, { operation_id: "new-config", replayed: false });
  });
  await configuration(page);
  await page
    .getByLabel("Nombre de versión", { exact: true })
    .fill("Mi propuesta antigua");
  await page.getByLabel("Primera jornada", { exact: true }).fill("5");
  await page.getByLabel("Monedas por medalla observada").fill("9");
  await page
    .getByRole("button", { name: "Crear versión", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "La temporada ha cambiado",
  );
  expect(attempts).toHaveLength(1);
  await page
    .getByRole("button", { name: "Actualizar datos antes de continuar" })
    .click();
  await expect(
    page.getByRole("button", { name: "Crear versión", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Revisar configuración actualizada" })
    .click();
  await expect(page.getByLabel("Monedas por medalla observada")).toHaveValue(
    "21",
  );
  await expect(
    page.getByLabel("Monedas por vencer al Campeón del juego"),
  ).toHaveValue("0");
  expect(attempts).toHaveLength(1);
  await page
    .getByLabel("Nombre de versión", { exact: true })
    .fill("Propuesta revisada");
  await page.getByLabel("Primera jornada", { exact: true }).fill("5");
  await page
    .getByRole("button", { name: "Crear versión", exact: true })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(attempts).toHaveLength(2);
  expect(attempts[0].body).toMatchObject({
    expected_config_revision: 2,
    expected_roster_revision: 3,
  });
  expect(attempts[1].body).toMatchObject({
    name: "Propuesta revisada",
    expected_config_revision: 3,
    expected_roster_revision: 4,
    rules: { badge_reward_coins: 21, game_completion_reward_coins: 0 },
  });
  expect(attempts[1].key).not.toBe(attempts[0].key);
});

test("discard requires the season name and reason; invalid lifecycle actions stay disabled", async ({
  page,
}) => {
  const data = setup("draft");
  const commands = await adminFixture(page, () => data);
  await page.getByRole("tab", { name: "Zona de riesgo", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Archivar temporada", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Descartar temporada", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Descartar temporada");
  await expect(dialog).not.toContainText("discard");
  expect(commands).toHaveLength(0);
  await dialog
    .getByLabel("Motivo", { exact: true })
    .fill("Borrador de prueba local sin uso");
  await dialog
    .getByLabel("Escribe Liga Horizonte para confirmar")
    .fill("Otra temporada");
  const confirm = dialog.getByRole("button", { name: "Confirmar operación" });
  if (await confirm.isEnabled()) await confirm.click();
  expect(commands).toHaveLength(0);
  await expect(dialog).toBeVisible();
  await dialog
    .getByLabel("Escribe Liga Horizonte para confirmar")
    .fill("Liga Horizonte");
  await dialog.getByRole("button", { name: "Confirmar operación" }).click();
  await expect(dialog).toHaveCount(0);
  expect(commands).toHaveLength(1);
  expect(commands[0].path).toBe(`/v1/admin/seasons/${sid}/discard`);
  expect(commands[0].body).toEqual({
    expected_revision: 7,
    reason: "Borrador de prueba local sin uso",
    confirmation: "DISCARD",
  });
});

test("League disqualification uses a named trainer, requires a reason, and does not imply Cup exclusion", async ({
  page,
}) => {
  const commands = await adminFixture(
    page,
    () => setup(),
    async () => {
      await page.route(`**/v1/read/seasons/${sid}/overview`, (route) =>
        reply(route, {
          ...overview,
          days: overview.days.map((value) =>
            value.id === day ? { ...value, status: "scheduled" } : value,
          ),
        }),
      );
      await page.route(`**/v1/admin/seasons/${sid}/matchdays/${day}`, (route) =>
        reply(route, {
          season_id: sid,
          matchday_id: day,
          current_matchday_id: day,
          state: "scheduled",
          revision: 2,
          results_revision: 0,
          snapshot_revision: 0,
          matches: overview.matches,
        }),
      );
    },
  );
  await page.getByRole("tab", { name: "Entrenadores", exact: true }).click();
  const trainer = page.locator("section.card").filter({
    has: page.getByRole("heading", { name: "Antonio", exact: true }),
  });
  await expect(trainer).toContainText("Activo");
  await expect(trainer).not.toContainText(pid);
  await trainer.getByRole("button", { name: "Gestionar estado" }).click();
  const dialog = page.getByRole("dialog", {
    name: "Estado de Antonio",
    exact: true,
  });
  await dialog.getByLabel("Acción", { exact: true }).selectOption("disqualify");
  await expect(
    dialog.getByRole("option", {
      name: "Descalificación de la Liga",
      exact: true,
    }),
  ).toHaveCount(1);
  await expect(dialog).toContainText(/no.*Copa/i);
  await dialog
    .getByRole("button", { name: "Confirmar cambio de estado" })
    .click();
  expect(commands).toHaveLength(0);
  await dialog
    .getByLabel("Motivo", { exact: true })
    .fill("Decisión externa de la Liga, con historial conservado");
  await dialog
    .getByRole("button", { name: "Confirmar cambio de estado" })
    .click();
  await expect(dialog).toHaveCount(0);
  expect(commands).toHaveLength(1);
  expect(commands[0].path).toBe(
    `/v1/admin/seasons/${sid}/participants/${pid}/disqualify`,
  );
  expect(commands[0].body).toEqual({
    expected_roster_revision: 3,
    reason: "Decisión externa de la Liga, con historial conservado",
  });
});

test("archived Admin history cannot submit setup, participant or lifecycle changes", async ({
  page,
}) => {
  const commands = await adminFixture(page, () => setup("archived"));
  await expect(page.getByText("Archivada", { exact: true })).toBeVisible();
  await configuration(page);
  await expect(
    page.getByRole("button", { name: "Guardar nombre", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Crear versión", exact: true }),
  ).toBeDisabled();
  await page.getByRole("tab", { name: "Entrenadores", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Añadir a la temporada", exact: true }),
  ).toBeDisabled();
  const actions = page.getByRole("button", {
    name: "Gestionar estado",
    exact: true,
  });
  for (let index = 0; index < (await actions.count()); index++)
    await expect(actions.nth(index)).toBeDisabled();
  await page.getByRole("tab", { name: "Zona de riesgo", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Archivar temporada", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Descartar temporada", exact: true }),
  ).toBeDisabled();
  expect(commands).toHaveLength(0);
});

test("participant sessions cannot open Admin or issue Admin reads through navigation", async ({
  page,
}) => {
  await fixture(page);
  await page.route("**/v1/me", (route) =>
    reply(route, {
      trainer_id: tid,
      display_name: "Antonio",
      is_admin: false,
      globally_enabled: true,
    }),
  );
  const adminRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/v1/admin/"))
      adminRequests.push(request.url());
  });
  await login(page);
  await expect(
    page.getByRole("link", { name: "Administración", exact: true }),
  ).toHaveCount(0);
  await page.evaluate(() => {
    history.pushState({}, "", "/admin");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("tablist", { name: "Administración", exact: true }),
  ).toHaveCount(0);
  expect(adminRequests).toEqual([]);
});

test("an uncertain configuration locks the editor and replays exactly the same request", async ({
  page,
}) => {
  const attempts: { key?: string; body: Record<string, unknown> }[] = [];
  await adminFixture(page);
  await page.route(`**${configPath}`, async (route) => {
    if (route.request().method() === "OPTIONS") return reply(route, null);
    attempts.push({
      key: route.request().headers()["idempotency-key"],
      body: route.request().postDataJSON(),
    });
    return attempts.length === 1
      ? reply(route, { detail: { code: "TEMPORARILY_UNAVAILABLE" } }, 503)
      : reply(route, { operation_id: "replayed-config", replayed: true });
  });
  await configuration(page);
  await page
    .getByLabel("Nombre de versión", { exact: true })
    .fill("Reglas futuras");
  await page.getByLabel("Primera jornada", { exact: true }).fill("5");
  await page.getByLabel("Monedas por medalla observada").fill("7");
  await page
    .getByRole("button", { name: "Crear versión", exact: true })
    .click();
  const retry = page.getByRole("button", {
    name: "Reintentar la misma solicitud",
  });
  await expect(retry).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Crear versión", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByLabel("Nombre de versión", { exact: true }),
  ).toBeDisabled();
  await expect(page.getByLabel("Monedas por medalla observada")).toBeDisabled();
  await expect(page.getByLabel("Versión a configurar")).toBeDisabled();
  const trainersTab = page.getByRole("tab", {
    name: "Entrenadores",
    exact: true,
  });
  const seasonPicker = page.getByRole("combobox", {
    name: "Temporada",
    exact: true,
  });
  const shopLink = page
    .getByRole("navigation", { name: "Principal" })
    .getByRole("link", { name: "Tienda", exact: true });
  const logout = page.getByRole("button", {
    name: "Cerrar sesión",
    exact: true,
  });
  await expect(trainersTab).toBeDisabled();
  await expect(seasonPicker).toBeDisabled();
  await expect(shopLink).toBeDisabled();
  await expect(logout).toBeDisabled();
  await shopLink.click({ force: true });
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByLabel("Monedas por medalla observada")).toHaveValue(
    "7",
  );
  expect(attempts).toHaveLength(1);
  await retry.click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  await expect(trainersTab).toBeEnabled();
  await expect(seasonPicker).toBeEnabled();
  await expect(shopLink).toBeEnabled();
  await expect(logout).toBeEnabled();
  expect(attempts).toHaveLength(2);
  expect(attempts[1]).toEqual(attempts[0]);
  expect(attempts[0].key).toBeTruthy();
  expect(attempts[0].body).toMatchObject({
    expected_config_revision: 2,
    expected_roster_revision: 3,
    rules: { badge_reward_coins: 7, game_completion_reward_coins: 37 },
  });
});

test("readiness uses human explanations and cannot activate an unready season", async ({
  page,
}) => {
  const data = setup("draft");
  data.readiness.checks.has_valid_config = false;
  data.readiness.checks.no_other_active_season = false;
  data.readiness.blocking_reasons = [
    "has_valid_config",
    "no_other_active_season",
    "future_unrecognized_condition",
  ];
  data.readiness.can_activate = false;
  const commands = await adminFixture(page, () => data);
  await expect(page.getByText("Borrador", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Guarda una configuración válida para la plantilla actual."),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Ya hay otra Liga en curso. Debe finalizar antes de activar esta.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Hay una condición de preparación pendiente. Actualiza los datos y revisa la temporada.",
    ),
  ).toBeVisible();
  const panel = page.getByRole("tabpanel");
  for (const raw of [...data.readiness.blocking_reasons, sid, "draft"])
    await expect(panel).not.toContainText(raw);
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Activar Liga", exact: true }),
  ).toBeDisabled();
  expect(commands).toHaveLength(0);
});

test("Admin names, Team Lock presence and configuration remain readable on desktop and mobile", async ({
  page,
}, testInfo) => {
  const data = setup();
  data.participants[2].display_name = "Entrenador_" + "abcdefghij".repeat(6);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const commands = await adminFixture(page, () => data);
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    for (const tab of [
      "Resumen",
      "Configuración",
      "Entrenadores",
      "Competición",
    ]) {
      await page.getByRole("tab", { name: tab, exact: true }).click();
      await expect(page.locator("main .loading")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        `${tab} at ${viewport.width}`,
      ).toBe(true);
      if (tab === "Competición") {
        const locks = page.locator("section.card").filter({
          has: page.getByRole("heading", {
            name: "Equipos fijados para la jornada",
            exact: true,
          }),
        });
        const fixed = locks.locator(".trainer-grid > div").filter({
          has: page.getByRole("heading", { name: "Lucía", exact: true }),
        });
        const pending = locks.locator(".trainer-grid > div").filter({
          has: page.getByRole("heading", { name: "Antonio", exact: true }),
        });
        await expect(fixed).toContainText("Fijado");
        await expect(pending).toContainText("Pendiente");
        await expect(locks).toContainText(
          "no determina si llegó a tiempo o tarde",
        );
        await expect(locks).not.toContainText(tid);
        await expect(
          page.getByRole("combobox", {
            name: "Jornada a gestionar",
            exact: true,
          }),
        ).toContainText("Jornada 4 · En juego");
      }
      await page.screenshot({
        path: testInfo.outputPath(`admin-${viewport.width}-${tab}.png`),
        fullPage: true,
      });
    }
  }
  expect(errors).toEqual([]);
  expect(commands).toHaveLength(0);
});
