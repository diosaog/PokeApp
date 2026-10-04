import { expect, test, type Page } from "@playwright/test";
import type { Model } from "../src/api/types";
import { fixture, login, navigate, sid, tid } from "./fixtures";

async function ownCounter(
  page: Page,
  mode?: "conflict" | "unknown" | "closed" | "outsider",
) {
  await fixture(page);
  await page.route("**/v1/me", (route) =>
    route.fulfill({
      json: {
        trainer_id: mode === "outsider" ? "outsider" : tid,
        display_name: "Antonio",
        slug: "anto",
        is_admin: false,
        globally_enabled: true,
      },
    }),
  );
  const current: Model<"WipeRevivalsRead"> = {
    season_id: sid,
    revived_after_wipe: 1,
    revision: 3,
    editable: mode !== "closed",
    blocking_reason: mode === "closed" ? "league_closed" : null,
    replayed: false,
  };
  const commands: {
    path: string;
    method: string;
    body: Model<"SetWipeRevivalsBody">;
    key: string | undefined;
  }[] = [];
  const reads: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "GET") reads.push(new URL(request.url()).pathname);
  });
  await page.route(`**/v1/seasons/${sid}/wipe-revivals`, (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") return route.fallback();
    if (request.method() === "GET") return route.fulfill({ json: current });
    commands.push({
      path: new URL(request.url()).pathname,
      method: request.method(),
      body: request.postDataJSON(),
      key: request.headers()["idempotency-key"],
    });
    if (commands.length === 1 && mode === "conflict") {
      current.revived_after_wipe = 2;
      current.revision++;
      return route.fulfill({
        status: 409,
        json: { detail: { code: "WIPE_REVISION_CONFLICT" } },
      });
    }
    if (commands.length === 1 || mode !== "unknown") {
      current.revived_after_wipe = request.postDataJSON().revived_after_wipe;
      current.revision++;
    }
    if (commands.length === 1 && mode === "unknown")
      return route.fulfill({
        status: 503,
        json: { detail: { code: "WIPE_STATE_UNAVAILABLE" } },
      });
    return route.fulfill({
      json: { ...current, replayed: mode === "unknown" },
    });
  });
  await login(page);
  await navigate(page, "Liga");
  return { commands, reads, current };
}

test("ordinary participant updates and corrects their own absolute count with narrow reads", async ({
  page,
}) => {
  const { commands, reads } = await ownCounter(page);
  await expect(
    page.getByRole("link", { name: "Administración", exact: true }),
  ).toHaveCount(0);
  const input = page.getByLabel("Cantidad de revividos tras wipe");
  await expect(input).toHaveValue("1");
  await expect(
    page.getByText(/Pendiente de observar las muertes del save/),
  ).toBeVisible();
  const before = reads.length;
  for (const [index, value] of [3, 0].entries()) {
    await input.fill(String(value));
    await page.getByRole("button", { name: "Actualizar revividos" }).click();
    await expect(page.getByText("Cambio confirmado.")).toBeVisible();
    await expect(input).toBeEnabled();
    await expect(input).toHaveValue(String(value));
    expect(commands[index]).toEqual({
      path: `/v1/seasons/${sid}/wipe-revivals`,
      method: "PUT",
      body: { revived_after_wipe: value, expected_revision: index + 3 },
      key: expect.any(String),
    });
  }
  expect(commands[1].key).not.toBe(commands[0].key);
  expect(
    reads
      .slice(before)
      .every((path) =>
        [
          `/v1/seasons/${sid}/wipe-revivals`,
          `/v1/read/seasons/${sid}/league`,
        ].includes(path),
      ),
  ).toBe(true);
  await expect(
    page.getByText(/Pendiente de observar las muertes del save/),
  ).toBeVisible();
});

test("invalid negative, fractional and overflowing values send no command", async ({
  page,
}) => {
  const { commands } = await ownCounter(page);
  const input = page.getByLabel("Cantidad de revividos tras wipe");
  for (const value of ["-1", "1.5", "2147483648", ""]) {
    await input.fill(value);
    await page.getByRole("button", { name: "Actualizar revividos" }).click();
    expect(commands).toHaveLength(0);
  }
});

test("stale count refreshes for review and the next explicit edit uses the new revision", async ({
  page,
}) => {
  const { commands } = await ownCounter(page, "conflict");
  const input = page.getByLabel("Cantidad de revividos tras wipe");
  await input.fill("3");
  await page.getByRole("button", { name: "Actualizar revividos" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Revisa la cantidad actual",
  );
  await expect(input).toHaveValue("2");
  await expect(input).toBeEnabled();
  expect(commands).toHaveLength(1);
  await input.fill("4");
  await page.getByRole("button", { name: "Actualizar revividos" }).click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  expect(commands[1].body).toEqual({
    revived_after_wipe: 4,
    expected_revision: 4,
  });
  expect(commands[1].key).not.toBe(commands[0].key);
});

test("mobile unknown outcome disables editing and retries only explicitly with the original request", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const { commands } = await ownCounter(page, "unknown");
  const input = page.getByLabel("Cantidad de revividos tras wipe");
  await input.fill("2");
  await page.getByRole("button", { name: "Actualizar revividos" }).click();
  await expect(
    page.getByRole("button", { name: "Reintentar la misma solicitud" }),
  ).toBeVisible();
  await expect(input).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Actualizar revividos" }),
  ).toBeDisabled();
  expect(commands).toHaveLength(1);
  await page
    .getByRole("button", { name: "Reintentar la misma solicitud" })
    .click();
  await expect(page.getByText("Cambio confirmado.")).toBeVisible();
  await expect(input).toHaveValue("2");
  await expect(input).toBeEnabled();
  expect(commands).toHaveLength(2);
  expect(commands[1]).toEqual(commands[0]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("frozen final day offers read-only current count without an ordinary command", async ({
  page,
}) => {
  const { commands } = await ownCounter(page, "closed");
  await expect(
    page.getByRole("heading", { name: "Revividos tras wipe" }),
  ).toBeVisible();
  await expect(
    page.getByText(/La última jornada ya está cerrada/),
  ).toBeVisible();
  await expect(page.getByText(/Cantidad registrada/)).toContainText("1");
  await expect(page.getByLabel("Cantidad de revividos tras wipe")).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("button", { name: "Actualizar revividos" }),
  ).toHaveCount(0);
  expect(commands).toHaveLength(0);
});

test("unrelated trainer has no own-counter request or editor", async ({
  page,
}) => {
  const { commands, reads } = await ownCounter(page, "outsider");
  await expect(
    page.getByRole("heading", { name: "Clasificación general" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Revividos tras wipe" }),
  ).toHaveCount(0);
  expect(reads).not.toContain(`/v1/seasons/${sid}/wipe-revivals`);
  expect(commands).toHaveLength(0);
});
