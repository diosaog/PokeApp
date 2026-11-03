import { expect, test, type Page } from "@playwright/test";
import type { Model } from "../src/api/types";
import { fixture, login, navigate, sid, tid } from "./fixtures";

// The own «Revividos tras wipe» counter lives under the licence card of the
// signed-in trainer's profile: − value + Actualizar, sent only on Actualizar.
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
  return { commands, reads, current };
}

async function openOwnProfile(page: Page) {
  await page.getByRole("link", { name: "Ver mi equipo y cajas →" }).click();
  const counter = page.locator(".profile-licence-column .wipe-revivals");
  await expect(counter).toBeVisible();
  return {
    counter,
    value: counter.getByLabel("Cantidad"),
    plus: counter.getByRole("button", { name: "Sumar un revivido" }),
    minus: counter.getByRole("button", { name: "Restar un revivido" }),
    update: counter.getByRole("button", { name: "Actualizar" }),
  };
}

test("the own counter sits under the licence and sends the absolute count only on Actualizar", async ({
  page,
}) => {
  const { commands } = await ownCounter(page);
  const { value, plus, minus, update } = await openOwnProfile(page);
  await expect(value).toHaveText("1");
  await expect(update).toBeDisabled();
  await plus.click();
  await plus.click();
  await expect(value).toHaveText("3");
  expect(commands).toHaveLength(0);
  await update.click();
  await expect(value).toHaveText("3");
  await expect(update).toBeDisabled();
  expect(commands[0]).toEqual({
    path: `/v1/seasons/${sid}/wipe-revivals`,
    method: "PUT",
    body: { revived_after_wipe: 3, expected_revision: 3 },
    key: expect.any(String),
  });
  for (let i = 0; i < 3; i++) await minus.click();
  await expect(value).toHaveText("0");
  await expect(minus).toBeDisabled();
  await update.click();
  await expect(minus).toBeDisabled();
  expect(commands[1].body).toEqual({
    revived_after_wipe: 0,
    expected_revision: 4,
  });
  expect(commands[1].key).not.toBe(commands[0].key);
});

test("no command without a change, and never below zero", async ({ page }) => {
  const { commands } = await ownCounter(page);
  const { value, plus, minus, update } = await openOwnProfile(page);
  await plus.click();
  await minus.click();
  await expect(update).toBeDisabled();
  await minus.click();
  await expect(value).toHaveText("0");
  await expect(minus).toBeDisabled();
  expect(commands).toHaveLength(0);
});

test("a stale count is shown again for review and the next edit uses the new revision", async ({
  page,
}) => {
  const { commands } = await ownCounter(page, "conflict");
  const { value, plus, update } = await openOwnProfile(page);
  await plus.click();
  await plus.click();
  await update.click();
  await expect(page.locator("#main").getByRole("alert")).toContainText(
    "Revisa la cantidad actual",
  );
  await expect(value).toHaveText("2");
  expect(commands).toHaveLength(1);
  await plus.click();
  await update.click();
  await expect(value).toHaveText("3");
  expect(commands[1].body).toEqual({
    revived_after_wipe: 3,
    expected_revision: 4,
  });
  expect(commands[1].key).not.toBe(commands[0].key);
});

test("mobile unknown outcome locks the control and retries only the original request", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const { commands } = await ownCounter(page, "unknown");
  const { value, plus, minus, update } = await openOwnProfile(page);
  await plus.click();
  await update.click();
  const retry = page
    .locator(".wipe-revivals")
    .getByRole("button", { name: "Reintentar la misma solicitud" });
  await expect(retry).toBeVisible();
  await expect(plus).toBeDisabled();
  await expect(minus).toBeDisabled();
  await expect(update).toBeDisabled();
  expect(commands).toHaveLength(1);
  await retry.click();
  await expect(value).toHaveText("2");
  await expect(plus).toBeEnabled();
  expect(commands).toHaveLength(2);
  expect(commands[1]).toEqual(commands[0]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
});

test("a closed League keeps the count read-only without any command", async ({
  page,
}) => {
  const { commands } = await ownCounter(page, "closed");
  await page.getByRole("link", { name: "Ver mi equipo y cajas →" }).click();
  const counter = page.locator(".wipe-revivals");
  await expect(
    counter.getByText(/La última jornada ya está cerrada/),
  ).toBeVisible();
  await expect(counter.getByText(/Cantidad:/)).toContainText("1");
  await expect(
    counter.getByRole("button", { name: "Sumar un revivido" }),
  ).toHaveCount(0);
  expect(commands).toHaveLength(0);
});

test("the League page no longer carries the counter, and an outsider never reads one", async ({
  page,
}) => {
  const { commands, reads } = await ownCounter(page, "outsider");
  await navigate(page, "Liga");
  await expect(
    page.getByRole("heading", { name: "Clasificación general" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Revividos tras wipe" }),
  ).toHaveCount(0);
  expect(reads).not.toContain(`/v1/seasons/${sid}/wipe-revivals`);
  expect(commands).toHaveLength(0);
});
