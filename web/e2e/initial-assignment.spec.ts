import { expect, test, type Page } from "@playwright/test";
import { fixture, login, navigate, overview, players, sid } from "./fixtures";

const initial = () => ({
  season_id: sid,
  rule: "observed_deaths_v1",
  state: "pending",
  config_version_id: "initial-config",
  division_sizes: { A: 2, B: 2 },
  setup_revision: 7,
  roster_revision: 3,
  input_hash: "a".repeat(64),
  ready: true,
  blocking_reasons: [] as string[],
  players: players.map((player, index) => ({
    id: player.id,
    trainer_id: player.trainer_id,
    display_name: player.display_name,
    progress_state: "observed",
    observed_badges: 2 as number | null,
    cap_reached: true,
    adjusted_deaths: (Math.floor(index / 2) + 1) as number | null,
    proposed_division: (index < 2 ? "A" : "B") as string | null,
  })),
  boundary_tie: null as null | {
    player_ids: string[];
    adjusted_deaths: number;
    places_in_a: number;
  },
});

async function modernFixture(
  page: Page,
  current: () => ReturnType<typeof initial>,
) {
  const commands = await fixture(page);
  const season = {
    ...overview.season,
    current_matchday_id: null,
    initial_assignment_rule: "observed_deaths_v1",
  };
  await page.route(`**/v1/admin/seasons/${sid}/setup`, (route) =>
    route.fulfill({
      json: {
        season,
        initial_assignment_rule: "observed_deaths_v1",
        setup_revision: 7,
        roster_revision: 3,
        config_revision: 2,
        current_matchday_id: null,
        participants: players.map((p) => ({
          ...p,
          stats_ready: true,
          seed_order: 1,
        })),
        config_versions: [],
        divisions: [],
        memberships: [],
        first_matchday: null,
        readiness: { checks: {}, blocking_reasons: [], can_activate: false },
      },
    }),
  );
  await page.route(`**/v1/read/seasons/${sid}/overview`, (route) =>
    route.fulfill({
      json: {
        ...overview,
        players: players.map((player) => ({
          ...player,
          badges_count:
            current().players.find((p) => p.id === player.id)
              ?.observed_badges ?? null,
          progress:
            current().players.find((p) => p.id === player.id)
              ?.progress_state === "observed"
              ? {
                  state: "observed",
                  badges_count: current().players.find(
                    (p) => p.id === player.id,
                  )?.observed_badges,
                  regions: [
                    {
                      region: "unova",
                      earned_badges: Array.from(
                        {
                          length:
                            current().players.find((p) => p.id === player.id)
                              ?.observed_badges ?? 0,
                        },
                        (_, i) => i + 1,
                      ),
                    },
                  ],
                  champion_defeated: null,
                }
              : { state: "unknown" },
        })),
        season,
        days: [],
        matches: [],
        snapshots: [],
        memberships: [],
      },
    }),
  );
  await page.route(`**/v1/read/seasons/${sid}/league`, (route) =>
    route.fulfill({ json: { season, days: [], rows: [] } }),
  );
  const reads: string[] = [];
  await page.route(`**/v1/seasons/${sid}/initial-assignment`, (route) => {
    reads.push(route.request().url());
    return route.fulfill({ json: current() });
  });
  return { commands, reads };
}

test("unobserved progress differs from observed zero; no manual accreditation or premature split", async ({
  page,
}) => {
  const state = initial();
  state.ready = false;
  state.blocking_reasons = ["progress_unobserved", "cap_not_reached"];
  state.players.forEach((p) => {
    p.proposed_division = null;
  });
  Object.assign(state.players[0], {
    progress_state: "unknown",
    observed_badges: null,
    cap_reached: false,
    adjusted_deaths: null,
  });
  Object.assign(state.players[1], { observed_badges: 0, cap_reached: false });
  const { commands, reads } = await modernFixture(page, () => state);
  await login(page);
  await navigate(page, "Liga");
  await expect(
    page.getByRole("heading", { name: "Reparto inicial A/B" }),
  ).toBeVisible();
  const unknown = page.getByRole("region", { name: "Antonio", exact: true });
  const zero = page.getByRole("region", { name: "Lucía", exact: true });
  await expect(unknown).toContainText(
    "Progreso no observado / pendiente de sincronizar save",
  );
  await expect(unknown).not.toContainText("0 medallas");
  await expect(zero).toContainText(
    "0 medallas observadas · Medalla 2 pendiente",
  );
  await expect(
    page.getByRole("button", { name: "Confirmar reparto inicial" }),
  ).toHaveCount(0);
  await navigate(page, "Entrenadores");
  await expect(
    page.getByText("Progreso no observado · Pendiente de sincronizar save.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("0 medallas observadas", { exact: true }),
  ).toBeVisible();
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Confirmar reparto inicial" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Guardar divisiones iniciales" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Preparar jornada" }),
  ).toHaveCount(0);
  await expect(page.getByRole("spinbutton")).toHaveCount(0);
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(unknown).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  expect(commands).toHaveLength(0);
  // Development StrictMode may abort and restart the initial aggregate read.
  expect(new Set(reads).size).toBe(1);
  expect(reads.length).toBeLessThanOrEqual(2);
});

test("neutral ties inside divisions require no ordering and submit only the observed revision", async ({
  page,
}) => {
  const state = initial();
  const { commands } = await modernFixture(page, () => state);
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await expect(
    page.getByText("Listo para confirmar el reparto", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/No hay empate que cruce el corte/),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Antonio", exact: true }),
  ).toContainText("Propuesta: A");
  await expect(
    page.getByRole("region", { name: "Marcos", exact: true }),
  ).toContainText("Propuesta: B");
  await expect(page.getByLabel(/Orden del empate/)).toHaveCount(0);
  await page.getByRole("button", { name: "Confirmar reparto inicial" }).click();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Cambio confirmado" })
      .filter({ hasText: "Cambio confirmado" }),
  ).toBeVisible();
  expect(commands).toHaveLength(1);
  expect(commands[0].path).toBe(
    `/v1/admin/seasons/${sid}/initial-assignment/finalize`,
  );
  expect(commands[0].body).toEqual({
    config_version_id: "initial-config",
    expected_setup_revision: 7,
    expected_roster_revision: 3,
    input_hash: "a".repeat(64),
  });
  expect(commands[0].key).toBeTruthy();
});

test("boundary decision starts empty, resets stale evidence and preserves the exact unknown-outcome retry", async ({
  page,
}) => {
  const state = initial();
  state.boundary_tie = {
    player_ids: players.slice(1).map((p) => p.id),
    adjusted_deaths: 3,
    places_in_a: 1,
  };
  state.players.slice(1).forEach((p) => {
    p.adjusted_deaths = 3;
    p.proposed_division = null;
  });
  const { reads } = await modernFixture(page, () => state);
  const sent: { body: Record<string, unknown>; key?: string }[] = [];
  await page.route(
    `**/v1/admin/seasons/${sid}/initial-assignment/finalize`,
    (route) => {
      sent.push({
        body: route.request().postDataJSON(),
        key: route.request().headers()["idempotency-key"],
      });
      if (sent.length === 1) {
        state.input_hash = "b".repeat(64);
        state.setup_revision = 8;
        return route.fulfill({
          status: 409,
          json: { detail: { code: "INITIAL_ASSIGNMENT_REVIEW_STALE" } },
        });
      }
      if (sent.length === 2)
        return route.fulfill({
          status: 503,
          json: { detail: { code: "INITIAL_ASSIGNMENT_UNAVAILABLE" } },
        });
      return route.fulfill({
        json: { operation_id: "initial-receipt", replayed: true },
      });
    },
  );
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  const choices = [1, 2, 3].map((n) =>
    page.getByLabel(`Orden del empate · puesto ${n}`, { exact: true }),
  );
  const reason = page.getByLabel("Motivo de la decisión externa");
  const submit = page.getByRole("button", {
    name: "Confirmar reparto inicial",
  });
  for (const choice of choices) await expect(choice).toHaveValue("");
  await submit.click();
  expect(sent).toHaveLength(0);
  const order = ["p4", "rival-player", "p3"];
  for (let i = 0; i < choices.length; i++)
    await choices[i].selectOption(order[i]);
  await expect(choices[1].locator('option[value="p4"]')).toBeDisabled();
  await submit.click();
  expect(sent).toHaveLength(0);
  await reason.fill("Decisión externa documentada");
  const readsBeforeConflict = reads.length;
  await submit.click();
  await expect(page.getByRole("alert")).toContainText(
    "El progreso o las muertes han cambiado",
  );
  await expect.poll(() => reads.length).toBe(readsBeforeConflict + 1);
  for (const choice of choices) await expect(choice).toHaveValue("");
  await expect(reason).toHaveValue("");
  expect(sent).toHaveLength(1);
  await page.setViewportSize({ width: 390, height: 844 });
  for (let i = 0; i < choices.length; i++)
    await choices[i].selectOption(order[i]);
  await reason.fill("Decisión revisada con nueva evidencia");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/initial-boundary-mobile.png",
    fullPage: true,
  });
  await submit.click();
  const retry = page.getByRole("button", {
    name: "Reintentar la misma solicitud",
  });
  await expect(retry).toBeVisible();
  await expect(submit).toBeDisabled();
  await expect(choices[0]).toBeDisabled();
  expect(sent).toHaveLength(2);
  await retry.click();
  await expect(
    page.getByRole("status").filter({ hasText: "Cambio confirmado" }),
  ).toContainText("Cambio confirmado");
  expect(sent).toHaveLength(3);
  expect(sent[1]).toEqual(sent[2]);
  expect(sent[1].body).toEqual({
    config_version_id: "initial-config",
    expected_setup_revision: 8,
    expected_roster_revision: 3,
    input_hash: "b".repeat(64),
    tie_resolution: {
      input_hash: "b".repeat(64),
      orders: [
        { player_ids: order, reason: "Decisión revisada con nueva evidencia" },
      ],
    },
  });
});

test("recorded modern assignment is read-only; legacy retains its established manual setup", async ({
  page,
}) => {
  const state = initial();
  state.state = "assigned";
  state.ready = false;
  state.blocking_reasons = ["initial_assignment_locked"];
  await modernFixture(page, () => state);
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await expect(
    page.getByText("Reparto registrado", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Antonio", exact: true }),
  ).toContainText("División: A");
  await expect(
    page.getByRole("button", { name: "Confirmar reparto inicial" }),
  ).toHaveCount(0);
  await page.unrouteAll();
  await fixture(page);
  await page.reload();
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Guardar divisiones iniciales" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Reparto inicial A/B" }),
  ).toHaveCount(0);
});
