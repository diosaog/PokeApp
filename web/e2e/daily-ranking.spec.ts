import { test, expect } from "@playwright/test";
import { fixture, login, navigate, day, sid, pid, overview } from "./fixtures";

const review = {
  input_hash: "a".repeat(64),
  groups: [
    {
      division: "A",
      player_ids: [pid, "rival-player"],
      position: 1,
      position_end: 2,
      wins: 2,
      adjusted_deaths: 1,
      consequences: ["podium", "points"],
    },
  ],
};

test("close requires an explicit external order; stale review resets choices and unknown retry preserves body/key", async ({
  page,
}) => {
  await fixture(page);
  const sent: { body: any; key?: string }[] = [];
  await page.route(
    `**/v1/admin/seasons/${sid}/matchdays/${day}/close`,
    async (route) => {
      sent.push({
        body: route.request().postDataJSON(),
        key: route.request().headers()["idempotency-key"],
      });
      if (sent.length <= 2)
        return route.fulfill({
          status: 409,
          json: {
            detail: {
              code:
                sent.length === 1
                  ? "RANKING_TIE_UNRESOLVED"
                  : "RANKING_REVIEW_STALE",
              ranking:
                sent.length === 1
                  ? review
                  : { ...review, input_hash: "b".repeat(64) },
            },
          },
        });
      if (sent.length === 3)
        return route.fulfill({
          status: 503,
          json: { detail: { code: "MATCHDAY_UNAVAILABLE" } },
        });
      return route.fulfill({
        json: { operation_id: "resolved", replayed: true },
      });
    },
  );
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await page
    .getByRole("button", { name: "Cerrar jornada", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Confirmar cierre" }).click();
  const first = dialog.getByLabel("Posición 1 · división A", { exact: true });
  const second = dialog.getByLabel("Posición 2 · división A", { exact: true });
  await expect(first).toHaveValue("");
  await expect(second).toHaveValue("");
  expect(sent).toHaveLength(1);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await expect(first).toBeVisible();
  await first.selectOption("rival-player");
  await second.selectOption(pid);
  await dialog
    .getByLabel(/Motivo del desempate/)
    .fill("Acuerdo externo revisado");
  await page.screenshot({
    path: "test-results/daily-tie-review.png",
    fullPage: true,
  });
  await dialog.getByRole("button", { name: "Confirmar cierre" }).click();
  await expect(first).toHaveValue("");
  await expect(second).toHaveValue("");
  expect(sent).toHaveLength(2);
  await first.selectOption("rival-player");
  await second.selectOption(pid);
  await dialog
    .getByLabel(/Motivo del desempate/)
    .fill("Acuerdo externo confirmado");
  await dialog.getByRole("button", { name: "Confirmar cierre" }).click();
  const retry = dialog.getByRole("button", {
    name: "Reintentar la misma solicitud",
  });
  await expect(retry).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Confirmar cierre" }),
  ).toBeDisabled();
  await retry.click();
  await expect(dialog.getByRole("status")).toContainText("Cambio confirmado");
  expect(sent).toHaveLength(4);
  expect(sent[2]).toEqual(sent[3]);
  expect(sent[2].body.tie_resolution).toEqual({
    input_hash: "b".repeat(64),
    orders: [
      {
        player_ids: ["rival-player", pid],
        reason: "Acuerdo externo confirmado",
      },
    ],
  });
  expect(sent[0].body).toEqual({ expected_results_revision: 3 });
});

test("closed-day correction carries the chosen results, reason and bound external decision", async ({
  page,
}) => {
  await fixture(page);
  await page.route(`**/v1/admin/seasons/${sid}/matchdays/${day}`, (route) =>
    route.fulfill({
      json: {
        season_id: sid,
        matchday_id: day,
        current_matchday_id: day,
        state: "closed",
        revision: 4,
        results_revision: 3,
        snapshot_revision: 1,
        matches: [
          {
            id: "match",
            player_a_id: pid,
            player_b_id: "rival-player",
            winner_id: pid,
          },
        ],
      },
    }),
  );
  const sent: any[] = [];
  await page.route(
    `**/v1/admin/seasons/${sid}/matchdays/${day}/correct`,
    (route) => {
      sent.push(route.request().postDataJSON());
      return route.fulfill(
        sent.length === 1
          ? {
              status: 409,
              json: {
                detail: { code: "RANKING_TIE_UNRESOLVED", ranking: review },
              },
            }
          : { json: { operation_id: "corrected" } },
      );
    },
  );
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Competición", exact: true }).click();
  await page
    .getByLabel("Antonio / Lucía", { exact: true })
    .selectOption("rival-player");
  await page
    .getByLabel("Motivo de corrección", { exact: true })
    .fill("Ganador transcrito incorrectamente");
  await page.getByRole("button", { name: "Corregir jornada" }).click();
  await expect(
    page.getByLabel("Posición 1 · división A", { exact: true }),
  ).toHaveValue("");
  await page
    .getByLabel("Posición 1 · división A", { exact: true })
    .selectOption(pid);
  await page
    .getByLabel("Posición 2 · división A", { exact: true })
    .selectOption("rival-player");
  await page
    .getByLabel(/Motivo del desempate/)
    .fill("Resultado externo acordado");
  await page.getByRole("button", { name: "Corregir jornada" }).click();
  await expect(page.getByRole("status")).toContainText("Cambio confirmado");
  expect(sent).toHaveLength(2);
  expect(sent[1]).toMatchObject({
    expected_snapshot_revision: 1,
    reason: "Ganador transcrito incorrectamente",
    results: [{ match_id: "match", winner_season_player_id: "rival-player" }],
    tie_resolution: {
      input_hash: review.input_hash,
      orders: [
        {
          player_ids: [pid, "rival-player"],
          reason: "Resultado externo acordado",
        },
      ],
    },
  });
});

test("daily neutral ties display a shared place while recorded legacy podium stays intact", async ({
  page,
}) => {
  await fixture(page);
  const data = structuredClone(overview);
  data.snapshots[0].standings = [
    ...data.snapshots[0].standings.slice(0, 2),
    ...data.snapshots[0].standings.slice(2).map((s) => ({
      ...s,
      position: 4,
      division: "B",
      division_position: 1,
      position_end: 5,
      tie_status: "unresolved_neutral",
    })),
  ];
  await page.route(`**/v1/read/seasons/${sid}/overview`, (route) =>
    route.fulfill({ json: data }),
  );
  await login(page);
  await navigate(page, "Liga");
  await page.getByRole("button", { name: "J3", exact: true }).click();
  await expect(page.getByText("1.º–2.º · empate", { exact: true })).toHaveCount(
    2,
  );
  await expect(page.getByText("POSICIÓN 1", { exact: true })).toBeVisible();
  await expect(page.getByText("POSICIÓN 2", { exact: true })).toBeVisible();
  await expect(page.getByText("POSICIÓN 4", { exact: true })).toHaveCount(0);
});
