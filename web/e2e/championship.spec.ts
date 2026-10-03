import { expect, test, type Page } from "@playwright/test";
import type { Model } from "../src/api/types";
import { fixture, login, navigate, players, sid } from "./fixtures";

const championship = (): Model<"ChampionshipRead"> => ({
  season_id: sid,
  state: "ready",
  setup_revision: 7,
  input_hash: "a".repeat(64),
  players: players.map((player, i) => ({
    season_player_id: player.id,
    trainer_id: player.trainer_id,
    display_name: player.display_name,
    total_points: i === 0 ? "-1.250000000000000001" : "-1.250000000000000000",
    adjusted_deaths: i + 2,
  })),
  tied_player_ids: [],
  champion_trainer_id: players[1].trainer_id,
  resolution_type: "unique_points",
  finalist_status: "OWNER_DECISION_REQUIRED",
  blocking_reason: null,
});
async function openReview(page: Page, current: Model<"ChampionshipRead">) {
  const commands = await fixture(page);
  let reads = 0;
  await page.route(`**/v1/admin/seasons/${sid}/championship`, (route) => {
    if (route.request().method() === "OPTIONS") return route.fallback();
    reads++;
    return route.fulfill({ json: current });
  });
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Zona de riesgo" }).click();
  await expect(
    page.getByRole("heading", { name: "Campeonato de Liga" }),
  ).toBeVisible();
  return { commands, reads: () => reads };
}
test("review preserves exact points and requires its current title evidence to finish", async ({
  page,
}) => {
  const current = championship();
  const { commands, reads } = await openReview(page, current);
  const initialReads = reads();
  await expect(
    page.getByRole("heading", { name: "Campeón de Liga: Lucía" }),
  ).toBeVisible();
  await expect(
    page.getByText("-1.250000000000000001", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Finalizar Liga", exact: true })
    .click();
  await page
    .getByLabel("Escribe Liga Horizonte para confirmar")
    .fill("Liga Horizonte");
  await page.getByRole("button", { name: "Confirmar finalización" }).click();
  await expect.poll(() => commands.length).toBe(1);
  expect(commands[0].path).toBe(`/v1/admin/seasons/${sid}/finish`);
  expect(commands[0].body).toEqual({
    expected_revision: 7,
    input_hash: "a".repeat(64),
  });
  expect(commands[0].key).toBeTruthy();
  await expect.poll(reads).toBe(initialReads + 1);
});
test("BO3 starts unselected and a stale decision refreshes and clears its form", async ({
  page,
}) => {
  const current = championship();
  Object.assign(current, {
    state: "bo3_required",
    champion_trainer_id: null,
    resolution_type: null,
    tied_player_ids: [players[0].id, players[1].id],
  });
  const { commands, reads } = await openReview(page, current);
  const initialReads = reads();
  const winner = page.getByRole("combobox", { name: "Ganador del Mejor de 3" });
  await expect(winner).toHaveValue("");
  await expect(winner.locator("option")).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: "Finalizar Liga", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Registrar ganador del desempate" })
    .click();
  expect(commands).toHaveLength(0);
  await page.route(
    `**/v1/admin/seasons/${sid}/championship/bo3`,
    async (route) => {
      const request = route.request();
      if (request.method() === "OPTIONS") return route.fallback();
      commands.push({
        path: new URL(request.url()).pathname,
        body: request.postDataJSON(),
        key: request.headers()["idempotency-key"],
      });
      if (commands.length === 1) {
        current.input_hash = "b".repeat(64);
        current.setup_revision = 8;
        return route.fulfill({
          status: 409,
          json: { detail: { code: "CHAMPIONSHIP_REVIEW_STALE" } },
        });
      }
      Object.assign(current, {
        state: "ready",
        champion_trainer_id: players[1].trainer_id,
        resolution_type: "championship_bo3",
      });
      return route.fulfill({
        json: { operation_id: "receipt", replayed: false },
      });
    },
  );
  await winner.selectOption(players[1].id);
  await page
    .getByLabel("Resultado y motivo del desempate")
    .fill("Mejor de 3 externo, 2-1.");
  await page
    .getByRole("button", { name: "Registrar ganador del desempate" })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Los datos del campeonato han cambiado",
  );
  await expect.poll(reads).toBe(initialReads + 1);
  await expect(winner).toHaveValue("");
  await expect(page.getByLabel("Resultado y motivo del desempate")).toHaveValue(
    "",
  );
  await winner.selectOption(players[1].id);
  await page
    .getByLabel("Resultado y motivo del desempate")
    .fill("Decisión revisada, Mejor de 3 externo 2-1.");
  await page
    .getByRole("button", { name: "Registrar ganador del desempate" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Campeón de Liga: Lucía" }),
  ).toBeVisible();
  expect(commands[1].body).toEqual({
    expected_revision: 8,
    input_hash: "b".repeat(64),
    winner_season_player_id: players[1].id,
    reason: "Decisión revisada, Mejor de 3 externo 2-1.",
  });
});
test("unapproved title ties stay unresolved without a title mutation", async ({
  page,
}) => {
  const current = championship();
  Object.assign(current, {
    state: "owner_decision_required",
    champion_trainer_id: null,
    resolution_type: null,
    tied_player_ids: players.map((p) => p.id),
  });
  const { commands } = await openReview(page, current);
  await expect(
    page.getByText(/el campeonato sigue sin resolverse/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Finalizar Liga", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Registrar ganador del desempate" }),
  ).toHaveCount(0);
  expect(commands).toHaveLength(0);
});
test("unknown BO3 outcome is retried only explicitly with the original body and key", async ({
  page,
}) => {
  const current = championship();
  Object.assign(current, {
    state: "bo3_required",
    champion_trainer_id: null,
    resolution_type: null,
    tied_player_ids: [players[0].id, players[1].id],
  });
  const { commands } = await openReview(page, current);
  await page.route(`**/v1/admin/seasons/${sid}/championship/bo3`, (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") return route.fallback();
    commands.push({
      path: new URL(request.url()).pathname,
      body: request.postDataJSON(),
      key: request.headers()["idempotency-key"],
    });
    return route.fulfill(
      commands.length === 1
        ? {
            status: 503,
            json: { detail: { code: "SEASON_LIFECYCLE_UNAVAILABLE" } },
          }
        : { json: { operation_id: "receipt", replayed: true } },
    );
  });
  await page
    .getByRole("combobox", { name: "Ganador del Mejor de 3" })
    .selectOption(players[0].id);
  await page
    .getByLabel("Resultado y motivo del desempate")
    .fill("Mejor de 3 externo, 2-0.");
  await page
    .getByRole("button", { name: "Registrar ganador del desempate" })
    .click();
  await expect(
    page.getByRole("button", { name: "Reintentar la misma solicitud" }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Ganador del Mejor de 3" }),
  ).toBeDisabled();
  expect(commands).toHaveLength(1);
  await page
    .getByRole("button", { name: "Reintentar la misma solicitud" })
    .click();
  await expect.poll(() => commands.length).toBe(2);
  expect(commands[1]).toEqual(commands[0]);
});
