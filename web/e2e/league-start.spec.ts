// 079 in a real browser (real CSS): «Mi perfil» tabs and proportions, the
// always-visible «Abrir jornada 1», «Fijar Equipo» above the six and the
// provisional Team Preview. Synthetic fixtures only.
import { test, expect, type Page, type Route } from "@playwright/test";
import { fixture, login, navigate, sid, tid, players } from "./fixtures";

type Handler = (route: Route, path: string) => Promise<unknown> | undefined;
async function override(page: Page, handler: Handler) {
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") return route.fallback();
    const path = new URL(request.url()).pathname;
    const handled = handler(route, path);
    if (handled === undefined) return route.fallback();
    await handled;
  });
}
const json = (route: Route, value: unknown) =>
  route.fulfill({
    json: value,
    headers: {
      "Access-Control-Allow-Origin":
        route.request().headers()["origin"] || "http://127.0.0.1:5173",
      "Cache-Control": "no-store",
    },
  });
const noJ1 = {
  id: sid,
  name: "Liga Horizonte",
  status: "active",
  current_matchday_id: null,
};
const readiness = (changes: Record<string, unknown> = {}) => ({
  season_id: sid,
  state: "unprepared",
  structure: "all_vs_all",
  matchday: null,
  next_number: 1,
  can_prepare: true,
  can_open: false,
  can_operate: true,
  reasons: [],
  participants: [
    {
      season_player_id: players[0].id,
      trainer_id: tid,
      display_name: "Antonio",
      reasons: ["death_history_baseline_required"],
      self_confirmable: true,
    },
    {
      season_player_id: players[1].id,
      trainer_id: players[1].trainer_id,
      display_name: "Lucía",
      reasons: ["save_missing", "death_history_baseline_required"],
      self_confirmable: false,
    },
    {
      season_player_id: players[2].id,
      trainer_id: players[2].trainer_id,
      display_name: "Marcos",
      reasons: ["badges_missing"],
      self_confirmable: false,
    },
    {
      season_player_id: players[3].id,
      trainer_id: players[3].trainer_id,
      display_name: "Elena",
      reasons: [],
      self_confirmable: false,
    },
  ],
  ...changes,
});
const ownDeaths = {
  season_id: sid,
  season_player_id: players[0].id,
  trainer_id: tid,
  revision: 1,
  known: false,
  blocking_reason: "death_history_baseline_required",
  actual_deaths: null,
  wipe_deaths: null,
  segment_deaths: null,
  dead_box_number: 7,
  source_sha256: "a".repeat(64),
  confirmed_at: null,
  current_matchday_id: null,
  can_confirm: true,
  confirm_blocker: null,
  proposed: { actual_deaths: 3, wipe_deaths: 0, segment_deaths: 3 },
  replayed: false,
};

async function noFirstMatchday(page: Page, ready = readiness()) {
  const commands: { method: string; path: string; body: unknown }[] = [];
  await fixture(page);
  await override(page, (route, path) => {
    const method = route.request().method();
    if (path.endsWith("/league/readiness")) return json(route, ready);
    if (path.endsWith("/death-history") && method === "GET")
      return json(route, ownDeaths);
    if (path.endsWith("/league/first-matchday")) {
      commands.push({ method, path, body: null });
      return json(route, {
        season_id: sid,
        matchday_id: "j1",
        number: 1,
        status: "scheduled",
        revision: 0,
        created: true,
      });
    }
    if (path.endsWith("/team-lock")) {
      commands.push({ method, path, body: route.request().postDataJSON() });
      return json(route, { id: "lock" });
    }
    if (path.endsWith("/read/seasons"))
      return json(route, { items: [noJ1], next_offset: null });
    if (path.endsWith("/overview")) return undefined; // the fixture's, J4 open: irrelevant here
    return undefined;
  });
  return commands;
}

for (const [width, height] of [
  [1280, 800],
  [1440, 900],
  [390, 844],
] as const) {
  test(`«Mi perfil» is a balanced dialog whose tabs really replace the content (${width}px)`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height });
    await fixture(page);
    await override(page, (route, path) => {
      if (path === "/v1/auth/account-capabilities")
        return json(route, {
          enabled: true,
          registration_enabled: false,
          renewal_enabled: true,
        });
      if (path.startsWith("/v1/accounts/"))
        return json(route, {
          trainer_id: tid,
          display_name: "Antonio",
          photo_url: null,
          revision: 0,
        });
      return undefined;
    });
    await login(page);
    const menu = page.getByRole("button", { name: "Abrir navegación" });
    if (await menu.isVisible()) await menu.click();
    await page.getByRole("button", { name: "Mi perfil", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Mi perfil" });
    await expect(dialog).toBeVisible();
    const box = (await dialog.boundingBox())!;
    if (width >= 1280) {
      // Medium width, never the old tall 560px column.
      expect(box.width).toBeGreaterThanOrEqual(820);
      expect(box.height).toBeLessThanOrEqual(height * 0.82);
    } else expect(box.width).toBeLessThanOrEqual(width);
    const name = dialog.getByLabel("Nombre de entrenador"),
      pin = dialog.getByLabel("PIN actual"),
      sound = dialog.getByRole("group", { name: "Sonidos" });
    await expect(name).toBeVisible();
    await expect(pin).toBeHidden();
    await expect(sound).toBeHidden();
    await page.screenshot({ path: info.outputPath(`perfil-${width}.png`) });
    await dialog.getByRole("tab", { name: "Seguridad" }).click();
    await expect(pin).toBeVisible();
    await expect(name).toBeHidden();
    await expect(sound).toBeHidden();
    await expect(
      dialog.getByText(/se cierran tus sesiones anteriores/),
    ).toBeVisible();
    await page.screenshot({ path: info.outputPath(`seguridad-${width}.png`) });
    await dialog.getByRole("tab", { name: "Preferencias" }).click();
    await expect(sound).toBeVisible();
    await expect(dialog.getByRole("slider")).toBeVisible();
    await expect(
      dialog.getByRole("group", { name: "Animaciones" }),
    ).toBeVisible();
    await expect(name).toBeHidden();
    await expect(pin).toBeHidden();
    await page.screenshot({
      path: info.outputPath(`preferencias-${width}.png`),
    });
    // Keyboard: arrows move between tabs and focus follows.
    await dialog.getByRole("tab", { name: "Preferencias" }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(dialog.getByRole("tab", { name: "Perfil" })).toBeFocused();
    await expect(name).toBeVisible();
    await expect(
      dialog.getByRole("link", { name: /Ver mi ficha de entrenador/ }),
    ).toBeVisible();
    await dialog.getByRole("button", { name: "Cerrar" }).click();
    await expect(dialog).toBeHidden();
  });
}

test("Liga › General keeps «Abrir jornada 1» visible without a J1, with each exact reason", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await noFirstMatchday(page);
  await login(page);
  await navigate(page, "Liga");
  const open = page.getByRole("button", { name: "Abrir jornada 1" });
  await expect(open).toBeVisible();
  await expect(open).toBeDisabled();
  const blockers = page.locator("#matchday-blockers");
  await expect(blockers).toContainText("Tú: confirma tu historial de muertes.");
  await expect(blockers).toContainText(
    "Lucía: falta registrar su partida oficial desde PokeApp Launcher",
  );
  await expect(blockers).toContainText(
    "Marcos: necesita las dos primeras medallas para la J1.",
  );
  await expect(blockers).not.toContainText("Elena");
  await expect(blockers).not.toContainText("Administración");
  await expect(
    blockers.getByRole("button", { name: "Confirmar mi historial" }),
  ).toBeVisible();
  await blockers.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: info.outputPath("liga-sin-j1.png"),
    fullPage: true,
  });
});

test("«Fijar Equipo» sits centred above the six and fixes them for a J1 it prepares", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  const commands = await noFirstMatchday(page);
  await login(page);
  await page.goto(`/entrenadores/${tid}`);
  const panel = page.locator(".party-panel");
  const button = panel.getByRole("button", { name: "Fijar Equipo" });
  await expect(button).toBeVisible();
  await expect(
    panel.getByRole("button", { name: "Generar Poképaste" }),
  ).toBeVisible();
  const slots = panel.locator(".party-slots > *");
  await expect(slots).toHaveCount(6);
  const [third, fourth, b] = [
    (await slots.nth(2).boundingBox())!,
    (await slots.nth(3).boundingBox())!,
    (await button.boundingBox())!,
  ];
  const gap = (third.x + third.width + fourth.x) / 2;
  expect(Math.abs(b.x + b.width / 2 - gap)).toBeLessThanOrEqual(6);
  // Above the cards, never over a sprite, name or level.
  expect(b.y + b.height).toBeLessThanOrEqual(Math.min(third.y, fourth.y));
  await panel.screenshot({ path: info.outputPath("equipo-fijar.png") });
  await button.click();
  const dialog = page.getByRole("dialog", { name: "Fijar Equipo" });
  await expect(dialog).toContainText("Jornada 1");
  await expect(
    dialog
      .getByRole("list", { name: "Equipo que se fijará" })
      .getByRole("listitem"),
  ).toHaveCount(6);
  await page.screenshot({ path: info.outputPath("fijar-equipo-dialog.png") });
  expect(commands).toEqual([]);
  await dialog
    .getByRole("button", { name: "Confirmar y fijar equipo" })
    .click();
  await expect(dialog).toBeHidden();
  expect(commands.map((c) => [c.method, c.path])).toEqual([
    ["POST", `/v1/seasons/${sid}/league/first-matchday`],
    ["PUT", `/v1/seasons/${sid}/matchdays/j1/team-lock`],
  ]);
  expect(commands[1].body).toEqual({ save_file_id: "save" });
  await expect(page.getByText(/Equipo fijado para la J1/)).toBeVisible();
});

test("Team Preview works with no matchday and labels current parties provisional", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await noFirstMatchday(page);
  const mon = {
    species: "Lucario",
    nickname: "Aura",
    level: 42,
    types: ["Lucha"],
    item: "",
    moves: [{ name: "Esfera aural", pp: 20 }],
    is_shiny: false,
    status_flags: [],
  };
  await override(page, (route, path) =>
    path.endsWith("/team-preview")
      ? json(route, {
          season: noJ1,
          day: null,
          mode: "spectator",
          trainers: players.map(({ trainer_id, display_name, status }) => ({
            trainer_id,
            display_name,
            status,
          })),
          teams: [
            {
              trainer_id: tid,
              visibility: "public",
              lock: null,
              provisional: { source: "league", team: Array(6).fill(mon) },
              unavailable_reason: null,
            },
            {
              trainer_id: players[1].trainer_id,
              visibility: "public",
              lock: null,
              provisional: null,
              unavailable_reason: "no_synced_save",
            },
          ],
        })
      : undefined,
  );
  await login(page);
  await page.goto("/battle");
  await expect(
    page.getByText("Sin jornada preparada · equipos actuales"),
  ).toBeVisible();
  await expect(
    page.getByText("Provisional · equipo actual sin fijar"),
  ).toBeVisible();
  await expect(
    page.getByText("Aún no ha sincronizado ninguna partida."),
  ).toBeVisible();
  await expect(page.getByText("Team Lock oficial")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Fijar Equipo" }),
  ).toBeEnabled();
  await page.screenshot({
    path: info.outputPath("team-preview-provisional.png"),
    fullPage: true,
  });
});
