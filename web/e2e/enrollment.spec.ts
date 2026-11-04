// Synthetic API fixtures only; actual CSS, modal and refresh/retry behavior.
import { test, expect, type Route } from "@playwright/test";
import { fixture, login, navigate, sid } from "./fixtures";

const path = `/v1/admin/seasons/${sid}/enrollment`;
function preview(hash = "a".repeat(64)) {
  return {
    season_id: sid,
    season_name: "ChampionsLocke",
    eligible_trainers: [{ id: "080-new", display_name: "Elena" }],
    first_matchday_number: 2,
    matchday_id: "day2",
    matchday_status: "open",
    closed_matchdays: 1,
    initial_coins: 10,
    initial_points: "0",
    new_matchups: 5,
    preview_hash: hash,
  };
}
const reply = (route: Route, value: unknown, status = 200) =>
  route.fulfill({
    status,
    json: value,
    headers: {
      "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
      "Access-Control-Allow-Headers":
        "authorization,content-type,idempotency-key",
      "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
      "Cache-Control": "no-store",
    },
  });
for (const width of [1440, 390]) {
  test(`admin enrollment summary and confirmation at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await fixture(page);
    const requests: { body: unknown; key?: string }[] = [];
    let enrolled = false;
    await page.route(`**${path}`, async (route) => {
      if (route.request().method() === "OPTIONS") return reply(route, {});
      if (route.request().method() === "GET")
        return reply(route, {
          ...preview(),
          eligible_trainers: enrolled ? [] : preview().eligible_trainers,
        });
      requests.push({
        body: route.request().postDataJSON(),
        key: route.request().headers()["idempotency-key"],
      });
      enrolled = true;
      return reply(route, { replayed: false });
    });
    await login(page);
    await navigate(page, "Administración");
    await page.getByRole("tab", { name: "Entrenadores", exact: true }).click();
    await page
      .getByLabel("Entrenador", { exact: true })
      .selectOption("080-new");
    await page.getByRole("button", { name: "Revisar incorporación" }).click();
    const dialog = page.getByRole("dialog", {
      name: "Incorporar entrenador a ChampionsLocke",
    });
    for (const text of [
      "Puntos iniciales: 0.",
      "Monedas iniciales: 10.",
      "Jornadas completadas: 1.",
      "Participará desde: J2 (en curso).",
      "Nuevos enfrentamientos: 5.",
    ])
      await expect(dialog).toContainText(text);
    expect(requests).toEqual([]);
    const bounds = await dialog.boundingBox();
    expect(bounds!.width).toBeLessThanOrEqual(width);
    await page.screenshot({ path: info.outputPath(`enrollment-${width}.png`) });
    await dialog
      .getByRole("button", { name: "Confirmar incorporación" })
      .click();
    await expect(dialog).toBeHidden();
    expect(requests).toHaveLength(1);
    expect(requests[0].body).toEqual({
      trainer_id: "080-new",
      preview_hash: "a".repeat(64),
    });
    expect(requests[0].key).toBeTruthy();
    await expect(
      page.getByText("No hay cuentas disponibles.", { exact: false }),
    ).toBeVisible();
  });
}
test("a stale confirmation refreshes the preview and requires a new explicit review", async ({
  page,
}) => {
  await fixture(page);
  let changed = false;
  let attempts = 0;
  await page.route(`**${path}`, async (route) => {
    if (route.request().method() === "OPTIONS") return reply(route, {});
    if (route.request().method() === "GET")
      return reply(
        route,
        changed
          ? {
              ...preview("b".repeat(64)),
              initial_coins: 20,
              first_matchday_number: 3,
            }
          : preview(),
      );
    attempts++;
    changed = true;
    return reply(route, { detail: { code: "ENROLLMENT_PREVIEW_STALE" } }, 409);
  });
  await login(page);
  await navigate(page, "Administración");
  await page.getByRole("tab", { name: "Entrenadores", exact: true }).click();
  await page.getByLabel("Entrenador", { exact: true }).selectOption("080-new");
  await page.getByRole("button", { name: "Revisar incorporación" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Confirmar incorporación" }).click();
  await expect(
    dialog.getByRole("button", { name: "Confirmar incorporación" }),
  ).toBeDisabled();
  await expect(dialog).toContainText("Monedas iniciales: 10.");
  expect(attempts).toBe(1);
  await dialog.getByRole("button", { name: "Cerrar", exact: true }).click();
  await page.getByRole("button", { name: "Revisar incorporación" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Monedas iniciales: 20.",
  );
});
