import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, day, sid, tid } from "./fixtures";

async function participant(
  page: Page,
  failure?: "conflict" | "unknown" | "closed",
) {
  await fixture(page);
  await page.route("**/v1/me", (route) =>
    route.fulfill({
      json: {
        trainer_id: tid,
        display_name: "Antonio",
        slug: "anto",
        is_admin: false,
        globally_enabled: true,
      },
    }),
  );
  let revision = 3,
    winner: string | null = null;
  const requests: { body: any; key: string | undefined }[] = [];
  const reads: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "GET") reads.push(new URL(r.url()).pathname);
  });
  await page.route(`**/v1/seasons/${sid}/matchdays/${day}`, (route) =>
    route.fulfill({
      json: {
        season_id: sid,
        matchday_id: day,
        current_matchday_id: day,
        state: failure === "closed" ? "closed" : "open",
        revision,
        results_revision: revision,
        snapshot_revision: failure === "closed" ? 1 : 0,
        matches: [
          {
            id: "third-party",
            player_a_id: "p3",
            player_b_id: "p4",
            winner_id: winner,
          },
        ],
      },
    }),
  );
  await page.route(
    `**/v1/seasons/${sid}/matchdays/${day}/results`,
    async (route) => {
      const r = route.request();
      requests.push({
        body: r.postDataJSON(),
        key: r.headers()["idempotency-key"],
      });
      if (requests.length === 1 && failure === "conflict") {
        revision++;
        return route.fulfill({
          status: 409,
          json: { detail: { code: "STALE_REVISION" } },
        });
      }
      winner = r.postDataJSON().results[0].winner_season_player_id;
      revision++;
      if (requests.length === 1 && failure === "unknown")
        return route.fulfill({
          status: 503,
          json: { detail: { code: "MATCHDAY_UNAVAILABLE" } },
        });
      return route.fulfill({
        json: {
          operation_id: "result-receipt",
          replayed: requests.length > 1 && failure === "unknown",
        },
      });
    },
  );
  await login(page);
  await navigate(page, "Liga");
  await page.getByRole("button", { name: "J4", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Registrar resultados" }),
  ).toBeVisible();
  return { requests, reads };
}

test("normal non-admin participant records, edits and clears another pair; narrow refetch", async ({
  page,
}) => {
  const { requests, reads } = await participant(page);
  await expect(
    page.getByRole("link", { name: "Administración", exact: true }),
  ).toHaveCount(0);
  const select = page.getByLabel("Ganador: Marcos / Elena", { exact: true });
  const before = reads.length;
  for (const [i, value] of ["p3", "p4", ""].entries()) {
    await select.selectOption(value);
    await page
      .getByRole("button", { name: "Guardar resultados", exact: true })
      .click();
    await expect(page.getByText("Cambio confirmado.")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Guardar resultados", exact: true }),
    ).toBeEnabled();
    expect(requests[i].body).toEqual({
      expected_results_revision: i + 3,
      results: [
        { match_id: "third-party", winner_season_player_id: value || null },
      ],
    });
    expect(requests[i].key).toBeTruthy();
  }
  expect(
    reads
      .slice(before)
      .every((path) =>
        [
          `/v1/seasons/${sid}/matchdays/${day}`,
          `/v1/read/seasons/${sid}/overview`,
          `/v1/read/seasons/${sid}/league`,
        ].includes(path),
      ),
  ).toBe(true);
});

test("409 stays visible with no automatic mutation retry; automatic read obtains new revision", async ({
  page,
}) => {
  const { requests } = await participant(page, "conflict");
  await page.getByLabel("Ganador: Marcos / Elena").selectOption("p3");
  await page
    .getByRole("button", { name: "Guardar resultados", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "La temporada ha cambiado" }),
  ).toBeVisible();
  expect(requests).toHaveLength(1);
  await expect(
    page.getByText(/Los datos cambiaron mientras editabas/),
  ).toBeVisible();
  await expect(page.getByLabel("Ganador: Marcos / Elena")).toHaveValue("");
  await page.getByLabel("Ganador: Marcos / Elena").selectOption("p4");
  await page
    .getByRole("button", { name: "Guardar resultados", exact: true })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(requests[1].body.expected_results_revision).toBe(4);
  expect(requests[1].key).not.toBe(requests[0].key);
});

test("unknown outcome retry retains original body/key and freezes inputs", async ({
  page,
}) => {
  const { requests } = await participant(page, "unknown");
  await page.getByLabel("Ganador: Marcos / Elena").selectOption("p3");
  await page
    .getByRole("button", { name: "Guardar resultados", exact: true })
    .click();
  await expect(page.getByLabel("Ganador: Marcos / Elena")).toBeDisabled();
  await page
    .getByRole("button", { name: "Reintentar la misma solicitud" })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[1]).toEqual(requests[0]);
});

test("concurrently closed day has no ordinary submission; Admin keeps only correction", async ({
  page,
}) => {
  const { requests } = await participant(page, "closed");
  await expect(
    page.getByRole("button", { name: "Guardar resultados", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText(/ya no admite cambios ordinarios/)).toBeVisible();
  expect(requests).toHaveLength(0);
});
