import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, overview, players } from "./fixtures";

// Spectator mode must show both full teams (6 vs 6) at once on a desktop
// screen: sprite, nickname, species, level, item and four moves with PP for
// every Pokémon, with no page or per-team scroll. Synthetic data only.
type Mon = {
  species: string;
  nickname: string | null;
  level: number;
  types: string[];
  item: string | null;
  moves: { name: string; pp: number }[];
};
const mon = (
  species: string,
  nickname: string | null,
  level: number,
  types: string[],
  item: string | null,
  moves: [string, number][],
): Mon => ({
  species,
  nickname,
  level,
  types,
  item,
  moves: moves.map(([name, pp]) => ({ name, pp })),
});
const teamA = [
  mon("Garchomp", "Tiburón", 78, ["Dragon", "Ground"], "Choice Scarf", [
    ["Earthquake", 16],
    ["Outrage", 16],
    ["Stone Edge", 8],
    ["Fire Fang", 24],
  ]),
  mon("Gyarados", "Leviatán", 77, ["Water", "Flying"], "Leftovers", [
    ["Waterfall", 24],
    ["Dragon Dance", 32],
    ["Ice Fang", 24],
    ["Bounce", 8],
  ]),
  mon("Gardevoir", "Hada", 76, ["Psychic", "Fairy"], "Life Orb", [
    ["Moonblast", 24],
    ["Psychic", 16],
    ["Shadow Ball", 24],
    ["Calm Mind", 32],
  ]),
  mon("Ferrothorn", "Pinchos", 75, ["Grass", "Steel"], "Rocky Helmet", [
    ["Leech Seed", 16],
    ["Gyro Ball", 8],
    ["Power Whip", 16],
    ["Stealth Rock", 32],
  ]),
  mon("Infernape", "Simiofuego", 78, ["Fire", "Fighting"], "Focus Sash", [
    ["Close Combat", 8],
    ["Flare Blitz", 24],
    ["U-turn", 32],
    ["Mach Punch", 48],
  ]),
  mon("Togekiss", null, 74, ["Fairy", "Flying"], "Sitrus Berry", [
    ["Air Slash", 24],
    ["Dazzling Gleam", 16],
    ["Roost", 16],
    ["Thunder Wave", 32],
  ]),
];
const teamB = [
  mon("Tyranitar", "Godzilla", 80, ["Rock", "Dark"], "Assault Vest", [
    ["Stone Edge", 8],
    ["Crunch", 24],
    ["Earthquake", 16],
    ["Ice Punch", 24],
  ]),
  mon("Metagross", null, 79, ["Steel", "Psychic"], "Expert Belt", [
    ["Meteor Mash", 16],
    ["Zen Headbutt", 24],
    ["Bullet Punch", 48],
    ["Hammer Arm", 16],
  ]),
  mon("Volcarona", "Polilla", 77, ["Bug", "Fire"], "Leftovers", [
    ["Quiver Dance", 32],
    ["Fiery Dance", 16],
    ["Bug Buzz", 16],
    ["Giga Drain", 16],
  ]),
  mon("Starmie", "Estrellita", 76, ["Water", "Psychic"], "Choice Specs", [
    ["Hydro Pump", 8],
    ["Psychic", 16],
    ["Ice Beam", 16],
    ["Thunderbolt", 24],
  ]),
  mon("Excadrill", "Topo", 78, ["Ground", "Steel"], "Choice Band", [
    ["Earthquake", 16],
    ["Iron Head", 24],
    ["Rock Slide", 16],
    ["Rapid Spin", 64],
  ]),
  mon("Sylveon", null, 75, ["Fairy"], null, [
    ["Hyper Voice", 16],
    ["Wish", 16],
    ["Protect", 16],
    ["Light Screen", 48],
  ]),
];

async function spectatorFixture(page: Page) {
  await fixture(page);
  await page.route("http://127.0.0.1:8000/**/team-preview*", async (route) => {
    const request = route.request();
    if (request.method() !== "GET") return route.fallback();
    const params = new URL(request.url()).searchParams;
    const mode = params.get("mode") || "spectator";
    const first = params.get("trainer_id") || players[0].trainer_id;
    const second =
      params.get("second_trainer_id") ||
      players.find((p) => p.trainer_id !== first)!.trainer_id;
    await route.fulfill({
      headers: {
        "Access-Control-Allow-Origin":
          request.headers()["origin"] || "http://127.0.0.1:5173",
      },
      json: {
        season: overview.season,
        day: overview.days[0],
        mode,
        trainers: players.map(({ trainer_id, display_name, status }) => ({
          trainer_id,
          display_name,
          status,
        })),
        teams: (mode === "spectator" ? [first, second] : [first]).map(
          (id, index) => ({
            trainer_id: id,
            visibility: "public",
            provisional: null,
            unavailable_reason: null,
            lock: {
              locked_at: "2026-11-09T10:00:00Z",
              is_late: false,
              timing_status: "on_time",
              team: index === 0 ? teamA : teamB,
            },
          }),
        ),
      },
    });
  });
}

// Everything a spectator must read on each card: nickname, species, level,
// item and the four moves with their PP, for both teams and in order.
async function expectFullTeams(page: Page) {
  for (const [side, team] of [
    [".matchup-left", teamA],
    [".matchup-right", teamB],
  ] as const) {
    const cards = page.locator(`${side} .battle-pokemon`);
    await expect(cards).toHaveCount(6);
    for (const [index, pokemon] of team.entries()) {
      const card = cards.nth(index);
      await expect(card.locator(".matchup-sprite img")).toBeVisible();
      await expect(card.locator(".matchup-species")).toContainText(
        `Nv. ${pokemon.level}`,
      );
      await expect(card.locator(".held-item")).toBeVisible();
      if (!pokemon.item)
        await expect(card.locator(".held-item")).toHaveText("Sin objeto");
      await expect(card.locator(".move-button small")).toHaveText(
        pokemon.moves.map(({ pp }) => `${pp} PP`),
      );
      for (const pp of await card.locator(".move-button small").all())
        await expect(pp).toBeVisible();
    }
  }
  await expect(page.locator(".matchup-left strong").first()).toHaveText(
    "Tiburón",
  );
  await expect(
    page.locator(".matchup-left .matchup-species").first(),
  ).toHaveText("Garchomp · Nv. 78");
  await expect(page.locator(".matchup-left .held-item").first()).toHaveText(
    "Pañuelo Elección",
  );
  await expect(
    page.locator(".matchup-right .battle-pokemon").nth(4).locator(".move-name"),
  ).toHaveText(["Terremoto", "Cabeza de Hierro", "Avalancha", "Giro Rápido"]);
  // Spectator reads are public: no private field is ever drawn.
  await expect(page.locator(".spectator-matchup .battle-private")).toHaveCount(
    0,
  );
  await expect(page.locator(".spectator-matchup .battle-values")).toHaveCount(
    0,
  );
}

async function measure(page: Page) {
  return page.evaluate(() => {
    const cards = [
      ...document.querySelectorAll(".spectator-matchup .battle-pokemon"),
    ].map((card) => card.getBoundingClientRect());
    const scroller = document.scrollingElement!;
    // Any text that does not fit its box (cut, ellipsis or spilling out).
    const clipped = [
      ...document.querySelectorAll(
        ".spectator-matchup .battle-pokemon :is(strong, .matchup-species, .held-item, .move-name, small)",
      ),
    ]
      .filter(
        (el) =>
          el.scrollWidth > el.clientWidth + 1 ||
          el.scrollHeight > el.clientHeight + 1,
      )
      .map(
        (el) =>
          `${el.className} "${el.textContent}" ${el.scrollWidth}x${el.scrollHeight} in ${el.clientWidth}x${el.clientHeight}`,
      );
    // Two cards of the same team must never overlap.
    const overlaps = cards.filter((a, i) =>
      cards.some(
        (b, j) =>
          i !== j &&
          a.left < b.right - 1 &&
          b.left < a.right - 1 &&
          a.top < b.bottom - 1 &&
          b.top < a.bottom - 1,
      ),
    ).length;
    return {
      bottom: Math.max(...cards.map((r) => r.bottom)),
      right: Math.max(...cards.map((r) => r.right)),
      top: Math.min(...cards.map((r) => r.top)),
      innerHeight,
      innerWidth,
      scrollHeight: scroller.scrollHeight,
      scrollWidth: scroller.scrollWidth,
      clipped,
      overlaps,
    };
  });
}

async function openSpectator(
  page: Page,
  size: { width: number; height: number },
) {
  await page.setViewportSize(size);
  await spectatorFixture(page);
  await login(page);
  await navigate(page, "Batallas");
  await expect(page.locator(".spectator-matchup .battle-pokemon")).toHaveCount(
    12,
  );
  await expect(page.locator(".spectator-matchup .move-button")).toHaveCount(48);
  // Every sprite settles before measuring.
  await page.waitForLoadState("networkidle");
}

for (const size of [
  { width: 1650, height: 900 },
  { width: 1920, height: 1080 },
  { width: 1366, height: 768 },
]) {
  test(`spectator shows both full teams without scroll at ${size.width}×${size.height}`, async ({
    page,
  }, info) => {
    await openSpectator(page, size);
    await expectFullTeams(page);
    await page.screenshot({
      path: info.outputPath(`spectator-${size.width}x${size.height}.png`),
    });
    const layout = await measure(page);
    expect(layout.top).toBeGreaterThanOrEqual(0);
    expect(layout.bottom).toBeLessThanOrEqual(layout.innerHeight);
    expect(layout.right).toBeLessThanOrEqual(layout.innerWidth);
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth + 1);
    expect(layout.scrollHeight).toBeLessThanOrEqual(layout.innerHeight + 1);
    expect(layout.clipped).toEqual([]);
    expect(layout.overlaps).toBe(0);
  });
}

// Smaller screens may scroll the page, never sideways, never inside a team,
// and never cut a name, item, move or PP.
for (const size of [
  { width: 1024, height: 768 },
  { width: 390, height: 844 },
]) {
  test(`spectator adapts without clipping at ${size.width}×${size.height}`, async ({
    page,
  }, info) => {
    await openSpectator(page, size);
    await expectFullTeams(page);
    await page.screenshot({
      path: info.outputPath(`spectator-${size.width}x${size.height}.png`),
      fullPage: true,
    });
    const layout = await measure(page);
    expect(layout.right).toBeLessThanOrEqual(layout.innerWidth);
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth + 1);
    expect(layout.clipped).toEqual([]);
    expect(layout.overlaps).toBe(0);
    const roster = await page
      .locator(".matchup-roster")
      .evaluateAll((lists) =>
        lists.map((l) => l.scrollHeight - l.clientHeight),
      );
    expect(roster.every((extra) => extra <= 1)).toBe(true);
  });
}

test("a move of the last row opens over the team without moving the page", async ({
  page,
}, info) => {
  await openSpectator(page, { width: 1650, height: 900 });
  const move = page.getByRole("button", { name: "Ver Pantalla de Luz" });
  await move.click();
  const details = page.locator(".move-expansion");
  await expect(details).toContainText("Referencia Pokémon X/Y");
  await page.screenshot({
    path: info.outputPath("spectator-move-open.png"),
    animations: "disabled",
  });
  // The details paint above the neighbouring cards.
  const top = await details.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const hit = document.elementFromPoint(
      r.left + r.width / 2,
      r.top + r.height / 2,
    );
    return !!hit && el.contains(hit);
  });
  expect(top).toBe(true);
  const box = (await details.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(900);
  expect(box.x + box.width).toBeLessThanOrEqual(1650);
  const layout = await measure(page);
  expect(layout.scrollHeight).toBeLessThanOrEqual(layout.innerHeight + 1);
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth + 1);
  await page.keyboard.press("Escape");
  await expect(details).toHaveCount(0);
});
